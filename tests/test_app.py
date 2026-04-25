from fastapi.testclient import TestClient

from app.main import create_app
from workflows.routing import ROUTES


def test_healthz_reports_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_reports_expected_routes() -> None:
    client = TestClient(create_app())

    response = client.get("/meta")

    assert response.status_code == 200
    assert response.json()["routes"] == list(ROUTES)
