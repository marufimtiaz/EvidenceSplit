from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from evidencesplit.database import get_db
from evidencesplit.config import settings

app = FastAPI(title="EvidenceSplit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str | dict[str, bool]]:
    try:
        result = await db.execute(text("SELECT 1"))
        result.all()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "environment": {
            "database_configured": bool(settings.DATABASE_URL),
            "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
        },
    }
