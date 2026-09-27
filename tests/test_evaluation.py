from evals.runner import run_evaluation
from evals.scenarios import SCENARIOS


def test_evaluation_has_at_least_fifty_scenarios():
    assert len(SCENARIOS) >= 50


def test_false_compliance_release_gate():
    results = run_evaluation()
    assert results["false_compliance_rate"] == 0
    assert results["assessment_accuracy"] >= .9

