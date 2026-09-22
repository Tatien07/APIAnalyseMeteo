from fastapi.testclient import TestClient

from energy_weather.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_openapi_is_available() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Energy Weather Monitor"
    assert response.headers["X-Request-ID"]
