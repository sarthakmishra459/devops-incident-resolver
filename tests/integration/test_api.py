from fastapi.testclient import TestClient

from devops_resolver.presentation.api.main import create_app


def test_api_lists_demos_and_creates_incident() -> None:
    app = create_app()
    with TestClient(app) as client:
        demos_response = client.get("/api/demos")
        assert demos_response.status_code == 200
        assert len(demos_response.json()["demos"]) == 10

        create_response = client.post(
            "/api/incidents",
            json={
                "title": "Redis Memory Full",
                "description": "Redis maxmemory reached and cache writes are failing.",
                "severity": "high",
                "demo_key": "redis-memory-full",
            },
        )
        assert create_response.status_code == 201
        incident = create_response.json()["incident"]
        assert incident["id"].startswith("inc_")

        get_response = client.get(f"/api/incidents/{incident['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["incident"]["title"] == "Redis Memory Full"


def test_healthcheck() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
