import logging
import math
from collections.abc import Sequence

import httpx

from evidencesplit.config import settings
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class OpenRouterEmbeddingService:
    def __init__(self) -> None:
        self.model = settings.OPENROUTER_EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed(texts, input_type="search_document")

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], input_type="search_query"))[0]

    async def _embed(self, texts: Sequence[str], *, input_type: str) -> list[list[float]]:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter.")

        logger.info(
            "external_request provider=openrouter operation=embed input_type=%s inputs=%s batches=%s model=%s",
            input_type,
            len(texts),
            math.ceil(len(texts) / 20),
            self.model,
        )
        embeddings: list[list[float]] = []
        headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            for start in range(0, len(texts), 20):
                response = await client.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json={
                        "model": self.model,
                        "input": list(texts[start : start + 20]),
                        "dimensions": self.dimensions,
                        "input_type": input_type,
                    },
                )
                if response.is_error:
                    error = ProviderHTTPError.from_response("openrouter", "embed", response)
                    logger.error(
                        "external_failure provider=%s operation=%s status=%s batch_start=%s model=%s detail=%s",
                        error.provider,
                        error.operation,
                        error.status_code,
                        start,
                        self.model,
                        error.detail,
                    )
                    raise error
                data = sorted(response.json()["data"], key=lambda item: item["index"])
                embeddings.extend(self._normalize(item["embedding"]) for item in data)

        logger.info(
            "external_success provider=openrouter operation=embed vectors=%s model=%s",
            len(embeddings),
            self.model,
        )
        return embeddings

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
