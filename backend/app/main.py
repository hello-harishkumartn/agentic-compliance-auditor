from contextlib import asynccontextmanager
from datetime import UTC, datetime
from html import escape

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agents import AGENT_REGISTRY
from backend.app import models
from backend.app.config import get_settings
from backend.app.database import SessionLocal, get_db, initialize_database
from backend.app.schemas import AuditCreate, ReviewDecision, ReviewView
from backend.app.seed import seed_database, seed_demo_audit
from backend.app.workflow import AuditWorkflow, WorkflowError


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    if get_settings().auto_seed:
        with SessionLocal() as db:
            seed_database(db)
            seed_demo_audit(db)
    yield


app = FastAPI(title="Agentic Compliance Auditor API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def dump(item, *fields):
    return {field: getattr(item, field) for field in fields}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": get_settings().app_name}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    findings = db.scalars(select(models.Finding)).all()
    audits = db.scalars(select(models.Audit).order_by(models.Audit.created_at.desc())).all()
    pending = db.scalar(select(func.count(models.Review.id)).where(models.Review.status == "PENDING")) or 0
    return {
        "metrics": {
            "active_audits": sum(a.status not in {"REPORT_READY", "FAILED"} for a in audits),
            "controls_tested": len(findings), "pending_reviews": pending,
            "high_risk_gaps": sum(f.assessment == "NON_COMPLIANT" for f in findings),
        },
        "assessments": {state: sum(f.assessment == state for f in findings) for state in
                        ["COMPLIANT", "PARTIALLY_COMPLIANT", "NON_COMPLIANT", "INSUFFICIENT_EVIDENCE", "REQUIRES_HUMAN_REVIEW"]},
        "audits": [dump(a, "id", "name", "status", "scope", "progress", "created_at") for a in audits[:5]],
        "disclaimer": "Synthetic demonstration only — not legal advice.",
    }


@app.get("/api/frameworks")
def frameworks(db: Session = Depends(get_db)):
    return [dump(x, "id", "name", "version", "source_type", "description", "created_at")
            for x in db.scalars(select(models.Framework)).all()]


class FrameworkCreate(BaseModel):
    name: str
    version: str
    content: str = Field(min_length=20)
    source_type: str = "synthetic"
    description: str = ""


@app.post("/api/frameworks", status_code=201)
def create_framework(body: FrameworkCreate, db: Session = Depends(get_db)):
    item = models.Framework(**body.model_dump())
    db.add(item); db.commit()
    return dump(item, "id", "name", "version", "source_type")


@app.get("/api/requirements")
def requirements(framework_id: str | None = None, db: Session = Depends(get_db)):
    query = select(models.Requirement)
    if framework_id:
        query = query.where(models.Requirement.framework_id == framework_id)
    return [dump(x, "id", "framework_id", "reference", "title", "statement", "source_quote", "status")
            for x in db.scalars(query).all()]


@app.get("/api/controls")
def controls(db: Session = Depends(get_db)):
    return [dump(x, "id", "requirement_id", "code", "title", "objective", "test_procedure", "expected_evidence")
            for x in db.scalars(select(models.Control)).all()]


@app.get("/api/evidence")
def evidence(db: Session = Depends(get_db)):
    return [dump(x, "id", "name", "kind", "trust_level", "metadata_json", "created_at")
            for x in db.scalars(select(models.Document)).all()]


class DocumentCreate(BaseModel):
    name: str
    kind: str = "evidence"
    content: str = Field(min_length=3)


@app.post("/api/evidence", status_code=201)
def create_document(body: DocumentCreate, db: Session = Depends(get_db)):
    from tools import ComplianceTools
    doc = models.Document(name=body.name, kind=body.kind, content=body.content,
                          trust_level="untrusted", metadata_json={"uploaded": True})
    db.add(doc); db.flush()
    db.add(models.EvidencePassage(document_id=doc.id, content=body.content, locator="uploaded text",
                                  content_hash=ComplianceTools.passage_hash(body.content),
                                  embedding=ComplianceTools.embedding(body.content), relevance=1))
    db.commit()
    return dump(doc, "id", "name", "kind", "trust_level")


@app.get("/api/audits")
def audits(db: Session = Depends(get_db)):
    return [dump(x, "id", "name", "framework_id", "status", "scope", "progress", "created_at", "updated_at")
            for x in db.scalars(select(models.Audit).order_by(models.Audit.created_at.desc())).all()]


@app.post("/api/audits", status_code=201)
def create_audit(body: AuditCreate, db: Session = Depends(get_db)):
    if not db.get(models.Framework, body.framework_id):
        raise HTTPException(404, "Framework not found")
    audit = models.Audit(**body.model_dump())
    db.add(audit); db.commit()
    return dump(audit, "id", "name", "status", "scope", "progress")


@app.post("/api/audits/{audit_id}/start")
def start_audit(audit_id: str, db: Session = Depends(get_db)):
    audit = db.get(models.Audit, audit_id)
    if not audit: raise HTTPException(404, "Audit not found")
    try: AuditWorkflow(db, audit).start()
    except WorkflowError as exc: raise HTTPException(409, str(exc)) from exc
    return dump(audit, "id", "status", "progress")


@app.post("/api/audits/{audit_id}/resume")
def resume_audit(audit_id: str, db: Session = Depends(get_db)):
    audit = db.get(models.Audit, audit_id)
    if not audit: raise HTTPException(404, "Audit not found")
    try: AuditWorkflow(db, audit).resume()
    except WorkflowError as exc: raise HTTPException(409, str(exc)) from exc
    return dump(audit, "id", "status", "progress")


@app.get("/api/findings")
def findings(audit_id: str | None = None, db: Session = Depends(get_db)):
    query = select(models.Finding)
    if audit_id: query = query.where(models.Finding.audit_id == audit_id)
    return [dump(x, "id", "audit_id", "requirement_id", "control_id", "assessment", "confidence",
                 "evidence_strength", "rationale", "gap", "recommendation", "human_status", "created_at")
            for x in db.scalars(query).all()]


@app.get("/api/findings/{finding_id}")
def finding_detail(finding_id: str, db: Session = Depends(get_db)):
    item = db.get(models.Finding, finding_id)
    if not item: raise HTTPException(404, "Finding not found")
    requirement, control = db.get(models.Requirement, item.requirement_id), db.get(models.Control, item.control_id)
    review = db.scalar(select(models.Review).where(models.Review.target_id == item.id))
    return {**dump(item, "id", "audit_id", "assessment", "confidence", "evidence_strength", "rationale",
                   "gap", "recommendation", "citations", "verification", "human_status", "created_at"),
            "requirement": dump(requirement, "id", "reference", "title", "statement", "source_quote"),
            "control": dump(control, "id", "code", "title", "objective", "test_procedure", "expected_evidence"),
            "human_review": dump(review, "id", "status", "decision", "reason", "reviewer", "decided_at") if review else None}


@app.get("/api/reviews", response_model=list[ReviewView])
def reviews(status_filter: str | None = None, db: Session = Depends(get_db)):
    query = select(models.Review).order_by(models.Review.created_at.desc())
    if status_filter: query = query.where(models.Review.status == status_filter)
    return db.scalars(query).all()


@app.post("/api/reviews/{review_id}/decision")
def decide_review(review_id: str, body: ReviewDecision, db: Session = Depends(get_db)):
    review = db.get(models.Review, review_id)
    if not review: raise HTTPException(404, "Review not found")
    if review.status == "DECIDED": raise HTTPException(409, "Review is already decided")
    next_status = "EVIDENCE_REQUESTED" if body.decision == "REQUEST_MORE_EVIDENCE" else "DECIDED"
    review.status, review.decision, review.reason = next_status, body.decision, body.reason
    review.reviewer, review.modified_value, review.decided_at = body.reviewer, body.modified_value, datetime.now(UTC)
    if review.target_type == "requirement":
        target = db.get(models.Requirement, review.target_id)
        target.status = ("APPROVED" if body.decision in {"APPROVE", "MODIFY"} else
                         "NEEDS_EVIDENCE" if body.decision == "REQUEST_MORE_EVIDENCE" else "REJECTED")
        if body.modified_value:
            for key in {"title", "statement", "rationale"} & body.modified_value.keys(): setattr(target, key, body.modified_value[key])
    elif review.target_type == "finding":
        target = db.get(models.Finding, review.target_id)
        target.human_status = body.decision
        if body.modified_value:
            for key in {"assessment", "rationale", "gap", "recommendation"} & body.modified_value.keys(): setattr(target, key, body.modified_value[key])
    db.add(models.AuditEvent(audit_id=review.audit_id, event_type="HUMAN_DECISION", actor=body.reviewer,
                             summary=f"{body.decision} on {review.target_type}",
                             payload={"target_id": review.target_id, "reason": body.reason}))
    db.commit()
    return {"id": review.id, "status": review.status, "decision": review.decision}


@app.get("/api/agent-runs")
def agent_runs(audit_id: str | None = None, db: Session = Depends(get_db)):
    query = select(models.AgentRun).order_by(models.AgentRun.started_at.desc())
    if audit_id: query = query.where(models.AgentRun.audit_id == audit_id)
    return [dump(x, "id", "audit_id", "agent", "model", "status", "input_summary", "output_summary",
                 "tool_calls", "validation_errors", "tokens", "latency_ms", "started_at", "finished_at")
            for x in db.scalars(query).all()]


@app.get("/api/agents")
def agent_catalog():
    return [vars(value) for value in AGENT_REGISTRY.values()]


@app.get("/api/audits/{audit_id}/events")
def audit_events(audit_id: str, db: Session = Depends(get_db)):
    return [dump(x, "id", "event_type", "actor", "summary", "payload", "immutable", "created_at")
            for x in db.scalars(select(models.AuditEvent).where(models.AuditEvent.audit_id == audit_id)
                                .order_by(models.AuditEvent.created_at)).all()]


@app.get("/api/reports")
def reports(db: Session = Depends(get_db)):
    audits = db.scalars(select(models.Audit)).all()
    return [{**dump(a, "id", "name", "status", "updated_at"),
             "finding_count": db.scalar(select(func.count(models.Finding.id)).where(models.Finding.audit_id == a.id))}
            for a in audits]


@app.get("/api/audits/{audit_id}/report.html")
def report_html(audit_id: str, db: Session = Depends(get_db)):
    audit = db.get(models.Audit, audit_id)
    if not audit: raise HTTPException(404, "Audit not found")
    findings = db.scalars(select(models.Finding).where(models.Finding.audit_id == audit.id)).all()
    rows = "".join(f"<tr><td>{escape(f.assessment)}</td><td>{f.confidence:.0%}</td><td>{escape(f.rationale)}</td><td>{escape(f.recommendation)}</td></tr>" for f in findings)
    body = f"""<!doctype html><html><head><meta charset='utf-8'><title>{escape(audit.name)}</title>
    <style>body{{font:15px system-ui;margin:48px;color:#17221d}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border:1px solid #ccd6d0;text-align:left}}.notice{{background:#fff5cc;padding:12px}}</style></head>
    <body><h1>{escape(audit.name)}</h1><p class='notice'>Synthetic demonstration only. Not legal advice.</p>
    <h2>Executive Summary</h2><p>This audit assessed {len(findings)} control(s) for Northstar Payments.</p>
    <h2>Scope</h2><p>{escape(audit.scope)}</p><h2>Requirements, evidence, findings, gaps and recommendations</h2>
    <table><thead><tr><th>Assessment</th><th>Confidence</th><th>Finding</th><th>Recommendation</th></tr></thead><tbody>{rows}</tbody></table>
    <p>Human-reviewed findings: {sum(f.human_status != 'PENDING' for f in findings)}.</p></body></html>"""
    return Response(body, media_type="text/html", headers={"Content-Disposition": f'attachment; filename="audit-{audit.id}.html"'})
