import pytest
import asyncio
import os
import uuid
import fitz
from httpx import AsyncClient, ASGITransport
from evidencesplit.main import app
from evidencesplit.shared.types import AnalysisStatus, SourceType
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.documents.repository import DocumentRepository
from evidencesplit.documents.models import Chunk
from sqlalchemy import select


@pytest.mark.anyio
async def test_async_create_analysis_endpoint() -> None:
    # Test POST /api/analyses and GET /api/analyses/{id}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/analyses", data={"claim": "Test claim"})
        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == AnalysisStatus.QUEUED
        analysis_id = data["analysis_id"]

        response = await ac.get(f"/api/analyses/{analysis_id}")
        assert response.status_code == 200
        assert response.json()["claim"] == "Test claim"


@pytest.mark.anyio
async def test_sse_progress_streaming() -> None:
    # Create analysis manually in the database to test the SSE stream independently
    async with async_session() as session:
        analysis = await AnalysisRepository.create(session, "Test claim")
        analysis_id = analysis.id

    async def simulate_db_updates():
        # Wait briefly for the client to establish the connection
        await asyncio.sleep(0.1)
        stages = [
            (AnalysisStatus.PROCESSING_UPLOADS, 10),
            (AnalysisStatus.SEARCHING, 25),
            (AnalysisStatus.COMPLETED, 100),
        ]
        for status, progress in stages:
            async with async_session() as session:
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=status,
                    progress=progress,
                    completed=(status == AnalysisStatus.COMPLETED),
                )
            await asyncio.sleep(0.1)

    async def read_sse_stream():
        events = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            async with ac.stream("GET", f"/api/analyses/{analysis_id}/events") as stream:
                async for line in stream.aiter_lines():
                    if line:
                        events.append(line)
                        if "event: completed" in line:
                            break
        return events

    # Run database updates and SSE streaming concurrently
    _, events = await asyncio.gather(simulate_db_updates(), read_sse_stream())

    assert len(events) > 0
    assert any("event: progress" in e for e in events)
    assert any("event: completed" in e for e in events)


def local_create_test_pdf(file_path: str, pages_content: list[str]) -> None:
    doc = fitz.open()
    for content in pages_content:
        page = doc.new_page()
        if content:
            page.insert_text((50, 50), content)
    doc.save(file_path)
    doc.close()


@pytest.mark.anyio
async def test_async_create_analysis_with_uploads(tmp_path: str) -> None:
    # 1. Create a test PDF

    pdf_path = os.path.join(tmp_path, "upload_test.pdf")
    local_create_test_pdf(pdf_path, ["Introduction\nThis is uploaded PDF content. " * 100])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Open file to post
        with open(pdf_path, "rb") as f:
            files = {"files": ("upload_test.pdf", f, "application/pdf")}
            response = await ac.post(
                "/api/analyses",
                data={"claim": "Test upload claim"},
                files=files,
            )

        assert response.status_code == 200
        data = response.json()
        analysis_id = data["analysis_id"]
        assert data["status"] == AnalysisStatus.QUEUED

        # Stream SSE events to completion
        events = []
        async with ac.stream("GET", f"/api/analyses/{analysis_id}/events") as stream:
            async for line in stream.aiter_lines():
                if line:
                    events.append(line)
                    if "event: completed" in line:
                        break

        assert len(events) > 0
        assert any("event: completed" in e for e in events)

        # 2. Verify Database Records
        async with async_session() as session:
            docs = await DocumentRepository.get_documents_by_analysis(session, uuid.UUID(analysis_id))
            assert len(docs) == 1
            assert docs[0].title == "upload_test.pdf"
            assert docs[0].source_type == SourceType.UPLOADED_PDF
            assert docs[0].processing_status == "COMPLETED"

            # Check chunks are created
            res = await session.execute(select(Chunk).where(Chunk.document_id == docs[0].id))
            chunks = res.scalars().all()
            assert len(chunks) > 0
            assert "uploaded PDF content" in chunks[0].content
            assert chunks[0].page_start == 1
