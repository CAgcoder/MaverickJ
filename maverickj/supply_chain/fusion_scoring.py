"""Derive composite scores for fusion from debate rounds (fact / logic / feasibility / relevance)."""

from __future__ import annotations

from dataclasses import dataclass

from maverickj.schemas.arguments import ArgumentStatus
from maverickj.schemas.debate import DebateState
from maverickj.schemas.supply_chain_engine import SupplyChainConfig


DEFAULT_DIM_SCORE = 5.0


@dataclass(frozen=True)
class ScoredArgumentForFusion:
    argument_id: str
    claim: str
    raised_by: str
    factuality: float
    logic: float
    feasibility: float
    relevance: float
    composite: float


def _latest_fact_check_for_argument(state: DebateState, arg_id: str):
    for rnd in reversed(state.rounds):
        for chk in rnd.fact_check.checks:
            if chk.target_argument_id == arg_id:
                return chk
    return None


def _latest_feasibility(state: DebateState, arg_id: str) -> float | None:
    for rnd in reversed(state.rounds):
        if arg_id in rnd.moderator.feasibility_scores:
            return rnd.moderator.feasibility_scores[arg_id]
    return None


def _latest_relevance(state: DebateState, arg_id: str) -> float | None:
    for rnd in reversed(state.rounds):
        if arg_id in rnd.moderator.relevance_scores:
            return rnd.moderator.relevance_scores[arg_id]
    return None


def collect_scored_arguments(state: DebateState) -> list[ScoredArgumentForFusion]:
    """One row per ACTIVE/MODIFIED argument in the registry with a 0–10 composite score."""
    rows: list[ScoredArgumentForFusion] = []
    for rec in state.argument_registry.values():
        arg = rec.argument
        if arg.status not in (ArgumentStatus.ACTIVE, ArgumentStatus.MODIFIED):
            continue
        fc = _latest_fact_check_for_argument(state, arg.id)
        fact = float(fc.factuality_score) if fc and fc.factuality_score is not None else DEFAULT_DIM_SCORE
        logic = float(fc.logic_score) if fc and fc.logic_score is not None else DEFAULT_DIM_SCORE
        feas = _latest_feasibility(state, arg.id)
        rel = _latest_relevance(state, arg.id)
        feasibility = float(feas) if feas is not None else DEFAULT_DIM_SCORE
        relevance = float(rel) if rel is not None else DEFAULT_DIM_SCORE
        composite = (fact + logic + feasibility + relevance) / 4.0
        rows.append(
            ScoredArgumentForFusion(
                argument_id=arg.id,
                claim=arg.claim,
                raised_by=rec.raised_by,
                factuality=fact,
                logic=logic,
                feasibility=feasibility,
                relevance=relevance,
                composite=composite,
            )
        )
    return rows


def filter_high_score_arguments(
    scored: list[ScoredArgumentForFusion],
    cfg: SupplyChainConfig,
) -> list[ScoredArgumentForFusion]:
    thr_c = cfg.fusion.composite_score_threshold
    thr_f = cfg.fusion.factuality_score_threshold
    return [s for s in scored if s.composite >= thr_c and s.factuality >= thr_f]
