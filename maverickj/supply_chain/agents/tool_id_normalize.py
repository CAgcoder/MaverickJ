"""Map LangChain/provider tool_call ids (e.g. toolu_...) to ledger TC-*** on structured output."""

from __future__ import annotations

from maverickj.schemas.agents import AgentResponse


def normalize_agent_response_tool_ids(
    response: AgentResponse,
    provider_to_ledger: dict[str, str],
) -> AgentResponse:
    """Replace provider ids in `tool_call_ids` and `evidence` with ledger ``TC-***`` ids."""
    if not provider_to_ledger:
        return response

    new_arguments = []
    for arg in response.arguments:
        new_ids = [provider_to_ledger.get(tid, tid) for tid in arg.tool_call_ids]
        ev = arg.evidence
        if ev:
            for prov, lid in sorted(provider_to_ledger.items(), key=lambda x: -len(x[0])):
                ev = ev.replace(prov, lid)
        new_arguments.append(arg.model_copy(update={"tool_call_ids": new_ids, "evidence": ev}))
    return response.model_copy(update={"arguments": new_arguments})
