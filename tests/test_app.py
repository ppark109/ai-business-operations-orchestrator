from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from workflows.orchestrator import WorkflowOrchestrator
from workflows.routing import ROUTES
from workflows.seeding import seed_cases

ADMIN_HEADERS = {"X-Admin-Token": "test-token"}


def test_healthz_reports_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_expected_routes() -> None:
    response = TestClient(create_app()).get("/meta")
    assert response.status_code == 200
    assert response.json()["routes"] == list(ROUTES)


def test_api_can_seed_and_run_case(tmp_path: Path) -> None:
    # Use a temporary DB for a deterministic run in tests.
    app = create_app(Settings(database_path=str(tmp_path / "app.sqlite3"), admin_token="test-token"))
    app.state.orchestrator.close()
    app.state.orchestrator = WorkflowOrchestrator(db_path=tmp_path / "app.sqlite3")

    client = TestClient(app)
    seeded = client.post("/api/cases/seed", headers=ADMIN_HEADERS).json()
    assert "inserted" in seeded

    case_id = sorted(Path("data/seed/cases").glob("*.json"))[0].stem
    response = client.post(f"/api/cases/{case_id}/run", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert "routing" in data


def test_api_approval_flow(tmp_path: Path) -> None:
    orchestrator = WorkflowOrchestrator(db_path=tmp_path / "approval.sqlite3")
    try:
        inserted, skipped = seed_cases(orchestrator.store, "data/seed/cases", overwrite=True)
        case_id = "seed-legal-001"
        result = orchestrator.run_case(case_id)
        assert result.approval_id
        state = orchestrator.store.get_case_state(case_id)
        assert state.approval and state.approval.status == "pending"

        app = create_app(Settings(database_path=str(tmp_path / "approval.sqlite3"), admin_token="test-token"))
        app.state.orchestrator.close()
        app.state.orchestrator = orchestrator
        client = TestClient(app)

        approval_id = result.approval_id
        response = client.post(
            f"/api/approvals/{approval_id}/approve",
            json={"reviewer": "qa", "comments": "ok"},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        state = orchestrator.store.get_case_state(case_id)
        assert state.approval is not None
        assert state.approval.status == "approved"
    finally:
        orchestrator.close()


def test_mutation_routes_require_admin_token(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=str(tmp_path / "secure.sqlite3"), admin_token="test-token"))
    client = TestClient(app)

    response = client.post("/api/cases/seed")

    assert response.status_code == 403


def test_seed_api_rejects_unknown_dataset(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=str(tmp_path / "seed.sqlite3"), admin_token="test-token"))
    client = TestClient(app)

    response = client.post(
        "/api/cases/seed?dataset=../../docs",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 400
    assert "Unsupported seed dataset" in response.json()["detail"]


def test_case_detail_is_redacted_without_admin_token(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=str(tmp_path / "redacted.sqlite3"), admin_token="test-token"))
    client = TestClient(app)
    client.post("/api/cases/seed", headers=ADMIN_HEADERS)

    public_response = client.get("/api/cases/seed-legal-001")
    admin_response = client.get("/api/cases/seed-legal-001", headers=ADMIN_HEADERS)

    assert public_response.status_code == 200
    assert admin_response.status_code == 200
    public_payload = public_response.json()
    assert "intake" not in public_payload
    assert "contract_text" not in str(public_payload)
    assert "intake" in admin_response.json()


def test_html_admin_forms_require_csrf_context(tmp_path: Path) -> None:
    orchestrator = WorkflowOrchestrator(db_path=tmp_path / "forms.sqlite3")
    try:
        seed_cases(orchestrator.store, "data/seed/cases", overwrite=True)
        result = orchestrator.run_case("seed-legal-001")
        assert result.approval_id
        app = create_app(Settings(database_path=str(tmp_path / "forms.sqlite3"), admin_token="test-token"))
        app.state.orchestrator.close()
        app.state.orchestrator = orchestrator
        client = TestClient(app)

        public_page = client.get(f"/approvals/{result.approval_id}")
        admin_page = client.get(f"/approvals/{result.approval_id}?admin_token=test-token")

        assert "csrf_token" not in public_page.text
        assert "csrf_token" in admin_page.text
    finally:
        orchestrator.close()
