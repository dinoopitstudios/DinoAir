from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.integration.events import EventHandler, EventType
from pseudocode_translator.models.base_model import (
    OutputLanguage,
    TranslationResult as ModelTranslationResult,
)
from pseudocode_translator.streaming.pipeline import StreamingPipeline
from pseudocode_translator.translator import TranslationManager


def _collecting_handler(events_out):
    def _handle(event):
        events_out.append(event)

    return EventHandler(_handle)


def _events_of(events, *types):
    return [e for e in events if e.type in types]


def test_translation_events_emitted_on_success():
    # Configure manager to use deterministic mock and disable plugins
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    manager = TranslationManager(cfg)
    try:
        # Register event collector (keep strong ref for weakref-based dispatcher)
        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        instruction = "Define a function add(a, b) that returns their sum."
        result = manager.translate_pseudocode(instruction)

        assert result.success is True

        # Capture translation lifecycle events in order
        lifecycle = _events_of(
            events,
            EventType.TRANSLATION_STARTED,
            EventType.TRANSLATION_COMPLETED,
            EventType.TRANSLATION_FAILED,
        )
        # Must have STARTED then COMPLETED (no FAILED expected on success path)
        types_in_order = [e.type for e in lifecycle]
        assert EventType.TRANSLATION_STARTED in types_in_order
        assert EventType.TRANSLATION_COMPLETED in types_in_order
        assert types_in_order.index(EventType.TRANSLATION_STARTED) < types_in_order.index(
            EventType.TRANSLATION_COMPLETED
        )

        # Completed payload should include success True
        completed = next(e for e in lifecycle if e.type == EventType.TRANSLATION_COMPLETED)
        assert completed.data.get("success") is True
    finally:
        manager.shutdown()


def test_model_changed_event_emitted():
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    manager = TranslationManager(cfg)
    try:
        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        # Switch model (to mock again is fine; event should still be emitted)
        manager.switch_model("mock")

        model_events = _events_of(events, EventType.MODEL_CHANGED)
        assert len(model_events) >= 1
        assert model_events[-1].data.get("model") == "mock"
    finally:
        manager.shutdown()


def test_stream_events_emitted(monkeypatch):
    # Deterministic, hermetic translation for streaming path
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    manager = TranslationManager(cfg)
    events = []
    handler = _collecting_handler(events)
    manager.get_event_dispatcher().register(handler)

    # Monkeypatch translate_text_block to avoid network and be deterministic
    def fake_translate_text_block(self, text: str, context=None, config=None):
        return ModelTranslationResult(
            success=True,
            code="def add(a, b):\n    return a + b\n",
            language=OutputLanguage.PYTHON,
            confidence=1.0,
            errors=[],
            warnings=[],
            metadata={"mocked": True},
        )

    monkeypatch.setattr(
        TranslationManager,
        "translate_text_block",
        fake_translate_text_block,
        raising=True,
    )

    # Use StreamingPipeline directly and inject our manager so it uses the same dispatcher
    pipeline = StreamingPipeline(cfg)
    pipeline.translator = manager  # share dispatcher via manager.get_event_dispatcher()

    input_text = "Define a function add(a, b) that returns their sum."

    # Execute streaming
    results = list(pipeline.stream_translate(input_text))
    assert len(results) >= 1

    # Verify emissions: STREAM_STARTED, at least one STREAM_CHUNK_PROCESSED, STREAM_COMPLETED
    started = any(e.type == EventType.STREAM_STARTED for e in events)
    completed = any(e.type == EventType.STREAM_COMPLETED for e in events)
    chunk_events = [e for e in events if e.type == EventType.STREAM_CHUNK_PROCESSED]

    assert started is True
    assert completed is True
    assert len(chunk_events) >= 1

    # Per-chunk event should include a boolean success
    assert all(isinstance(e.data.get("success"), bool) for e in chunk_events)
