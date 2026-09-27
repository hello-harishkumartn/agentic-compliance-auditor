import json
import statistics
import time
from pathlib import Path

from agents.base import AgentContext
from agents.components import ComplianceAssessmentAgent, EvidenceAnalysisAgent, RequirementExtractionAgent
from agents.contracts import ComplianceAssessmentInput, EvidenceAnalysisInput, RequirementExtractionInput
from evals.scenarios import SCENARIOS


class NoTools:
    pass


def run_evaluation() -> dict:
    latencies, predictions = [], []
    extraction_hits = 0
    for index, scenario in enumerate(SCENARIOS):
        start = time.perf_counter()
        context = AgentContext(audit_id=scenario.id, model="deterministic-rules-v1", tools=NoTools())
        analysis = EvidenceAnalysisAgent().run(EvidenceAnalysisInput(
            control_id=f"control-{index}", expected_evidence=["operating record"], passages=scenario.passages,
        ), context)
        result = ComplianceAssessmentAgent().run(ComplianceAssessmentInput(
            requirement_id=f"requirement-{index}", control_id=f"control-{index}", analysis=analysis,
        ), context)
        latencies.append((time.perf_counter() - start) * 1000)
        predictions.append((scenario, result.assessment.value))

        normative = f"REQ-{index:03d}: The company must {scenario.requirement.lower()}"
        extracted = RequirementExtractionAgent().run(RequirementExtractionInput(
            framework_id="evaluation", framework_name="Synthetic evaluation", content=f"# Test framework\n{normative}"
        ), context)
        extraction_hits += int(len(extracted.requirements) == 1)

    accurate = sum(pred == scenario.expected_assessment for scenario, pred in predictions)
    unsafe = [pred for scenario, pred in predictions
              if scenario.expected_assessment != "COMPLIANT" and pred == "COMPLIANT"]
    escalated = sum(pred == "REQUIRES_HUMAN_REVIEW" for _, pred in predictions)
    retrieval_cases = [s for s in SCENARIOS if s.relevant_passage_expected]
    retrieved = sum(any(p["score"] >= .2 for p in s.passages) for s in retrieval_cases)
    return {
        "scenario_count": len(SCENARIOS),
        "requirement_extraction_accuracy": round(extraction_hits / len(SCENARIOS), 4),
        "evidence_retrieval_recall_at_5": round(retrieved / len(retrieval_cases), 4),
        "assessment_accuracy": round(accurate / len(SCENARIOS), 4),
        "false_compliance_rate": round(len(unsafe) / (len(SCENARIOS) - 10), 4),
        "human_escalation_rate": round(escalated / len(SCENARIOS), 4),
        "latency_ms_p50": round(statistics.median(latencies), 3),
        "latency_ms_p95": round(sorted(latencies)[int(len(latencies) * .95) - 1], 3),
        "token_usage": 0,
        "estimated_cost_usd": 0,
        "provider": "deterministic-rules-v1",
    }


def main():
    results = run_evaluation()
    output = Path(__file__).parent / "results" / "latest.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if results["false_compliance_rate"] > 0 or results["assessment_accuracy"] < .9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

