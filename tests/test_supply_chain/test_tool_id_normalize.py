from maverickj.schemas.agents import AgentResponse
from maverickj.schemas.arguments import Argument, ArgumentStatus
from maverickj.supply_chain.agents.tool_id_normalize import normalize_agent_response_tool_ids


def test_normalize_replaces_provider_ids() -> None:
    prov = "toolu_01TESTabc"
    r = AgentResponse(
        agent_role="advocate",
        arguments=[
            Argument(
                id="COST-R1-01",
                claim="c",
                reasoning="r",
                tool_call_ids=[prov, "TC-001"],
                evidence=f"See {prov} and TC-001",
            )
        ],
    )
    out = normalize_agent_response_tool_ids(
        r,
        {prov: "TC-014"},
    )
    a0 = out.arguments[0]
    assert prov not in a0.tool_call_ids
    assert "TC-014" in a0.tool_call_ids
    assert "TC-001" in a0.tool_call_ids
    assert prov not in (a0.evidence or "")
    assert "TC-014" in (a0.evidence or "")
