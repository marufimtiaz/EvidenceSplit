import json
from typing import Any

import httpx


def _response_detail(response: httpx.Response) -> str:
    try:
        payload: Any = response.json()
        if isinstance(payload, dict):
            payload = payload.get("error") or payload.get("message") or payload
        detail = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    except (ValueError, TypeError):
        detail = response.text
    return " ".join(detail.split())[:1200] or "No provider response body."


class ProviderHTTPError(RuntimeError):
    def __init__(self, provider: str, operation: str, status_code: int, detail: str) -> None:
        self.provider = provider
        self.operation = operation
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{provider} {operation} failed with HTTP {status_code}: {detail}")

    @classmethod
    def from_response(cls, provider: str, operation: str, response: httpx.Response) -> "ProviderHTTPError":
        return cls(provider, operation, response.status_code, _response_detail(response))
