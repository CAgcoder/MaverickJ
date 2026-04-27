from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    id: str
    tool_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    invoked_at_round: int
    invoked_by: str
    source: str = "warmup"
    created_at: datetime = Field(default_factory=datetime.utcnow)

