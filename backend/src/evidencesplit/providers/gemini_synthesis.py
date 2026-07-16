import json
import logging
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
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


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
        logger.info(
            "external_request provider=gemini operation=synthesis papers=%s findings=%s model=%s",
            len(papers),
            len(allowed_ids),
            settings.GEMINI_GENERATION_MODEL,
        )
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=payload,
            )
        if response.is_error:
            error = ProviderHTTPError.from_response("gemini", "synthesis", response)
            logger.error(
                "external_failure provider=%s operation=%s status=%s papers=%s detail=%s",
                error.provider,
                error.operation,
                error.status_code,
                len(papers),
                error.detail,
            )
            raise error
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        output = GeminiComparisonOutput.model_validate_json(text)
        report = format_comparison_report(output, allowed_ids)
        logger.info("external_success provider=gemini operation=synthesis assessment=%s", report.overall_assessment)
        return report
