"""Unit tests for document parsing and text chunking."""

import io

import pymupdf
import pytest
from docx import Document as DocxDocument

from app.core.errors import BadRequestError, UnsupportedMediaTypeError
from app.services.chunking import ChunkingService
from app.services.document_parser import DocumentParser, ParsedDocument, ParsedPage


def create_test_pdf_bytes(pages_text: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with known pages."""
    doc = pymupdf.open()
    for text_content in pages_text:
        page = doc.new_page()
        page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_test_docx_bytes(paragraphs: list[str]) -> bytes:
    """Helper to generate an in-memory DOCX file."""
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


def test_parse_text_and_markdown():
    """Verify text and markdown parsing."""
    raw_text = "This is a simple plain text document for testing."
    parsed = DocumentParser.validate_and_parse("guide.txt", raw_text.encode("utf-8"))
    assert parsed.filename == "guide.txt"
    assert len(parsed.pages) == 1
    assert parsed.pages[0].page_number is None
    assert parsed.pages[0].text == raw_text


def test_parse_pdf_preserves_page_numbers():
    """Verify PDF parsing retains 1-based page numbers."""
    page_1 = "Payment API Documentation - Page 1 content"
    page_2 = "Retry Policy Configuration - Page 2 content"
    pdf_bytes = create_test_pdf_bytes([page_1, page_2])

    parsed = DocumentParser.validate_and_parse("manual.pdf", pdf_bytes)
    assert parsed.filename == "manual.pdf"
    assert len(parsed.pages) == 2
    assert parsed.pages[0].page_number == 1
    assert "Page 1 content" in parsed.pages[0].text
    assert parsed.pages[1].page_number == 2
    assert "Page 2 content" in parsed.pages[1].text


def test_parse_docx():
    """Verify DOCX parsing extracts paragraphs."""
    docx_bytes = create_test_docx_bytes(["Heading 1", "Paragraph content inside docx."])
    parsed = DocumentParser.validate_and_parse("notes.docx", docx_bytes)
    assert len(parsed.pages) == 1
    assert "Paragraph content inside docx." in parsed.pages[0].text


def test_unsupported_extension_rejected():
    """Verify unsupported file formats raise 415."""
    with pytest.raises(UnsupportedMediaTypeError):
        DocumentParser.validate_and_parse("archive.zip", b"fake zip binary data")


def test_empty_file_rejected():
    """Verify empty file raises 400."""
    with pytest.raises(BadRequestError, match="Uploaded file is empty"):
        DocumentParser.validate_and_parse("empty.txt", b"")


def test_chunker_preserves_page_metadata():
    """Verify chunking preserves page numbers and index ordering."""
    parsed_doc = ParsedDocument(
        filename="manual.pdf",
        content_type="application/pdf",
        checksum_sha256="abc123",
        file_size_bytes=1000,
        pages=[
            ParsedPage(page_number=1, text="First page content sentence."),
            ParsedPage(page_number=2, text="Second page content sentence."),
        ],
    )

    chunker = ChunkingService(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(parsed_doc)

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert "First page" in chunks[0].content
    assert chunks[1].page_number == 2
    assert chunks[1].chunk_index == 1
    assert "Second page" in chunks[1].content
