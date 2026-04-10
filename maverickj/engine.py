"""
DebateEngine — high-level Facade API.

Main entry point for third-party developers. Encapsulates config loading,
graph construction, and event routing, providing a clean async-first interface.

Quick start::

    from maverickj import DebateEngine

    engine = DebateEngine()
    result = await engine.debate("Should we build or buy?")
    print(result.report.recommendation)
    print(result.to_markdown())

With config::

    engine = DebateEngine(
        provider="openai",
        model="gpt-4o",
        max_rounds=3,
    )

Silent mode (no terminal output, suitable for integration)::

    engine = DebateEngine(on_event=None)

Custom event callback::

    def my_handler(event):
        print(event.type, event.round_number)

    engine = DebateEngine(on_event=my_handler)

Load from YAML::

    engine = DebateEngine.from_yaml("my_config.yaml")
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from maverickj.events import EventCallback
from maverickj.main import load_config, run_debate, _SENTINEL
from maverickj.output.renderer import render_report_to_markdown
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateState
from maverickj.schemas.report import DecisionReport


@dataclass
class DebateResult:
    """Debate execution result: contains the final report and full debate state."""

    state: DebateState
    report: DecisionReport

    def to_markdown(self) -> str:
        """Render the full debate report as Markdown."""
        return render_report_to_markdown(self.report, self.state)

    def to_dict(self) -> dict:
        """Serialise the report to a dict (safe for JSON serialisation)."""
        return self.report.model_dump()


class DebateEngine:
    """High-level Facade for the multi-agent debate decision engine.

    Args:
        config:     Pass a DebateEngineConfig instance directly (mutually exclusive with other args).
        provider:   Default LLM provider, e.g. "claude" / "openai" / "gemini".
        model:      Default model name.
        max_rounds: Maximum debate rounds (overrides debate.max_rounds in config).
        on_event:   Event callback:
                    - Omitted (default) → Rich terminal output
                    - None              → silent mode
                    - callable          → custom handler, suppresses Rich output
    """

    def __init__(
        self,
        *,
        config: Optional[DebateEngineConfig] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_rounds: Optional[int] = None,
        on_event: Optional[EventCallback] = _SENTINEL,  # type: ignore[assignment]
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = load_config()

        # Override individual fields if provided
        if provider is not None:
            self._config = self._config.model_copy(
                update={"default_provider": provider}
            )
        if model is not None:
            self._config = self._config.model_copy(
                update={"default_model": model}
            )
        if max_rounds is not None:
            updated_debate = self._config.debate.model_copy(
                update={"max_rounds": max_rounds}
            )
            self._config = self._config.model_copy(
                update={"debate": updated_debate}
            )

        self._on_event = on_event

    @classmethod
    def from_yaml(cls, config_path: str, **kwargs) -> "DebateEngine":
        """Create a DebateEngine instance from a YAML file.

        Args:
            config_path: Path to the YAML config file.
            **kwargs:    Additional arguments forwarded to DebateEngine.__init__.
        """
        config = load_config(config_path)
        return cls(config=config, **kwargs)

    async def debate(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> DebateResult:
        """Run a complete debate and return structured results.

        Args:
            question: The decision question, e.g. "Should we migrate to microservices?"
            context:  Optional background information (team size, budget, constraints, etc.)

        Returns:
            DebateResult with .report (DecisionReport) and .state (DebateState).
        """
        state = await run_debate(
            question=question,
            config=self._config,
            context=context,
            on_event=self._on_event,
        )

        report = state.final_report
        if report is None:
            raise RuntimeError("Debate completed without generating a final report.")
        if isinstance(report, dict):
            report = DecisionReport(**report)

        return DebateResult(state=state, report=report)
