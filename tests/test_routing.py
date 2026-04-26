from schemas.case import Finding
from workflows.routing import choose_route


def _finding(rule_id: str, severity: str, route: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        finding_id=rule_id,
        finding_type="t",
        severity=severity,
        route=route,
        summary=rule_id,
        confidence=0.9,
        evidence=[],
        source_agent="x",
    )


def test_clean_case_auto_approves_without_review() -> None:
    route, needs_approval, _ = choose_route([], confidence=0.96)

    assert route == "auto_approve"
    assert needs_approval is False


def test_low_confidence_clean_case_requires_approval() -> None:
    route, needs_approval, _ = choose_route([], confidence=0.70)

    assert route == "auto_approve"
    assert needs_approval is True


def test_high_severity_case_escalates_to_legal() -> None:
    route, needs_approval, _ = choose_route(
        [
            _finding("x", "high", "legal")
        ],
        confidence=0.90,
    )

    assert route == "legal"
    assert needs_approval is True


def test_requested_route_cannot_override_deterministic_route() -> None:
    route, needs_approval, _ = choose_route(
        [
            _finding("x", "medium", "security")
        ],
        confidence=0.90,
    )

    assert route == "security"
    assert needs_approval is True


def test_same_severity_route_choice_is_order_independent() -> None:
    findings = [
        _finding("finance", "medium", "finance"),
        _finding("implementation", "medium", "implementation"),
    ]
    reversed_findings = list(reversed(findings))

    route, _, secondary = choose_route(findings, confidence=0.9)
    reversed_route, _, reversed_secondary = choose_route(reversed_findings, confidence=0.9)

    assert route == "implementation"
    assert reversed_route == "implementation"
    assert secondary == ["finance"]
    assert reversed_secondary == ["finance"]
