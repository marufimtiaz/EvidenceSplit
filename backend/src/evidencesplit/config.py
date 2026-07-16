from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5435/evidencesplit")
    GEMINI_API_KEY: str = Field(default="")
    OPENALEX_API_KEY: str = Field(default="")
    UNPAYWALL_EMAIL: str = Field(default="admin@example.com")

    # Other pipeline configuration limits
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001")
    EMBEDDING_DIMENSIONS: int = Field(default=384)
    MAX_UPLOAD_FILES: int = Field(default=5)
    MAX_UPLOAD_SIZE_MB: int = Field(default=20)
    MAX_PDF_PAGES: int = Field(default=100)
    OPENALEX_RESULT_LIMIT: int = Field(default=8)
    MAX_LIVE_FULL_TEXT_PAPERS: int = Field(default=5)
    MAX_PASSAGES_PER_DOCUMENT: int = Field(default=4)
    MAX_TOTAL_PASSAGES: int = Field(default=20)
    REMOTE_DOWNLOAD_TIMEOUT_SECONDS: int = Field(default=20)
    MAX_REMOTE_PDF_SIZE_MB: int = Field(default=25)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
