from collections.abc import Sequence

import httpx

from evidencesplit.config import settings
from evidencesplit.evidence.prompts import EVIDENCE_SYSTEM_PROMPT, build_evidence_prompt
from evidencesplit.evidence.schemas import EvidenceBatchOutput, EvidenceFindingOutput
from evidencesplit.retrieval.schemas import RetrievedPassage


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

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return EvidenceBatchOutput.model_validate_json(text).findings
