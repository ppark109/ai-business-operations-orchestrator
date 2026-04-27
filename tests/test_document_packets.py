from pathlib import Path

from workflows.seeding import load_case_files


def test_document_backed_seed_case_loads_source_documents() -> None:
    cases = {case.case_id: case for case in load_case_files(Path("data/seed/cases"))}
    case = cases["seed-legal-001"]

    assert len(case.source_documents) == 5
    assert "liability cap is above 1x fees" in case.contract_text
    assert all(document.content for document in case.source_documents)
    assert all(document.path and document.path.startswith("documents/") for document in case.source_documents)


def test_document_backed_heldout_case_loads_source_documents() -> None:
    cases = {case.case_id: case for case in load_case_files(Path("data/held_out/cases"))}
    case = cases["heldout-security-001"]

    assert len(case.source_documents) == 5
    assert "The DPA is missing" in case.security_questionnaire_text
    assert case.expected_route == "security"
