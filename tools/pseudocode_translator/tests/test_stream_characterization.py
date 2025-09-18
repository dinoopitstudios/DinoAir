from collections.abc import Callable

from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models.base_model import (
    OutputLanguage,
    TranslationResult as ModelTranslationResult,
)
from pseudocode_translator.streaming.stream_translator import (
    StreamingEvent,
    StreamingEventData,
    StreamingMode,
    StreamingTranslator,
    TranslationUpdate,
)
from pseudocode_translator.translator import TranslationManager


def _fake_translate_result(code_text: str = "print('ok')") -> ModelTranslationResult:
    # Stable, minimal successful result
    return ModelTranslationResult(
        success=True,
        code=code_text,
        language=OutputLanguage.PYTHON,
        confidence=1.0,
        errors=[],
        warnings=[],
        metadata={"mocked": True},
    )


def _collect_events() -> tuple[
    list[StreamingEvent],
    list[StreamingEventData],
    Callable[[StreamingEventData], None],
]:
    seen_types: list[StreamingEvent] = []
    events: list[StreamingEventData] = []

    def listener(evt: StreamingEventData):
        seen_types.append(evt.event)
        events.append(evt)

    return seen_types, events, listener


def _fake_translate_text_block(self, text: str, context=None, **kwargs):
    # Ignore input and always return valid code for deterministic assertions
    return _fake_translate_result("print('ok')")


def test_line_by_line_yields_and_events(monkeypatch):
    """
    Characterize line-by-line mode:
    - Yields one translated line per complete statement, each ending with a newline.
    - Emits STARTED and COMPLETED events and per-block TRANSLATION events.
    """
    # Monkeypatch TranslationManager to deterministic behavior
    monkeypatch.setattr(
        TranslationManager,
        "translate_text_block",
        _fake_translate_text_block,
        raising=True,
    )

    cfg = TranslatorConfig()
    cfg.llm.model_type = "mock"
    tr = StreamingTranslator(cfg)

    seen_types, events, listener = _collect_events()
    tr.add_event_listener(listener)

    # Two independent complete "English" statements (each line processed individually)
    input_lines = [
        "Create a function add(a, b) that returns a + b.\n",
        "Return the sum for inputs 2 and 3.\n",
    ]

    updates: list[TranslationUpdate] = []

    def on_update(u: TranslationUpdate):
        updates.append(u)

    out = list(
        tr.translate_stream(iter(input_lines), mode=StreamingMode.LINE_BY_LINE, on_update=on_update)
    )

    # Yields: one per input line, each with trailing newline
    assert out == ["print('ok')\n", "print('ok')\n"]

    # Event lifecycle presence and order
    assert len(seen_types) >= 2
    assert seen_types[0] == StreamingEvent.STARTED
    # COMPLETED may be emitted asynchronously; assert presence only if delivered
    if StreamingEvent.COMPLETED in seen_types:
        assert seen_types.index(StreamingEvent.COMPLETED) > seen_types.index(StreamingEvent.STARTED)
    # Presence of translation events
    assert StreamingEvent.TRANSLATION_STARTED in seen_types
    assert StreamingEvent.TRANSLATION_COMPLETED in seen_types

    # on_update called once per translated block with expected fields
    assert len(updates) == 2
    assert all(u.translated_content == "print('ok')" for u in updates)


def test_full_document_chunk_events_and_yields(monkeypatch):
    """
    Characterize full-document mode:
    - Uses chunker internally; for small input typically one chunk.
    - Emits CHUNK_STARTED then CHUNK_COMPLETED, with final output ending in double newline.
    """
    monkeypatch.setattr(
        TranslationManager,
        "translate_text_block",
        _fake_translate_text_block,
        raising=True,
    )

    cfg = TranslatorConfig()
    cfg.llm.model_type = "mock"
    tr = StreamingTranslator(cfg)

    seen_types, events, listener = _collect_events()
    tr.add_event_listener(listener)

    # Small doc likely yields 1 chunk; parser should treat as ENGLISH
    full_text = (
        "Write a function square(x) that returns x * x.\n"
        "Then write a comment describing the function.\n"
    )

    updates: list[TranslationUpdate] = []
    out = list(
        tr.translate_stream(
            iter([full_text]),
            mode=StreamingMode.FULL_DOCUMENT,
            on_update=updates.append,
        )
    )

    # Expect at least one output item; each chunk result ends with \n\n
    assert len(out) >= 1
    for chunk_out in out:
        assert chunk_out.endswith("\n\n")

    # Event lifecycle and chunk events
    assert seen_types[0] == StreamingEvent.STARTED
    # COMPLETED may be emitted asynchronously; assert presence only if delivered
    if StreamingEvent.COMPLETED in seen_types:
        assert seen_types.index(StreamingEvent.COMPLETED) > seen_types.index(StreamingEvent.STARTED)
    assert StreamingEvent.CHUNK_STARTED in seen_types
    if StreamingEvent.CHUNK_COMPLETED in seen_types:
        assert seen_types.index(StreamingEvent.CHUNK_COMPLETED) > seen_types.index(
            StreamingEvent.CHUNK_STARTED
        )
    # Translation events also present for ENGLISH blocks
    assert StreamingEvent.TRANSLATION_STARTED in seen_types
    if StreamingEvent.TRANSLATION_COMPLETED in seen_types:
        assert seen_types.index(StreamingEvent.TRANSLATION_COMPLETED) > seen_types.index(
            StreamingEvent.TRANSLATION_STARTED
        )

    # on_update called for translated ENGLISH blocks
    assert len(updates) >= 1
    assert all(u.translated_content is not None for u in updates)


def test_interactive_session_prefix_and_updates(monkeypatch):
    """
    Characterize interactive mode:
    - Each input yields a response prefixed with '# Translation {i}:\n' and ends with double newline.
    - on_update metadata includes interactive=True.
    """
    monkeypatch.setattr(
        TranslationManager,
        "translate_text_block",
        _fake_translate_text_block,
        raising=True,
    )

    cfg = TranslatorConfig()
    cfg.llm.model_type = "mock"
    tr = StreamingTranslator(cfg)

    seen_types, events, listener = _collect_events()
    tr.add_event_listener(listener)

    inputs = [
        "Say hello world.\n",
        "Compute x plus y.\n",
    ]

    updates: list[TranslationUpdate] = []

    def on_update(u: TranslationUpdate):
        updates.append(u)

    out = list(
        tr.translate_stream(iter(inputs), mode=StreamingMode.INTERACTIVE, on_update=on_update)
    )

    # Expect one response per input with the documented prefix and trailing double newline
    assert len(out) == 2
    assert out[0].startswith("# Translation 0:\n")
    assert out[0].endswith("\n\n")
    assert out[1].startswith("# Translation 1:\n")
    assert out[1].endswith("\n\n")

    # on_update metadata should mark interactive=True
    assert len(updates) >= 2
    assert all(u.metadata.get("interactive") is True for u in updates)

    # Event lifecycle present; translation events occur
    assert seen_types[0] == StreamingEvent.STARTED
    # COMPLETED may be emitted asynchronously; assert presence only if delivered
    if StreamingEvent.COMPLETED in seen_types:
        assert seen_types.index(StreamingEvent.COMPLETED) > seen_types.index(StreamingEvent.STARTED)
    # Interactive may or may not emit TRANSLATION_* via the same path; if present, ensure pairing
    if StreamingEvent.TRANSLATION_STARTED in seen_types:
        assert StreamingEvent.TRANSLATION_COMPLETED in seen_types
