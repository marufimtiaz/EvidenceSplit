import uuid
from fastapi import APIRouter, Depends, Form, File, UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.database import get_db
from evidencesplit.analyses.service import AnalysisService
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.analyses.schemas import AnalysisRead

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("")
async def create_analysis(
    background_tasks: BackgroundTasks,
    claim: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    analysis = await AnalysisService.trigger_analysis(db, claim, background_tasks)
    return {"analysis_id": str(analysis.id), "status": analysis.status}


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisRead:
    analysis = await AnalysisRepository.get(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRead.model_validate(analysis)
