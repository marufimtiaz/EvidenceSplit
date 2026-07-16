import os
import shutil
import uuid
from fastapi import APIRouter, Depends, Form, File, UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.database import get_db
from evidencesplit.analyses.service import AnalysisService
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.analyses.schemas import AnalysisRead
from evidencesplit.config import settings

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("")
async def create_analysis(
    background_tasks: BackgroundTasks,
    claim: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # 1. Filter out empty files and validate upload count limit
    valid_files = [f for f in files if f.filename]
    if len(valid_files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {settings.MAX_UPLOAD_FILES} uploaded PDFs is allowed.",
        )

    # 2. Validate extensions
    for f in valid_files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} is not a valid PDF file.",
            )

    # 3. Store uploaded files temporarily inside workspace temp folder
    temp_dir = "/home/maruf/Projects/EvidenceSplit/backend/temp"
    os.makedirs(temp_dir, exist_ok=True)

    uploaded_files = []
    for f in valid_files:
        if not f.filename:
            continue
        unique_filename = f"{uuid.uuid4()}_{f.filename}"
        file_path = os.path.join(temp_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        uploaded_files.append((file_path, f.filename))

    analysis = await AnalysisService.trigger_analysis(db, claim, uploaded_files, background_tasks)
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
