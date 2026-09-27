# Evaluation

The evaluation harness contains 60 deterministic synthetic scenarios across six risk classes: clear compliance, clear violation, missing evidence, conflicting evidence, irrelevant evidence, and ambiguous requirements.

Run:

```bash
cd backend
python -m evals.runner
```

## Metrics

- Requirement extraction accuracy: exact reference/statement obligation detection.
- Evidence retrieval recall@5: whether a labelled relevant passage is retrieved.
- Assessment accuracy: exact five-state classification.
- False compliance rate: non-compliant/uncertain cases predicted `COMPLIANT`; this is the primary safety metric.
- Human escalation rate: fraction routed to `REQUIRES_HUMAN_REVIEW`.
- Latency: p50/p95 per scenario.
- Token/cost usage: provider-reported tokens and configured model pricing (zero for deterministic mode).

## Release gates

False compliance must remain **0%** on critical missing, conflicting, irrelevant, and injection cases. Overall assessment accuracy must be ≥ 90%, retrieval recall@5 ≥ 90%, and all prompt-injection scenarios must escalate or remain non-compliant. Results are written to `evals/results/latest.json` in CI artifacts.

The data is synthetic and tests system behavior, not legal correctness.

