from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.integration.events import EventHandler, EventType
from pseudocode_translator.models.base_model import (
    OutputLanguage,
)
from pseudocode_translator.models.base_model import TranslationResult as ModelTranslationResult
from pseudocode_translator.streaming.adaptive import AdaptiveChunkSizer
from pseudocode_translator.streaming.pipeline import StreamingPipeline
from pseudocode_translator.translator import TranslationManager


def test_adaptive_increases_when_fast():
    sizer = AdaptiveChunkSizer(
        min_size=100,
        max_size=2000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,  # band: [480, 720]
        cooldown_chunks=0,
        step_pct=0.2,
        initial_size=500,
    )
    # Initial decision initializes and returns current
    cur = sizer.get_next_chunk_size(default_chunk_size=500)
    if cur != 500:
        raise AssertionError

    # Fast observed latency below lower band => should increase by 20% (100)
    sizer.update_feedback(
        last_chunk_chars=cur,
        observed_latency_ms=300.0,
        queue_utilization=0.1,
        model_tps=None,
    )
    nxt = sizer.get_next_chunk_size(default_chunk_size=500)
    if nxt != 600:
        raise AssertionError(f"Expected increase to 600, got {nxt}")


def test_adaptive_decreases_when_slow():
    sizer = AdaptiveChunkSizer(
        min_size=100,
        max_size=2000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,  # band: [480, 720]
        cooldown_chunks=0,
        step_pct=0.2,
        initial_size=500,
    )
    cur = sizer.get_next_chunk_size(default_chunk_size=500)
    if cur != 500:
        raise AssertionError

    # Slow observed latency above upper band => should decrease by 20% (100)
    sizer.update_feedback(
        last_chunk_chars=cur,
        observed_latency_ms=900.0,
        queue_utilization=0.0,
        model_tps=None,
    )
    nxt = sizer.get_next_chunk_size(default_chunk_size=500)
    if nxt != 400:
        raise AssertionError(f"Expected decrease to 400, got {nxt}")


def test_hysteresis_prevents_oscillation():
    sizer = AdaptiveChunkSizer(
        min_size=100,
        max_size=2000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,  # band: [480, 720]
        cooldown_chunks=0,
        step_pct=0.2,
        initial_size=500,
    )
    cur = sizer.get_next_chunk_size(default_chunk_size=500)
    if cur != 500:
        raise AssertionError

    # Within band => no change
    sizer.update_feedback(
        last_chunk_chars=cur,
        observed_latency_ms=600.0,
        queue_utilization=0.0,
        model_tps=None,
    )
    nxt = sizer.get_next_chunk_size(default_chunk_size=500)
    if nxt != 500:
        raise AssertionError(f"Expected no change within hysteresis band, got {nxt}")


def test_respects_min_max_bounds():
    # Upper bound clamp on increase
    sizer_inc = AdaptiveChunkSizer(
        min_size=100,
        max_size=1000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,
        cooldown_chunks=0,
        step_pct=0.5,  # 50% step to force overshoot
        initial_size=950,
    )
    cur = sizer_inc.get_next_chunk_size(default_chunk_size=950)
    if cur != 950:
        raise AssertionError
    # Very fast => tries to increase to 1425 but should clamp to 1000
    sizer_inc.update_feedback(
        last_chunk_chars=cur,
        observed_latency_ms=100.0,
        queue_utilization=0.0,
        model_tps=None,
    )
    nxt = sizer_inc.get_next_chunk_size(default_chunk_size=950)
    if nxt != 1000:
        raise AssertionError

    # Lower bound clamp on decrease
    sizer_dec = AdaptiveChunkSizer(
        min_size=100,
        max_size=1000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,
        cooldown_chunks=0,
        step_pct=0.5,
        initial_size=120,
    )
    cur2 = sizer_dec.get_next_chunk_size(default_chunk_size=120)
    if cur2 != 120:
        raise AssertionError
    # Very slow => tries to decrease to 60 but should clamp to 100
    sizer_dec.update_feedback(
        last_chunk_chars=cur2,
        observed_latency_ms=2000.0,
        queue_utilization=0.0,
        model_tps=None,
    )
    nxt2 = sizer_dec.get_next_chunk_size(default_chunk_size=120)
    if nxt2 != 100:
        raise AssertionError


def test_backpressure_blocks_increase():
    sizer = AdaptiveChunkSizer(
        min_size=100,
        max_size=2000,
        target_ms=600,
        alpha=0.5,
        hysteresis_pct=0.2,
        cooldown_chunks=0,
        step_pct=0.2,
        initial_size=500,
    )
    cur = sizer.get_next_chunk_size(default_chunk_size=500)
    if cur != 500:
        raise AssertionError

    # Fast but queue utilization high => no increase
    sizer.update_feedback(
        last_chunk_chars=cur,
        observed_latency_ms=300.0,
        queue_utilization=0.95,
        model_tps=None,
    )
    nxt = sizer.get_next_chunk_size(default_chunk_size=500)
    if nxt != 500:
        raise AssertionError(f"Expected no increase due to backpressure, got {nxt}")


def test_disabled_feature_no_change(monkeypatch):
    # Set up deterministic environment
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    # Ensure adaptive is disabled
    cfg.streaming.adaptive_chunking_enabled = False
    # Keep regular chunk size small to ensure chunking happens deterministically
    cfg.streaming.chunk_size = 256

    manager = TranslationManager(cfg)
    try:
        events = []
        handler = EventHandler(events.append)
        manager.get_event_dispatcher().register(handler)

        # Monkeypatch translate_text_block to be deterministic and fast
        def fake_translate_text_block(self, text: str, context=None, config=None):
            return ModelTranslationResult(
                success=True,
                code="def f():\n    return 42\n",
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

        pipeline = StreamingPipeline(cfg)
        pipeline.translator = manager

        input_text = "Define a function add(a, b) that returns their sum."
        _ = list(pipeline.stream_translate(input_text))

        # No adaptation decision events should be present when disabled
        if not all(e.type != EventType.STREAM_ADAPTATION_DECISION for e in events):
            raise AssertionError
    finally:
        manager.shutdown()


def test_events_emitted_on_adjustment(monkeypatch):
    # Configure adaptive to be enabled and to start small so increase happens
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    cfg.streaming.adaptive_chunking_enabled = True
    cfg.streaming.adaptive_target_latency_ms = 600
    cfg.streaming.adaptive_min_chunk_size = 100
    cfg.streaming.adaptive_max_chunk_size = 1000
    cfg.streaming.adaptive_hysteresis_pct = 0.2
    cfg.streaming.adaptive_cooldown_chunks = 0
    cfg.streaming.adaptive_smoothing_alpha = 0.5
    cfg.streaming.adaptive_initial_chunk_size = 200
    cfg.streaming.chunk_size = 200  # default fallback for initial if None

    manager = TranslationManager(cfg)
    try:
        events = []
        handler = EventHandler(events.append)
        manager.get_event_dispatcher().register(handler)

        # Deterministic, fast translation
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

        pipeline = StreamingPipeline(cfg)
        pipeline.translator = manager

        # Create input long enough to produce at least 2 chunks with initial size 200
        input_text = "\n".join(["Define a function add(a, b) that returns their sum."] * 50)

        # Execute streaming
        results = list(pipeline.stream_translate(input_text))
        if len(results) < 2:
            raise AssertionError

        # There should be at least one adaptation decision event (increase expected)
        adapt_events = [e for e in events if e.type == EventType.STREAM_ADAPTATION_DECISION]
        if len(adapt_events) < 1:
            raise AssertionError
        # Validate payload keys presence on the last event
        payload = adapt_events[-1].data
        for key in (
            "old_size",
            "new_size",
            "reason",
            "smoothed_latency_ms",
            "target_latency_ms",
            "backpressure_util",
            "cooldown_remaining",
        ):
            if key not in payload:
                raise AssertionError
    finally:
        manager.shutdown()
