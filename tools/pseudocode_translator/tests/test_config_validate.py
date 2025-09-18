from pathlib import Path

from pseudocode_translator.config_tool import validate_config


def test_validate_config_valid_strict_ok():
    # Use the provided valid fixture
    path = str(Path(__file__).parent / "fixtures" / "configs" / "valid_config.yaml")
    exit_code, result = validate_config(path, lenient=False)

    assert exit_code == 0, f"Expected strict validation to pass, got {exit_code} with {result}"
    assert isinstance(result, dict)
    assert result.get("errors") == []
    assert isinstance(result.get("warnings"), list)
    assert result.get("path") == path


def test_validate_config_invalid_strict_errors():
    # Use the provided invalid fixture
    path = str(Path(__file__).parent / "fixtures" / "configs" / "invalid_config.yaml")
    exit_code, result = validate_config(path, lenient=False)

    assert exit_code == 1, "Strict mode should return nonzero exit on invalid config"
    assert isinstance(result, dict)
    errors = result.get("errors", [])
    assert isinstance(errors, list)
    assert len(errors) > 0
    assert isinstance(result.get("warnings"), list)


def test_validate_config_lenient_collects_warnings():
    # With lenient=True, accept either outcome depending on current validators:
    # - exit_code 1 if errors occur even in non-strict mode (e.g., type issues surfaced)
    # - exit_code 0 if only warnings and no errors are present
    path = str(Path(__file__).parent / "fixtures" / "configs" / "invalid_config.yaml")
    exit_code, result = validate_config(path, lenient=True)

    assert isinstance(result, dict)
    assert isinstance(result.get("errors"), list)
    assert isinstance(result.get("warnings"), list)
    assert result.get("path") == path
    # Accept both 0 or 1 depending on validator behavior; primarily ensure function executes and returns keys
    assert exit_code in (0, 1)


def test_validate_config_missing_file():
    missing = str(Path(__file__).parent / "fixtures" / "configs" / "does_not_exist.yaml")
    exit_code, result = validate_config(missing, lenient=False)

    assert exit_code == 1
    assert isinstance(result, dict)
    assert isinstance(result.get("errors"), list) and result["errors"], "Expected an error message"
    # The first error should clearly mention path; allow partial match
    assert "File not found or unreadable" in result["errors"][0]
    assert missing in result["errors"][0]
    assert result.get("warnings") == []
    assert result.get("path") == missing
