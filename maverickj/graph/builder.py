"""
LangGraph 状态图构建器。

构建辩论引擎的 DAG：
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
    """每轮开始前：递增 round 计数，清空当前轮的临时数据"""
    return {
        "current_round": state.current_round + 1,
        "current_round_advocate": None,
        "current_round_critic": None,
        "current_round_fact_check": None,
        "current_round_moderator": None,
    }


def build_debate_graph(router: ModelRouter) -> Any:
    """构建并编译辩论引擎的 LangGraph 状态图"""

    workflow = StateGraph(DebateState)

    # 添加节点（使用 partial 注入 router 依赖）
    workflow.add_node("round_setup", _round_setup_node)
    workflow.add_node("advocate", partial(advocate_node, router=router))
    workflow.add_node("critic", partial(critic_node, router=router))
    workflow.add_node("fact_checker", partial(fact_checker_node, router=router))
    workflow.add_node("moderator", partial(moderator_node, router=router))
    workflow.add_node("report", partial(report_node, router=router))

    # 定义边
    workflow.set_entry_point("round_setup")
    workflow.add_edge("round_setup", "advocate")
    workflow.add_edge("advocate", "critic")
    workflow.add_edge("critic", "fact_checker")
    workflow.add_edge("fact_checker", "moderator")

    # 条件分支：继续辩论 or 生成报告
    workflow.add_conditional_edges(
        "moderator",
        should_continue,
        {
            "continue": "round_setup",
            "terminate": "report",
        },
    )
    workflow.add_edge("report", END)

    # 编译
    app = workflow.compile()
    logger.info("辩论引擎图编译完成")
    return app
