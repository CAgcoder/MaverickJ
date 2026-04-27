"""
Phase 6 smoke: run fusion_synthesis → convergence_critique → fusion_finalize on a tiny synthetic state.

Requires API keys as in the rest of MaverickJ (e.g. ANTHROPIC_API_KEY from .env).

Usage:
  # Local
  python examples/fusion_phase6_smoke.py

  # Podman (from repo root; pass env with your keys)
  podman build -f Containerfile -t maverickj-fusion6 .
  podman run --rm -e ANTHROPIC_API_KEY -v "$PWD/config.yaml:/app/config.yaml:ro" maverickj-fusion6

  # Scoring only (no LLM; no keys)
  python examples/fusion_phase6_smoke.py --scoring-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Allow running as `python examples/...` from repo root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from maverickj.llm.router import ModelRouter
from maverickj.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse
from maverickj.schemas.arguments import (
    Argument,
    ArgumentRecord,
    ArgumentStatus,
    FactCheck,
    FactCheckVerdict,
)
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateRound, DebateState, DebateStatus
from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.main import load_config
from maverickj.supply_chain.fusion_scoring import collect_scored_arguments, filter_high_score_arguments
from maverickj.supply_chain.nodes.convergence_critique import convergence_critique_node
from maverickj.supply_chain.nodes.fusion_finalize import fusion_finalize_node
from maverickj.supply_chain.nodes.fusion_synthesis import fusion_synthesis_node


def _synthetic_state() -> DebateState:
    arg = Argument(
        id="COST-R1-01",
        claim="[战略方向] 评估将 SKU-A21 主供应从本地迁往东南亚的 TCO。",
        reasoning="Baseline paths diverge on freight and tariff.",
        evidence="TC-001 warmup EOQ",
        tool_call_ids=["TC-001"],
        status=ArgumentStatus.ACTIVE,
    )
    reg = {
        "COST-R1-01": ArgumentRecord(argument=arg, raised_in_round=1, raised_by="advocate"),
    }
    fc = FactCheckResponse(
        checks=[
            FactCheck(
                target_argument_id="COST-R1-01",
                verdict=FactCheckVerdict.VALID,
                explanation="Numbers trace to warmup ledger.",
                factuality_score=8.5,
                logic_score=8.0,
            )
        ],
        overall_assessment="ok",
    )
    mod = ModeratorResponse(
        round_summary="Round 1",
        key_divergences=["cost vs risk"],
        convergence_score=0.4,
        should_continue=True,
        feasibility_scores={"COST-R1-01": 8.5},
        relevance_scores={"COST-R1-01": 8.5},
    )
    rnd = DebateRound(
        round_number=1,
        advocate=AgentResponse(agent_role="advocate", arguments=[arg]),
        critic=AgentResponse(agent_role="critic", arguments=[]),
        fact_check=fc,
        moderator=mod,
    )
    return DebateState(
        id=str(uuid.uuid4()),
        question="我们是否应将 SKU-A21 主供应商从本地切换到东南亚 SUP-SEA-03？",
        context=None,
        config=DebateConfig(mode="supply_chain"),
        rounds=[rnd],
        argument_registry=reg,
        current_round=1,
        status=DebateStatus.RUNNING,
        metadata=DebateMetadata(started_at=datetime.now()),
        supply_chain_config=SupplyChainConfig(),
    )


async def _run_pipeline(cfg: DebateEngineConfig, scoring_only: bool) -> None:
    state = _synthetic_state()
    state.supply_chain_config = cfg.supply_chain

    scored = collect_scored_arguments(state)
    cand = filter_high_score_arguments(scored, cfg.supply_chain)
    print("--- scoring (deterministic) ---")
    print(json.dumps([s.__dict__ for s in scored], ensure_ascii=False, indent=2))
    print("candidates after thresholds:", [c.argument_id for c in cand])

    if scoring_only:
        return

    router = ModelRouter(cfg)
    u1 = await fusion_synthesis_node(state, router)
    state = state.model_copy(update=u1)
    u2 = await convergence_critique_node(state, router)
    state = state.model_copy(update=u2)
    u3 = await fusion_finalize_node(state, router)
    state = state.model_copy(update=u3)

    print("\n--- fusion_draft ---")
    print(state.fusion_draft)
    print("\n--- convergence_critiques ---")
    print(state.convergence_critiques)
    print("\n--- final_fused_decision ---")
    print(state.final_fused_decision)
    print("\n--- metadata (llm calls / tokens) ---")
    print(state.metadata.total_llm_calls, state.metadata.total_tokens_used)


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--scoring-only", action="store_true", help="No LLM; print deterministic scores only.")
    ap.add_argument("--config", type=str, default="config.yaml")
    args = ap.parse_args()

    path = Path(args.config)
    cfg = load_config(str(path)) if path.exists() else DebateEngineConfig()

    asyncio.run(_run_pipeline(cfg, scoring_only=args.scoring_only))


if __name__ == "__main__":
    main()
