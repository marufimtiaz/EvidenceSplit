import os
import pytest
import fitz
from evidencesplit.documents.pdf_parser import PDFParser
from evidencesplit.documents.chunker import Chunker, ParsedPage


def create_test_pdf(file_path: str, pages_content: list[str]) -> None:
    doc = fitz.open()
    for content in pages_content:
        page = doc.new_page()
        if content:
            page.insert_text((50, 50), content)
    doc.save(file_path)
    doc.close()


@pytest.mark.anyio
async def test_pdf_parser_valid(tmp_path: str) -> None:
    pdf_path = os.path.join(tmp_path, "test.pdf")
    pages_text = [
        "Introduction\nThis is page one content about the method.",
        "Results\nThis is page two content detailing results.",
    ]
    create_test_pdf(pdf_path, pages_text)

    pages, warning = PDFParser.parse_pdf(pdf_path, "test.pdf")
    assert warning is None
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Introduction" in pages[0].text
    assert pages[1].page_number == 2
    assert "Results" in pages[1].text


@pytest.mark.anyio
async def test_pdf_parser_ocr_scanned(tmp_path: str) -> None:
    pdf_path = os.path.join(tmp_path, "scanned.pdf")
    # Empty pages (representing a scanned PDF without text layer)
    create_test_pdf(pdf_path, ["", ""])

    with pytest.raises(ValueError, match="Scanned-document OCR is not supported"):
        PDFParser.parse_pdf(pdf_path, "scanned.pdf")


@pytest.mark.anyio
async def test_chunker_basic() -> None:
    pages = [
        ParsedPage(page_number=1, text="Introduction\nThis is page 1 text. " * 300),  # ~600 words
        ParsedPage(page_number=2, text="Results\nThis is page 2 text. " * 300),  # ~600 words
    ]
    chunks = Chunker.chunk_document(pages)
    assert len(chunks) > 0
    assert chunks[0].page_start == 1
    # Check section detection
    assert chunks[0].section == "Introduction"
