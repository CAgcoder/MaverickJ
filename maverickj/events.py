"""
Debate engine event system — decouples Rich console output from core logic.

Third-party integrators can pass an `on_event` callback to DebateEngine (or
`run_debate`) to receive structured events instead of (or in addition to) the
default Rich terminal output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Callable


class DebateEventType(str, Enum):
    """Types of events emitted during a debate session."""

    DEBATE_START = "debate_start"
    ROUND_START = "round_start"
    ADVOCATE_DONE = "advocate_done"
    CRITIC_DONE = "critic_done"
    FACT_CHECK_DONE = "fact_check_done"
    MODERATOR_DONE = "moderator_done"
    DEBATE_COMPLETE = "debate_complete"


@dataclass
class DebateEvent:
    """A structured event emitted at each stage of the debate."""

    type: DebateEventType
    round_number: int
    data: Any = field(default=None)
    """
    Payload type per event:
    - DEBATE_START      → str (the question)
    - ROUND_START       → int (round number, same as round_number)
    - ADVOCATE_DONE     → AgentResponse
    - CRITIC_DONE       → AgentResponse
    - FACT_CHECK_DONE   → FactCheckResponse
    - MODERATOR_DONE    → ModeratorResponse
    - DEBATE_COMPLETE   → DebateState (final state)
    """


# Type alias for the callback signature
EventCallback = Callable[[DebateEvent], None]
