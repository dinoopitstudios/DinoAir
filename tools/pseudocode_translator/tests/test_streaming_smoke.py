from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models.base_model import (
    OutputLanguage,
)
from pseudocode_translator.models.base_model import TranslationResult as ModelTranslationResult
from pseudocode_translator.streaming.pipeline import StreamingPipeline
from pseudocode_translator.translator import TranslationManager


def test_streaming_smoke_minimal(monkeypatch):
    # Disable plugin auto-discovery and keep config deterministic
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"  # safe default; we monkeypatch below anyway

    # Monkeypatch TranslationManager.translate_text_block to be deterministic and hermetic
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

    # Use StreamingPipeline directly to avoid size gating in manager.translate_streaming
    pipeline = StreamingPipeline(cfg)

    input_text = "Define a function add(a, b) that returns their sum."

    # Collect streaming chunk results
    results = list(pipeline.stream_translate(input_text))
    if len(results) < 1:
        raise AssertionError
    if not any(r.success for r in results):
        raise AssertionError
    if not any(r.translated_blocks for r in results):
        raise AssertionError

    # Assemble final code from streamed blocks and verify expected token
    final_code = pipeline.assemble_streamed_code()
    assert isinstance(final_code, str)
    if "def add(" not in final_code:
        raise AssertionError

    # Validate syntactic correctness without executing arbitrary behavior
    compile(final_code, "<test>", "exec")
