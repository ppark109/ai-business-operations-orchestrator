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
    from workflows.demo_bundle import export_demo_bundle
    from workflows.orchestrator import WorkflowOrchestrator

    parser = argparse.ArgumentParser(description="Export a sanitized AI FlowOps demo bundle.")
    parser.add_argument("output_path", nargs="?", help="Bundle output path.")
    args = parser.parse_args()

    settings = get_settings()
    output_path = Path(args.output_path or settings.demo_bundle_path)
    orchestrator = WorkflowOrchestrator(settings.database_file)
    try:
        bundle = export_demo_bundle(orchestrator.store, output_path)
        count = sum(len(rows) for rows in bundle.tables.values())
        print(f"exported={output_path} rows={count}")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
