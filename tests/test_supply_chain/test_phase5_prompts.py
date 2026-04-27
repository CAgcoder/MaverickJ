"""Smoke tests for supply-chain fact_checker + moderator prompt dispatch (phase 5)."""

from datetime import datetime
from pathlib import Path

import pytest

from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateState, DebateStatus
from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.supply_chain.schemas.fallacy import SupplyChainFallacy


def test_fallacy_enum_six_kinds() -> None:
    assert len(SupplyChainFallacy) == 6


@pytest.mark.asyncio
async def test_sc_fact_checker_prompt_contains_tool_ledger_and_fallacies() -> None:
    from maverickj.prompts.fact_checker import build_fact_checker_system_prompt, build_fact_checker_user_message
    from maverickj.schemas.agents import AgentResponse
    from maverickj.schemas.arguments import Argument
    from unittest.mock import MagicMock
    from maverickj.supply_chain.nodes.data_warmup import data_warmup_node
    from maverickj.schemas.supply_chain_engine import MarketDataConfig

    repo = Path(__file__).resolve().parents[2]
    data_dir = repo / "maverickj" / "supply_chain" / "data"
    sc = SupplyChainConfig(data_path=str(data_dir), market_data=MarketDataConfig(offline_mode=True))
    state = DebateState(
        id="p5",
        question="SKU-A21 切换？",
        config=DebateConfig(mode="supply_chain", language="zh"),
        metadata=DebateMetadata(started_at=datetime.now()),
        current_round=1,
        status=DebateStatus.RUNNING,
        supply_chain_config=sc,
    )
    warm = await data_warmup_node(state, MagicMock())
    state = state.model_copy(
        update={
            "tool_calls": warm["tool_calls"],
            "current_round_data_pack": warm["current_round_data_pack"],
            "current_round_advocate": AgentResponse(
                agent_role="advocate",
                arguments=[
                    Argument(
                        id="COST-R1-01",
                        claim="x",
                        reasoning="y",
                        tool_call_ids=["TC-001"],
                    )
                ],
                rebuttals=[],
            ),
        }
    )
    sp = build_fact_checker_system_prompt(state)
    assert "Supply-Chain Fact-Checker" in sp
    assert "local_optima_trap" in sp
    assert "tool_calls" in sp or "工具" in sp
    um = build_fact_checker_user_message(state)
    assert "TC-001" in um or "tool call ledger" in um.lower() or "Tool call ledger" in um
    assert "COST-R1-01" in um


def test_sc_moderator_system_prompt_asks_for_scores() -> None:
    from maverickj.prompts.moderator import build_moderator_system_prompt
    from maverickj.schemas.agents import AgentResponse
    from maverickj.schemas.arguments import Argument

    state = DebateState(
        id="p5b",
        question="q",
        config=DebateConfig(mode="supply_chain", language="en"),
        metadata=DebateMetadata(started_at=datetime.now()),
        current_round=1,
        status=DebateStatus.RUNNING,
        supply_chain_config=SupplyChainConfig(),
        current_round_advocate=AgentResponse(
            agent_role="advocate",
            arguments=[Argument(id="COST-R1-01", claim="a", reasoning="b")],
        ),
        current_round_critic=AgentResponse(
            agent_role="critic",
            arguments=[Argument(id="RISK-R1-01", claim="c", reasoning="d")],
        ),
    )
    sp = build_moderator_system_prompt(state)
    assert "feasibility_scores" in sp and "relevance_scores" in sp
    assert "Supply-Chain Debate Moderator" in sp
    assert "COST-R1-01" in sp and "RISK-R1-01" in sp
