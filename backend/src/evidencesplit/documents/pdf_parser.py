import os
import fitz  # PyMuPDF
from pydantic import BaseModel
from evidencesplit.config import settings


class ParsedPage(BaseModel):
    page_number: int
    text: str


class PDFParser:
    @staticmethod
    def parse_pdf(file_path: str, filename: str) -> tuple[list[ParsedPage], str | None]:
        # Validate size
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(f"File {filename} exceeds the maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB.")

        # Validate PDF header (MIME check)
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                raise ValueError(f"File {filename} is not a valid PDF file.")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF {filename}: {str(e)}")

        page_count = doc.page_count
        if page_count > settings.MAX_PDF_PAGES:
            doc.close()
            raise ValueError(f"File {filename} exceeds the maximum page limit of {settings.MAX_PDF_PAGES} pages.")

        parsed_pages = []
        total_text_length = 0

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text()
            parsed_pages.append(ParsedPage(page_number=page_num + 1, text=text))
            total_text_length += len(text.strip())

        doc.close()

        warning_message = None
        # OCR Check: Check if PDF has minimal text
        if total_text_length < 20 or (total_text_length / page_count) < 10:
            warning_message = (
                "This PDF appears to contain little or no extractable text. "
                "Scanned-document OCR is not supported in this version."
            )

        return parsed_pages, warning_message
