import logging
from collections.abc import Sequence

import httpx

from evidencesplit.config import settings
from evidencesplit.evidence.prompts import EVIDENCE_SYSTEM_PROMPT, build_evidence_prompt
from evidencesplit.evidence.schemas import EvidenceBatchOutput, EvidenceFindingOutput
from evidencesplit.retrieval.schemas import RetrievedPassage
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class GeminiEvidenceAnalysisService:
    async def analyze_passages(
        self,
        *,
        claim: str,
        passages: Sequence[RetrievedPassage],
    ) -> list[EvidenceFindingOutput]:
        if not passages:
            return []
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for evidence analysis.")

        prompt = build_evidence_prompt(
            claim,
            [
                {
                    "chunk_id": str(passage.chunk_id),
                    "title": passage.title,
                    "source_type": passage.source_type.value,
                    "pages": f"{passage.page_start}-{passage.page_end}",
                    "content": passage.content,
                }
                for passage in passages
            ],
        )
        schema = EvidenceBatchOutput.model_json_schema()
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_GENERATION_MODEL}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": EVIDENCE_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }

        logger.info(
            "external_request provider=gemini operation=evidence_analysis passages=%s model=%s",
            len(passages),
            settings.GEMINI_GENERATION_MODEL,
        )
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=payload,
            )
        if response.is_error:
            error = ProviderHTTPError.from_response("gemini", "evidence_analysis", response)
            logger.error(
                "external_failure provider=%s operation=%s status=%s passages=%s detail=%s",
                error.provider,
                error.operation,
                error.status_code,
                len(passages),
                error.detail,
            )
            raise error
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        findings = EvidenceBatchOutput.model_validate_json(text).findings
        logger.info("external_success provider=gemini operation=evidence_analysis findings=%s", len(findings))
        return findings
