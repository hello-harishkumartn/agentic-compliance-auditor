import hashlib
import math
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models


class ToolPermissionError(PermissionError):
    pass


class RestrictedTools:
    """Runtime capability facade; agents cannot reach methods outside their declaration."""

    def __init__(self, tools: "ComplianceTools", allowed: frozenset[str]):
        self._tools, self._allowed = tools, allowed

    def __getattr__(self, name: str):
        if name not in self._allowed:
            raise ToolPermissionError(f"Tool '{name}' is not permitted for this agent")
        return getattr(self._tools, name)


class ComplianceTools:
    """MCP-ready service methods. Every method is narrow and side effects are explicit."""

    def __init__(self, db: Session, audit_id: str, actor: str = "workflow"):
        self.db, self.audit_id, self.actor = db, audit_id, actor

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2}

    def search_documents(self, query: str, limit: int = 5) -> list[dict]:
        terms = self._tokens(query)
        query_vector = self.embedding(query)
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            passages = self.db.scalars(select(models.EvidencePassage).order_by(
                models.EvidencePassage.embedding.cosine_distance(query_vector)
            ).limit(max(limit * 4, 20))).all()
        else:
            passages = self.db.scalars(select(models.EvidencePassage)).all()
        docs = {d.id: d for d in self.db.scalars(select(models.Document)).all()}
        scored = []
        for passage in passages:
            overlap = len(terms & self._tokens(passage.content))
            lexical_score = overlap / max(len(terms), 1)
            vector_score = self.cosine(query_vector, passage.embedding or self.embedding(passage.content))
            score = 0.65 * lexical_score + 0.35 * max(vector_score, 0)
            if score >= 0.12:
                doc = docs[passage.document_id]
                scored.append({"id": passage.id, "document_id": doc.id, "document_name": doc.name,
                               "locator": passage.locator, "content": passage.content, "score": round(score, 3)})
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]

    def retrieve_evidence(self, passage_id: str) -> dict:
        passage = self.db.get(models.EvidencePassage, passage_id)
        if not passage:
            raise KeyError("Evidence passage not found")
        doc = self.db.get(models.Document, passage.document_id)
        return {"id": passage.id, "document_id": doc.id, "document_name": doc.name,
                "locator": passage.locator, "content": passage.content, "score": passage.relevance}

    def get_document(self, document_id: str) -> dict:
        doc = self.db.get(models.Document, document_id)
        if not doc:
            raise KeyError("Document not found")
        return {"id": doc.id, "name": doc.name, "kind": doc.kind, "content": doc.content,
                "trust_level": doc.trust_level}

    def extract_section(self, document_id: str, heading: str) -> str:
        doc = self.get_document(document_id)
        match = re.search(rf"(?ims)^#+\s*{re.escape(heading)}.*?(?=^#|\Z)", doc["content"])
        return match.group(0).strip() if match else ""

    def list_controls(self) -> list[dict]:
        return [{"id": c.id, "code": c.code, "title": c.title}
                for c in self.db.scalars(select(models.Control)).all()]

    def get_requirement(self, requirement_id: str) -> dict:
        item = self.db.get(models.Requirement, requirement_id)
        if not item:
            raise KeyError("Requirement not found")
        return {"id": item.id, "reference": item.reference, "statement": item.statement, "status": item.status}

    def save_finding(self, **values) -> models.Finding:
        finding = models.Finding(audit_id=self.audit_id, **values)
        self.db.add(finding)
        self._event("FINDING_SAVED", f"Finding {finding.id} saved", {"assessment": finding.assessment})
        self.db.flush()
        return finding

    def request_human_review(self, target_type: str, target_id: str, recommendation: str) -> models.Review:
        review = models.Review(audit_id=self.audit_id, target_type=target_type, target_id=target_id,
                               ai_recommendation=recommendation)
        self.db.add(review)
        self._event("HUMAN_REVIEW_REQUESTED", f"Review requested for {target_type}", {"target_id": target_id})
        self.db.flush()
        return review

    def _event(self, event_type: str, summary: str, payload: dict):
        self.db.add(models.AuditEvent(audit_id=self.audit_id, event_type=event_type,
                                      actor=self.actor, summary=summary, payload=payload))

    @staticmethod
    def passage_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def embedding(cls, content: str, dimensions: int = 64) -> list[float]:
        """Local deterministic embedding for zero-cost demos; replaceable with provider embeddings."""
        vector = [0.0] * dimensions
        for token in cls._tokens(content):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % dimensions
            vector[index] += 1.0 if digest[2] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    @staticmethod
    def cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))
