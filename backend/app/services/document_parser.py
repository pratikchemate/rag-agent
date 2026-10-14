"""Document parsing service supporting PDF, TXT, Markdown, and DOCX."""

import hashlib
import io
from dataclasses import dataclass
from typing import List, Optional

import pymupdf
from docx import Document as DocxDocument

from app.core.config import get_settings
from app.core.errors import BadRequestError, PayloadTooLargeError, UnsupportedMediaTypeError


@dataclass
class ParsedPage:
    """Extracted text page with optional page number."""

    page_number: Optional[int]
    text: str


@dataclass
class ParsedDocument:
    """Result of document parsing."""

    filename: str
    content_type: str
    checksum_sha256: str
    file_size_bytes: int
    pages: List[ParsedPage]


class DocumentParser:
    """Validates and parses uploaded documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}
    SUPPORTED_MIME_TYPES = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # Fallback for some browsers
    }

    @classmethod
    def validate_file_format(
        cls,
        filename: str,
        content: bytes,
        declared_content_type: Optional[str] = None,
    ) -> str:
        """Validate filename extension, MIME type, and magic bytes before ingestion.

        Returns the resolved MIME type or raises UnsupportedMediaTypeError.
        """
        clean_filename = filename.strip()
        lower_name = clean_filename.lower()
        ext = None
        for candidate_ext in cls.SUPPORTED_EXTENSIONS:
            if lower_name.endswith(candidate_ext):
                ext = candidate_ext
                break

        if not ext:
            raise UnsupportedMediaTypeError(
                f"Unsupported file extension for '{filename}'. Allowed extensions: {', '.join(sorted(cls.SUPPORTED_EXTENSIONS))}"
            )

        # Magic bytes and signature inspection
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise UnsupportedMediaTypeError(
                    "Invalid PDF file: Missing %PDF- file header signature."
                )
            return "application/pdf"
        elif ext == ".docx":
            if not content.startswith(b"PK\x03\x04"):
                raise UnsupportedMediaTypeError(
                    "Invalid DOCX file: Missing PK archive file signature."
                )
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in (".txt", ".md", ".markdown"):
            if b"\x00" in content[:1024]:
                raise UnsupportedMediaTypeError(
                    "Binary content detected in plain text/markdown file."
                )
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content.decode("latin-1")
                except Exception:
                    raise UnsupportedMediaTypeError(
                        "Text file encoding is not valid UTF-8 or Latin-1."
                    )
            return "text/markdown" if ext in (".md", ".markdown") else "text/plain"

        return declared_content_type or "application/octet-stream"

    @classmethod
    def validate_and_parse(
        cls,
        filename: str,
        content: bytes,
        declared_content_type: Optional[str] = None,
    ) -> ParsedDocument:
        """Validate format/size and extract text page by page."""
        settings = get_settings()
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

        # 1. Size Validation
        file_size = len(content)
        if file_size > max_bytes:
            raise PayloadTooLargeError(
                f"File size {file_size / (1024 * 1024):.2f}MB exceeds limit of {settings.MAX_UPLOAD_MB}MB."
            )
        if file_size == 0:
            raise BadRequestError("Uploaded file is empty.")

        # 2. Extension, MIME Type, and Magic Bytes Check
        effective_mime = cls.validate_file_format(filename, content, declared_content_type)
        clean_filename = filename.strip()
        lower_name = clean_filename.lower()
        ext = next(c for c in cls.SUPPORTED_EXTENSIONS if lower_name.endswith(c))

        # 3. Compute SHA256 Checksum
        checksum = hashlib.sha256(content).hexdigest()

        # 4. Extract Text by Type
        pages: List[ParsedPage] = []
        if ext == ".pdf":
            pages = cls._parse_pdf(content)
        elif ext in (".txt", ".md", ".markdown"):
            pages = cls._parse_text(content)
        elif ext == ".docx":
            pages = cls._parse_docx(content)

        # 5. Sanity check extracted content
        total_chars = sum(len(p.text.strip()) for p in pages)
        if total_chars == 0:
            raise BadRequestError(
                "No readable text could be extracted from document. Scanned documents and image-only PDFs are not supported."
            )

        return ParsedDocument(
            filename=clean_filename,
            content_type=effective_mime,
            checksum_sha256=checksum,
            file_size_bytes=file_size,
            pages=pages,
        )

    @staticmethod
    def _parse_pdf(content: bytes) -> List[ParsedPage]:
        """Extract PDF text page by page preserving page numbering."""
        pages: List[ParsedPage] = []
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text("text") or ""
                pages.append(ParsedPage(page_number=page_idx + 1, text=text))
            doc.close()
        except Exception as e:
            raise BadRequestError(f"Corrupted or invalid PDF file: {str(e)}")
        return pages

    @staticmethod
    def _parse_text(content: bytes) -> List[ParsedPage]:
        """Extract plain text or markdown as single page."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as e:
                raise BadRequestError(f"Unable to decode text file: {str(e)}")
        return [ParsedPage(page_number=None, text=text)]

    @staticmethod
    def _parse_docx(content: bytes) -> List[ParsedPage]:
        """Extract docx paragraphs into combined text."""
        try:
            stream = io.BytesIO(content)
            doc = DocxDocument(stream)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)
            return [ParsedPage(page_number=None, text=text)]
        except Exception as e:
            raise BadRequestError(f"Corrupted or invalid DOCX file: {str(e)}")
