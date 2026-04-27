from __future__ import annotations

import json
from pathlib import Path

from schemas.guided_demo import DemoCaseSpec

GUIDED_DEMO_CASE_PATH = Path("data/guided_demo/flagship_case.json")


def load_guided_demo_case(path: Path = GUIDED_DEMO_CASE_PATH) -> DemoCaseSpec:
    return DemoCaseSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_guided_demo_case(case: DemoCaseSpec) -> None:
    evidence_ids = set(case.evidence_by_id)
    missing = sorted(case.referenced_evidence_ids() - evidence_ids)
    if missing:
        raise ValueError(f"Unknown guided-demo evidence ids: {', '.join(missing)}")

    packet_departments = {packet.department for packet in case.department_packets}
    conclusion_departments = {item.department for item in case.specialist_conclusions}
    if packet_departments != conclusion_departments:
        raise ValueError("Guided-demo packet departments and conclusion departments must match.")
