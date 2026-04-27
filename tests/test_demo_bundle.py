from pathlib import Path

import pytest

from workflows.demo_bundle import export_demo_bundle, import_demo_bundle
from workflows.orchestrator import WorkflowOrchestrator


def test_demo_bundle_export_import_recreates_dashboard_state(tmp_path: Path) -> None:
    source = WorkflowOrchestrator(db_path=tmp_path / "source.sqlite3")
    target = WorkflowOrchestrator(db_path=tmp_path / "target.sqlite3")
    try:
        source.seed("data/seed/cases", overwrite=True)
        source.run_case("seed-legal-001")
        bundle_path = tmp_path / "demo-bundle.json"

        bundle = export_demo_bundle(source.store, bundle_path)
        imported = import_demo_bundle(target.store, bundle_path)

        assert bundle_path.exists()
        assert len(bundle.tables["cases"]) == 24
        assert imported.bundle_version == bundle.bundle_version
        state = target.store.get_case_state("seed-legal-001")
        assert state.routing_decision is not None
        assert state.normalized_case.document_refs[0].content
        assert state.findings
    finally:
        source.close()
        target.close()


def test_demo_bundle_rejects_private_markers(tmp_path: Path) -> None:
    orchestrator = WorkflowOrchestrator(db_path=tmp_path / "bad.sqlite3")
    try:
        orchestrator.seed("data/seed/cases", overwrite=True)
        intake = orchestrator.store.get_intake("seed-legal-001")
        intake.metadata["leak"] = "OPENAI_API_KEY=secret"
        orchestrator.store.upsert_case(intake, status="draft")

        with pytest.raises(ValueError, match="forbidden"):
            export_demo_bundle(orchestrator.store, tmp_path / "bad-bundle.json")
    finally:
        orchestrator.close()
