from pseudocode_translator.config import Config, TranslatorConfig
from pseudocode_translator.validator import ValidationResult, Validator


def make_validator(allow_unsafe: bool = False) -> Validator:
    base = Config(allow_unsafe_operations=allow_unsafe)
    cfg = TranslatorConfig(base)
    # Keep validation deterministic and strict enough to flag issues
    # Disable plugins if any system tries to auto-load
    cfg.enable_plugins = False
    return Validator(cfg)


def test_validate_syntax_passes_on_simple_code():
    validator = make_validator()
    code = "def add(a, b):\n    return a + b\n"
    result = validator.validate_syntax(code)
    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert result.errors == []


def test_validate_syntax_flags_invalid_code():
    validator = make_validator()
    bad_code = "def broken(\n    return 1\n"
    result = validator.validate_syntax(bad_code)
    assert isinstance(result, ValidationResult)
    assert not result.is_valid
    assert any("Syntax error" in err or "Failed to parse code" in err for err in result.errors)


def test_security_finding_detects_eval_exec():
    # Ensure unsafe operations are not allowed so findings surface as errors
    validator = make_validator(allow_unsafe=False)
    insecure_code = "def risky(x):\n    return eval('x + 1')\n"
    result = validator.validate_syntax(insecure_code)
    assert not result.is_valid
    assert any(
        "Unsafe operation detected" in err or "Unsafe operation" in err for err in result.errors
    )
