from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas.case import Route

DemoDepartment = Literal["Legal", "Security", "Finance", "Implementation"]
ReviewDecision = Literal["approved", "approved_with_conditions", "needs_info", "blocker"]
ConditionType = Literal["blocker", "condition", "advisory"]


class DemoEvidenceRef(BaseModel):
    evidence_id: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    source_phrase: str = Field(min_length=1)
    extracted_fact: str = Field(min_length=1)
    downstream_use: str = Field(min_length=1)


class DemoSpecialistLane(BaseModel):
    department: DemoDepartment
    purpose: str = Field(min_length=1)
    expected_risks: list[str] = Field(min_length=1)


class DemoDepartmentPacket(BaseModel):
    department: DemoDepartment
    packet_status: str = Field(min_length=1)
    action_needed: str = Field(min_length=1)
    key_information: list[str] = Field(min_length=1)
    ai_generated_task: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class DemoSpecialistConclusion(BaseModel):
    department: DemoDepartment
    reviewer_role: str = Field(min_length=1)
    status: ReviewDecision
    decision: str = Field(min_length=1)
    note: str = Field(min_length=1)
    condition_type: ConditionType
    result: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class DemoAiSynthesis(BaseModel):
    recommendation: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    blockers: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)


class DemoBdOpsDecision(BaseModel):
    decision: str = Field(min_length=1)
    ai_synthesis_recommendation: str = Field(min_length=1)
    decision_owner: str = Field(min_length=1)
    owner_note: str = Field(min_length=1)
    approved_next_steps: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class DemoCaseSpec(BaseModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    workflow_type: str = Field(min_length=1)
    input_type: str = Field(min_length=1)
    customer_agency: str = Field(min_length=1)
    account_name: str = Field(min_length=1)
    estimated_value_usd: int = Field(gt=0)
    response_deadline: str = Field(min_length=1)
    status: str = Field(min_length=1)
    ai_recommendation: str = Field(min_length=1)
    final_decision: str = Field(min_length=1)
    decision_owner: str = Field(min_length=1)
    risk_level: str = Field(min_length=1)
    primary_route: Route
    supporting_routes: list[Route] = Field(min_length=1)
    summary: str = Field(min_length=1)
    specialist_lanes: list[DemoSpecialistLane] = Field(min_length=1)
    expected_evidence: list[DemoEvidenceRef] = Field(min_length=1)
    department_packets: list[DemoDepartmentPacket] = Field(default_factory=list)
    specialist_conclusions: list[DemoSpecialistConclusion] = Field(default_factory=list)
    ai_synthesis: DemoAiSynthesis | None = None
    expected_bd_ops_decision: DemoBdOpsDecision

    @property
    def evidence_by_id(self) -> dict[str, DemoEvidenceRef]:
        return {item.evidence_id: item for item in self.expected_evidence}

    def referenced_evidence_ids(self) -> set[str]:
        refs: set[str] = set()
        for packet in self.department_packets:
            refs.update(packet.evidence_ids)
        for conclusion in self.specialist_conclusions:
            refs.update(conclusion.evidence_ids)
        if self.ai_synthesis:
            refs.update(self.ai_synthesis.evidence_ids)
        refs.update(self.expected_bd_ops_decision.evidence_ids)
        return refs
