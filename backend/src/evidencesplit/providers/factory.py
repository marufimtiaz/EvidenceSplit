from evidencesplit.providers.gemini_embeddings import GeminiEmbeddingService
from evidencesplit.providers.gemini_evidence import GeminiEvidenceAnalysisService
from evidencesplit.providers.gemini_synthesis import GeminiSynthesisService
from evidencesplit.providers.protocols import EmbeddingService, EvidenceAnalysisService, SynthesisService


def get_embedding_service() -> EmbeddingService:
    return GeminiEmbeddingService()


def get_evidence_analysis_service() -> EvidenceAnalysisService:
    return GeminiEvidenceAnalysisService()


def get_synthesis_service() -> SynthesisService:
    return GeminiSynthesisService()
