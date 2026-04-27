"""
Supply-chain LangGraph topology.

START → round_setup → data_warmup → advocate → critic → fact_checker → moderator → should_continue
         ↑___________________________________________________________________|
         └ continue                                           terminate → fusion_synthesis
                                                                           → convergence_critique
                                                                           → fusion_finalize
                                                                           → report → END
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from maverickj.graph.conditions import should_continue
from maverickj.graph.nodes.advocate import advocate_node
from maverickj.graph.nodes.critic import critic_node
from maverickj.graph.nodes.fact_checker import fact_checker_node
from maverickj.graph.nodes.moderator import moderator_node
from maverickj.graph.nodes.report import report_node
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.nodes.convergence_critique import convergence_critique_node
from maverickj.supply_chain.nodes.data_warmup import data_warmup_node
from maverickj.supply_chain.nodes.fusion_finalize import fusion_finalize_node
from maverickj.supply_chain.nodes.fusion_synthesis import fusion_synthesis_node

logger = logging.getLogger(__name__)


def _round_setup_node(state: DebateState) -> dict:
    """At the start of each round: increment round counter and clear transient data."""
    return {
        "current_round": state.current_round + 1,
        "current_round_advocate": None,
        "current_round_critic": None,
        "current_round_fact_check": None,
        "current_round_moderator": None,
    }


def build_supply_chain_graph(router: ModelRouter) -> Any:
    """Build and compile the supply-chain debate DAG (warmup + Tier-2 agents + fusion + report)."""
    workflow = StateGraph(DebateState)

    workflow.add_node("round_setup", _round_setup_node)
    workflow.add_node("data_warmup", partial(data_warmup_node, router=router))
    workflow.add_node("advocate", partial(advocate_node, router=router))
    workflow.add_node("critic", partial(critic_node, router=router))
    workflow.add_node("fact_checker", partial(fact_checker_node, router=router))
    workflow.add_node("moderator", partial(moderator_node, router=router))
    workflow.add_node("fusion_synthesis", partial(fusion_synthesis_node, router=router))
    workflow.add_node("convergence_critique", partial(convergence_critique_node, router=router))
    workflow.add_node("fusion_finalize", partial(fusion_finalize_node, router=router))
    workflow.add_node("report", partial(report_node, router=router))

    workflow.set_entry_point("round_setup")
    workflow.add_edge("round_setup", "data_warmup")
    workflow.add_edge("data_warmup", "advocate")
    workflow.add_edge("advocate", "critic")
    workflow.add_edge("critic", "fact_checker")
    workflow.add_edge("fact_checker", "moderator")

    workflow.add_conditional_edges(
        "moderator",
        should_continue,
        {
            "continue": "round_setup",
            "terminate": "fusion_synthesis",
        },
    )
    workflow.add_edge("fusion_synthesis", "convergence_critique")
    workflow.add_edge("convergence_critique", "fusion_finalize")
    workflow.add_edge("fusion_finalize", "report")
    workflow.add_edge("report", END)

    app = workflow.compile()
    logger.info("Supply-chain debate graph compiled successfully")
    return app
