import logging
from urllib.parse import quote

import httpx

from evidencesplit.config import settings
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class UnpaywallClient:
    async def resolve_pdf_urls(self, doi: str) -> list[str]:
        if not settings.UNPAYWALL_EMAIL or settings.UNPAYWALL_EMAIL == "admin@example.com":
            return []
        url = f"https://api.unpaywall.org/v2/{quote(doi, safe='')}"
        logger.info("external_request provider=unpaywall operation=resolve doi=%s", doi)
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            response = await client.get(url, params={"email": settings.UNPAYWALL_EMAIL})
        if response.status_code == 404:
            logger.info("external_miss provider=unpaywall operation=resolve doi=%s status=404", doi)
            return []
        if response.is_error:
            error = ProviderHTTPError.from_response("unpaywall", "resolve", response)
            logger.error(
                "external_failure provider=%s operation=%s status=%s doi=%s detail=%s",
                error.provider,
                error.operation,
                error.status_code,
                doi,
                error.detail,
            )
            raise error
        payload = response.json()
        locations = [payload.get("best_oa_location"), *(payload.get("oa_locations") or [])]
        urls: list[str] = []
        for location in locations:
            if not isinstance(location, dict):
                continue
            pdf_url = location.get("url_for_pdf")
            if pdf_url and pdf_url not in urls:
                urls.append(str(pdf_url))
        selected = urls[:3]
        logger.info("external_success provider=unpaywall operation=resolve doi=%s pdf_urls=%s", doi, len(selected))
        return selected
