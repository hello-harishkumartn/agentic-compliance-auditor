from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.base import AgentContext, AgentError
from agents.components import (
    ComplianceAssessmentAgent,
    ControlMappingAgent,
    EvidenceAnalysisAgent,
    EvidenceDiscoveryAgent,
    RequirementExtractionAgent,
    VerificationAgent,
)
from agents.contracts import (
    ComplianceAssessmentInput,
    ControlMappingInput,
    EvidenceAnalysisInput,
    EvidenceDiscoveryInput,
    RequirementExtractionInput,
    ReportGenerationInput,
    VerificationInput,
)
from agents.providers import build_provider
from backend.app import models
from backend.app.config import get_settings
from tools import ComplianceTools, RestrictedTools


class WorkflowError(RuntimeError):
    pass


class AuditWorkflow:
    """Visible, deterministic state machine. No orchestration is hidden in an agent framework."""

    TRANSITIONS = {
        "DRAFT": {"EXTRACTING_REQUIREMENTS"},
        "EXTRACTING_REQUIREMENTS": {"AWAITING_REQUIREMENT_REVIEW", "FAILED"},
        "AWAITING_REQUIREMENT_REVIEW": {"MAPPING_CONTROLS", "FAILED"},
        "MAPPING_CONTROLS": {"DISCOVERING_EVIDENCE", "FAILED"},
        "DISCOVERING_EVIDENCE": {"ANALYZING_EVIDENCE", "FAILED"},
        "ANALYZING_EVIDENCE": {"ASSESSING", "FAILED"},
        "ASSESSING": {"VERIFYING", "FAILED"},
        "VERIFYING": {"AWAITING_FINDING_REVIEW", "FAILED"},
        "AWAITING_FINDING_REVIEW": {"REPORT_READY", "FAILED"},
        "REPORT_READY": set(), "FAILED": set(),
    }

    def __init__(self, db: Session, audit: models.Audit):
        self.db, self.audit = db, audit
        self.tools = ComplianceTools(db, audit.id)

    def transition(self, next_state: str, progress: float, actor: str = "workflow"):
        if next_state not in self.TRANSITIONS.get(self.audit.status, set()):
            raise WorkflowError(f"Invalid transition: {self.audit.status} -> {next_state}")
        previous = self.audit.status
        self.audit.status, self.audit.progress = next_state, progress
        self.audit.updated_at = datetime.now(UTC)
        self.db.add(models.AuditEvent(
            audit_id=self.audit.id, event_type="STATE_TRANSITION", actor=actor,
            summary=f"{previous} → {next_state}", payload={"from": previous, "to": next_state},
        ))
        self.db.flush()

    def _record_run(self, agent, input_data, operation):
        settings = get_settings()
        provider = build_provider(settings)
        model = (settings.gemini_model if settings.llm_provider == "gemini" else
                 settings.ollama_model if settings.llm_provider == "ollama" else "deterministic-rules-v1")
        context = AgentContext(
            audit_id=self.audit.id, model=model,
            tools=RestrictedTools(self.tools, agent.allowed_tools), provider=provider,
            max_iterations=settings.max_agent_iterations,
        )
        run = models.AgentRun(
            audit_id=self.audit.id, agent=agent.name, model=context.model, status="RUNNING",
            input_summary=str(input_data.model_dump())[:1000], output_summary="",
        )
        self.db.add(run)
        self.db.flush()
        started = perf_counter()
        try:
            output = operation(context)
            run.status, run.output_summary = "SUCCEEDED", str(output.model_dump())[:2000]
            return output
        except AgentError as exc:
            run.status, run.output_summary, run.validation_errors = "FAILED", str(exc), [str(exc)]
            raise
        finally:
            run.latency_ms = int((perf_counter() - started) * 1000)
            run.tool_calls = context.tool_calls
            run.finished_at = datetime.now(UTC)
            self.db.flush()

    def start(self):
        if self.audit.status != "DRAFT":
            raise WorkflowError("Only draft audits can be started")
        framework = self.db.get(models.Framework, self.audit.framework_id)
        self.transition("EXTRACTING_REQUIREMENTS", 8)
        agent = RequirementExtractionAgent()
        data = RequirementExtractionInput(framework_id=framework.id, framework_name=framework.name, content=framework.content)
        try:
            output = self._record_run(agent, data, lambda ctx: agent.run(data, ctx))
            for item in output.requirements:
                existing = self.db.scalar(select(models.Requirement).where(
                    models.Requirement.framework_id == framework.id,
                    models.Requirement.reference == item.reference,
                ))
                requirement = existing or models.Requirement(framework_id=framework.id, **item.model_dump())
                requirement.status = "PENDING_REVIEW"
                self.db.add(requirement)
                self.db.flush()
                self.tools.request_human_review("requirement", requirement.id, "Approve extracted normative requirement")
            self.transition("AWAITING_REQUIREMENT_REVIEW", 18)
            self.db.commit()
        except Exception:
            self.transition("FAILED", self.audit.progress)
            self.db.commit()
            raise
        return self.audit

    def resume(self):
        if self.audit.status == "AWAITING_REQUIREMENT_REVIEW":
            pending = self.db.scalars(select(models.Review).where(
                models.Review.audit_id == self.audit.id, models.Review.target_type == "requirement",
                models.Review.status != "DECIDED",
            )).all()
            if pending:
                raise WorkflowError(f"{len(pending)} requirement reviews are still pending")
            approved_ids = set(self.db.scalars(select(models.Review.target_id).where(
                models.Review.audit_id == self.audit.id, models.Review.target_type == "requirement",
                models.Review.decision.in_(["APPROVE", "MODIFY"]),
            )).all())
            if not approved_ids:
                raise WorkflowError("No requirements were approved")
            requirements = self.db.scalars(select(models.Requirement).where(models.Requirement.id.in_(approved_ids))).all()
            self._execute_assessment(requirements)
        elif self.audit.status == "AWAITING_FINDING_REVIEW":
            pending = self.db.scalars(select(models.Review).where(
                models.Review.audit_id == self.audit.id, models.Review.target_type == "finding",
                models.Review.status != "DECIDED",
            )).all()
            if pending:
                raise WorkflowError(f"{len(pending)} finding reviews are still pending")
            from agents.components import ReportGenerationAgent

            findings = self.db.scalars(select(models.Finding).where(
                models.Finding.audit_id == self.audit.id
            )).all()
            agent = ReportGenerationAgent()
            data = ReportGenerationInput(
                audit_id=self.audit.id, name=self.audit.name, scope=self.audit.scope,
                findings=[{
                    "id": finding.id, "assessment": finding.assessment,
                    "rationale": finding.rationale, "gap": finding.gap,
                    "recommendation": finding.recommendation, "human_status": finding.human_status,
                } for finding in findings],
            )
            report = self._record_run(agent, data, lambda ctx: agent.run(data, ctx))
            self.db.add(models.AuditEvent(
                audit_id=self.audit.id, event_type="REPORT_GENERATED", actor=agent.name,
                summary=report.title, payload={"disclaimer": report.disclaimer},
            ))
            self.transition("REPORT_READY", 100, actor="human-gate")
            self.db.commit()
        else:
            raise WorkflowError(f"Audit cannot resume from {self.audit.status}")
        return self.audit

    def _execute_assessment(self, requirements):
        try:
            self.transition("MAPPING_CONTROLS", 28)
            controls = []
            for req in requirements:
                agent = ControlMappingAgent()
                data = ControlMappingInput(requirement_id=req.id, reference=req.reference, statement=req.statement)
                output = self._record_run(agent, data, lambda ctx, a=agent, d=data: a.run(d, ctx))
                control = self.db.scalar(select(models.Control).where(models.Control.requirement_id == req.id))
                if not control:
                    control = models.Control(**output.model_dump())
                    self.db.add(control)
                    self.db.flush()
                controls.append(control)

            self.transition("DISCOVERING_EVIDENCE", 42)
            discoveries = {}
            for control in controls:
                agent = EvidenceDiscoveryAgent()
                query = f"{control.objective} {' '.join(control.expected_evidence)}"
                data = EvidenceDiscoveryInput(control_id=control.id, query=query)
                discoveries[control.id] = self._record_run(agent, data, lambda ctx, a=agent, d=data: a.run(d, ctx))

            self.transition("ANALYZING_EVIDENCE", 57)
            analyses = {}
            for control in controls:
                passages = [self.tools.retrieve_evidence(pid) for pid in discoveries[control.id].passage_ids]
                for passage, score in zip(passages, discoveries[control.id].scores, strict=False):
                    passage["score"] = score
                agent = EvidenceAnalysisAgent()
                data = EvidenceAnalysisInput(control_id=control.id, expected_evidence=control.expected_evidence, passages=passages)
                analyses[control.id] = self._record_run(agent, data, lambda ctx, a=agent, d=data: a.run(d, ctx))

            self.transition("ASSESSING", 70)
            outputs = []
            for control in controls:
                agent = ComplianceAssessmentAgent()
                data = ComplianceAssessmentInput(requirement_id=control.requirement_id, control_id=control.id, analysis=analyses[control.id])
                outputs.append(self._record_run(agent, data, lambda ctx, a=agent, d=data: a.run(d, ctx)))

            self.transition("VERIFYING", 82)
            for output in outputs:
                agent = VerificationAgent()
                data = VerificationInput(assessment=output)
                verification = self._record_run(agent, data, lambda ctx, a=agent, d=data: a.run(d, ctx))
                finding = self.tools.save_finding(
                    requirement_id=output.requirement_id, control_id=output.control_id,
                    assessment=verification.final_assessment.value, confidence=output.confidence,
                    evidence_strength=output.evidence_strength, rationale=output.rationale,
                    gap=output.gap, recommendation=output.recommendation,
                    citations=[c.model_dump() for c in output.citations], verification=verification.model_dump(),
                )
                self.tools.request_human_review("finding", finding.id, f"{finding.assessment}: {finding.rationale}")
            self.transition("AWAITING_FINDING_REVIEW", 90)
            self.db.commit()
        except Exception:
            self.transition("FAILED", self.audit.progress)
            self.db.commit()
            raise
