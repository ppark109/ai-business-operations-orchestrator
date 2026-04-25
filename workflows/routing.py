from collections.abc import Sequence

from schemas.case import Route, Severity

ROUTES: tuple[Route, ...] = (
    "auto_approve",
    "legal",
    "security",
    "implementation",
    "finance",
)

ESCALATION_ROUTES: tuple[Route, ...] = (
    "legal",
    "security",
    "implementation",
    "finance",
)


def approval_required(severity: Severity, confidence: float) -> bool:
    return severity in {"high", "critical"} or confidence < 0.75


def choose_route(
    severities: Sequence[Severity],
    requested_route: Route | None = None,
    confidence: float = 1.0,
) -> tuple[Route, bool]:
    if requested_route in ESCALATION_ROUTES:
        highest = max(severities, key=_severity_rank) if severities else "medium"
        return requested_route, approval_required(highest, confidence)

    if not severities:
        return "auto_approve", confidence < 0.85

    highest = max(severities, key=_severity_rank)
    if highest in {"high", "critical"}:
        return "legal", True
    return "auto_approve", confidence < 0.85


def _severity_rank(severity: Severity) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }[severity]
