from backend.app import models
from tools import ComplianceTools


def test_search_documents_returns_traceable_passage(db):
    doc = models.Document(name="Access record", kind="evidence", content="Quarterly access review approved")
    db.add(doc); db.flush()
    passage = models.EvidencePassage(document_id=doc.id, content=doc.content, locator="page 1", content_hash="x",
                                     embedding=ComplianceTools.embedding(doc.content))
    db.add(passage); db.commit()
    results = ComplianceTools(db, "audit").search_documents("quarterly privileged access review")
    assert results[0]["id"] == passage.id
    assert results[0]["document_name"] == "Access record"
