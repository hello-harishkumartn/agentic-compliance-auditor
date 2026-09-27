import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Framework(Base):
    __tablename__ = "frameworks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(40))
    source_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    description: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    framework_id: Mapped[str] = mapped_column(ForeignKey("frameworks.id"), index=True)
    reference: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(250))
    statement: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    source_quote: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Control(Base):
    __tablename__ = "controls"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(250))
    objective: Mapped[str] = mapped_column(Text)
    test_procedure: Mapped[str] = mapped_column(Text)
    expected_evidence: Mapped[list] = mapped_column(JSON, default=list)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(250))
    kind: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    trust_level: Mapped[str] = mapped_column(String(20), default="untrusted")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidencePassage(Base):
    __tablename__ = "evidence_passages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(100))
    relevance: Mapped[float] = mapped_column(Float, default=0)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list | None] = mapped_column(Vector(64).with_variant(JSON(), "sqlite"), nullable=True)


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(250))
    framework_id: Mapped[str] = mapped_column(ForeignKey("frameworks.id"))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT")
    scope: Mapped[str] = mapped_column(Text)
    progress: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"))
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.id"))
    assessment: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    evidence_strength: Mapped[str] = mapped_column(String(20))
    rationale: Mapped[str] = mapped_column(Text)
    gap: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list] = mapped_column(JSON, default=list)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)
    human_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str] = mapped_column(String, index=True)
    ai_recommendation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
