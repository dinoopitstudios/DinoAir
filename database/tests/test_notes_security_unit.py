"""
Unit tests for NotesSecurity and FallbackSecurity.
Covers permission checks, SQL wildcard escaping, and input validation behavior.
"""

import os
from unittest.mock import patch

from database.notes_security import FallbackSecurity, NotesSecurity


def test_notes_security_uses_fallback_policy_by_default():
    """NotesSecurity should fall back to FallbackSecurity when GUI policy is unavailable."""
    with patch.dict(os.environ, {}, clear=True):
        sec = NotesSecurity()
        assert isinstance(sec.policy, FallbackSecurity)


def test_can_perform_write_operation_blocked_by_default():
    """Fallback policy should block writes unless ALLOW_NOTES_FALLBACK_WRITES is set."""
    with patch.dict(os.environ, {}, clear=True):
        sec = NotesSecurity()
        allowed, msg = sec.can_perform_write_operation("create")
        if allowed is not False:
            raise AssertionError
        assert isinstance(msg, str)
        if not ("blocked" in msg.lower() or "unavailable" in msg.lower()):
            raise AssertionError


def test_can_perform_write_operation_allowed_when_env_enabled():
    """Setting ALLOW_NOTES_FALLBACK_WRITES enables write operations under fallback policy."""
    with patch.dict(os.environ, {"ALLOW_NOTES_FALLBACK_WRITES": "1"}, clear=True):
        sec = NotesSecurity()
        allowed, msg = sec.can_perform_write_operation("update")
        if allowed is not True:
            raise AssertionError
        assert msg is None


def test_escape_sql_wildcards_via_policy():
    """Escape should delegate to policy and escape backslash, %, and _."""
    policy = FallbackSecurity()
    # Input contains %, _, and a backslash
    escaped = policy.escape_sql_wildcards(r"a%_b\c")
    # Expect backslash escaped first, then % and _
    if escaped != r"a\%\_b\\c":
        raise AssertionError


def test_validate_note_data_errors_and_success():
    """FallbackSecurity validation: various error cases and a valid case."""
    policy = FallbackSecurity()

    # Empty title
    res = policy.validate_note_data("", "x", ["t"])
    if res["valid"] is not False:
        raise AssertionError
    if not any("title" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Title too long
    res = policy.validate_note_data("a" * 301, "x", ["t"])
    if res["valid"] is not False:
        raise AssertionError
    if not any("exceeds 300" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Non-string content
    res = policy.validate_note_data("ok", 123, ["t"])
    if res["valid"] is not False:
        raise AssertionError
    if not any("content must be a string" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Content too long
    res = policy.validate_note_data("ok", "x" * 20001, [])
    if res["valid"] is not False:
        raise AssertionError
    if not any("exceeds 20000" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Tags not a list
    res = policy.validate_note_data("ok", "x", "not-a-list")  # type: ignore[arg-type]
    if res["valid"] is not False:
        raise AssertionError
    if not any("tags must be a list" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Tag too long and non-string
    res = policy.validate_note_data("ok", "x", ["a" * 51, 123])  # type: ignore[list-item]
    if res["valid"] is not False:
        raise AssertionError
    errs = " ".join(res["errors"]).lower()
    if not ("strings" in errs or "tag length exceeds" in errs):
        raise AssertionError

    # Too many tags
    res = policy.validate_note_data("ok", "x", [f"t{i}" for i in range(101)])
    if res["valid"] is not False:
        raise AssertionError
    if not any("too many tags" in e.lower() for e in res["errors"]):
        raise AssertionError

    # Valid minimal case
    res = policy.validate_note_data("Title", "", [])
    if res["valid"] is not True:
        raise AssertionError


def test_notes_security_escape_sql_wildcards_delegates_to_policy():
    """NotesSecurity.escape_sql_wildcards should produce same result as policy."""
    with patch.dict(os.environ, {}, clear=True):
        sec = NotesSecurity()
        s = r"100%_pattern\end"
        if sec.escape_sql_wildcards(s) != FallbackSecurity().escape_sql_wildcards(s):
            raise AssertionError
