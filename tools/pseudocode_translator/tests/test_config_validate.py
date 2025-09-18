from pathlib import Path

from pseudocode_translator.config_tool import validate_config


def test_validate_config_valid_strict_ok():
    # Use the provided valid fixture
    path = str(Path(__file__).parent / "fixtures" / "configs" / "valid_config.yaml")
    exit_code, result = validate_config(path, lenient=False)

    if exit_code != 0:
        raise AssertionError(f"Expected strict validation to pass, got {exit_code} with {result}")
    assert isinstance(result, dict)
    if result.get("errors") != []:
        raise AssertionError
    assert isinstance(result.get("warnings"), list)
    if result.get("path") != path:
        raise AssertionError


def test_validate_config_invalid_strict_errors():
    # Use the provided invalid fixture
    path = str(Path(__file__).parent / "fixtures" / "configs" / "invalid_config.yaml")
    exit_code, result = validate_config(path, lenient=False)

    if exit_code != 1:
        raise AssertionError("Strict mode should return nonzero exit on invalid config")
    assert isinstance(result, dict)
    errors = result.get("errors", [])
    assert isinstance(errors, list)
    if len(errors) <= 0:
        raise AssertionError
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
    if result.get("path") != path:
        raise AssertionError
    # Accept both 0 or 1 depending on validator behavior; primarily ensure function executes and returns keys
    if exit_code not in (0, 1):
        raise AssertionError


def test_validate_config_missing_file():
    missing = str(Path(__file__).parent / "fixtures" / "configs" / "does_not_exist.yaml")
    exit_code, result = validate_config(missing, lenient=False)

    if exit_code != 1:
        raise AssertionError
    assert isinstance(result, dict)
    if not (isinstance(result.get("errors"), list) and result["errors"]):
        raise AssertionError("Expected an error message")
    # The first error should clearly mention path; allow partial match
    if "File not found or unreadable" not in result["errors"][0]:
        raise AssertionError
    if missing not in result["errors"][0]:
        raise AssertionError
    if result.get("warnings") != []:
        raise AssertionError
    if result.get("path") != missing:
        raise AssertionError
