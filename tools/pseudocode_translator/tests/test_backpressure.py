import concurrent.futures as cf
import threading
import time

from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models.base_model import (
    OutputLanguage,
    TranslationResult as ModelTranslationResult,
)
import pseudocode_translator.streaming.pipeline as pipeline_module
from pseudocode_translator.streaming.pipeline import StreamConfig, StreamingPipeline
from pseudocode_translator.translator import TranslationManager


def _build_long_input(min_bytes: int) -> str:
    # English instruction that the parser will treat as English text
    line = "Define a function f(x) that returns x plus 1.\n"
    repeats = int(min_bytes / len(line)) + 8
    return line * repeats


def test_backpressure_enabled_limits_window(monkeypatch):
    """
    Verify enforced submission window when enable_backpressure=True:
    outstanding submissions (running + queued in executor, i.e., submitted minus completed)
    never exceed (max_concurrent_chunks + max_queue_size).
    """
    # Capture the real executor before monkeypatching so our wrapper can delegate
    RealThreadPoolExecutor = cf.ThreadPoolExecutor

    class TrackingExecutor:
        """
        Tracking wrapper for ThreadPoolExecutor that records peak outstanding tasks.
        Outstanding = submitted - completed (tracked via done callbacks).
        """

        outstanding = 0
        peak_outstanding = 0
        lock = threading.Lock()

        def __init__(self, max_workers=None, *args, **kwargs):
            self._real = RealThreadPoolExecutor(max_workers=max_workers, *args, **kwargs)

        def submit(self, fn, *args, **kwargs):
            with TrackingExecutor.lock:
                TrackingExecutor.outstanding += 1
                TrackingExecutor.peak_outstanding = max(
                    TrackingExecutor.peak_outstanding, TrackingExecutor.outstanding
                )

            fut = self._real.submit(fn, *args, **kwargs)

            def _done(_f):
                with TrackingExecutor.lock:
                    TrackingExecutor.outstanding -= 1

            fut.add_done_callback(_done)
            return fut

        def shutdown(self, wait=True, cancel_futures=False):
            try:
                return self._real.shutdown(wait=wait, cancel_futures=cancel_futures)
            except TypeError:
                # Older Python may not support cancel_futures
                return self._real.shutdown(wait=wait)

        def __enter__(self):
            self._real.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._real.__exit__(exc_type, exc, tb)

        def __getattr__(self, name):
            return getattr(self._real, name)

        @classmethod
        def reset_metrics(cls):
            with cls.lock:
                cls.outstanding = 0
                cls.peak_outstanding = 0

    # Monkeypatch both the generic and the pipeline-local ThreadPoolExecutor references
    monkeypatch.setattr(cf, "ThreadPoolExecutor", TrackingExecutor, raising=True)
    monkeypatch.setattr(pipeline_module, "ThreadPoolExecutor", TrackingExecutor, raising=True)

    # Monkeypatch translation to introduce a small per-chunk delay (sleep only once per chunk)
    seen_chunks = set()

    def fake_translate_text_block(self, text: str, context=None, config=None):
        chunk_index = (context or {}).get("chunk_index")
        if chunk_index is not None and chunk_index not in seen_chunks:
            seen_chunks.add(chunk_index)
            time.sleep(0.03)  # small, deterministic delay per chunk
        return ModelTranslationResult(
            success=True,
            code="pass",
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

    # Deterministic, hermetic config
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    # Use small concurrency and queue to make the combined window easy to assert
    stream_cfg = StreamConfig(
        max_concurrent_chunks=2,
        max_queue_size=1,
        enable_backpressure=True,
        thread_pool_size=4,
    )
    pipeline = StreamingPipeline(cfg, stream_config=stream_cfg)

    # Ensure we get at least ~6 chunks by exceeding the internal chunker's max_chunk_size (≈ 2 * max_context_length)
    max_chunk_size = cfg.max_context_length * 2  # matches StreamingPipeline's ChunkConfig
    target_chunks = 6
    input_text = _build_long_input(min_bytes=max_chunk_size * target_chunks + 1024)

    TrackingExecutor.reset_metrics()
    # Drain the stream to completion
    _ = list(pipeline.stream_translate(input_text))

    expected_window = stream_cfg.max_concurrent_chunks + stream_cfg.max_queue_size
    if TrackingExecutor.peak_outstanding > expected_window:
        raise AssertionError(
            f"Peak outstanding {TrackingExecutor.peak_outstanding} exceeded expected window {expected_window} "
            f"with backpressure enabled."
        )


def test_backpressure_disabled_limits_window(monkeypatch):
    """
    Verify enforced submission window when enable_backpressure=False:
    window equals max_concurrent_chunks (no extra queuing).
    """
    # Capture the real executor before monkeypatching so our wrapper can delegate
    RealThreadPoolExecutor = cf.ThreadPoolExecutor

    class TrackingExecutor:
        """
        Tracking wrapper for ThreadPoolExecutor that records peak outstanding tasks.
        Outstanding = submitted - completed (tracked via done callbacks).
        """

        outstanding = 0
        peak_outstanding = 0
        lock = threading.Lock()

        def __init__(self, max_workers=None, *args, **kwargs):
            self._real = RealThreadPoolExecutor(max_workers=max_workers, *args, **kwargs)

        def submit(self, fn, *args, **kwargs):
            with TrackingExecutor.lock:
                TrackingExecutor.outstanding += 1
                TrackingExecutor.peak_outstanding = max(
                    TrackingExecutor.peak_outstanding, TrackingExecutor.outstanding
                )

            fut = self._real.submit(fn, *args, **kwargs)

            def _done(_f):
                with TrackingExecutor.lock:
                    TrackingExecutor.outstanding -= 1

            fut.add_done_callback(_done)
            return fut

        def shutdown(self, wait=True, cancel_futures=False):
            try:
                return self._real.shutdown(wait=wait, cancel_futures=cancel_futures)
            except TypeError:
                # Older Python may not support cancel_futures
                return self._real.shutdown(wait=wait)

        def __enter__(self):
            self._real.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._real.__exit__(exc_type, exc, tb)

        def __getattr__(self, name):
            return getattr(self._real, name)

        @classmethod
        def reset_metrics(cls):
            with cls.lock:
                cls.outstanding = 0
                cls.peak_outstanding = 0

    # Monkeypatch both the generic and the pipeline-local ThreadPoolExecutor references
    monkeypatch.setattr(cf, "ThreadPoolExecutor", TrackingExecutor, raising=True)
    monkeypatch.setattr(pipeline_module, "ThreadPoolExecutor", TrackingExecutor, raising=True)

    # Monkeypatch translation to introduce a small per-chunk delay (sleep only once per chunk)
    seen_chunks = set()

    def fake_translate_text_block(self, text: str, context=None, config=None):
        chunk_index = (context or {}).get("chunk_index")
        if chunk_index is not None and chunk_index not in seen_chunks:
            seen_chunks.add(chunk_index)
            time.sleep(0.03)  # small, deterministic delay per chunk
        return ModelTranslationResult(
            success=True,
            code="pass",
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

    # Deterministic, hermetic config
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"

    # Disable backpressure - window should equal max_concurrent_chunks
    stream_cfg = StreamConfig(
        max_concurrent_chunks=2,
        max_queue_size=1,  # ignored for window calculation when backpressure is disabled
        enable_backpressure=False,
        thread_pool_size=4,
    )
    pipeline = StreamingPipeline(cfg, stream_config=stream_cfg)

    # Build input large enough to produce multiple chunks
    max_chunk_size = cfg.max_context_length * 2
    target_chunks = 6
    input_text = _build_long_input(min_bytes=max_chunk_size * target_chunks + 1024)

    TrackingExecutor.reset_metrics()
    # Drain the stream to completion
    _ = list(pipeline.stream_translate(input_text))

    expected_window = stream_cfg.max_concurrent_chunks
    if TrackingExecutor.peak_outstanding > expected_window:
        raise AssertionError(
            f"Peak outstanding {TrackingExecutor.peak_outstanding} exceeded expected window {expected_window} "
            f"with backpressure disabled."
        )
