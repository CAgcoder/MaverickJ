"""Agent wrapper with optional LangChain tool-calling before structured output."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.supply_chain.tools.registry import ToolCallRegistry

logger = logging.getLogger(__name__)


class SupplyChainAgent(BaseAgent):
    """Same as BaseAgent, plus Tier-2 tool rounds then a final structured completion."""

    def __init__(self, router: ModelRouter, role: str):
        super().__init__(router)
        self.role = role

    async def invoke_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: type[BaseModel],
        tools: list[Any],
        *,
        max_tool_calls: int = 5,
        tool_registry: ToolCallRegistry | None = None,
        invoked_at_round: int = 1,
        invoked_by: str = "",
        source: str = "agent",
    ) -> tuple[Any, dict, dict[str, str]]:
        if not tools or max_tool_calls <= 0:
            parsed, usage = await self.invoke(system_prompt, user_message, output_schema)
            return parsed, usage, {}

        model = self.router.get_model(self.role)
        try:
            bound = model.bind_tools(tools)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] bind_tools unsupported, using structured-only: %s", self.role, exc)
            parsed, usage = await self.invoke(system_prompt, user_message, output_schema)
            return parsed, usage, {}

        by_name = {getattr(t, "name", None): t for t in tools if getattr(t, "name", None)}
        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        provider_to_ledger: dict[str, str] = {}
        calls_used = 0
        while calls_used < max_tool_calls:
            response = await bound.ainvoke(messages)
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                messages.append(response)
                break

            messages.append(response)
            for tc in tool_calls:
                if calls_used >= max_tool_calls:
                    break
                name = tc.get("name")
                args = tc.get("args") or {}
                tool_call_id = tc.get("id") or ""
                tool = by_name.get(name)
                if tool is None:
                    payload = {"error": f"unknown tool {name!r}"}
                else:
                    try:
                        if hasattr(tool, "ainvoke"):
                            payload = await tool.ainvoke(args)
                        else:
                            payload = tool.invoke(args)
                    except Exception as err:  # noqa: BLE001
                        logger.exception("[%s] tool %s failed", self.role, name)
                        payload = {"error": str(err)}
                if tool_registry is not None and name:
                    out_dict = payload if isinstance(payload, dict) else {"result": payload}
                    in_dict = dict(args) if isinstance(args, dict) else {"args": args}
                    rec = tool_registry.record(
                        tool_name=name,
                        inputs=in_dict,
                        outputs=out_dict,
                        summary=f"{name} tier-2",
                        invoked_at_round=invoked_at_round,
                        invoked_by=invoked_by or self.role,
                        source=source,
                    )
                    if tool_call_id:
                        provider_to_ledger[tool_call_id] = rec.id
                calls_used += 1
                text = json.dumps(payload, default=str)[:12000]
                messages.append(ToolMessage(content=text, tool_call_id=tool_call_id))

        transcript_lines: list[str] = []
        for msg in messages[2:]:
            label = msg.__class__.__name__
            body = getattr(msg, "content", "") or ""
            transcript_lines.append(f"{label}: {body}")

        augmented = user_message
        if transcript_lines:
            augmented += "\n\n### Tool transcript\n" + "\n".join(transcript_lines)
        if provider_to_ledger:
            lines = [
                "### Provider → Ledger ID mapping (mandatory)",
                "In `arguments[].tool_call_ids` and in `evidence` strings, cite **only** Ledger IDs (`TC-***`). "
                "Do **not** use raw provider ids (`toolu_...`, etc.).",
            ]
            for prov, lid in sorted(provider_to_ledger.items()):
                lines.append(f"- `{prov}` → **{lid}**")
            augmented += "\n\n" + "\n".join(lines)

        parsed, usage = await self.invoke(system_prompt, augmented, output_schema)
        return parsed, usage, provider_to_ledger
