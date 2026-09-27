from pydantic import BaseModel, Field

from backend.app.schemas import AssessmentOutput, EvidenceAnalysis, ExtractedRequirement


class RequirementExtractionInput(BaseModel):
    framework_id: str
    framework_name: str
    content: str = Field(min_length=20)


class RequirementExtractionOutput(BaseModel):
    requirements: list[ExtractedRequirement]
    warnings: list[str] = []


class ControlMappingInput(BaseModel):
    requirement_id: str
    reference: str
    statement: str


class ControlMappingOutput(BaseModel):
    requirement_id: str
    code: str
    title: str
    objective: str
    test_procedure: str
    expected_evidence: list[str]


class EvidenceDiscoveryInput(BaseModel):
    control_id: str
    query: str
    limit: int = Field(default=5, ge=1, le=10)


class EvidenceDiscoveryOutput(BaseModel):
    control_id: str
    passage_ids: list[str]
    scores: list[float]


class EvidenceAnalysisInput(BaseModel):
    control_id: str
    expected_evidence: list[str]
    passages: list[dict]


class ComplianceAssessmentInput(BaseModel):
    requirement_id: str
    control_id: str
    analysis: EvidenceAnalysis


class VerificationInput(BaseModel):
    assessment: AssessmentOutput


class ReportGenerationInput(BaseModel):
    audit_id: str
    name: str
    scope: str
    findings: list[dict]


class ReportGenerationOutput(BaseModel):
    title: str
    executive_summary: str
    sections: list[dict]
    disclaimer: str

