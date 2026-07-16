import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from evidencesplit.main import app
from evidencesplit.shared.types import AnalysisStatus
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository


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
