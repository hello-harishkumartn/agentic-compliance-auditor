# Security

## Threat model

Primary risks are prompt injection in uploaded evidence, unsupported compliance claims, data leakage across audit scopes, over-privileged tools, malicious files, and unaudited human overrides.

## Controls implemented

- Uploaded and retrieved content is explicitly tagged untrusted.
- Evidence analysis detects common instruction-like patterns and excludes those passages.
- Agents receive narrow allow-lists; mutations exist only in `save_finding` and `request_human_review`.
- Structured Pydantic validation rejects unsupported `COMPLIANT` outputs.
- The verifier independently checks citation, evidence-strength, and confidence invariants.
- Workflow transitions and human decisions generate append-oriented audit events.
- Context is bounded to necessary passages, and displayed rationale is a concise summary—not chain-of-thought.
- Credentials are environment variables and `.env` is ignored.

## Production hardening backlog

- Authentication, tenant-scoped RBAC, row-level security, and reviewer separation of duties.
- Malware scanning, file-type allow-listing, OCR isolation, size limits, and object-store signed URLs.
- Encrypted fields, secret manager integration, retention rules, and immutable/WORM event export.
- Rate limits, request IDs, OpenTelemetry, dependency/image scanning, and signed releases.
- Egress restrictions for model providers and configurable data residency.
- Adversarial prompt-injection evaluation before every release.

## Reporting vulnerabilities

Do not include sensitive evidence in a public issue. Contact the repository owner privately with reproduction steps and impact.

