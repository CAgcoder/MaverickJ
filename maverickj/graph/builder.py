"""
LangGraph state graph builder.

Builds the debate engine DAG:
  START → round_setup → advocate → critic → fact_checker → moderator → should_continue
    ↑                                                                        │
    └──────────────── continue ◄─────────────────────────────────────────────┘
                                                                             │
                                                  terminate ────► report → END
"""
import logging
from functools import partial
from typing import Any

from langgraph.graph import StateGraph, END

from maverickj.graph.conditions import should_continue
from maverickj.graph.nodes.advocate import advocate_node
from maverickj.graph.nodes.critic import critic_node
from maverickj.graph.nodes.fact_checker import fact_checker_node
from maverickj.graph.nodes.moderator import moderator_node
from maverickj.graph.nodes.report import report_node
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState

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


def build_debate_graph(router: ModelRouter) -> Any:
    """Build and compile the LangGraph state graph for the debate engine."""

    workflow = StateGraph(DebateState)

    # Add nodes (inject router dependency via partial)
    workflow.add_node("round_setup", _round_setup_node)
    workflow.add_node("advocate", partial(advocate_node, router=router))
    workflow.add_node("critic", partial(critic_node, router=router))
    workflow.add_node("fact_checker", partial(fact_checker_node, router=router))
    workflow.add_node("moderator", partial(moderator_node, router=router))
    workflow.add_node("report", partial(report_node, router=router))

    # Define edges
    workflow.set_entry_point("round_setup")
    workflow.add_edge("round_setup", "advocate")
    workflow.add_edge("advocate", "critic")
    workflow.add_edge("critic", "fact_checker")
    workflow.add_edge("fact_checker", "moderator")

    # Conditional branch: continue debate or generate report
    workflow.add_conditional_edges(
        "moderator",
        should_continue,
        {
            "continue": "round_setup",
            "terminate": "report",
        },
    )
    workflow.add_edge("report", END)

    # Compile
    app = workflow.compile()
    logger.info("Debate engine graph compiled successfully")
    return app
