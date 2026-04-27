from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from workflows.storage import WorkflowStore

BUNDLE_VERSION = "ai-flowops-demo-bundle-v1"
EXPORT_TABLES = (
    "cases",
    "documents",
    "findings",
    "routing_decisions",
    "approvals",
    "generated_outputs",
    "tasks",
    "trace_records",
    "eval_results",
    "kpi_records",
)
FORBIDDEN_BUNDLE_TEXT = (
    "OPENAI_API_KEY",
    "ADMIN_TOKEN",
    "C:\\",
    "/Users/",
    "/home/ubuntu",
    "~/.hermes",
    "~/.openclaw",
    ".env",
)


class DemoBundle(BaseModel):
    bundle_version: str = BUNDLE_VERSION
    source: str = "ai-flowops-sanitized-export"
    tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


def export_demo_bundle(store: WorkflowStore, output_path: Path) -> DemoBundle:
    payload: dict[str, list[dict[str, Any]]] = {}
    for table in EXPORT_TABLES:
        rows = store.conn.execute(f"SELECT * FROM {table}").fetchall()
        payload[table] = [dict(row) for row in rows]

    bundle = DemoBundle(tables=payload)
    _assert_sanitized(bundle)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return bundle


def import_demo_bundle(store: WorkflowStore, bundle_path: Path) -> DemoBundle:
    bundle = DemoBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
    _assert_sanitized(bundle)
    store.clear()
    for table in EXPORT_TABLES:
        for row in bundle.tables.get(table, []):
            _insert_row(store.conn, table, row)
    store.conn.commit()
    return bundle


def _insert_row(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> None:
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    conn.execute(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        [row[column] for column in columns],
    )


def _assert_sanitized(bundle: DemoBundle) -> None:
    text = bundle.model_dump_json()
    for forbidden in FORBIDDEN_BUNDLE_TEXT:
        if forbidden.lower() in text.lower():
            raise ValueError(f"Demo bundle contains forbidden local/private marker: {forbidden}")
