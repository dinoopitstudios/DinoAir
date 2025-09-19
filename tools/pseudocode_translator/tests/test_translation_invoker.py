import pytest
from pseudocode_translator.models.base_model import (
    OutputLanguage,
)
from pseudocode_translator.models.base_model import TranslationResult as ModelTranslationResult
from pseudocode_translator.streaming.buffer import ContextBuffer
from pseudocode_translator.streaming.translation_invoker import TranslationInvoker


def _collect_events():
    events = []

    def emit(evt):
        events.append(evt)

    return events, emit


class _ManagerOK:
    def translate_text_block(self, text: str, context=None):
        return ModelTranslationResult(
            success=True,
            code="x = 1",
            language=OutputLanguage.PYTHON,
            confidence=1.0,
            errors=[],
            warnings=[],
            metadata={"mocked": True},
        )


class _ManagerNoCode:
    def translate_text_block(self, text: str, context=None):
        return ModelTranslationResult(
            success=False,
            code=None,
            language=OutputLanguage.PYTHON,
            confidence=0.0,
            errors=[],
            warnings=[],
            metadata={"mocked": True},
        )


class _ManagerErrors:
    def translate_text_block(self, text: str, context=None):
        return ModelTranslationResult(
            success=False,
            code=None,
            language=OutputLanguage.PYTHON,
            confidence=0.0,
            errors=["err_a", "err_b"],
            warnings=[],
            metadata={"mocked": True},
        )


def test_invoker_emits_started_then_completed_and_updates_buffer():
    buffer = ContextBuffer(window_size=128)
    events, emit = _collect_events()
    invoker = TranslationInvoker(emit_event=emit, context_buffer=buffer)

    out = invoker.translate_english(
        text="Translate to code.",
        context={"k": "v"},
        manager=_ManagerOK(),
        chunk_index=7,
        block_type="english",
    )

    # Validate return and buffer update
    if out != "x = 1":
        raise AssertionError
    if "x = 1" not in buffer.get_context():
        raise AssertionError

    # Validate event ordering and types
    if len(events) < 2:
        raise AssertionError
    from pseudocode_translator.streaming.stream_translator import StreamingEvent

    types = [e.event for e in events]
    if types[0] != StreamingEvent.TRANSLATION_STARTED:
        raise AssertionError
    if types[-1] != StreamingEvent.TRANSLATION_COMPLETED:
        raise AssertionError


def test_invoker_failure_no_code_returns_expected_message():
    buffer = ContextBuffer(window_size=64)
    events, emit = _collect_events()
    invoker = TranslationInvoker(emit_event=emit, context_buffer=buffer)

    with pytest.raises(RuntimeError) as ex:
        _ = invoker.translate_english(
            text="bad",
            context={},
            manager=_ManagerNoCode(),
            chunk_index=0,
        )
    if "Translation failed: No code returned" not in str(ex.value):
        raise AssertionError


def test_invoker_failure_with_errors_list_in_message():
    buffer = ContextBuffer(window_size=64)
    events, emit = _collect_events()
    invoker = TranslationInvoker(emit_event=emit, context_buffer=buffer)

    with pytest.raises(RuntimeError) as ex:
        _ = invoker.translate_english(
            text="bad",
            context={},
            manager=_ManagerErrors(),
            chunk_index=0,
        )
    # Comma-joined errors should be present
    if "Translation failed: err_a, err_b" not in str(ex.value):
        raise AssertionError
