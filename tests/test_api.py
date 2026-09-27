from fastapi.testclient import TestClient

from backend.app.database import get_db
from backend.app.main import app
from backend.app import models
from backend.app.seed import seed_database


def test_dashboard_and_endpoints(db):
    seed_database(db)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/frameworks").json()[0]["source_type"] == "synthetic"
        assert client.get("/api/dashboard").status_code == 200
    app.dependency_overrides.clear()


def test_human_decision_records_actor_reason_and_timestamp(db):
    framework = models.Framework(name="F", version="1", source_type="synthetic", description="", content="REQ-1: Team must test controls.")
    db.add(framework); db.flush()
    requirement = models.Requirement(framework_id=framework.id, reference="REQ-1", title="Test", statement="Must test", rationale="", source_quote="Must test")
    db.add(requirement); db.flush()
    audit = models.Audit(name="A", framework_id=framework.id, scope="test")
    db.add(audit); db.flush()
    review = models.Review(audit_id=audit.id, target_type="requirement", target_id=requirement.id, ai_recommendation="Approve")
    db.add(review); db.commit()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        response = client.post(f"/api/reviews/{review.id}/decision", json={
            "decision": "APPROVE", "reason": "Matches the cited source.", "reviewer": "A. Reviewer"
        })
        assert response.status_code == 200
    db.refresh(review)
    assert review.reviewer == "A. Reviewer" and review.decided_at is not None
    assert db.query(models.AuditEvent).filter_by(event_type="HUMAN_DECISION").count() == 1
    app.dependency_overrides.clear()
