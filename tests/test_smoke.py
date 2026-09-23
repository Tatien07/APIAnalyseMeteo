import httpx
import pytest

from energy_weather.smoke import run_smoke_test


def test_smoke_test_validates_the_deployed_services() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payloads = {
            "/api/v1/health": {"status": "ok"},
            "/api/v1/ready": {"status": "ready", "database": "up"},
            "/api/v1/data-freshness": {
                "status": "healthy",
                "weather": {"status": "fresh"},
                "energy": {"status": "fresh"},
            },
            "/api/v1/analytics/weather-energy": {"points_count": 12},
        }
        if request.url.host == "dashboard.example.test":
            return httpx.Response(200, text="dashboard")
        return httpx.Response(200, json=payloads[request.url.path])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = run_smoke_test(
            "https://api.example.test",
            "https://dashboard.example.test",
            client=client,
        )

    assert result.weather_status == "fresh"
    assert result.energy_status == "fresh"
    assert result.analytics_points == 12


def test_smoke_test_fails_when_data_is_stale() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payloads = {
            "/api/v1/health": {"status": "ok"},
            "/api/v1/ready": {"status": "ready", "database": "up"},
            "/api/v1/data-freshness": {
                "status": "degraded",
                "weather": {"status": "fresh"},
                "energy": {"status": "stale"},
            },
        }
        return httpx.Response(200, json=payloads[request.url.path])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="énergie=stale"):
            run_smoke_test(
                "https://api.example.test",
                "https://dashboard.example.test",
                client=client,
            )
