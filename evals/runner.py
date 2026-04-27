from __future__ import annotations

import json
import uuid
from pathlib import Path

from schemas.case import EvalResult, IntakePackage
from workflows.seeding import load_case_files
from workflows.storage import WorkflowStore

RUNTIME_EVAL_OUTPUT = Path("data/runtime/evals/latest.json")


def run_eval(store: WorkflowStore, folder: Path, output: Path | None = None):
    cases = load_case_files(folder)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    rows: list[dict[str, object]] = []

    total = len(cases)
    route_pass = 0
    approval_pass = 0
    grounding_pass = 0
    brief_pass = 0
    total_pass = 0

    # Simple deterministic workflow: route and save each seeded held-out case.
    for seed in cases:
        # Use store directly to avoid HTTP dependency.
        store.upsert_case(seed, status="draft")

        from workflows.orchestrator import WorkflowOrchestrator

        # Build a one-off orchestrator over same DB so traces are persisted.
        orchestrator = WorkflowOrchestrator(store.db_path)
        orchestrator.run_case(seed.case_id)
        state = orchestrator.store.get_case_state(seed.case_id)
        routing = state.routing_decision
        findings = state.findings

        is_route_ok = bool(routing and routing.recommended_route == seed.expected_route)
        is_approval_ok = bool(
            routing and routing.approval_required == seed.expected_approval_required
        )
        detected_labels = _detected_risk_labels(findings)
        expected_labels = seed.expected_key_risk_labels
        is_clause_match_ok = _expected_labels_detected(expected_labels, detected_labels)

        # quote grounding check: all findings evidence should be present in intake text.
        source_text = _case_text(seed)
        is_grounding_ok = _all_finding_evidence_in_text(findings, source_text)
        has_brief = state.brief is not None
        is_brief_ok = bool(has_brief or (routing and routing.approval_required))
        is_trace_ok = _trace_completeness(state.traces)

        route_pass += int(is_route_ok)
        approval_pass += int(is_approval_ok)
        grounding_pass += int(is_grounding_ok)
        brief_pass += int(is_brief_ok)
        total_pass += int(
            is_route_ok
            and is_approval_ok
            and is_grounding_ok
            and is_clause_match_ok
            and is_brief_ok
            and is_trace_ok
        )

        eval_row = EvalResult(
            case_id=seed.case_id,
            expected_route=seed.expected_route,
            actual_route=routing.recommended_route if routing else "auto_approve",
            expected_approval_required=seed.expected_approval_required,
            actual_approval_required=routing.approval_required if routing else None,
            expected_key_risk_labels=expected_labels,
            detected_key_risk_labels=detected_labels,
            route_pass=is_route_ok,
            grounding_pass=is_grounding_ok,
            approval_pass=is_approval_ok,
            clause_match_pass=is_clause_match_ok,
            trace_complete=is_trace_ok,
            brief_completeness_pass=is_brief_ok and is_trace_ok,
            notes=f"route={routing.recommended_route if routing else 'none'} trace={len(state.traces)}",
        )
        store.save_eval_result(run_id, eval_row)
        orchestrator.close()
        rows.append(
            {
                "case_id": seed.case_id,
                "expected_route": seed.expected_route,
                "actual_route": eval_row.actual_route,
                "route_pass": is_route_ok,
                "approval_pass": is_approval_ok,
                "grounding_pass": is_grounding_ok,
                "clause_match_pass": is_clause_match_ok,
                "expected_key_risk_labels": expected_labels,
                "detected_key_risk_labels": detected_labels,
                "brief_completeness_pass": eval_row.brief_completeness_pass,
                "trace_complete": is_trace_ok,
            }
        )

    summary = {
        "run_id": run_id,
        "total": total,
        "route_pass": route_pass,
        "approval_pass": approval_pass,
        "grounding_pass": grounding_pass,
        "brief_pass": brief_pass,
        "total_pass": total_pass,
        "route_accuracy": route_pass / max(total, 1),
        "approval_accuracy": approval_pass / max(total, 1),
        "grounding_accuracy": grounding_pass / max(total, 1),
        "brief_accuracy": brief_pass / max(total, 1),
        "total_accuracy": total_pass / max(total, 1),
        "rows": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _case_text(payload: IntakePackage) -> str:
    if payload.source_documents:
        return " ".join(document.content or "" for document in payload.source_documents).lower()
    return " ".join(
        [
            payload.intake_email_text,
            payload.contract_text,
            payload.order_form_text,
            payload.implementation_notes,
            payload.security_questionnaire_text,
        ]
    ).lower()


def _all_finding_evidence_in_text(findings, source_text: str) -> bool:
    text = source_text.lower()
    for finding in findings:
        for quote in [span.quote for span in finding.evidence]:
            if quote and quote.strip().lower() not in text:
                return False
    return True


def _trace_completeness(traces) -> bool:
    required = {
        "intake_normalization",
        "evidence_extraction",
        "contract_risk_review",
        "security_review",
        "implementation_review",
        "finance_review",
        "playbook_and_routing",
        "routing_recommendation",
        "critic",
    }
    trace_steps = {trace.step_name for trace in traces}
    return required.issubset(trace_steps)


def _detected_risk_labels(findings) -> list[str]:
    labels = set()
    for finding in findings:
        labels.add(finding.rule_id)
        labels.add(finding.rule_id.removeprefix("playbook-"))
        labels.add(finding.rule_id.replace("-", "_"))
        labels.add(finding.rule_id.removeprefix("playbook-").replace("-", "_"))
    return sorted(labels)


def _expected_labels_detected(expected: list[str], detected: list[str]) -> bool:
    if not expected:
        return True
    detected_set = set(detected)
    return all(label in detected_set for label in expected)
