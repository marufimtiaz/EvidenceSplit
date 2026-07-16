from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from evidencesplit.api.analyses import stage_upload


def upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.anyio
async def test_stage_upload_rejects_invalid_file_without_raising() -> None:
    staged, warning = await stage_upload(upload("notes.txt", "text/plain", b"not pdf"))

    assert staged is None
    assert warning == "notes.txt: only PDF files are supported."


@pytest.mark.anyio
async def test_stage_upload_keeps_pdf_metadata() -> None:
    staged, warning = await stage_upload(upload("paper.pdf", "application/pdf", b"%PDF-test"))

    assert warning is None
    assert staged is not None
    path, filename, content_type = staged
    assert filename == "paper.pdf"
    assert content_type == "application/pdf"

    import os

    os.unlink(path)
