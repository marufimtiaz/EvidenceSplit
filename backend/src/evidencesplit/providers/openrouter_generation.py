import json
import logging
from collections.abc import Sequence
from typing import Any

import httpx

from evidencesplit.config import settings
from evidencesplit.evidence.prompts import EVIDENCE_SYSTEM_PROMPT, build_evidence_prompt
from evidencesplit.evidence.schemas import EvidenceBatchOutput, EvidenceFindingOutput
from evidencesplit.retrieval.schemas import RetrievedPassage
from evidencesplit.shared.http_errors import ProviderHTTPError
from evidencesplit.synthesis.formatter import format_comparison_report
from evidencesplit.synthesis.prompts import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt
from evidencesplit.synthesis.schemas import (
    ComparisonReport,
    GeminiComparisonOutput,
    PaperForSynthesis,
)

logger = logging.getLogger(__name__)


def _strict_json_schema(value: Any) -> Any:
    if isinstance(value, dict):
        value.pop("default", None)
        properties = value.get("properties")
        if isinstance(properties, dict):
            value["additionalProperties"] = False
            value["required"] = list(properties)
        for child in value.values():
            _strict_json_schema(child)
    elif isinstance(value, list):
        for child in value:
            _strict_json_schema(child)
    return value


async def _chat_json(
    *,
    operation: str,
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict[str, Any],
) -> str:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter.")

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": _strict_json_schema(schema),
        },
    }
    async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            json={
                "model": settings.OPENROUTER_GENERATION_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
                "response_format": response_format,
                "provider": {"require_parameters": True},
            },
        )
    if response.is_error:
        error = ProviderHTTPError.from_response("openrouter", operation, response)
        logger.error(
            "external_failure provider=%s operation=%s status=%s model=%s detail=%s",
            error.provider,
            error.operation,
            error.status_code,
            settings.OPENROUTER_GENERATION_MODEL,
            error.detail,
        )
        raise error

    content = response.json()["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise RuntimeError("OpenRouter returned an unsupported structured response.")
    return content


class OpenRouterEvidenceAnalysisService:
    async def analyze_passages(
        self,
        *,
        claim: str,
        passages: Sequence[RetrievedPassage],
    ) -> list[EvidenceFindingOutput]:
        if not passages:
            return []
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
        logger.info(
            "external_request provider=openrouter operation=evidence_analysis passages=%s model=%s",
            len(passages),
            settings.OPENROUTER_GENERATION_MODEL,
        )
        content = await _chat_json(
            operation="evidence_analysis",
            system_prompt=EVIDENCE_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema_name="evidence_batch",
            schema=EvidenceBatchOutput.model_json_schema(),
        )
        findings = EvidenceBatchOutput.model_validate_json(content).findings
        logger.info(
            "external_success provider=openrouter operation=evidence_analysis findings=%s",
            len(findings),
        )
        return findings


class OpenRouterSynthesisService:
    async def synthesize(
        self,
        *,
        claim: str,
        papers: Sequence[PaperForSynthesis],
    ) -> ComparisonReport:
        allowed_ids = {finding.id for paper in papers for finding in paper.findings}
        prompt = build_synthesis_prompt(
            claim,
            json.dumps([paper.model_dump(mode="json") for paper in papers]),
        )
        logger.info(
            "external_request provider=openrouter operation=synthesis papers=%s findings=%s model=%s",
            len(papers),
            len(allowed_ids),
            settings.OPENROUTER_GENERATION_MODEL,
        )
        content = await _chat_json(
            operation="synthesis",
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema_name="comparison_report",
            schema=GeminiComparisonOutput.model_json_schema(),
        )
        output = GeminiComparisonOutput.model_validate_json(content)
        report = format_comparison_report(output, allowed_ids)
        logger.info(
            "external_success provider=openrouter operation=synthesis assessment=%s",
            report.overall_assessment,
        )
        return report
