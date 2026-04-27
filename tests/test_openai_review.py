from pathlib import Path

import pytest

from agents.openai_review import SYSTEM_PROMPT, AIReviewResult, CodexReviewAgent
from workflows.seeding import load_case_files


class _Runner:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def __call__(self, prompt, schema, timeout_seconds):
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.parsed


def test_codex_review_agent_accepts_grounded_structured_output() -> None:
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
                    "finding_type": "ai_review",
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
    runner = _Runner(parsed)
    agent = CodexReviewAgent(
        model="gpt-5.5",
        runner=runner,
    )

    evidence, findings, trace = agent.run(case)

    prompt = runner.calls[0]["prompt"]
    assert SYSTEM_PROMPT in prompt
    assert "exact, contiguous substring" in prompt
    assert "Do not paraphrase quotes" in prompt
    assert len(evidence) == 1
    assert findings[0].route == "legal"
    assert findings[0].source_agent == "CodexReviewAgent"
    assert trace.step_name == "codex_document_review"
    assert trace.model_provider_label == "openai-codex"


def test_codex_review_agent_rejects_ungrounded_quotes() -> None:
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
    agent = CodexReviewAgent(model="gpt-5.5", runner=_Runner(parsed))

    with pytest.raises(ValueError, match="not grounded"):
        agent.run(case)


def test_codex_review_agent_regrounds_paraphrased_quote_to_source_sentence() -> None:
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
                    "finding_type": "ai_review",
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
    agent = CodexReviewAgent(model="gpt-5.5", runner=_Runner(parsed))

    evidence, findings, _ = agent.run(case)

    assert (
        evidence[0].quote
        == "The discount is above the standard approval threshold and must be reviewed by finance before booking."
    )
    assert findings[0].evidence[0].quote == evidence[0].quote
