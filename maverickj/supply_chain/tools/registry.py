from __future__ import annotations

from typing import Any

from maverickj.supply_chain.schemas.tool_call import ToolCallRecord


class ToolCallRegistry:
    """Generate and persist tool call records into state.tool_calls."""

    def __init__(self, state):
        self.state = state

    def _next_id(self) -> str:
        current = len(self.state.tool_calls) + 1
        return f"TC-{current:03d}"

    def record(
        self,
        *,
        tool_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        summary: str,
        invoked_at_round: int,
        invoked_by: str,
        source: str,
    ) -> ToolCallRecord:
        record = ToolCallRecord(
            id=self._next_id(),
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs,
            summary=summary,
            invoked_at_round=invoked_at_round,
            invoked_by=invoked_by,
            source=source,
        )
        self.state.tool_calls[record.id] = record.model_dump(mode="json")
        return record

