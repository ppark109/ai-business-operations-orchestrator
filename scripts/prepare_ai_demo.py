from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_project_root() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def main() -> None:
    _ensure_project_root()
    from app.settings import get_settings
    from evals.runner import run_eval
    from workflows.demo_bundle import export_demo_bundle
    from workflows.orchestrator import WorkflowOrchestrator
    from workflows.seeding import load_case_files

    parser = argparse.ArgumentParser(description="Prepare a sanitized AI-reviewed demo bundle locally.")
    parser.add_argument("--case-id", action="append", default=[], help="Specific seed case to run.")
    parser.add_argument("--include-evals", action="store_true", help="Run held-out evals before export.")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.enable_llm_agents:
        raise SystemExit("Set ENABLE_LLM_AGENTS=true for local AI demo preparation.")

    orchestrator = WorkflowOrchestrator(
        settings.database_file,
        enable_llm_agents=True,
        codex_command=settings.codex_command,
        codex_model=settings.codex_model,
        codex_timeout_seconds=settings.codex_timeout_seconds,
    )
    try:
        orchestrator.store.clear()
        orchestrator.seed("data/seed/cases", overwrite=True)
        selected = set(args.case_id) or {
            case.case_id
            for case in load_case_files(Path("data/seed/cases"))
            if case.source_documents
        }
        for case_id in sorted(selected):
            orchestrator.run_case(case_id)
            print(f"ran={case_id}")
        if args.include_evals:
            result = run_eval(orchestrator.store, Path("data/held_out/cases"))
            print(f"eval_route_accuracy={result['route_accuracy']:.2f}")
        bundle = export_demo_bundle(orchestrator.store, Path(settings.demo_bundle_path))
        print(f"exported={settings.demo_bundle_path} tables={len(bundle.tables)}")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
