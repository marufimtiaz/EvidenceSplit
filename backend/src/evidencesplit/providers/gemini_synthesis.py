import json
from collections.abc import Sequence

import httpx

from evidencesplit.config import settings
from evidencesplit.synthesis.formatter import format_comparison_report
from evidencesplit.synthesis.prompts import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt
from evidencesplit.synthesis.schemas import (
    ComparisonReport,
    GeminiComparisonOutput,
    PaperForSynthesis,
)


class GeminiSynthesisService:
    async def synthesize(
        self,
        *,
        claim: str,
        papers: Sequence[PaperForSynthesis],
    ) -> ComparisonReport:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for synthesis.")
        allowed_ids = {finding.id for paper in papers for finding in paper.findings}
        prompt = build_synthesis_prompt(
            claim,
            json.dumps([paper.model_dump(mode="json") for paper in papers]),
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_GENERATION_MODEL}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": SYNTHESIS_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": GeminiComparisonOutput.model_json_schema(),
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
        output = GeminiComparisonOutput.model_validate_json(text)
        return format_comparison_report(output, allowed_ids)
