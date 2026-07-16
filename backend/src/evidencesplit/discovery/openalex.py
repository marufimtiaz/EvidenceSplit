import logging
import re
from collections.abc import Mapping
from typing import Any

import httpx

from evidencesplit.config import settings
from evidencesplit.discovery.schemas import CandidatePaper
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


def rebuild_abstract(index: Mapping[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positioned = sorted((position, word) for word, positions in index.items() for position in positions)
    abstract = " ".join(word for _, word in positioned).strip()
    return abstract or None


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.IGNORECASE)
    return normalized.lower() or None


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def relevance_score(claim: str, title: str, abstract: str | None, rank: int) -> float:
    claim_terms = set(re.findall(r"[a-z0-9]+", claim.lower()))
    text_terms = set(re.findall(r"[a-z0-9]+", f"{title} {abstract or ''}".lower()))
    overlap = len(claim_terms & text_terms) / max(len(claim_terms), 1)
    return 0.85 * overlap + 0.15 / (rank + 1)


class OpenAlexClient:
    async def search(self, claim: str) -> list[CandidatePaper]:
        if not settings.OPENALEX_API_KEY:
            raise RuntimeError("OPENALEX_API_KEY is required for live discovery.")

        params = {
            "api_key": settings.OPENALEX_API_KEY,
            "search.exact": claim,
            "per_page": min(max(settings.OPENALEX_RESULT_LIMIT * 3, 10), 50),
        }
        logger.info(
            "external_request provider=openalex operation=search query_chars=%s requested_results=%s",
            len(claim),
            params["per_page"],
        )
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            response = await client.get("https://api.openalex.org/works", params=params)
        if response.is_error:
            error = ProviderHTTPError.from_response("openalex", "search", response)
            logger.error(
                "external_failure provider=%s operation=%s status=%s detail=%s",
                error.provider,
                error.operation,
                error.status_code,
                error.detail,
            )
            raise error

        candidates: list[CandidatePaper] = []
        seen: set[str] = set()
        for rank, raw in enumerate(response.json().get("results", [])):
            if not isinstance(raw, dict) or raw.get("is_retracted"):
                continue
            title = str(raw.get("title") or raw.get("display_name") or "").strip()
            if not title:
                continue
            doi = normalize_doi(raw.get("doi"))
            dedupe_key = f"doi:{doi}" if doi else f"title:{normalize_title(title)}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            abstract = rebuild_abstract(raw.get("abstract_inverted_index"))
            authors = []
            for item in raw.get("authorships", []):
                if not isinstance(item, dict):
                    continue
                author = item.get("author") or {}
                if author.get("display_name"):
                    authors.append(str(author["display_name"]))
            primary_location: dict[str, Any] = raw.get("primary_location") or {}
            source_url = primary_location.get("landing_page_url") or raw.get("doi") or raw.get("id")
            candidates.append(
                CandidatePaper(
                    openalex_id=str(raw.get("id") or ""),
                    title=title,
                    authors=authors,
                    year=raw.get("publication_year"),
                    doi=doi,
                    abstract=abstract,
                    source_url=source_url,
                    relevance_score=relevance_score(claim, title, abstract, rank),
                )
            )

        candidates.sort(key=lambda item: item.relevance_score, reverse=True)
        selected = candidates[: settings.OPENALEX_RESULT_LIMIT]
        logger.info(
            "external_success provider=openalex operation=search raw_results=%s selected_results=%s",
            len(response.json().get("results", [])),
            len(selected),
        )
        return selected
