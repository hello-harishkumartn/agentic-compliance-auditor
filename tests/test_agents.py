from agents.base import AgentContext
from agents.components import RequirementExtractionAgent
from agents.contracts import RequirementExtractionInput


def test_extracts_only_normative_requirements():
    output = RequirementExtractionAgent().run(RequirementExtractionInput(
        framework_id="f", framework_name="Synthetic", content=(
            "# Framework\nREQ-001: Teams must review access quarterly.\n"
            "NOTE-1: Teams may use the sample template."
        )), AgentContext(audit_id="a", model="test", tools=object()))
    assert [r.reference for r in output.requirements] == ["REQ-001"]

