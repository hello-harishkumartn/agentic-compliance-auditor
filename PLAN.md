# Implementation Plan

## Goal

Deliver an auditable, human-supervised compliance workflow for the fictional fintech **Northstar Payments**. The system is a decision workflow, not a chatbot, and uses the clearly labelled synthetic **Northstar Control Framework (NCF) v1.0**.

## Architecture

1. Ingest a framework and evidence documents as untrusted text.
2. Run seven narrow agents through an explicit Python state machine.
3. Persist every artifact, tool call, transition, citation, and review decision.
4. Pause at requirement validation and finding approval checkpoints.
5. Export an evidence-linked report only after required human approvals.

The production stack is Next.js, FastAPI, SQLAlchemy, PostgreSQL, and pgvector. A deterministic provider makes the demo and tests reproducible; Gemini and Ollama share the same provider contract.

## Milestones

- [x] Architecture and contracts
- [x] Backend domain and persistence
- [x] Agent tools and orchestration
- [x] API and report export
- [x] Recruiter-friendly frontend
- [x] 50+ scenario evaluation harness
- [x] Tests, security docs, and CI
- [x] Local frontend verification; backend execution delegated to Python CI

## Definition of done

- A seeded audit can run from regulation to review-ready findings.
- No uncertain or uncited finding can become `COMPLIANT`.
- Review decisions and AI recommendations remain separately traceable.
- The UI explains each finding using citations and concise rationale, never hidden chain-of-thought.
- Tests cover guardrails, state transitions, APIs, tools, and audit history.
