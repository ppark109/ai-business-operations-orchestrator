import json
from pathlib import Path

from evals.runner import RUNTIME_EVAL_OUTPUT, run_eval
from workflows.orchestrator import WorkflowOrchestrator


def test_eval_runner_produces_results(tmp_path: Path) -> None:
    orchestrator = WorkflowOrchestrator(db_path=tmp_path / "eval.sqlite3")
    try:
        out = tmp_path / "latest.json"
        result = run_eval(orchestrator.store, Path("data/held_out/cases"), output=out)
        assert result["total"] == 5
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert "rows" in payload
        assert result["total_accuracy"] == 1.0
    finally:
        orchestrator.close()


def test_runtime_eval_output_is_ignored_path() -> None:
    assert RUNTIME_EVAL_OUTPUT == Path("data/runtime/evals/latest.json")
    assert "evals/baselines" not in RUNTIME_EVAL_OUTPUT.as_posix()


def test_eval_runner_can_rerun_held_out_fixture_cases(tmp_path: Path) -> None:
    orchestrator = WorkflowOrchestrator(db_path=tmp_path / "rerun.sqlite3")
    try:
        first = run_eval(orchestrator.store, Path("data/held_out/cases"), output=tmp_path / "first.json")
        second = run_eval(orchestrator.store, Path("data/held_out/cases"), output=tmp_path / "second.json")
        assert first["total"] == 5
        assert second["total"] == 5
    finally:
        orchestrator.close()
