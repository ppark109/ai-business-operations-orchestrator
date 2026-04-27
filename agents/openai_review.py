from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel, Field

from agents.base import build_trace
from schemas.case import EvidenceSpan, Finding, IntakePackage, Route, Severity, TraceRecord

SYSTEM_PROMPT = (
    "You are an AI commercial operations reviewer. Extract grounded evidence and "
    "business risk findings from synthetic intake documents. Every evidence.quote "
    "must be copied as an exact, contiguous substring from the named document. Do "
    "not paraphrase quotes, summarize quotes, combine text from multiple places, or "
    "invent wording. If a finding cannot be supported by an exact quote, omit it."
)


class AIReviewEvidence(BaseModel):
    source_document_type: str
    locator: str
    quote: str
    normalized_fact: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIReviewFinding(BaseModel):
    rule_id: str
    finding_type: str = "ai_review"
    severity: Severity
    route: Route
    summary: str
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class AIReviewResult(BaseModel):
    evidence: list[AIReviewEvidence] = Field(default_factory=list)
    findings: list[AIReviewFinding] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    rationale: str = ""


class OpenAIReviewAgent:
    provider_label = "openai-responses"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("OPENAI_API_KEY is required when ENABLE_LLM_AGENTS=true")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = client or self._build_client(api_key)

    def run(self, payload: IntakePackage) -> tuple[list[EvidenceSpan], list[Finding], TraceRecord]:
        start = time.perf_counter()
        documents = _format_documents(payload)
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Case id: {payload.case_id}\n"
                        f"Customer: {payload.customer_name}\n"
                        f"{documents}"
                    ),
                },
            ],
            text_format=AIReviewResult,
            timeout=self.timeout_seconds,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI review returned no parsed output")

        evidence = [
            EvidenceSpan(
                source_document_type=item.source_document_type,
                locator=item.locator,
                quote=item.quote,
                normalized_fact=item.normalized_fact,
                confidence=item.confidence,
            )
            for item in parsed.evidence
        ]
        evidence = _ground_evidence_quotes(evidence, payload)

        findings = [
            Finding(
                finding_id=f"{payload.case_id}-ai-{index:02d}-{item.rule_id}",
                rule_id=item.rule_id,
                finding_type=item.finding_type,
                severity=item.severity,
                route=item.route,
                summary=item.summary,
                evidence=_evidence_for_quotes(evidence, item.evidence_quotes),
                confidence=item.confidence,
                source_agent="OpenAIReviewAgent",
            )
            for index, item in enumerate(parsed.findings, start=1)
        ]
        for finding in findings:
            if finding.route != "auto_approve" and not finding.evidence:
                raise ValueError(f"AI finding lacks grounded evidence: {finding.rule_id}")

        trace = build_trace(
            case_id=payload.case_id,
            step_name="openai_document_review",
            agent_name="OpenAIReviewAgent",
            inputs_summary=f"documents={len(_document_texts(payload))}",
            outputs_summary=f"evidence={len(evidence)} findings={len(findings)}",
            start_time=start,
        ).model_copy(update={"model_provider_label": self.provider_label})
        return evidence, findings, trace

    @staticmethod
    def _build_client(api_key: str):
        from openai import OpenAI

        return OpenAI(api_key=api_key)


def _document_texts(payload: IntakePackage) -> list[tuple[str, str]]:
    if payload.source_documents:
        return [
            (document.document_type, document.content or "")
            for document in payload.source_documents
        ]
    return [
        ("intake_email", payload.intake_email_text),
        ("contract", payload.contract_text),
        ("order_form", payload.order_form_text),
        ("implementation_notes", payload.implementation_notes),
        ("security_questionnaire", payload.security_questionnaire_text),
    ]


def _format_documents(payload: IntakePackage) -> str:
    return "\n\n".join(
        f"## {document_type}\n{text}"
        for document_type, text in _document_texts(payload)
    )


def _ground_evidence_quotes(evidence: list[EvidenceSpan], payload: IntakePackage) -> list[EvidenceSpan]:
    text_by_type = {document_type: text for document_type, text in _document_texts(payload)}
    grounded: list[EvidenceSpan] = []
    for item in evidence:
        source_text = text_by_type.get(item.source_document_type, "")
        if _contains_quote(source_text, item.quote):
            grounded.append(item)
            continue
        replacement = _best_source_sentence(
            source_text,
            search_text=f"{item.quote} {item.normalized_fact}",
        )
        if replacement is None:
            raise ValueError(f"AI evidence quote is not grounded: {item.normalized_fact}")
        grounded.append(item.model_copy(update={"quote": replacement}))
    return grounded


def _contains_quote(source_text: str, quote: str) -> bool:
    return _normalize_text(quote) in _normalize_text(source_text)


def _best_source_sentence(source_text: str, search_text: str) -> str | None:
    terms = _search_terms(search_text)
    if not terms:
        return None

    best_sentence = ""
    best_score = 0
    for sentence in _source_sentences(source_text):
        sentence_terms = set(_search_terms(sentence))
        score = len(terms.intersection(sentence_terms))
        if score > best_score:
            best_score = score
            best_sentence = sentence

    minimum_score = 2 if len(terms) >= 2 else 1
    if best_score < minimum_score:
        return None
    return best_sentence


def _source_sentences(source_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", source_text).strip()
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if sentence.strip()
    ]


def _search_terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"\d+%?|[a-zA-Z][a-zA-Z_'-]{2,}", text.lower())
        if term not in {"the", "and", "for", "that", "with", "from", "this", "will", "are", "has"}
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _evidence_for_quotes(
    evidence: list[EvidenceSpan],
    quotes: list[str],
) -> list[EvidenceSpan]:
    if not quotes:
        return []
    quote_set = {quote.strip().lower() for quote in quotes}
    selected = [
        item
        for item in evidence
        if item.quote.strip().lower() in quote_set
    ]
    if selected:
        return selected

    for quote in quotes:
        quote_terms = _search_terms(quote)
        best_item = None
        best_score = 0
        for item in evidence:
            item_terms = _search_terms(f"{item.quote} {item.normalized_fact}")
            score = len(quote_terms.intersection(item_terms))
            if score > best_score:
                best_score = score
                best_item = item
        if best_item is not None and best_score >= 2 and best_item not in selected:
            selected.append(best_item)
    return selected
