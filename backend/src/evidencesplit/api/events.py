import asyncio
import json
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.shared.types import AnalysisStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analyses", tags=["events"])


@router.get("/{analysis_id}/events")
async def stream_analysis_events(analysis_id: uuid.UUID) -> StreamingResponse:
    # Verify first if the analysis exists
    async with async_session() as db:
        analysis = await AnalysisRepository.get(db, analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        last_status = None

        last_progress = -1
        while True:
            async with async_session() as db:
                analysis = await AnalysisRepository.get(db, analysis_id)
                if not analysis:
                    break

                if analysis.status != last_status or analysis.progress != last_progress:
                    last_status = analysis.status
                    last_progress = analysis.progress

                    stage_messages = {
                        AnalysisStatus.QUEUED: "Job queued",
                        AnalysisStatus.PROCESSING_UPLOADS: "Processing uploaded documents",
                        AnalysisStatus.SEARCHING: "Searching scholarly sources",
                        AnalysisStatus.FETCHING_FULL_TEXT: "Fetching open-access full text",
                        AnalysisStatus.INDEXING: "Indexing and normalization",
                        AnalysisStatus.RETRIEVING: "Retrieving relevant passages",
                        AnalysisStatus.ANALYZING_EVIDENCE: "Analyzing evidence findings",
                        AnalysisStatus.SYNTHESIZING: "Synthesizing report comparison",
                        AnalysisStatus.COMPLETED: "Analysis completed",
                        AnalysisStatus.COMPLETED_WITH_WARNINGS: "Analysis completed with warnings",
                        AnalysisStatus.FAILED: "Analysis failed",
                    }
                    message = stage_messages.get(analysis.status, "Processing")

                    event_data = {
                        "stage": analysis.status,
                        "progress": analysis.progress,
                        "message": message,
                    }
                    if analysis.error_message:
                        event_data["error"] = analysis.error_message
                    if analysis.warning_message:
                        event_data["warning"] = analysis.warning_message

                    event_type = "progress"
                    if analysis.status in [
                        AnalysisStatus.COMPLETED,
                        AnalysisStatus.COMPLETED_WITH_WARNINGS,
                        AnalysisStatus.FAILED,
                    ]:
                        event_type = analysis.status.lower()

                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                if analysis.status in [
                    AnalysisStatus.COMPLETED,
                    AnalysisStatus.COMPLETED_WITH_WARNINGS,
                    AnalysisStatus.FAILED,
                ]:
                    break

            await asyncio.sleep(0.2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
