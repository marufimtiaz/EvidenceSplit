from evidencesplit.config import settings
from evidencesplit.providers.gemini_embeddings import GeminiEmbeddingService
from evidencesplit.providers.gemini_evidence import GeminiEvidenceAnalysisService
from evidencesplit.providers.gemini_synthesis import GeminiSynthesisService
from evidencesplit.providers.openrouter_embeddings import OpenRouterEmbeddingService
from evidencesplit.providers.openrouter_generation import (
    OpenRouterEvidenceAnalysisService,
    OpenRouterSynthesisService,
)
from evidencesplit.providers.protocols import EmbeddingService, EvidenceAnalysisService, SynthesisService


def get_embedding_service() -> EmbeddingService:
    if settings.AI_PROVIDER == "gemini":
        return GeminiEmbeddingService()
    if settings.AI_PROVIDER == "openrouter":
        return OpenRouterEmbeddingService()
    raise ValueError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")


def get_evidence_analysis_service() -> EvidenceAnalysisService:
    if settings.AI_PROVIDER == "gemini":
        return GeminiEvidenceAnalysisService()
    if settings.AI_PROVIDER == "openrouter":
        return OpenRouterEvidenceAnalysisService()
    raise ValueError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")


def get_synthesis_service() -> SynthesisService:
    if settings.AI_PROVIDER == "gemini":
        return GeminiSynthesisService()
    if settings.AI_PROVIDER == "openrouter":
        return OpenRouterSynthesisService()
    raise ValueError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")
