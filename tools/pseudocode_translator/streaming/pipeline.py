"""
Streaming pipeline for memory-efficient pseudocode translation

This module provides a streaming pipeline that processes code chunks through
the translation stages while maintaining context and handling backpressure.
"""

import logging
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from queue import Queue
from typing import Any

# Note on imports: to avoid circular imports with translator.py, we avoid
# importing TranslationManager at module import time. We import it lazily
# inside methods that need it.
from ..assembler import CodeAssembler
from ..config import TranslatorConfig
from ..integration.events import EventType
from ..models import BlockType, CodeBlock
from ..models.base_model import TranslationResult as ModelTranslationResult
from ..parser import ParserModule
from ..telemetry import get_recorder
from ..validator import Validator
from .adaptive import AdaptiveChunkSizer
from .buffer import BufferConfig, StreamBuffer
from .chunker import ChunkConfig, CodeChunk, CodeChunker

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for streaming pipeline"""

    enable_streaming: bool = True
    min_file_size_for_streaming: int = 1024 * 100  # 100KB
    max_concurrent_chunks: int = 3
    chunk_timeout: float = 30.0
    progress_callback_interval: float = 0.5
    maintain_context_window: bool = True
    context_window_size: int = 1024  # Characters
    enable_backpressure: bool = True
    max_queue_size: int = 10
    thread_pool_size: int = 4


@dataclass
class StreamingProgress:
    """Progress information for streaming operations"""

    total_chunks: int = 0
    processed_chunks: int = 0
    current_chunk: int | None = None
    bytes_processed: int = 0
    total_bytes: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100

    @property
    def is_complete(self) -> bool:
        """Check if streaming is complete"""
        return self.processed_chunks >= self.total_chunks


@dataclass
class ChunkResult:
    """Result of processing a single chunk"""

    chunk_index: int
    success: bool
    parsed_blocks: list[Any] | None = None
    translated_blocks: list[Any] | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    processing_time: float = 0.0


class StreamingPipeline:
    """
    Manages streaming translation pipeline with backpressure and context
    """

    def __init__(self, config: TranslatorConfig, stream_config: StreamConfig | None = None):
        """
        Initialize streaming pipeline

        Args:
            config: Translator configuration
            stream_config: Streaming-specific configuration
        """
        self.config = config
        self.stream_config = stream_config or StreamConfig()

        # Initialize components
        self.chunker = CodeChunker(
            ChunkConfig(max_chunk_size=config.max_context_length * 2, respect_boundaries=True)
        )
        self.parser = ParserModule()
        self.translator = None  # Will be created per stream
        self.assembler = CodeAssembler(config)
        self.validator = Validator(config)

        # Streaming state
        self.buffer = StreamBuffer(BufferConfig(max_size_mb=50, enable_compression=True))
        self.context_window = []
        self.result_queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=self.stream_config.thread_pool_size)

        # Progress tracking
        self.progress = StreamingProgress()
        self.progress_callbacks = []
        self._stop_event = threading.Event()
        self._progress_thread = None

    def _dispatch(self, event_type, **data):
        """Best-effort event dispatch via manager's dispatcher; never raises."""
        try:
            if self.translator:
                dispatcher = None
                try:
                    dispatcher = self.translator.get_event_dispatcher()
                except Exception:
                    dispatcher = None
                if dispatcher:
                    dispatcher.dispatch_event(event_type, source=self.__class__.__name__, **data)
        except Exception:
            pass

    def should_use_streaming(self, code: str) -> bool:
        """Determine if streaming should be used for given code"""
        if not self.stream_config.enable_streaming:
            return False

        code_size = len(code.encode("utf-8"))
        return code_size >= self.stream_config.min_file_size_for_streaming

    def stream_translate(
        self,
        code: str,
        filename: str | None = None,
        progress_callback: Callable[[StreamingProgress], None] | None = None,
    ) -> Iterator[ChunkResult]:
        """
        Stream translation of pseudocode

        Args:
            code: Source code to translate
            filename: Optional filename for better error reporting
            progress_callback: Optional callback for progress updates

        Yields:
            ChunkResult objects as chunks are processed
        """
        # Initialize translation manager for this stream (lazy import)
        from ..translator import TranslationManager  # local import to avoid cycle

        # Reuse provided translator if already set; otherwise create a new one
        if self.translator is None:
            self.translator = TranslationManager(self.config)

        recorder = get_recorder()
        _total_start = time.perf_counter()

        # Setup progress tracking
        if progress_callback:
            self.progress_callbacks.append(progress_callback)

        # Emit STREAM_STARTED for direct pipeline usage
        self._dispatch(EventType.STREAM_STARTED, reason="selected_by_config")

        # Start progress reporting thread
        self._start_progress_reporting()

        try:
            # Decide chunking path (feature-flagged adaptive vs. existing behavior)
            self.progress.total_bytes = len(code.encode("utf-8"))

            if getattr(self.config.streaming, "adaptive_chunking_enabled", False):
                # Instantiate sizer with config snapshot
                sc = self.config.streaming
                initial_size = (
                    sc.adaptive_initial_chunk_size
                    if sc.adaptive_initial_chunk_size is not None
                    else sc.chunk_size
                )
                sizer = AdaptiveChunkSizer(
                    min_size=int(sc.adaptive_min_chunk_size),
                    max_size=int(sc.adaptive_max_chunk_size),
                    target_ms=int(sc.adaptive_target_latency_ms),
                    alpha=float(sc.adaptive_smoothing_alpha),
                    hysteresis_pct=float(sc.adaptive_hysteresis_pct),
                    cooldown_chunks=int(sc.adaptive_cooldown_chunks),
                    step_pct=0.2,
                    initial_size=int(initial_size),
                )

                # Local helper: adaptive sequential slicing respecting simple line boundaries
                def _adaptive_sequential_stream() -> Iterator[ChunkResult]:
                    text = code
                    n = len(text)
                    pos = 0
                    chunk_idx = 0
                    prev_size: int | None = None

                    # Hard cap consistent with existing chunker initialization
                    hard_cap_max = int(self.config.max_context_length * 2)

                    while pos < n and not self._stop_event.is_set():
                        # Compute desired size and clamp
                        desired = int(sizer.get_next_chunk_size(default_chunk_size=sc.chunk_size))
                        desired = max(1, min(desired, hard_cap_max))

                        # Emit decision event if size changed
                        if prev_size is not None and desired != prev_size:
                            reason = "increase" if desired > prev_size else "decrease"
                            util = 0.0  # sequential path
                            try:
                                self._dispatch(
                                    EventType.STREAM_ADAPTATION_DECISION,
                                    old_size=int(prev_size),
                                    new_size=int(desired),
                                    reason=reason,
                                    smoothed_latency_ms=float(sizer.smoothed_latency_ms or 0.0),
                                    target_latency_ms=int(sc.adaptive_target_latency_ms),
                                    backpressure_util=float(util),
                                    cooldown_remaining=int(sizer.cooldown_remaining),
                                )
                                rec = get_recorder()
                                rec.record_event(
                                    "adapt.decision",
                                    counters={f"adapt.{reason}": 1},
                                    extra={
                                        "old_size": int(prev_size),
                                        "new_size": int(desired),
                                    },
                                )
                            except Exception:
                                pass

                        prev_size = desired

                        # Choose slice end aligned to last newline if possible
                        end = min(n, pos + desired)
                        slice_text = text[pos:end]
                        if end < n:
                            nl = slice_text.rfind("\n")
                            if nl >= 0 and (pos + nl + 1) > pos:
                                end = pos + nl + 1
                                slice_text = text[pos:end]

                        # Build CodeChunk consistent with expectations
                        start_line = text.count("\n", 0, pos) + 1
                        end_line = start_line + slice_text.count("\n")

                        chunk = CodeChunk(
                            content=slice_text,
                            start_line=start_line,
                            end_line=end_line,
                            start_byte=pos,
                            end_byte=end,
                            chunk_index=chunk_idx,
                            total_chunks=None,
                            metadata={"adaptive": True, "line_based": True},
                        )

                        # Process and measure latency (processing_time set by _process_single_chunk)
                        result = self._process_single_chunk(chunk)
                        # Ensure processing_time is populated
                        if getattr(result, "processing_time", 0.0) is None:
                            result.processing_time = 0.0

                        # After each chunk completes: update feedback
                        observed_ms = float(result.processing_time * 1000.0)
                        # Optional TPS ceiling from model
                        model_tps: float | None = None
                        try:
                            tm = self.translator
                            mdl = getattr(tm, "_current_model", None) if tm else None
                            if mdl:
                                caps = mdl.get_capabilities()
                                tps = caps.get("tokens_per_second")
                                if isinstance(tps, tuple | list) and len(tps) == 2:
                                    # Use upper bound as optimistic ceiling
                                    model_tps = float(tps[1])
                                elif isinstance(tps, int | float):
                                    model_tps = float(tps)
                        except Exception:
                            model_tps = None

                        try:
                            sizer.update_feedback(
                                last_chunk_chars=chunk.size,
                                observed_latency_ms=observed_ms,
                                queue_utilization=0.0,
                                model_tps=model_tps,
                            )
                            rec = get_recorder()
                            rec.record_event(
                                "adapt.latency_ms",
                                duration_ms=float(sizer.smoothed_latency_ms or observed_ms),
                            )
                        except Exception:
                            pass

                        # Update progress and emit per-chunk event (already handled in _process_single_chunk caller paths)
                        self.progress.processed_chunks += 1
                        self.progress.bytes_processed += chunk.size
                        # Keep total_chunks in sync for assembler; adaptive path discovers count incrementally
                        self.progress.total_chunks = max(self.progress.total_chunks, chunk_idx + 1)

                        yield result

                        # Advance
                        pos = end
                        chunk_idx += 1

                # Run adaptive sequential path (keep parallel path unchanged/off for adaptive in this version)
                yield from _adaptive_sequential_stream()
            else:
                # Existing behavior (precompute chunks via chunker and process)
                chunks = list(self.chunker.stream_chunks(code, filename))
                self.progress.total_chunks = len(chunks)

                if self.stream_config.max_concurrent_chunks > 1:
                    # Parallel processing
                    yield from self._process_chunks_parallel(chunks)
                else:
                    # Sequential processing
                    yield from self._process_chunks_sequential(chunks)

        finally:
            # Record total stream time
            try:
                recorder = get_recorder()
                recorder.record_event("stream.total", (time.perf_counter() - _total_start) * 1000.0)
            except Exception:
                pass

            # Emit STREAM_COMPLETED with processed chunk count
            self._dispatch(EventType.STREAM_COMPLETED, chunks=self.progress.processed_chunks)

            # Cleanup
            self._stop_progress_reporting()
            if self.translator:
                self.translator.shutdown()

    def _process_chunks_sequential(self, chunks: list[CodeChunk]) -> Iterator[ChunkResult]:
        """
        Process chunks sequentially

        Args:
            chunks: List of code chunks

        Yields:
            ChunkResult objects
        """
        for chunk in chunks:
            if self._stop_event.is_set():
                break

            start_time = time.time()
            self.progress.current_chunk = chunk.chunk_index

            try:
                # Process chunk
                result = self._process_single_chunk(chunk)
                result.processing_time = time.time() - start_time
                try:
                    recorder = get_recorder()
                    recorder.record_event(
                        "stream.chunk",
                        result.processing_time * 1000.0,
                        extra={"chunk_index": chunk.chunk_index, "size": chunk.size},
                    )
                except Exception:
                    pass

                # Update progress
                self.progress.processed_chunks += 1
                self.progress.bytes_processed += chunk.size

                if result.error:
                    self.progress.errors.append(result.error)
                self.progress.warnings.extend(result.warnings)

                # Emit per-chunk event
                self._dispatch(
                    EventType.STREAM_CHUNK_PROCESSED,
                    index=chunk.chunk_index,
                    success=bool(result.success),
                    duration_ms=int(result.processing_time * 1000.0),
                )

                yield result

            except Exception as e:
                logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
                fail = ChunkResult(
                    chunk_index=chunk.chunk_index,
                    success=False,
                    error=str(e),
                    processing_time=time.time() - start_time,
                )
                # Emit per-chunk event for failure
                self._dispatch(
                    EventType.STREAM_CHUNK_PROCESSED,
                    index=chunk.chunk_index,
                    success=False,
                    duration_ms=int(fail.processing_time * 1000.0),
                )
                yield fail

    def _process_chunks_parallel(self, chunks: list[CodeChunk]) -> Iterator[ChunkResult]:
        """
        Process chunks in parallel with backpressure

        Args:
            chunks: List of code chunks

        Yields:
            ChunkResult objects
        """
        from concurrent.futures import FIRST_COMPLETED, wait

        # Track all outstanding work (running + queued in executor)
        futures: dict[Any, CodeChunk] = {}
        chunk_iter = iter(chunks)

        # Pre-fill up to max_concurrent_chunks to cap initial in-flight work.
        # Additional submissions are bounded by (max_concurrent_chunks + max_queue_size)
        # which limits queued-but-not-yet-executing work, providing backpressure upstream.
        initial = min(self.stream_config.max_concurrent_chunks, len(chunks))
        for _ in range(initial):
            try:
                chunk = next(chunk_iter)
            except StopIteration:
                break
            fut = self.executor.submit(self._process_single_chunk, chunk)
            futures[fut] = chunk

        # Combined window for outstanding work. When backpressure is disabled, we
        # fall back to strict concurrency only.
        combined_limit = (
            self.stream_config.max_concurrent_chunks + self.stream_config.max_queue_size
            if self.stream_config.enable_backpressure
            else self.stream_config.max_concurrent_chunks
        )

        # Submission/collection loop
        while True:
            # Submit as many as allowed by the combined window
            while len(futures) < combined_limit:
                try:
                    next_chunk = next(chunk_iter)
                except StopIteration:
                    break
                fut = self.executor.submit(self._process_single_chunk, next_chunk)
                futures[fut] = next_chunk

            if not futures:
                # No outstanding work and no more chunks to submit
                break

            # Backpressure: we've reached the window or have nothing more to submit.
            # Block until at least one future completes to free capacity.
            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)

            for fut in list(done):
                chunk = futures.pop(fut)
                try:
                    result = fut.result(timeout=self.stream_config.chunk_timeout)

                    try:
                        recorder = get_recorder()
                        recorder.record_event(
                            "stream.chunk",
                            getattr(result, "processing_time", 0.0) * 1000.0,
                            extra={
                                "chunk_index": chunk.chunk_index,
                                "size": chunk.size,
                            },
                        )
                    except Exception:
                        pass

                    # Update progress
                    self.progress.processed_chunks += 1
                    self.progress.bytes_processed += chunk.size

                    if result.error:
                        self.progress.errors.append(result.error)
                    self.progress.warnings.extend(result.warnings)

                    # Emit per-chunk event
                    self._dispatch(
                        EventType.STREAM_CHUNK_PROCESSED,
                        index=chunk.chunk_index,
                        success=bool(result.success),
                        duration_ms=int(getattr(result, "processing_time", 0.0) * 1000.0),
                    )

                    yield result
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
                    # Emit per-chunk failure event
                    self._dispatch(
                        EventType.STREAM_CHUNK_PROCESSED,
                        index=chunk.chunk_index,
                        success=False,
                    )
                    yield ChunkResult(chunk_index=chunk.chunk_index, success=False, error=str(e))

    def _process_single_chunk(self, chunk: CodeChunk) -> ChunkResult:
        """
        Process a single chunk through the pipeline

        Args:
            chunk: Code chunk to process

        Returns:
            ChunkResult
        """
        start_time = time.time()
        result = ChunkResult(chunk_index=chunk.chunk_index, success=True)

        try:
            # Add context from previous chunks
            chunk_with_context = self._add_context_to_chunk(chunk)

            # Parse the chunk
            parse_result = self.parser.get_parse_result(chunk_with_context)

            # Be robust to different ParseResult shapes (property vs computed)
            success_attr = getattr(parse_result, "success", None)
            parse_success = (
                success_attr if isinstance(success_attr, bool) else (len(parse_result.errors) == 0)
            )
            if not parse_success:
                result.success = False
                result.error = f"Parse error: {parse_result.errors}"
                return result

            result.parsed_blocks = parse_result.blocks
            result.warnings.extend(parse_result.warnings)

            # Translate English blocks
            translated_blocks = []
            for block in parse_result.blocks:
                if block.type == BlockType.ENGLISH:
                    # Build translation context
                    context = self._build_translation_context(chunk.chunk_index)

                    try:
                        # Delegate via TranslationManager public wrapper
                        translator = self.translator
                        if translator is None:
                            raise RuntimeError("Translator not initialized")
                        res = translator.translate_text_block(text=block.content, context=context)
                        # Normalize translation result to expected type with .success attribute
                        if (
                            not isinstance(res, ModelTranslationResult)
                            or not getattr(res, "success", False)
                            or getattr(res, "code", None) is None
                        ):
                            raise RuntimeError(
                                "Translation failed: "
                                + (
                                    ", ".join(getattr(res, "errors", []))
                                    if getattr(res, "errors", [])
                                    else "No code returned"
                                )
                            )
                        translated_code = str(res.code)

                        # Create translated block
                        translated_block = CodeBlock(
                            type=BlockType.PYTHON,
                            content=translated_code,
                            line_numbers=block.line_numbers,
                            metadata={**block.metadata, "translated": True},
                            context=block.context,
                        )
                        translated_blocks.append(translated_block)

                    except Exception as e:
                        logger.error(f"Translation error in chunk {chunk.chunk_index}: {e}")
                        result.warnings.append(f"Translation error: {str(e)}")
                        translated_blocks.append(block)  # Keep original
                else:
                    translated_blocks.append(block)

            result.translated_blocks = translated_blocks

            # Update context window
            self._update_context_window(chunk, translated_blocks)

            # Buffer the result
            self.buffer.add_chunk(chunk.chunk_index, result)

        except Exception as e:
            logger.error(f"Error in chunk {chunk.chunk_index}: {e}")
            result.success = False
            result.error = str(e)

        result.processing_time = time.time() - start_time
        return result

    def _add_context_to_chunk(self, chunk: CodeChunk) -> str:
        """
        Add context from previous chunks to current chunk

        Args:
            chunk: Current chunk

        Returns:
            Chunk content with context
        """
        if not self.stream_config.maintain_context_window:
            return chunk.content

        # Get context from buffer
        context_lines = []

        # Add previous chunk's tail if available
        if chunk.chunk_index > 0:
            prev_result = self.buffer.get_chunk(chunk.chunk_index - 1)
            if prev_result and prev_result.translated_blocks:
                # Get last few lines from previous chunk
                last_block = prev_result.translated_blocks[-1]
                context_lines.extend(last_block.content.splitlines()[-10:])

        if context_lines:
            context = "\n".join(context_lines)
            return f"{context}\n\n# --- Chunk {chunk.chunk_index} ---\n\n{chunk.content}"

        return chunk.content

    def _build_translation_context(self, chunk_index: int) -> dict[str, Any]:
        """
        Build context for translation

        Args:
            chunk_index: Current chunk index

        Returns:
            Context dictionary
        """
        context = {"chunk_index": chunk_index, "code": "", "before": "", "after": ""}

        # Get previous chunk's code
        if chunk_index > 0:
            prev_result = self.buffer.get_chunk(chunk_index - 1)
            if prev_result and prev_result.translated_blocks:
                prev_code = "\n".join(
                    block.content
                    for block in prev_result.translated_blocks
                    if block.type == BlockType.PYTHON
                )
                context["before"] = prev_code[-self.stream_config.context_window_size :]
                context["code"] = context["before"]

        return context

    def _update_context_window(self, chunk: CodeChunk, blocks: list[Any]):
        """
        Update the context window with processed blocks

        Args:
            chunk: Processed chunk
            blocks: Translated blocks
        """
        # Keep a sliding window of recent code
        for block in blocks:
            if block.type == BlockType.PYTHON:
                self.context_window.append(
                    {
                        "chunk_index": chunk.chunk_index,
                        "content": block.content,
                        "metadata": block.metadata,
                    }
                )

        # Limit context window size
        max_items = 10
        if len(self.context_window) > max_items:
            self.context_window = self.context_window[-max_items:]

    def assemble_streamed_code(self) -> str:
        """
        Assemble all streamed chunks into final code

        Returns:
            Complete assembled code
        """
        all_blocks = []

        # Get all chunks from buffer in order
        for i in range(self.progress.total_chunks):
            result = self.buffer.get_chunk(i)
            if result and result.translated_blocks:
                all_blocks.extend(result.translated_blocks)

        # Use assembler to create final code
        return self.assembler.assemble(all_blocks)

    def _start_progress_reporting(self):
        """Start the progress reporting thread"""
        self._stop_event.clear()
        self._progress_thread = threading.Thread(target=self._progress_reporter, daemon=True)
        self._progress_thread.start()

    def _stop_progress_reporting(self):
        """Stop the progress reporting thread"""
        self._stop_event.set()
        if self._progress_thread:
            self._progress_thread.join(timeout=1)

    def _progress_reporter(self):
        """Thread function for reporting progress"""
        while not self._stop_event.is_set():
            # Report progress to all callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")

            # Wait before next update
            self._stop_event.wait(self.stream_config.progress_callback_interval)

    def cancel_streaming(self):
        """Cancel ongoing streaming operation"""
        self._stop_event.set()
        self.executor.shutdown(wait=False)
        logger.info("Streaming operation cancelled")

    def get_memory_usage(self) -> dict[str, int]:
        """
        Get current memory usage statistics

        Returns:
            Memory usage in bytes
        """
        return {
            "buffer_size": self.buffer.get_size(),
            "context_window_size": sum(
                len(item["content"].encode("utf-8")) for item in self.context_window
            ),
            # No internal chunk_queue; queued work is bounded via submission window.
            # Expose 0 to preserve key without referencing removed attribute.
            "queue_size": 0,
        }
