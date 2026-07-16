import asyncio
import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, Form, File, UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.database import get_db
from evidencesplit.analyses.service import AnalysisService
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.analyses.schemas import AnalysisRead
from evidencesplit.config import settings

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

StagedUpload = tuple[str, str, str]


async def stage_upload(upload: UploadFile) -> tuple[StagedUpload | None, str | None]:
    filename = upload.filename or "unnamed file"
    if not filename.lower().endswith(".pdf") or upload.content_type != "application/pdf":
        await upload.close()
        return None, f"{filename}: only PDF files are supported."

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    size = 0
    staged = False
    try:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                return None, f"{filename}: file exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
            await asyncio.to_thread(temp_file.write, chunk)
        staged = True
        return (temp_file.name, filename, upload.content_type), None
    finally:
        temp_file.close()
        await upload.close()
        if not staged and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@router.post("")
async def create_analysis(
    background_tasks: BackgroundTasks,
    claim: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not claim.strip():
        raise HTTPException(status_code=400, detail="Claim must not be blank.")

    # 1. Filter out empty files and validate upload count limit
    valid_files = [f for f in files if f.filename]
    if len(valid_files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {settings.MAX_UPLOAD_FILES} uploaded PDFs is allowed.",
        )

    uploaded_files: list[StagedUpload] = []
    staging_warnings: list[str] = []
    for f in valid_files:
        staged, warning = await stage_upload(f)
        if staged:
            uploaded_files.append(staged)
        if warning:
            staging_warnings.append(warning)

    try:
        analysis = await AnalysisService.trigger_analysis(db, claim, uploaded_files, staging_warnings, background_tasks)
    except Exception:
        for file_path, _, _ in uploaded_files:
            if os.path.exists(file_path):
                os.unlink(file_path)
        raise
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
