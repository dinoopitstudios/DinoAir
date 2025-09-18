from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.translator import TranslationManager


def test_translate_with_mock_model_produces_output():
    # Configure manager to use local/deterministic mock model and disable plugins
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    cfg.llm.model_type = "mock"  # use the registered mock model

    manager = TranslationManager(cfg)
    try:
        instruction = "Define a function add(a, b) that returns their sum."
        result = manager.translate_pseudocode(instruction)

        assert isinstance(result.success, bool)
        if not result.success:
            raise AssertionError
        assert isinstance(result.code, str)
        if len(result.code) <= 0:
            raise AssertionError

        # Sanity check: compiled as Python without executing arbitrary code
        compile(result.code, "<test>", "exec")
    finally:
        manager.shutdown()
