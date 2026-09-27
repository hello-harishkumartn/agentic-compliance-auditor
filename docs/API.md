# API Notes

Interactive OpenAPI documentation is available at `/docs`.

Core mutation flow:

1. `POST /api/audits`
2. `POST /api/audits/{id}/start`
3. Decide requirement items through `POST /api/reviews/{id}/decision`
4. `POST /api/audits/{id}/resume`
5. Decide finding items through the same review endpoint
6. `POST /api/audits/{id}/resume`
7. `GET /api/audits/{id}/report.html`

Read endpoints cover frameworks, requirements, controls, evidence, audits, findings, reviews, agent runs, reports, and audit events.

