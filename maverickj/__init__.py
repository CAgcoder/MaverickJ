"""
maverickj — Multi-Agent adversarial debate-driven decision engine.

Quick start::

    from maverickj import DebateEngine

    engine = DebateEngine()
    result = await engine.debate("Should we build or buy?")
    print(result.report.recommendation)
    print(result.to_markdown())
"""
__version__ = "0.2.0"

from maverickj.engine import DebateEngine, DebateResult
from maverickj.events import DebateEvent, DebateEventType, EventCallback
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateConfig, DebateState, DebateStatus
from maverickj.schemas.report import DecisionReport

__all__ = [
    # High-level API
    "DebateEngine",
    "DebateResult",
    # Events
    "DebateEvent",
    "DebateEventType",
    "EventCallback",
    # Config schemas
    "DebateEngineConfig",
    "DebateConfig",
    # State / result schemas
    "DebateState",
    "DebateStatus",
    "DecisionReport",
    # Version
    "__version__",
]
