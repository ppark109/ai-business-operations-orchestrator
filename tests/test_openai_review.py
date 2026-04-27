from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.openai_review import AIReviewResult, OpenAIReviewAgent
from workflows.seeding import load_case_files


class _Responses:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.parsed)


class _Client:
    def __init__(self, parsed):
        self.responses = _Responses(parsed)


def test_openai_review_agent_accepts_grounded_structured_output() -> None:
    case = {item.case_id: item for item in load_case_files(Path("data/seed/cases"))}[
        "seed-legal-001"
    ]
    parsed = AIReviewResult.model_validate(
        {
            "evidence": [
                {
                    "source_document_type": "contract",
                    "locator": "contract:liability",
                    "quote": "liability cap is above 1x fees",
                    "normalized_fact": "liability cap above standard",
                    "confidence": 0.94,
                }
            ],
            "findings": [
                {
                    "rule_id": "liability_cap_above_standard",
                    "severity": "high",
                    "route": "legal",
                    "summary": "Liability cap exceeds the standard threshold.",
                    "evidence_quotes": ["liability cap is above 1x fees"],
                    "confidence": 0.92,
                }
            ],
            "risk_signals": ["liability_cap_above_standard"],
            "rationale": "Legal review is needed.",
        }
    )
    client = _Client(parsed)
    agent = OpenAIReviewAgent(
        api_key="",
        model="gpt-4o-mini",
        client=client,
    )

    evidence, findings, trace = agent.run(case)

    system_message = client.responses.calls[0]["input"][0]["content"]
    assert "exact, contiguous substring" in system_message
    assert "Do not paraphrase quotes" in system_message
    assert len(evidence) == 1
    assert findings[0].route == "legal"
    assert findings[0].source_agent == "OpenAIReviewAgent"
    assert trace.step_name == "openai_document_review"


def test_openai_review_agent_rejects_ungrounded_quotes() -> None:
    case = {item.case_id: item for item in load_case_files(Path("data/seed/cases"))}[
        "seed-legal-001"
    ]
    parsed = AIReviewResult.model_validate(
        {
            "evidence": [
                {
                    "source_document_type": "contract",
                    "locator": "contract:1",
                    "quote": "not present in the document",
                    "normalized_fact": "unsupported claim",
                    "confidence": 0.8,
                }
            ],
            "findings": [],
            "risk_signals": [],
            "rationale": "",
        }
    )
    agent = OpenAIReviewAgent(api_key="", model="gpt-4o-mini", client=_Client(parsed))

    with pytest.raises(ValueError, match="not grounded"):
        agent.run(case)


def test_openai_review_agent_regrounds_paraphrased_quote_to_source_sentence() -> None:
    case = {item.case_id: item for item in load_case_files(Path("data/seed/cases"))}[
        "seed-finance-001"
    ]
    parsed = AIReviewResult.model_validate(
        {
            "evidence": [
                {
                    "source_document_type": "order_form",
                    "locator": "order_form:pricing",
                    "quote": "A 45% discount is requested, requiring finance review.",
                    "normalized_fact": "45% discount above threshold",
                    "confidence": 0.88,
                }
            ],
            "findings": [
                {
                    "rule_id": "discount_above_threshold",
                    "severity": "medium",
                    "route": "finance",
                    "summary": "Discount requires finance review.",
                    "evidence_quotes": ["A 45% discount is requested, requiring finance review."],
                    "confidence": 0.86,
                }
            ],
            "risk_signals": ["discount_above_threshold"],
            "rationale": "",
        }
    )
    agent = OpenAIReviewAgent(api_key="", model="gpt-4o-mini", client=_Client(parsed))

    evidence, findings, _ = agent.run(case)

    assert (
        evidence[0].quote
        == "The discount is above the standard approval threshold and must be reviewed by finance before booking."
    )
    assert findings[0].evidence[0].quote == evidence[0].quote
