import pytest

from backend.app import models
from backend.app.seed import FRAMEWORK_TEXT, DOCUMENTS
from backend.app.workflow import AuditWorkflow, WorkflowError
from tools import ComplianceTools


def prepare(db):
    framework = models.Framework(name="NCF", version="1", source_type="synthetic", description="test", content=FRAMEWORK_TEXT)
    db.add(framework); db.flush()
    for name, kind, content in DOCUMENTS:
        doc = models.Document(name=name, kind=kind, content=content)
        db.add(doc); db.flush()
        db.add(models.EvidencePassage(document_id=doc.id, content=content, locator="p1",
                                      content_hash=ComplianceTools.passage_hash(content),
                                      embedding=ComplianceTools.embedding(content)))
    audit = models.Audit(name="Test", framework_id=framework.id, scope="All")
    db.add(audit); db.commit()
    return audit


def test_workflow_pauses_for_requirement_review(db):
    audit = prepare(db)
    AuditWorkflow(db, audit).start()
    assert audit.status == "AWAITING_REQUIREMENT_REVIEW"
    with pytest.raises(WorkflowError, match="still pending"):
        AuditWorkflow(db, audit).resume()
    assert any(event.event_type == "STATE_TRANSITION" for event in db.query(models.AuditEvent).all())


def test_more_evidence_request_keeps_human_gate_closed(db):
    audit = prepare(db)
    AuditWorkflow(db, audit).start()
    reviews = db.query(models.Review).filter_by(audit_id=audit.id).all()
    for review in reviews:
        review.status, review.decision = "DECIDED", "APPROVE"
    reviews[0].status, reviews[0].decision = "EVIDENCE_REQUESTED", "REQUEST_MORE_EVIDENCE"
    db.commit()
    with pytest.raises(WorkflowError, match="still pending"):
        AuditWorkflow(db, audit).resume()


def test_invalid_state_transition_is_rejected(db):
    audit = prepare(db)
    with pytest.raises(WorkflowError):
        AuditWorkflow(db, audit).transition("REPORT_READY", 100)
