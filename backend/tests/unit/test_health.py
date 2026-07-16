from fastapi.testclient import TestClient
from evidencesplit.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "environment" in data
    # Environment keys should be present
    env = data["environment"]
    assert "database_configured" in env
    assert "gemini_api_key_configured" in env
