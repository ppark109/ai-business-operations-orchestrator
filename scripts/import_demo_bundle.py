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
    from workflows.demo_bundle import import_demo_bundle
    from workflows.orchestrator import WorkflowOrchestrator

    parser = argparse.ArgumentParser(description="Import a sanitized AI FlowOps demo bundle.")
    parser.add_argument("bundle_path", nargs="?", help="Bundle path to import.")
    args = parser.parse_args()

    settings = get_settings()
    bundle_path = Path(args.bundle_path or settings.demo_bundle_path)
    orchestrator = WorkflowOrchestrator(settings.database_file)
    try:
        bundle = import_demo_bundle(orchestrator.store, bundle_path)
        case_count = len(bundle.tables.get("cases", []))
        print(f"imported={bundle_path} cases={case_count}")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
