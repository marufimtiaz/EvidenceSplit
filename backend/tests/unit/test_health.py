import pytest
from httpx import AsyncClient, ASGITransport
from evidencesplit.main import app


@pytest.mark.anyio
async def test_health_check_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "environment" in data
        # Environment keys should be present
        env = data["environment"]
        assert "database_configured" in env
        assert "gemini_api_key_configured" in env
