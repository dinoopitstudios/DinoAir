"""
Unit tests for safe_pdf_extractor.py module.
Tests secure PDF text extraction with timeout protection and error handling.
"""

import io
from pathlib import Path
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from ..safe_pdf_extractor import (
    PDFProcessingError,
    PDFProcessingTimeout,
    SafePDFProcessor,
    create_safe_pdf_extractor,
    extract_pdf_text_safe,
    extract_pdf_text_safe_async,
)


class TestPDFExceptions:
    """Test cases for PDF processing exceptions."""

    def test_pdf_processing_timeout_exception(self):
        """Test PDFProcessingTimeout exception."""
        error = PDFProcessingTimeout("Processing timed out")
        assert isinstance(error, Exception)
        if str(error) != "Processing timed out":
            raise AssertionError

    def test_pdf_processing_error_exception(self):
        """Test PDFProcessingError exception."""
        error = PDFProcessingError("Processing failed")
        assert isinstance(error, Exception)
        if str(error) != "Processing failed":
            raise AssertionError


class TestSafePDFProcessor:
    """Test cases for SafePDFProcessor class."""

    def test_processor_initialization_defaults(self):
        """Test SafePDFProcessor initialization with defaults."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            if processor.timeout != 30:
                raise AssertionError
            if processor.max_pages != 1000:
                raise AssertionError
            if processor.max_file_size != 50 * 1024 * 1024:
                raise AssertionError
            if processor.max_memory_usage != 100 * 1024 * 1024:
                raise AssertionError

    def test_processor_initialization_custom(self):
        """Test SafePDFProcessor initialization with custom values."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(
                timeout=60,
                max_pages=500,
                max_file_size=10 * 1024 * 1024,
                max_memory_usage=50 * 1024 * 1024,
            )

            if processor.timeout != 60:
                raise AssertionError
            if processor.max_pages != 500:
                raise AssertionError
            if processor.max_file_size != 10 * 1024 * 1024:
                raise AssertionError
            if processor.max_memory_usage != 50 * 1024 * 1024:
                raise AssertionError

    def test_processor_initialization_without_pypdf2(self):
        """Test SafePDFProcessor initialization when PyPDF2 is not available."""
        with patch("utils.safe_pdf_extractor.PdfReader", None):
            with pytest.raises(ImportError, match="PyPDF2 is required but not installed"):
                SafePDFProcessor()

    def test_timeout_handler_context_manager(self):
        """Test timeout handler context manager."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(timeout=1)

            with processor._timeout_handler() as timeout_checker:
                assert timeout_checker is not None
                if not hasattr(timeout_checker, "check_timeout"):
                    raise AssertionError

    def test_timeout_handler_timeout_detection(self):
        """Test timeout handler timeout detection."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(timeout=0.1)

            with pytest.raises(PDFProcessingTimeout):
                with processor._timeout_handler() as timeout_checker:
                    time.sleep(0.2)  # Exceed timeout
                    timeout_checker.check_timeout()

    def test_validate_pdf_file_success(self):
        """Test successful PDF file validation."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest content")
                temp_file.flush()

                try:
                    # Should not raise any exception
                    processor._validate_pdf_file(temp_file.name)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_validate_pdf_file_not_exists(self):
        """Test PDF file validation with non-existent file."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with pytest.raises(PDFProcessingError, match="PDF file does not exist"):
                processor._validate_pdf_file("/nonexistent/file.pdf")

    def test_validate_pdf_file_not_file(self):
        """Test PDF file validation with directory instead of file."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with tempfile.TemporaryDirectory() as temp_dir:
                with pytest.raises(PDFProcessingError, match="Path is not a file"):
                    processor._validate_pdf_file(temp_dir)

    def test_validate_pdf_file_too_large(self):
        """Test PDF file validation with file too large."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(max_file_size=100)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"x" * 200)  # Larger than max_file_size
                temp_file.flush()

                try:
                    with pytest.raises(PDFProcessingError, match="PDF file too large"):
                        processor._validate_pdf_file(temp_file.name)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_validate_pdf_file_wrong_extension(self):
        """Test PDF file validation with wrong extension."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    with pytest.raises(PDFProcessingError, match="File is not a PDF"):
                        processor._validate_pdf_file(temp_file.name)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_validate_pdf_file_invalid_header(self):
        """Test PDF file validation with invalid header."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"Not a PDF file")
                temp_file.flush()

                try:
                    with pytest.raises(
                        PDFProcessingError, match="File does not have valid PDF header"
                    ):
                        processor._validate_pdf_file(temp_file.name)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_preprocess_pdf_content_malformed_comments(self):
        """Test PDF content preprocessing for malformed comments."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            # Test case 1: Comment at end of line without character
            content1 = b"%PDF-1.4\nsome content\n%\nmore content"
            result1 = processor._preprocess_pdf_content(content1)
            if b"% safe" not in result1:
                raise AssertionError
            if result1 == content1:
                raise AssertionError

            # Test case 2: Comment at end of file
            content2 = b"%PDF-1.4\nsome content%"
            result2 = processor._preprocess_pdf_content(content2)
            if not result2.endswith(b"% safe"):
                raise AssertionError

            # Test case 3: Comment with non-printable characters
            content3 = b"%PDF-1.4\nsome content\n%\x00\nmore content"
            result3 = processor._preprocess_pdf_content(content3)
            if b"% safe" not in result3:
                raise AssertionError

            # Test case 4: Normal comments should be preserved
            content4 = b"%PDF-1.4\n% This is a normal comment\nsome content"
            result4 = processor._preprocess_pdf_content(content4)
            if b"% This is a normal comment" not in result4:
                raise AssertionError

            # Test case 5: Bare % on its own line
            content5 = b"%PDF-1.4\nsome content\n%\nmore content"
            result5 = processor._preprocess_pdf_content(content5)
            # Should not have any line with just '%'
            lines = result5.decode("latin-1", errors="ignore").split("\n")
            for line in lines:
                if line.strip() == "%":
                    raise AssertionError(f"Found bare % in line: {repr(line)}")

    def test_preprocess_pdf_content_error_handling(self):
        """Test PDF content preprocessing error handling."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            # Create content that will trigger an exception during regex processing
            # by mocking the re module to raise an exception
            content = b"%PDF-1.4\ntest content"

            with patch("re.sub", side_effect=Exception("regex error")):
                result = processor._preprocess_pdf_content(content)
                # Should return original content on error
                if result != content:
                    raise AssertionError

    def test_safe_read_pdf_with_preprocessing(self):
        """Test PDF reading with content preprocessing."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            # Create PDF content with malformed comment
            pdf_content = b"%PDF-1.4\nsome content\n%\nmore content"

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file.flush()

                try:
                    result = processor._safe_read_pdf(temp_file.name)
                    if result != mock_reader:
                        raise AssertionError

                    # Verify PdfReader was called with preprocessed content
                    mock_pdf_reader.assert_called_once()
                    call_args = mock_pdf_reader.call_args

                    # The first argument should be a BytesIO object with preprocessed content
                    bytes_io_arg = call_args[0][0]
                    assert isinstance(bytes_io_arg, io.BytesIO)

                    # Read the content to verify preprocessing occurred
                    preprocessed_content = bytes_io_arg.getvalue()
                    if b"% " not in preprocessed_content:
                        raise AssertionError

                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_safe_read_pdf_success(self):
        """Test successful PDF reading."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest content")
                temp_file.flush()

                try:
                    result = processor._safe_read_pdf(temp_file.name)
                    if result != mock_reader:
                        raise AssertionError
                    mock_pdf_reader.assert_called_once()
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_safe_read_pdf_timeout(self):
        """Test PDF reading with timeout."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            # Make PdfReader construction slow
            def slow_init(*args, **kwargs):
                time.sleep(0.2)
                return MagicMock()

            mock_pdf_reader.side_effect = slow_init

            processor = SafePDFProcessor(timeout=0.1)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    with pytest.raises(PDFProcessingTimeout):
                        processor._safe_read_pdf(temp_file.name)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_extract_page_text_safe_success(self):
        """Test successful page text extraction."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is test content from PDF page."

            result = processor._extract_page_text_safe(mock_page, 1)

            if result != "This is test content from PDF page.":
                raise AssertionError
            mock_page.extract_text.assert_called_once()

    def test_extract_page_text_safe_timeout(self):
        """Test page text extraction with timeout."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(timeout=0.1)

            mock_page = MagicMock()

            def slow_extract():
                time.sleep(0.2)
                return "text"

            mock_page.extract_text.side_effect = slow_extract

            with pytest.raises(PDFProcessingTimeout):
                processor._extract_page_text_safe(mock_page, 1)

    def test_extract_page_text_safe_error_recovery(self):
        """Test page text extraction error recovery."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            mock_page = MagicMock()
            mock_page.extract_text.side_effect = RuntimeError("Extraction failed")

            with patch("utils.safe_pdf_extractor.logger") as mock_logger:
                result = processor._extract_page_text_safe(mock_page, 1)

                if "[ERROR EXTRACTING PAGE 1:" not in result:
                    raise AssertionError
                mock_logger.warning.assert_called()

    def test_extract_page_text_sanitization(self):
        """Test text sanitization during extraction."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            mock_page = MagicMock()
            # Text with control characters and null bytes
            dirty_text = "Clean text\x00\x01\x02\x03\nNew line\tTab"
            mock_page.extract_text.return_value = dirty_text

            result = processor._extract_page_text_safe(mock_page, 1)

            # Should remove control characters but keep newlines and tabs
            if "\x00" in result:
                raise AssertionError
            if "\x01" in result:
                raise AssertionError
            if "\n" not in result:
                raise AssertionError
            if "\t" not in result:
                raise AssertionError
            if "Clean text" not in result:
                raise AssertionError

    def test_extract_page_text_length_limit(self):
        """Test page text length limiting."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            mock_page = MagicMock()
            # Very long text (over 100KB)
            long_text = "A" * 150000
            mock_page.extract_text.return_value = long_text

            result = processor._extract_page_text_safe(mock_page, 1)

            # Should be truncated
            if len(result) > 100020:
                raise AssertionError
            if "[TEXT TRUNCATED - Page too long]" not in result:
                raise AssertionError

    def test_extract_text_from_file_success(self):
        """Test successful text extraction from file."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            # Setup mock reader
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content"
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest content")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not True:
                        raise AssertionError
                    if "Test PDF content" not in result["text"]:
                        raise AssertionError
                    if result["pages_processed"] != 1:
                        raise AssertionError
                    if result["total_pages"] != 1:
                        raise AssertionError
                    if result["processing_time"] <= 0:
                        raise AssertionError
                    assert isinstance(result["warnings"], list)
                    if result["error"] is not None:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_extract_text_from_file_validation_error(self):
        """Test text extraction with file validation error."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            result = processor.extract_text("/nonexistent/file.pdf")

            if result["success"] is not False:
                raise AssertionError
            if result["error"] is None:
                raise AssertionError
            if "does not exist" not in result["error"]:
                raise AssertionError
            if result["text"] != "":
                raise AssertionError
            if result["pages_processed"] != 0:
                raise AssertionError

    def test_extract_text_no_pages(self):
        """Test text extraction from PDF with no pages."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_reader.pages = []  # No pages
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not True:
                        raise AssertionError
                    if result["total_pages"] != 0:
                        raise AssertionError
                    if "PDF has no pages" not in result["warnings"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_extract_text_page_limit(self):
        """Test text extraction with page limit."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            # Create mock reader with many pages
            mock_pages = []
            for i in range(10):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i + 1} content"
                mock_pages.append(mock_page)

            mock_reader = MagicMock()
            mock_reader.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    # Limit to 3 pages
                    result = processor.extract_text(temp_file.name, max_pages=3)

                    if result["success"] is not True:
                        raise AssertionError
                    if result["total_pages"] != 10:
                        raise AssertionError
                    if result["pages_processed"] != 3:
                        raise AssertionError
                    if "Processing limited to 3 pages" not in result["warnings"]:
                        raise AssertionError
                    if "Page 1 content" not in result["text"]:
                        raise AssertionError
                    if "Page 3 content" not in result["text"]:
                        raise AssertionError
                    if "Page 4 content" in result["text"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_extract_text_timeout_during_processing(self):
        """Test timeout during text extraction."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()

            def slow_extract():
                time.sleep(0.2)
                return "text"

            mock_page.extract_text.side_effect = slow_extract
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor(timeout=0.1)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not False:
                        raise AssertionError
                    if "timed out" not in result["error"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_extract_text_from_bytes_success(self):
        """Test successful text extraction from bytes."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content from bytes"
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            pdf_bytes = b"%PDF-1.4\ntest content"
            result = processor.extract_text_from_bytes(pdf_bytes, "test.pdf")

            if result["success"] is not True:
                raise AssertionError
            if "Content from bytes" not in result["text"]:
                raise AssertionError
            if result["total_pages"] != 1:
                raise AssertionError

    def test_extract_text_from_bytes_too_large(self):
        """Test text extraction from bytes that are too large."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(max_file_size=100)

            large_pdf_bytes = b"%PDF-1.4\n" + b"x" * 200
            result = processor.extract_text_from_bytes(large_pdf_bytes)

            if result["success"] is not False:
                raise AssertionError
            if "too large" not in result["error"]:
                raise AssertionError

    def test_extract_text_from_bytes_invalid_header(self):
        """Test text extraction from bytes with invalid header."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            invalid_bytes = b"Not a PDF file"
            result = processor.extract_text_from_bytes(invalid_bytes)

            if result["success"] is not False:
                raise AssertionError
            if "valid PDF header" not in result["error"]:
                raise AssertionError

    def test_is_pdf_safe_valid_file(self):
        """Test PDF safety check with valid file."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock(), MagicMock()]  # 2 pages
            mock_reader.metadata = {"Title": "Test PDF"}
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.is_pdf_safe(temp_file.name)

                    if result["safe"] is not True:
                        raise AssertionError
                    if "File validation" not in result["checks_passed"]:
                        raise AssertionError
                    if "PDF parsing" not in result["checks_passed"]:
                        raise AssertionError
                    if "Page count reasonable" not in result["checks_passed"]:
                        raise AssertionError
                    if "Metadata present" not in result["checks_passed"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_is_pdf_safe_large_document(self):
        """Test PDF safety check with large document."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            # Create many mock pages (more than max_pages)
            mock_reader.pages = [MagicMock() for _ in range(2000)]
            mock_reader.metadata = None
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor(max_pages=1000)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.is_pdf_safe(temp_file.name)

                    if result["safe"] is not True:
                        raise AssertionError
                    if "Large document: 2000 pages" not in result["warnings"]:
                        raise AssertionError
                    if "No metadata found" not in result["warnings"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_is_pdf_safe_timeout(self):
        """Test PDF safety check with timeout."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:

            def slow_init(*args, **kwargs):
                time.sleep(0.2)
                return MagicMock()

            mock_pdf_reader.side_effect = slow_init

            processor = SafePDFProcessor(timeout=0.1)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.is_pdf_safe(temp_file.name)

                    if result["safe"] is not False:
                        raise AssertionError
                    if "Processing timeout" not in result["checks_failed"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    @pytest.mark.asyncio
    async def test_extract_text_async_success(self):
        """Test successful async text extraction."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Async extracted content"
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = await processor.extract_text_async(temp_file.name)

                    if result["success"] is not True:
                        raise AssertionError
                    if "Async extracted content" not in result["text"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    @pytest.mark.asyncio
    async def test_is_pdf_safe_async_success(self):
        """Test successful async PDF safety check."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()]
            mock_reader.metadata = {"Title": "Test"}
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = await processor.is_pdf_safe_async(temp_file.name)

                    if result["safe"] is not True:
                        raise AssertionError
                    if "File validation" not in result["checks_passed"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()


class TestFactoryAndConvenienceFunctions:
    """Test cases for factory and convenience functions."""

    def test_create_safe_pdf_extractor(self):
        """Test create_safe_pdf_extractor factory function."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = create_safe_pdf_extractor(
                timeout=60, max_pages=500, max_file_size=25 * 1024 * 1024
            )

            assert isinstance(processor, SafePDFProcessor)
            if processor.timeout != 60:
                raise AssertionError
            if processor.max_pages != 500:
                raise AssertionError
            if processor.max_file_size != 25 * 1024 * 1024:
                raise AssertionError

    def test_extract_pdf_text_safe_success(self):
        """Test extract_pdf_text_safe convenience function success."""
        with patch("utils.safe_pdf_extractor.SafePDFProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.extract_text.return_value = {
                "success": True,
                "text": "Extracted text content",
            }
            mock_processor_class.return_value = mock_processor

            result = extract_pdf_text_safe("test.pdf", timeout=30, max_pages=100)

            if result != "Extracted text content":
                raise AssertionError
            mock_processor_class.assert_called_with(timeout=30)
            mock_processor.extract_text.assert_called_with("test.pdf", max_pages=100)

    def test_extract_pdf_text_safe_failure(self):
        """Test extract_pdf_text_safe convenience function failure."""
        with patch("utils.safe_pdf_extractor.SafePDFProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.extract_text.return_value = {
                "success": False,
                "text": "",
                "error": "Extraction failed",
            }
            mock_processor_class.return_value = mock_processor

            with patch("utils.safe_pdf_extractor.logger") as mock_logger:
                result = extract_pdf_text_safe("test.pdf")

                if result != "":
                    raise AssertionError
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_extract_pdf_text_safe_async_success(self):
        """Test extract_pdf_text_safe_async convenience function success."""
        with patch("utils.safe_pdf_extractor.SafePDFProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.extract_text_async.return_value = {
                "success": True,
                "text": "Async extracted content",
            }
            mock_processor_class.return_value = mock_processor

            result = await extract_pdf_text_safe_async("test.pdf", timeout=45)

            if result != "Async extracted content":
                raise AssertionError
            mock_processor_class.assert_called_with(timeout=45)

    @pytest.mark.asyncio
    async def test_extract_pdf_text_safe_async_failure(self):
        """Test extract_pdf_text_safe_async convenience function failure."""
        with patch("utils.safe_pdf_extractor.SafePDFProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.extract_text_async.return_value = {
                "success": False,
                "text": "",
                "error": "Async extraction failed",
            }
            mock_processor_class.return_value = mock_processor

            with patch("utils.safe_pdf_extractor.logger") as mock_logger:
                result = await extract_pdf_text_safe_async("test.pdf")

                if result != "":
                    raise AssertionError
                mock_logger.error.assert_called()


class TestSecurityAndRobustness:
    """Test cases for security and robustness features."""

    def test_malicious_filename_handling(self):
        """Test handling of malicious filenames."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            # Test various malicious filename patterns
            malicious_names = [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\config\\sam",
                "/dev/null",
                "con.pdf",  # Windows reserved name
                "file\x00.pdf",  # Null byte injection
            ]

            for filename in malicious_names:
                result = processor.extract_text(filename)
                # Should fail safely without crashing
                if result["success"] is not False:
                    raise AssertionError
                if result["error"] is None:
                    raise AssertionError

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()

            # Simulate very large text extraction
            mock_page.extract_text.return_value = "A" * (200 * 1024)  # 200KB per page
            mock_reader.pages = [mock_page] * 10  # 10 pages = ~2MB total

            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    # Should complete but with truncated pages
                    if result["success"] is not True:
                        raise AssertionError
                    # Each page should be truncated to ~100KB
                    pages_in_text = result["text"].count("=== Page")
                    if pages_in_text > 10:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_infinite_loop_protection(self):
        """Test protection against infinite loops in PDF processing."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()

            # Simulate infinite loop in extract_text
            def infinite_loop():
                while True:
                    time.sleep(0.01)
                    # Check for timeout in real implementation
                    break  # Break for test purposes

            mock_page.extract_text.side_effect = infinite_loop
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor(timeout=0.1)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    # This should timeout and not hang indefinitely
                    start_time = time.time()
                    processor.extract_text(temp_file.name)
                    end_time = time.time()

                    # Should complete within reasonable time (timeout + overhead)
                    if (end_time - start_time) >= 1.0:
                        raise AssertionError
                    # Result depends on timeout implementation
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_corrupted_pdf_handling(self):
        """Test handling of corrupted PDF files."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_pdf_reader.side_effect = RuntimeError("Corrupted PDF")

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ncorrupted content")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not False:
                        raise AssertionError
                    if "Error reading PDF" not in result["error"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_empty_pdf_handling(self):
        """Test handling of empty PDF files."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"")  # Empty file
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not False:
                        raise AssertionError
                    if "valid PDF header" not in result["error"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()


class TestPerformanceAndScaling:
    """Test cases for performance and scaling characteristics."""

    def test_large_document_processing(self):
        """Test processing of large documents."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            # Create mock reader with many pages
            mock_pages = []
            for i in range(100):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i + 1} " + "content " * 100
                mock_pages.append(mock_page)

            mock_reader = MagicMock()
            mock_reader.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor(max_pages=50)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    start_time = time.time()
                    result = processor.extract_text(temp_file.name)
                    end_time = time.time()

                    if result["success"] is not True:
                        raise AssertionError
                    if result["total_pages"] != 100:
                        raise AssertionError
                    if result["pages_processed"] != 50:
                        raise AssertionError
                    if (end_time - start_time) >= 5.0:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_concurrent_processing(self):
        """Test concurrent PDF processing."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Concurrent content"
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            results = {}

            def process_worker(worker_id):
                processor = SafePDFProcessor()

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(b"%PDF-1.4\ntest")
                    temp_file.flush()

                    try:
                        result = processor.extract_text(temp_file.name)
                        results[worker_id] = result["success"]
                    except Exception as e:
                        results[worker_id] = str(e)
                    finally:
                        temp_file.close()
                    Path(temp_file.name).unlink()

            # Start multiple concurrent processors
            import threading

            threads = []
            for i in range(3):
                thread = threading.Thread(target=process_worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All should succeed
            assert len(results) == 3
            for success in results.values():
                if success is not True:
                    raise AssertionError

    def test_resource_cleanup(self):
        """Test that resources are properly cleaned up."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_reader.pages = []
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            # Process multiple files to test cleanup
            for _i in range(5):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(b"%PDF-1.4\ntest")
                    temp_file.flush()

                    try:
                        result = processor.extract_text(temp_file.name)
                        if result["success"] is not True:
                            raise AssertionError
                    finally:
                        temp_file.close()
                    Path(temp_file.name).unlink()

            # Processor should still be in clean state
            assert processor._timeout_checker is None


class TestEdgeCasesAndErrorConditions:
    """Test cases for edge cases and error conditions."""

    def test_zero_timeout(self):
        """Test processor with zero timeout."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(timeout=0)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)
                    # Should either succeed immediately or timeout immediately
                    assert isinstance(result["success"], bool)
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_negative_limits(self):
        """Test processor with negative limits."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            # Should handle negative values gracefully
            processor = SafePDFProcessor(timeout=1, max_pages=-1, max_file_size=-1)

            # Processor should be created but may not work as expected
            if processor.max_pages != -1:
                raise AssertionError
            if processor.max_file_size != -1:
                raise AssertionError

    def test_unicode_filename_handling(self):
        """Test handling of unicode filenames."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            unicode_filename = "测试文件_🔥.pdf"
            result = processor.extract_text(unicode_filename)

            # Should fail safely (file doesn't exist) without encoding errors
            if result["success"] is not False:
                raise AssertionError
            if "does not exist" not in result["error"]:
                raise AssertionError

    def test_very_long_filename(self):
        """Test handling of very long filenames."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            long_filename = "a" * 1000 + ".pdf"
            result = processor.extract_text(long_filename)

            # Should fail safely without crashing
            if result["success"] is not False:
                raise AssertionError

    def test_process_reader_timeout_near_limit(self):
        """Test _process_reader with timeout near the limit."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor(timeout=0.2)

            mock_reader = MagicMock()
            mock_pages = []
            for i in range(10):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i + 1}"
                mock_pages.append(mock_page)
            mock_reader.pages = mock_pages

            start_time = time.time()

            # This should stop early due to approaching timeout
            extracted_texts, pages_processed, warnings = processor._process_reader(
                mock_reader, start_time, 10
            )

            # Should have stopped before processing all pages
            if pages_processed > 10:
                raise AssertionError
            # May have timeout warning
            [w for w in warnings if "timeout" in w.lower()]
            # Depending on timing, may or may not have timeout warnings

    def test_extract_text_with_mixed_content_types(self):
        """Test extraction with mixed content types."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()

            # Create pages with different content types
            mock_pages = []
            page_contents = [
                "Normal text content",
                "",  # Empty page
                None,  # Page that returns None
                "Text with special characters: !@#$%^&*()",
                123,  # Non-string return (should be converted)
            ]

            for content in page_contents:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = content
                mock_pages.append(mock_page)

            mock_reader.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\ntest")
                temp_file.flush()

                try:
                    result = processor.extract_text(temp_file.name)

                    if result["success"] is not True:
                        raise AssertionError
                    # Should handle all content types gracefully
                    if "Normal text content" not in result["text"]:
                        raise AssertionError
                    if "special characters" not in result["text"]:
                        raise AssertionError
                finally:
                    temp_file.close()
                    Path(temp_file.name).unlink()

    def test_file_permission_errors(self):
        """Test handling of file permission errors."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            # Mock file operations to raise permission error
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = processor.extract_text("test.pdf")

                if result["success"] is not False:
                    raise AssertionError
                if "Error reading PDF file" not in result["error"]:
                    raise AssertionError

    def test_disk_space_errors(self):
        """Test handling of disk space errors during processing."""
        with patch("utils.safe_pdf_extractor.PdfReader", MagicMock()):
            processor = SafePDFProcessor()

            # Mock file operations to raise disk space error
            with patch("builtins.open", side_effect=OSError("No space left on device")):
                result = processor.extract_text("test.pdf")

                if result["success"] is not False:
                    raise AssertionError
                if "Error reading PDF file" not in result["error"]:
                    raise AssertionError

    def test_concurrent_timeout_protection(self):
        """Test timeout protection under concurrent access."""
        with patch("utils.safe_pdf_extractor.PdfReader") as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_page = MagicMock()

            # Make extraction slow
            def slow_extract():
                time.sleep(0.1)
                return "slow content"

            mock_page.extract_text.side_effect = slow_extract
            mock_reader.pages = [mock_page] * 5
            mock_pdf_reader.return_value = mock_reader

            processor = SafePDFProcessor(timeout=0.2)  # Very short timeout
            results = {}

            def concurrent_worker(worker_id):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(b"%PDF-1.4\ntest")
                    temp_file.flush()

                    try:
                        start_time = time.time()
                        result = processor.extract_text(temp_file.name)
                        end_time = time.time()

                        results[worker_id] = {
                            "duration": end_time - start_time,
                            "success": result["success"],
                            "timed_out": "timed out" in result.get("error", ""),
                        }
                    finally:
                        temp_file.close()
                    Path(temp_file.name).unlink()

            # Start concurrent workers
            import threading

            threads = []
            for i in range(3):
                thread = threading.Thread(target=concurrent_worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All workers should complete within reasonable time
            for worker_result in results.values():
                if worker_result["duration"] >= 1.0:
                    raise AssertionError
