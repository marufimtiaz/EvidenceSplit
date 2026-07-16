import asyncio
import logging
import math
from collections.abc import Sequence

import httpx

from evidencesplit.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    def __init__(self) -> None:
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], task_type="FACT_VERIFICATION"))[0]

    async def _embed(self, texts: Sequence[str], *, task_type: str) -> list[list[float]]:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for embeddings.")
        embeddings: list[list[float]] = []
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents"
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY}

        async with httpx.AsyncClient(timeout=30) as client:
            for start in range(0, len(texts), 20):
                batch = texts[start : start + 20]
                payload = {
                    "requests": [
                        {
                            "model": f"models/{self.model}",
                            "content": {"parts": [{"text": text}]},
                            "taskType": task_type,
                            "outputDimensionality": self.dimensions,
                        }
                        for text in batch
                    ]
                }
                for attempt in range(4):
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code != 429 or attempt == 3:
                        break
                    retry_after = response.headers.get("retry-after")
                    try:
                        delay = float(retry_after) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    delay = min(max(delay, 1), 30)
                    logger.warning("Gemini embedding rate limit reached; retrying in %.1fs", delay)
                    await asyncio.sleep(delay)
                response.raise_for_status()
                values = [item["values"] for item in response.json()["embeddings"]]
                embeddings.extend(self._normalize(vector) for vector in values)

        return embeddings

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
