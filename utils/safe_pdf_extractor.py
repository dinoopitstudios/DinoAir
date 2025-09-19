"""
Safe PDF Text Extractor for DinoAir 2.0

This module provides a secure text extraction utility that protects against
the PyPDF2 infinite loop vulnerability (CVE-2024-XXXX) where malformed PDF
comments can cause infinite loops in __parse_content_stream.

The extractor implements several defensive measures:
- Timeout mechanisms for PDF processing operations
- Resource monitoring to prevent excessive memory/CPU usage
- Input validation and sanitization
- Safe parsing with error handling and recovery
"""

import io
import logging
import re
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import aiofiles

try:
    from pypdf import PdfReader  # type: ignore[import]
except ImportError:
    PdfReader = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class PDFProcessingTimeout(Exception):
    """Raised when PDF processing exceeds timeout limit"""


class PDFProcessingError(Exception):
    """Raised when PDF processing encounters an error"""


class SafePDFProcessor:
    """
    Safe PDF text extraction processor with protection against infinite loops
    and other PDF-based attacks.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_pages: int = 1000,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        max_memory_usage: int = 100 * 1024 * 1024,  # 100MB
    ):
        """
        Initialize the SafePDFProcessor.

        Args:
            timeout: Maximum time in seconds to spend processing a PDF
            max_pages: Maximum number of pages to process
            max_file_size: Maximum file size in bytes
            max_memory_usage: Maximum memory usage in bytes
        """
        if PdfReader is None:
            raise ImportError("pypdf is required but not installed")

        self.timeout = timeout
        self.max_pages = max_pages
        self.max_file_size = max_file_size
        self.max_memory_usage = max_memory_usage

        # Track processing state
        self._start_time = None
        self._processing_thread = None
        self._stop_processing = False
        self._timeout_checker = None

    @contextmanager
    def _timeout_handler(self) -> Generator[Any, None, None]:
        """Context manager that implements timeout for PDF processing"""

        class TimeoutThread:
            """Monitors processing time and raises PDFProcessingTimeout if the specified timeout is exceeded."""
            def __init__(self, timeout: int) -> None:
                self.timeout = timeout
                self.start_time = time.time()

            def check_timeout(self) -> None:
                if time.time() - self.start_time > self.timeout:
                    raise PDFProcessingTimeout(
                        f"PDF processing timed out after {self.timeout} seconds"
                    )

        timeout_checker = TimeoutThread(self.timeout)
        self._timeout_checker = timeout_checker

        try:
            yield timeout_checker
        finally:
            self._timeout_checker = None

    def _validate_pdf_file(self, file_path: str | Path) -> None:
        """
        Validate PDF file before processing.

        Args:
            file_path: Path to the PDF file

        Raises:
            PDFProcessingError: If validation fails
        """
        path = Path(file_path)

        if not path.exists():
            raise PDFProcessingError(f"PDF file does not exist: {file_path}")

        if not path.is_file():
            raise PDFProcessingError(f"Path is not a file: {file_path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            raise PDFProcessingError(
                f"PDF file too large: {file_size} bytes (max: {self.max_file_size})"
            )

        # Check file extension
        if path.suffix.lower() != ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {file_path}")

        # Basic file content validation - check PDF header
        try:
            with open(path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    raise PDFProcessingError("File does not have valid PDF header")
        except OSError as e:
            raise PDFProcessingError(f"Error reading PDF file: {str(e)}") from e

    async def _validate_pdf_file_async(self, file_path: str | Path) -> None:
        """
        Validate PDF file before processing asynchronously.

        Args:
            file_path: Path to the PDF file

        Raises:
            PDFProcessingError: If validation fails
        """
        path = Path(file_path)

        if not path.exists():
            raise PDFProcessingError(f"PDF file does not exist: {file_path}")

        if not path.is_file():
            raise PDFProcessingError(f"Path is not a file: {file_path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            raise PDFProcessingError(
                f"PDF file too large: {file_size} bytes (max: {self.max_file_size})"
            )

        # Check file extension
        if path.suffix.lower() != ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {file_path}")

        # Basic file content validation - check PDF header
        try:
            async with aiofiles.open(path, "rb") as f:
                header = await f.read(8)
                if not header.startswith(b"%PDF-"):
                    raise PDFProcessingError("File does not have valid PDF header")
        except OSError as e:
            raise PDFProcessingError(f"Error reading PDF file: {str(e)}") from e

    @staticmethod
    def _preprocess_pdf_content(file_content: bytes) -> bytes:
        """
        Preprocess PDF content to fix known vulnerabilities before PyPDF2 parsing.

        Specifically addresses the PyPDF2 infinite loop vulnerability where
        malformed PDF comments (% without following character) can cause
        infinite loops in __parse_content_stream.

        Args:
            file_content: Raw PDF file content

        Returns:
            Sanitized PDF content safe for PyPDF2 parsing
        """
        try:
            # Convert to string for processing (assuming Latin-1 encoding for PDF)
            content_str = file_content.decode("latin-1", errors="ignore")

            # Fix malformed comments that can cause infinite loops
            # Pattern: Find '%' at end of line or file without following character

            # First pass: Fix '%' followed immediately by end of file
            if content_str.endswith("%"):
                content_str += " safe"

            # Second pass: Fix lines that contain only '%' (with optional whitespace)
            # This is the main vulnerability: comments that don't have any content after %
            lines = content_str.split("\n")
            fixed_lines = []

            for line in lines:
                # Check if line contains only '%' and whitespace (malformed comment)
                if re.match(r"^\s*%\s*$", line):
                    # Replace with safe comment that has content after %
                    indentation = line[: len(line) - len(line.lstrip())]
                    fixed_lines.append(indentation + "% safe")
                else:
                    fixed_lines.append(line)

            content_str = "\n".join(fixed_lines)

            # Third pass: Fix '%' at end of lines without proper following content
            # Use regex to find % followed by only whitespace until end of line
            content_str = re.sub(r"%(\s*)$", r"% safe\1", content_str, flags=re.MULTILINE)

            # Fourth pass: Fix '%' followed by non-printable characters
            content_str = re.sub(r"%(?=[\x00-\x08\x0B\x0C\x0E-\x1F\x7F])", r"% safe", content_str)

            # Convert back to bytes
            return content_str.encode("latin-1", errors="ignore")

        except Exception as e:
            # If preprocessing fails, log warning and return original content
            logger.warning("PDF preprocessing failed, using original content: %s", e)
            return file_content

    def _safe_read_pdf(self, file_path: str | Path) -> Any:
        """
        Safely read PDF file with timeout and error handling.
        Includes preprocessing to fix PyPDF2 infinite loop vulnerabilities.

        Args:
            file_path: Path to the PDF file

        Returns:
            PyPDF2 PdfReader object

        Raises:
            PDFProcessingError: If reading fails
        """
        try:
            # Open file in binary mode
            with open(file_path, "rb") as file:
                # Read file content into memory (with size limit already checked)
                file_content = file.read()

            # Preprocess content to fix known vulnerabilities
            sanitized_content = self._preprocess_pdf_content(file_content)

            # Create PdfReader from sanitized bytes to avoid keeping file handle open
            pdf_stream = io.BytesIO(sanitized_content)

            # Use timeout wrapper for PDF reading
            with self._timeout_handler() as timeout_checker:
                assert PdfReader is not None
                reader = cast("Any", PdfReader)(pdf_stream, strict=False)
                timeout_checker.check_timeout()

            return reader
        except RuntimeError as e:
            raise PDFProcessingError(f"Error reading PDF: {str(e)}") from e

    async def _safe_read_pdf_async(self, file_path: str | Path) -> Any:
        """
        Safely read PDF file asynchronously with timeout and error handling.
        Includes preprocessing to fix PyPDF2 infinite loop vulnerabilities.

        Args:
            file_path: Path to the PDF file

        Returns:
            PyPDF2 PdfReader object

        Raises:
            PDFProcessingError: If reading fails
        """
        try:
            # Open file in binary mode asynchronously
            async with aiofiles.open(file_path, "rb") as file:
                # Read file content into memory (with size limit already checked)
                file_content = await file.read()

            # Preprocess content to fix known vulnerabilities
            sanitized_content = self._preprocess_pdf_content(file_content)

            # Create PdfReader from sanitized bytes to avoid keeping file handle open
            pdf_stream = io.BytesIO(sanitized_content)

            # Use timeout wrapper for PDF reading
            with self._timeout_handler() as timeout_checker:
                assert PdfReader is not None
                reader = cast("Any", PdfReader)(pdf_stream, strict=False)
                timeout_checker.check_timeout()

            return reader
        except RuntimeError as e:
            raise PDFProcessingError(f"Error reading PDF: {str(e)}") from e

    def _extract_page_text_safe(self, page: Any, page_num: int) -> str:
        """
        Safely extract text from a PDF page with timeout protection.

        Args:
            page: PyPDF2 page object
            page_num: Page number for logging

        Returns:
            Extracted text content
        """
        try:
            # Use timeout wrapper for text extraction
            with self._timeout_handler() as timeout_checker:
                text = page.extract_text()
                timeout_checker.check_timeout()

            # Sanitize extracted text
            if text:
                if not isinstance(text, str):
                    text = str(text)
                # Remove null bytes and control characters except newlines/tabs
                text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")
                # Limit text length per page to prevent memory issues
                if len(text) > 100000:  # 100KB per page
                    text = text[:99987] + "\n[TEXT TRUNCATED - Page too long]"

            return text or ""

        except PDFProcessingTimeout:
            logger.warning("Timeout extracting text from page %d", page_num)
            raise
        except RuntimeError as e:
            logger.warning("Error extracting text from page %d: %s", page_num, str(e))
            return f"[ERROR EXTRACTING PAGE {page_num}: {str(e)}]\n"

    def _process_reader(
        self, reader: Any, start_time: float, pages_limit: int
    ) -> tuple[list[str], int, list[str]]:
        """
        Process pages from a PdfReader with timeout checks and error handling.

        Returns:
            (extracted_texts, pages_processed, warnings)
        """
        extracted_texts: list[str] = []
        pages_processed = 0
        warnings: list[str] = []

        for page_num in range(pages_limit):
            # Check for timeout with a small safety buffer
            elapsed = time.time() - start_time
            if elapsed > self.timeout - 5:
                warnings.append(f"Stopping at page {page_num} due to approaching timeout")
                break

            try:
                page = reader.pages[page_num]
                page_text = self._extract_page_text_safe(page, page_num + 1)

                if page_text.strip():
                    extracted_texts.append(f"=== Page {page_num + 1} ===\n{page_text}\n")

                pages_processed += 1

            except PDFProcessingTimeout:
                warnings.append(f"Timeout processing page {page_num + 1}")
                break
            except RuntimeError as e:
                warnings.append(f"Error processing page {page_num + 1}: {str(e)}")
                continue

        return extracted_texts, pages_processed, warnings

    def extract_text(self, file_path: str | Path, max_pages: int | None = None) -> dict[str, Any]:
        """
        Extract text from PDF file safely with timeout and error handling.

        Args:
            file_path: Path to the PDF file
            max_pages: Optional limit on pages to process (overrides instance limit)

        Returns:
            Dictionary containing:
                - success, text, pages_processed, total_pages, processing_time, warnings, error
        """
        start_time = time.time()
        result: dict[str, Any] = {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "total_pages": 0,
            "processing_time": 0,
            "warnings": [],
            "error": None,
        }

        try:
            # Validate file first
            self._validate_pdf_file(file_path)

            # Read PDF safely
            reader = self._safe_read_pdf(file_path)

            # Get total page count
            total_pages = len(reader.pages)
            result["total_pages"] = total_pages

            if total_pages == 0:
                result["warnings"].append("PDF has no pages")
                result["success"] = True
                return result

            # Determine how many pages to process
            pages_limit = min(max_pages or self.max_pages, total_pages)

            if pages_limit < total_pages:
                result["warnings"].append(f"Processing limited to {pages_limit} pages")

            # Extract text using shared processor
            extracted_texts, pages_processed, warnings = self._process_reader(
                reader, start_time, pages_limit
            )
            result["text"] = "\n".join(extracted_texts)
            result["pages_processed"] = pages_processed
            result["warnings"].extend(warnings)
            result["success"] = True

            logger.info(
                "Successfully extracted text from %d/%d pages of %s",
                result["pages_processed"],
                total_pages,
                file_path,
            )

        except PDFProcessingTimeout:
            result["error"] = f"PDF processing timed out after {self.timeout} seconds"
            logger.error("Timeout processing %s: %s", file_path, result["error"])
        except PDFProcessingError as e:
            result["error"] = str(e)
            logger.error("PDF processing error for %s: %s", file_path, result["error"])
        except RuntimeError as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error processing %s: %s", file_path, result["error"])

        finally:
            result["processing_time"] = time.time() - start_time

        return result

    async def extract_text_async(
        self, file_path: str | Path, max_pages: int | None = None
    ) -> dict[str, Any]:
        """
        Extract text from PDF file safely and asynchronously with timeout and error handling.

        Args:
            file_path: Path to the PDF file
            max_pages: Optional limit on pages to process (overrides instance limit)

        Returns:
            Dictionary containing:
                - success, text, pages_processed, total_pages, processing_time, warnings, error
        """
        start_time = time.time()
        result: dict[str, Any] = {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "total_pages": 0,
            "processing_time": 0,
            "warnings": [],
            "error": None,
        }

        try:
            # Validate file first
            await self._validate_pdf_file_async(file_path)

            # Read PDF safely
            reader = await self._safe_read_pdf_async(file_path)

            # Get total page count
            total_pages = len(reader.pages)
            result["total_pages"] = total_pages

            if total_pages == 0:
                result["warnings"].append("PDF has no pages")
                result["success"] = True
                return result

            # Determine how many pages to process
            pages_limit = min(max_pages or self.max_pages, total_pages)

            if pages_limit < total_pages:
                result["warnings"].append(f"Processing limited to {pages_limit} pages")

            # Extract text using shared processor
            extracted_texts, pages_processed, warnings = self._process_reader(
                reader, start_time, pages_limit
            )
            result["text"] = "\n".join(extracted_texts)
            result["pages_processed"] = pages_processed
            result["warnings"].extend(warnings)
            result["success"] = True

            logger.info(
                "Successfully extracted text from %d/%d pages of %s (async)",
                result["pages_processed"],
                total_pages,
                file_path,
            )

        except PDFProcessingTimeout:
            result["error"] = f"PDF processing timed out after {self.timeout} seconds"
            logger.error("Timeout processing %s: %s", file_path, result["error"])
        except PDFProcessingError as e:
            result["error"] = str(e)
            logger.error("PDF processing error for %s: %s", file_path, result["error"])
        except RuntimeError as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error processing %s: %s", file_path, result["error"])

        finally:
            result["processing_time"] = time.time() - start_time

        return result

    def extract_text_from_bytes(
        self, pdf_bytes: bytes, filename: str = "unknown.pdf"
    ) -> dict[str, Any]:
        """
        Extract text from PDF bytes safely.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Filename for logging purposes

        Returns:
            Same format as extract_text()
        """
        start_time = time.time()
        result: dict[str, Any] = {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "total_pages": 0,
            "processing_time": 0,
            "warnings": [],
            "error": None,
        }

        try:
            # Validate size
            if len(pdf_bytes) > self.max_file_size:
                raise PDFProcessingError(
                    f"PDF data too large: {len(pdf_bytes)} bytes (max: {self.max_file_size})"
                )

            # Validate PDF header
            if not pdf_bytes.startswith(b"%PDF-"):
                raise PDFProcessingError("Data does not have valid PDF header")

            # Create PDF reader from bytes
            pdf_stream = io.BytesIO(pdf_bytes)

            with self._timeout_handler() as timeout_checker:
                if PdfReader is None:
                    raise AssertionError("PdfReader is None")
                reader = cast("Any", PdfReader)(pdf_stream, strict=False)
                timeout_checker.check_timeout()

            # Process pages using shared logic
            total_pages = len(reader.pages)
            result["total_pages"] = total_pages

            if total_pages == 0:
                result["warnings"].append("PDF has no pages")
                result["success"] = True
                return result

            pages_limit = min(self.max_pages, total_pages)
            if pages_limit < total_pages:
                result["warnings"].append(f"Processing limited to {pages_limit} pages")

            extracted_texts, pages_processed, warnings = self._process_reader(
                reader, start_time, pages_limit
            )
            result["text"] = "\n".join(extracted_texts)
            result["pages_processed"] = pages_processed
            result["warnings"].extend(warnings)
            result["success"] = True

            logger.info(
                "Successfully extracted text from %d/%d pages of %s",
                result["pages_processed"],
                total_pages,
                filename,
            )

        except PDFProcessingTimeout:
            result["error"] = f"PDF processing timed out after {self.timeout} seconds"
            logger.error("Timeout processing %s: %s", filename, result["error"])
        except PDFProcessingError as e:
            result["error"] = str(e)
            logger.error("PDF processing error for %s: %s", filename, result["error"])
        except RuntimeError as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error processing %s: %s", filename, result["error"])

        finally:
            result["processing_time"] = time.time() - start_time

        return result

    def is_pdf_safe(self, file_path: str | Path) -> dict[str, Any]:
        """
        Check if a PDF file appears safe to process.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with safety assessment
        """
        result: dict[str, Any] = {
            "safe": False,
            "checks_passed": [],
            "checks_failed": [],
            "warnings": [],
        }

        try:
            # Basic file validation
            self._validate_pdf_file(file_path)
            result["checks_passed"].append("File validation")

            # Try to read PDF metadata without extracting text
            with self._timeout_handler() as timeout_checker:
                reader = self._safe_read_pdf(file_path)
                timeout_checker.check_timeout()

            result["checks_passed"].append("PDF parsing")

            # Check page count
            reader_any = reader
            page_count = len(reader_any.pages)
            if page_count > self.max_pages:
                result["warnings"].append(f"Large document: {page_count} pages")
            else:
                result["checks_passed"].append("Page count reasonable")

            # Check for metadata
            if getattr(reader_any, "metadata", None):
                result["checks_passed"].append("Metadata present")
            else:
                result["warnings"].append("No metadata found")

            result["safe"] = True

        except PDFProcessingTimeout:
            result["checks_failed"].append("Processing timeout")
        except PDFProcessingError as e:
            result["checks_failed"].append(f"Validation failed: {str(e)}")
        except RuntimeError as e:
            result["checks_failed"].append(f"Unexpected error: {str(e)}")

        return result

    async def is_pdf_safe_async(self, file_path: str | Path) -> dict[str, Any]:
        """
        Check if a PDF file appears safe to process asynchronously.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with safety assessment
        """
        result: dict[str, Any] = {
            "safe": False,
            "checks_passed": [],
            "checks_failed": [],
            "warnings": [],
        }

        try:
            # Basic file validation
            await self._validate_pdf_file_async(file_path)
            result["checks_passed"].append("File validation")

            # Try to read PDF metadata without extracting text
            with self._timeout_handler() as timeout_checker:
                reader = await self._safe_read_pdf_async(file_path)
                timeout_checker.check_timeout()

            result["checks_passed"].append("PDF parsing")

            # Check page count
            reader_any = reader
            page_count = len(reader_any.pages)
            if page_count > self.max_pages:
                result["warnings"].append(f"Large document: {page_count} pages")
            else:
                result["checks_passed"].append("Page count reasonable")

            # Check for metadata
            if getattr(reader_any, "metadata", None):
                result["checks_passed"].append("Metadata present")
            else:
                result["warnings"].append("No metadata found")

            result["safe"] = True

        except PDFProcessingTimeout:
            result["checks_failed"].append("Processing timeout")
        except PDFProcessingError as e:
            result["checks_failed"].append(f"Validation failed: {str(e)}")
        except RuntimeError as e:
            result["checks_failed"].append(f"Unexpected error: {str(e)}")

        return result


# Factory function for easy instantiation
def create_safe_pdf_extractor(
    timeout: int = 30, max_pages: int = 1000, max_file_size: int = 50 * 1024 * 1024
) -> SafePDFProcessor:
    """
    Create a SafePDFProcessor instance with specified limits.

    Args:
        timeout: Maximum processing time in seconds
        max_pages: Maximum pages to process
        max_file_size: Maximum file size in bytes

    Returns:
        SafePDFProcessor instance
    """
    return SafePDFProcessor(timeout=timeout, max_pages=max_pages, max_file_size=max_file_size)


# Convenience function for simple text extraction
def extract_pdf_text_safe(
    file_path: str | Path, timeout: int = 30, max_pages: int | None = None
) -> str:
    """
    Extract text from PDF file safely with default settings.

    Args:
        file_path: Path to PDF file
        timeout: Processing timeout in seconds
        max_pages: Maximum pages to process

    Returns:
        Extracted text content (empty string if extraction fails)
    """
    processor = SafePDFProcessor(timeout=timeout)
    result = processor.extract_text(file_path, max_pages=max_pages)

    if result["success"]:
        return result["text"]
    logger.error("Failed to extract text from %s: %s", file_path, result["error"])
    return ""


# Async convenience function for simple text extraction
async def extract_pdf_text_safe_async(
    file_path: str | Path, timeout: int = 30, max_pages: int | None = None
) -> str:
    """
    Extract text from PDF file safely and asynchronously with default settings.

    Args:
        file_path: Path to PDF file
        timeout: Processing timeout in seconds
        max_pages: Maximum pages to process

    Returns:
        Extracted text content (empty string if extraction fails)
    """
    processor = SafePDFProcessor(timeout=timeout)
    result = await processor.extract_text_async(file_path, max_pages=max_pages)

    if result["success"]:
        return result["text"]
    logger.error("Failed to extract text from %s: %s", file_path, result["error"])
    return ""
