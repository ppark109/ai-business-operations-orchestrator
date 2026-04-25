from typing import Literal

from pydantic import BaseModel, Field

Route = Literal["auto_approve", "legal", "security", "implementation", "finance"]
Severity = Literal["low", "medium", "high", "critical"]


class DocumentRef(BaseModel):
    document_id: str
    document_type: str
    source_name: str
    content_hash: str | None = None


class EvidenceSpan(BaseModel):
    document_id: str
    locator: str
    quote: str = Field(min_length=1)


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    route: Route
    summary: str
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    recommended_route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    approval_required: bool
    rationale: str


class CaseFile(BaseModel):
    case_id: str
    customer_name: str
    documents: list[DocumentRef]
    findings: list[Finding] = Field(default_factory=list)
    routing: RoutingDecision | None = None
