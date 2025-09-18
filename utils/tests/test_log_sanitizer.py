"""Tests for log sanitization utilities."""

import pytest
from utils.log_sanitizer import sanitize_for_log


class TestLogSanitizer:
    """Test the log sanitizer utility."""

    def test_sanitize_normal_string(self):
        """Test that normal strings pass through unchanged."""
        normal = "normal/path/to/file.txt"
        result = sanitize_for_log(normal)
        assert result == normal

    def test_sanitize_newlines(self):
        """Test that newlines are escaped."""
        malicious = "path/to/file.txt\nFAKE LOG ENTRY"
        result = sanitize_for_log(malicious)
        assert result == "path/to/file.txt\\nFAKE LOG ENTRY"

    def test_sanitize_carriage_returns(self):
        """Test that carriage returns are escaped."""
        malicious = "path/to/file.txt\rFAKE LOG ENTRY"
        result = sanitize_for_log(malicious)
        assert result == "path/to/file.txt\\rFAKE LOG ENTRY"

    def test_sanitize_tabs(self):
        """Test that tabs are escaped."""
        malicious = "path/to/file.txt\tFAKE LOG ENTRY"
        result = sanitize_for_log(malicious)
        assert result == "path/to/file.txt\\tFAKE LOG ENTRY"

    def test_sanitize_control_characters(self):
        """Test that control characters are removed."""
        malicious = "path/to/file.txt\x00\x07\x1FFAKE"
        result = sanitize_for_log(malicious)
        assert result == "path/to/file.txtFAKE"

    def test_sanitize_length_limit(self):
        """Test that overly long strings are truncated."""
        long_string = "A" * 250
        result = sanitize_for_log(long_string, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_sanitize_none_value(self):
        """Test that None is handled gracefully."""
        result = sanitize_for_log(None)
        assert result == "None"

    def test_sanitize_non_string_value(self):
        """Test that non-string values are converted to string."""
        result = sanitize_for_log(123)
        assert result == "123"

    def test_sanitize_complex_log_injection(self):
        """Test a complex log injection attack."""
        attack = "/api/test\n2023-01-01 FAKE INFO: Admin login successful\r\nAttacker controlled content"
        result = sanitize_for_log(attack)
        expected = "/api/test\\n2023-01-01 FAKE INFO: Admin login successful\\r\\nAttacker controlled content"
        assert result == expected

    def test_sanitize_unicode_preserved(self):
        """Test that safe Unicode characters are preserved."""
        unicode_path = "/home/user/文档/file.txt"
        result = sanitize_for_log(unicode_path)
        assert result == unicode_path