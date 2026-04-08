"""
多 Agent 辩论式决策引擎 — 主入口
"""
import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from src.graph.builder import build_debate_graph
from src.llm.router import ModelRouter
from src.output.renderer import render_report_to_markdown
from src.output.stream import (
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
from src.schemas.config import DebateEngineConfig
from src.schemas.debate import DebateConfig, DebateMetadata, DebateState, DebateStatus
from src.schemas.report import DecisionReport

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> DebateEngineConfig:
    """从 YAML 加载配置"""
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
) -> DebateState:
    """运行一场完整的辩论"""

    if config is None:
        config = load_config()

    # 初始化状态
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
    )

    # 创建模型路由器
    router = ModelRouter(config)

    # 构建 LangGraph 图
    app = build_debate_graph(router)

    print_debate_start(question)

    # 运行图 — 使用 astream 实现实时输出
    final_state = None
    current_round_num = 0

    async for event in app.astream(initial_state, stream_mode="values"):
        state = event if isinstance(event, DebateState) else DebateState(**event)

        # 检测新一轮开始
        if state.current_round > current_round_num:
            current_round_num = state.current_round
            print_round_start(current_round_num)

        # 实时打印各 Agent 结果
        if state.current_round_advocate and (
            final_state is None or final_state.current_round_advocate != state.current_round_advocate
        ):
            print_advocate_result(state.current_round_advocate)

        if state.current_round_critic and (
            final_state is None or final_state.current_round_critic != state.current_round_critic
        ):
            print_critic_result(state.current_round_critic)

        if state.current_round_fact_check and (
            final_state is None or final_state.current_round_fact_check != state.current_round_fact_check
        ):
            print_fact_check_result(state.current_round_fact_check)

        if state.current_round_moderator and (
            final_state is None or final_state.current_round_moderator != state.current_round_moderator
        ):
            print_moderator_result(state.current_round_moderator)

        final_state = state

    if final_state:
        print_debate_complete(
            final_state.status.value,
            final_state.convergence_reason,
        )

    return final_state


def main():
    """CLI 入口"""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

    if len(sys.argv) < 2:
        print("用法: python -m src.main <决策问题> [补充背景]")
        print('示例: python -m src.main "我们应该将 Java 后端迁移到 Go 吗？" "团队50人，使用 Spring Boot 3年"')
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
        output_file = "debate-report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"\n📄 报告已保存至: {output_file}")


if __name__ == "__main__":
    main()
