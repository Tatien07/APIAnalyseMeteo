import argparse
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class SmokeTestResult:
    weather_status: str
    energy_status: str
    analytics_points: int


def run_smoke_test(
    api_url: str,
    dashboard_url: str,
    *,
    client: httpx.Client | None = None,
) -> SmokeTestResult:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=30)
    api_base = api_url.rstrip("/")
    dashboard_base = dashboard_url.rstrip("/")

    try:
        health = _get_json(http_client, f"{api_base}/api/v1/health")
        if health.get("status") != "ok":
            raise RuntimeError("L'endpoint health ne renvoie pas le statut ok.")

        readiness = _get_json(http_client, f"{api_base}/api/v1/ready")
        if readiness.get("status") != "ready" or readiness.get("database") != "up":
            raise RuntimeError("L'API ou PostgreSQL n'est pas prêt.")

        freshness = _get_json(http_client, f"{api_base}/api/v1/data-freshness")
        weather_status = freshness.get("weather", {}).get("status", "unknown")
        energy_status = freshness.get("energy", {}).get("status", "unknown")
        if freshness.get("status") != "healthy":
            raise RuntimeError(
                f"Données dégradées : météo={weather_status}, énergie={energy_status}."
            )

        analytics = _get_json(
            http_client,
            f"{api_base}/api/v1/analytics/weather-energy?hours=24",
        )
        points_count = analytics.get("points_count")
        if not isinstance(points_count, int):
            raise RuntimeError("La réponse analytique ne contient pas points_count.")

        dashboard_response = http_client.get(dashboard_base)
        dashboard_response.raise_for_status()
        return SmokeTestResult(
            weather_status=weather_status,
            energy_status=energy_status,
            analytics_points=points_count,
        )
    finally:
        if owns_client:
            http_client.close()


def _get_json(client: httpx.Client, url: str) -> dict:
    response = client.get(url)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"La réponse de {url} n'est pas un objet JSON.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Valide un déploiement Energy Weather Monitor.")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--dashboard-url", required=True)
    arguments = parser.parse_args()

    try:
        result = run_smoke_test(arguments.api_url, arguments.dashboard_url)
    except (httpx.HTTPError, RuntimeError) as error:
        print(f"Échec du test post-déploiement : {error}")
        return 1

    print("Tous les tests post-déploiement ont réussi.")
    print(
        f"Fraîcheur : météo={result.weather_status}, énergie={result.energy_status}; "
        f"analyse={result.analytics_points} points."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
