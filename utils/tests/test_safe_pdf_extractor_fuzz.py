"""
Property-based fuzz tests for utils.safe_pdf_extractor.SafePDFProcessor

Goals:
- Generate bounded, diverse inputs to harden sanitization and error handling.
- Ensure well-formed PDFs (1–3 blank pages, optional metadata) never crash and yield a string result.
- Ensure malformed inputs (random bytes, with/without %PDF- header) do not crash and return safe errors.
- Validate timeout behavior with extremely small timeout by inducing slow reader construction.

Notes:
- We deliberately avoid complex PDF text drawing; PyPDF2 PdfWriter is used to construct minimal, valid PDFs in-memory.
- For page-level timeouts, the implementation records a warning instead of surfacing an exception; this is documented for follow-up.
"""

import io
import time

import pytest

from utils.safe_pdf_extractor import SafePDFProcessor


# Skip entire module if hypothesis is not available
hypothesis = pytest.importorskip("hypothesis")
HealthCheck = hypothesis.HealthCheck
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


try:
    # Only used to build well-formed PDFs in-memory
    from pypdf import PdfWriter  # type: ignore[import]
except Exception:  # pragma: no cover - CI pins pypdf; locally it may be missing
    PdfWriter = None  # type: ignore[assignment]

HAVE_PYPDF2 = PdfWriter is not None
pytestmark = pytest.mark.skipif(not HAVE_PYPDF2, reason="PyPDF2 required for fuzz tests")

# Bounded, mixed-character alphabet: ASCII letters/digits/punct, whitespace, and a small unicode subset.
ASCII_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
PUNCT = " .,:;!?-_/\\()[]{}@#%^&*+=~|\"'`<>"
WHITESPACE = "\n\t\r "
UNICODE_SUBSET = "äöüßéñ—–“”•✓αβγ漢字🔥"
CONTROL_SAFE = "\x00\x0b\x0c"  # a few non-printables; extractor will sanitize

ALPHABET = ASCII_LETTERS + DIGITS + PUNCT + WHITESPACE + UNICODE_SUBSET + CONTROL_SAFE


def _assume_pypdf2():
    if PdfWriter is None:
        pytest.skip("PyPDF2 not available; CI workflow pins it for test runs only.")


def build_blank_pdf_bytes(num_pages: int, metadata_text: str | None = None) -> bytes:
    """
    Build a minimal, valid PDF with 1–3 blank pages using PyPDF2.
    Optionally embed metadata (not used for text extraction, but exercises parser paths).
    """
    _assume_pypdf2()
    writer = PdfWriter()
    # Standard A4-ish size in points
    width, height = 595, 842
    for _ in range(num_pages):
        writer.add_blank_page(width=width, height=height)
    if metadata_text:
        # Limit metadata length to keep size bounded
        writer.add_metadata({"/Title": metadata_text[:120]})

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.fuzz
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow],
    seed=12345,
    database=None,
)
@given(
    num_pages=st.integers(min_value=1, max_value=3),
    meta=st.text(alphabet=ALPHABET, min_size=0, max_size=256),
)
def test_well_formed_blank_pdfs_property(num_pages: int, meta: str):
    """
    For valid, blank PDFs:
    - Processor should succeed, never crash, and return a string result.
    - Total page count matches generated count; pages_processed does not exceed it.
    - Text may be empty (blank pages) but must be a str.
    """
    pdf_bytes = build_blank_pdf_bytes(num_pages, metadata_text=meta)
    proc = SafePDFProcessor(timeout=2, max_pages=3, max_file_size=5 * 1024 * 1024)  # 5 MiB cap
    result = proc.extract_text_from_bytes(pdf_bytes, filename="fuzz.pdf")

    if result["success"] is not True:
        raise AssertionError
    if result["error"] is not None:
        raise AssertionError
    if result["total_pages"] != num_pages:
        raise AssertionError
    assert isinstance(result["text"], str)
    assert isinstance(result["warnings"], list)
    if not 0 <= result["pages_processed"] <= num_pages:
        raise AssertionError
    # Bound result size comfortably (blank pages should be very small)
    if len(result["text"]) > 10000:
        raise AssertionError


@pytest.mark.fuzz
@settings(max_examples=40, deadline=400, seed=12345, database=None)
@given(
    payload=st.binary(min_size=0, max_size=2048).map(
        # Ensure it does NOT start with a valid %PDF- header to trigger header validation
        lambda b: (b"\x01" + b[1:]) if b.startswith(b"%PDF-") else b
    )
)
def test_malformed_bytes_without_header_returns_error(payload: bytes):
    """
    For random bytes without a %PDF- header:
    - extract_text_from_bytes should not crash and should return a safe error about header validity.
    """
    proc = SafePDFProcessor(timeout=1)
    result = proc.extract_text_from_bytes(payload, filename="random.bin")
    if result["success"] is not False:
        raise AssertionError
    if result["text"] != "":
        raise AssertionError
    if result["error"] is None:
        raise AssertionError
    # Error should indicate missing/invalid header
    if "valid PDF header" not in (result.get("error") or ""):
        raise AssertionError


@pytest.mark.fuzz
@settings(max_examples=30, deadline=600, seed=12345, database=None)
@given(rest=st.binary(min_size=0, max_size=2048))
def test_random_bytes_with_pdf_header_never_crash(rest: bytes):
    """
    For random bytes prefixed with %PDF-:
    - Reader may fail to parse (unexpected/invalid structure) or may succeed.
    - Regardless, processing must not crash the test runner.
    - Ensure bounded outputs and well-formed result schema.
    """
    payload = b"%PDF-" + rest
    proc = SafePDFProcessor(timeout=1)
    result = proc.extract_text_from_bytes(payload, filename="maybe_malformed.pdf")

    # Schema checks
    assert isinstance(result.get("success"), bool)
    assert isinstance(result.get("text"), str)
    assert isinstance(result.get("warnings"), list)
    # Either we got a parse error or a parsed doc (possibly 0 pages)
    if result["success"]:
        if result["error"] not in (None, ""):
            raise AssertionError
        assert isinstance(result.get("total_pages"), int)
        assert isinstance(result.get("pages_processed"), int)
    else:
        if result["error"] is None:
            raise AssertionError

    # Keep output bounded for safety; real extractor also truncates per page to ~100KB
    if len(result["text"]) > 300000:
        raise AssertionError


@pytest.mark.unit
def test_tiny_timeout_induces_timeout_on_reader_construction(monkeypatch):
    """
    Induce a predictable timeout by making PdfReader construction slow.
    This exercises the timeout path that surfaces as a top-level PDFProcessingTimeout.
    """
    pdf_bytes = build_blank_pdf_bytes(1, metadata_text="t")

    # Use the real PdfReader to parse, but add a delay before returning it.
    from pypdf import PdfReader as RealPdfReader  # type: ignore[import]

    def slow_reader(stream, strict=False):  # noqa: D401
        time.sleep(0.2)
        return RealPdfReader(stream, strict=strict)

    # Patch the module-level PdfReader reference used by the extractor
    monkeypatch.setattr("utils.safe_pdf_extractor.PdfReader", slow_reader, raising=True)

    proc = SafePDFProcessor(timeout=0.05)
    result = proc.extract_text_from_bytes(pdf_bytes, filename="slow.pdf")

    if result["success"] is not False:
        raise AssertionError
    if "timed out" not in (result.get("error") or ""):
        raise AssertionError
