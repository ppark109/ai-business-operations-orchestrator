from app.guided_demo import load_guided_demo_case, validate_guided_demo_case


def test_guided_demo_case_has_specialist_packets_and_bd_ops_decision() -> None:
    case = load_guided_demo_case()
    validate_guided_demo_case(case)

    assert case.case_id == "demo-gov-benefits-001"
    assert case.primary_route == "legal"
    assert case.decision_owner == "BD/Ops"
    assert case.expected_bd_ops_decision.decision_owner == "BD/Ops"
    assert {packet.department for packet in case.department_packets} == {
        "Legal",
        "Security",
        "Finance",
        "Implementation",
    }
    assert {item.department for item in case.specialist_conclusions} == {
        "Legal",
        "Security",
        "Finance",
        "Implementation",
    }
    assert case.ai_synthesis is not None
    assert case.ai_synthesis.recommendation == "Proceed to qualification with conditions"


def test_guided_demo_evidence_references_are_resolvable() -> None:
    case = load_guided_demo_case()
    evidence_ids = set(case.evidence_by_id)

    assert case.referenced_evidence_ids()
    assert case.referenced_evidence_ids() <= evidence_ids
