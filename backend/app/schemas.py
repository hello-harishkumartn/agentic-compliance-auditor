from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssessmentState(StrEnum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class Citation(BaseModel):
    passage_id: str
    document_id: str
    document_name: str
    locator: str
    quote: str = Field(max_length=500)


class ExtractedRequirement(BaseModel):
    reference: str
    title: str
    statement: str
    rationale: str
    source_quote: str


class GeneratedControl(BaseModel):
    requirement_id: str
    code: str
    title: str
    objective: str
    test_procedure: str
    expected_evidence: list[str]


class EvidenceMatch(BaseModel):
    passage_id: str
    document_id: str
    score: float = Field(ge=0, le=1)
    reason: str


class EvidenceAnalysis(BaseModel):
    control_id: str
    supports: list[Citation] = []
    contradicts: list[Citation] = []
    missing: list[str] = []
    strength: Literal["STRONG", "MODERATE", "WEAK", "NONE"]
    suspicious_instructions_ignored: bool = False


class AssessmentOutput(BaseModel):
    requirement_id: str
    control_id: str
    assessment: AssessmentState
    confidence: float = Field(ge=0, le=1)
    evidence_strength: Literal["STRONG", "MODERATE", "WEAK", "NONE"]
    rationale: str = Field(description="Concise decision summary, not chain-of-thought")
    gap: str = ""
    recommendation: str = ""
    citations: list[Citation] = []

    @model_validator(mode="after")
    def prevent_unsupported_compliance(self):
        if self.assessment == AssessmentState.COMPLIANT:
            if not self.citations or self.evidence_strength != "STRONG" or self.confidence < 0.82:
                raise ValueError("COMPLIANT requires strong cited evidence and confidence >= 0.82")
        return self


class VerificationOutput(BaseModel):
    valid: bool
    checks: dict[str, bool]
    issues: list[str]
    final_assessment: AssessmentState


class ReviewDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT", "MODIFY", "REQUEST_MORE_EVIDENCE"]
    reason: str = Field(min_length=3)
    reviewer: str = Field(min_length=2)
    modified_value: dict[str, Any] | None = None

    @model_validator(mode="after")
    def modification_is_supplied(self):
        if self.decision == "MODIFY" and not self.modified_value:
            raise ValueError("modified_value is required when decision is MODIFY")
        return self


class AuditCreate(BaseModel):
    name: str
    framework_id: str
    scope: str


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReviewView(ORMModel):
    id: str
    audit_id: str
    target_type: str
    target_id: str
    ai_recommendation: str
    status: str
    decision: str | None
    reason: str | None
    reviewer: str | None
    decided_at: datetime | None
    created_at: datetime
