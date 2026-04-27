"""
Multi-Agent Debate Decision Engine — main entry point.
"""
import asyncio
import logging
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from maverickj.events import DebateEvent, DebateEventType, EventCallback
from maverickj.graph.builder import build_debate_graph
from maverickj.llm.router import ModelRouter
from maverickj.output.renderer import render_report_to_markdown
from maverickj.output.stream import (
    console,
    print_advocate_result,
    print_agent_start,
    print_critic_result,
    print_debate_complete,
    print_debate_start,
    print_fact_check_result,
    print_moderator_result,
    print_round_start,
)
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateState, DebateStatus
from maverickj.schemas.report import DecisionReport

logger = logging.getLogger(__name__)

_SENTINEL = object()  # marks "use default Rich output"


def load_config(config_path: str = "config.yaml") -> DebateEngineConfig:
    """Load configuration from YAML."""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return DebateEngineConfig(**data)
    return DebateEngineConfig()


async def run_debate(
    question: str,
    config: Optional[DebateEngineConfig] = None,
    context: Optional[str] = None,
    on_event: Optional[EventCallback] = _SENTINEL,  # type: ignore[assignment]
) -> DebateState:
    """Run a complete debate.

    Args:
        question: The decision question.
        config: Engine config (defaults to loading from config.yaml).
        context: Optional background information.
        on_event: Event callback.
            - Omitted / _SENTINEL → use Rich terminal output (default, backwards-compatible)
            - None              → silent mode, no output
            - custom callable   → receives DebateEvent, suppresses Rich output
    """
    use_rich = on_event is _SENTINEL  # type: ignore[comparison-overlap]

    if config is None:
        config = load_config()

    # Initialise state
    initial_state = DebateState(
        id=str(uuid.uuid4()),
        question=question,
        context=context,
        config=config.debate,
        rounds=[],
        argument_registry={},
        current_round=0,
        status=DebateStatus.RUNNING,
        metadata=DebateMetadata(started_at=datetime.now()),
        supply_chain_config=config.supply_chain,
    )

    # Create model router
    router = ModelRouter(config)

    # Build LangGraph
    app = build_debate_graph(router)

    def _emit(event_type: DebateEventType, round_num: int, data=None) -> None:
        if use_rich:
            return  # Rich output is handled directly by the if-blocks below
        if on_event is not None:
            on_event(DebateEvent(type=event_type, round_number=round_num, data=data))

    if use_rich:
        print_debate_start(question)
    elif on_event is not None:
        on_event(DebateEvent(type=DebateEventType.DEBATE_START, round_number=0, data=question))

    # Run graph — use astream for real-time output
    final_state = None
    current_round_num = 0

    async for event in app.astream(initial_state, stream_mode="values"):
        state = event if isinstance(event, DebateState) else DebateState(**event)

        # Detect new round start
        if state.current_round > current_round_num:
            current_round_num = state.current_round
            if use_rich:
                print_round_start(current_round_num)
            else:
                _emit(DebateEventType.ROUND_START, current_round_num, current_round_num)

        # Print each agent result in real-time
        if state.current_round_advocate and (
            final_state is None or final_state.current_round_advocate != state.current_round_advocate
        ):
            if use_rich:
                print_advocate_result(state.current_round_advocate)
            else:
                _emit(DebateEventType.ADVOCATE_DONE, current_round_num, state.current_round_advocate)

        if state.current_round_critic and (
            final_state is None or final_state.current_round_critic != state.current_round_critic
        ):
            if use_rich:
                print_critic_result(state.current_round_critic)
            else:
                _emit(DebateEventType.CRITIC_DONE, current_round_num, state.current_round_critic)

        if state.current_round_fact_check and (
            final_state is None or final_state.current_round_fact_check != state.current_round_fact_check
        ):
            if use_rich:
                print_fact_check_result(state.current_round_fact_check)
            else:
                _emit(DebateEventType.FACT_CHECK_DONE, current_round_num, state.current_round_fact_check)

        if state.current_round_moderator and (
            final_state is None or final_state.current_round_moderator != state.current_round_moderator
        ):
            if use_rich:
                print_moderator_result(state.current_round_moderator)
            else:
                _emit(DebateEventType.MODERATOR_DONE, current_round_num, state.current_round_moderator)

        final_state = state

    if final_state:
        if use_rich:
            print_debate_complete(
                final_state.status.value,
                final_state.convergence_reason,
            )
        else:
            _emit(DebateEventType.DEBATE_COMPLETE, current_round_num, final_state)

    return final_state


def main():
    """CLI entry point."""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

    if len(sys.argv) < 2:
        print("Usage: python -m maverickj.main <decision question> [context]")
        print('Example: python -m maverickj.main "Should we migrate our Java backend to Go?" "50-person team, 3 years on Spring Boot"')
        sys.exit(1)

    question = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else None

    config = load_config()
    state = asyncio.run(run_debate(question, config, context))

    if state and state.final_report:
        report = state.final_report
        if isinstance(report, dict):
            report = DecisionReport(**report)
        markdown = render_report_to_markdown(report, state)
        import os
        os.makedirs("reports", exist_ok=True)
        slug = re.sub(r'[\\/:*?"<>|]+', "-", question)
        slug = re.sub(r'\s+', "-", slug).strip("-")[:60] or "debate"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = f"reports/{slug}-{timestamp}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"\n📄 Report saved to: {output_file}")


if __name__ == "__main__":
    main()
