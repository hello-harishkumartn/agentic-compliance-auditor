import pytest

from tools import ComplianceTools, RestrictedTools, ToolPermissionError


def test_agent_tool_permissions_are_enforced(db):
    restricted = RestrictedTools(ComplianceTools(db, "audit"), frozenset({"search_documents"}))
    assert restricted.search_documents("anything") == []
    with pytest.raises(ToolPermissionError):
        restricted.save_finding(assessment="COMPLIANT")
