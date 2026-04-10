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
    on_event: Optional[EventCallback] = _SENTINEL,  # type: ignore[assignment]
) -> DebateState:
    """运行一场完整的辩论。

    Args:
        question: 决策问题
        config: 引擎配置（默认从 config.yaml 加载）
        context: 可选背景信息
        on_event: 事件回调。
            - 缺省 / 传 _SENTINEL → 使用 Rich 终端输出（默认行为，向后兼容）
            - 传 None             → 静默模式，不产生任何输出
            - 传自定义 callable   → 接收 DebateEvent，不再触发 Rich 输出
    """
    use_rich = on_event is _SENTINEL  # type: ignore[comparison-overlap]

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

    def _emit(event_type: DebateEventType, round_num: int, data=None) -> None:
        if use_rich:
            return  # Rich 输出由下方各 if 块直接调用
        if on_event is not None:
            on_event(DebateEvent(type=event_type, round_number=round_num, data=data))

    if use_rich:
        print_debate_start(question)
    elif on_event is not None:
        on_event(DebateEvent(type=DebateEventType.DEBATE_START, round_number=0, data=question))

    # 运行图 — 使用 astream 实现实时输出
    final_state = None
    current_round_num = 0

    async for event in app.astream(initial_state, stream_mode="values"):
        state = event if isinstance(event, DebateState) else DebateState(**event)

        # 检测新一轮开始
        if state.current_round > current_round_num:
            current_round_num = state.current_round
            if use_rich:
                print_round_start(current_round_num)
            else:
                _emit(DebateEventType.ROUND_START, current_round_num, current_round_num)

        # 实时打印各 Agent 结果
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
    """CLI 入口"""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

    if len(sys.argv) < 2:
        print("用法: python -m maverickj.main <决策问题> [补充背景]")
        print('示例: python -m maverickj.main "我们应该将 Java 后端迁移到 Go 吗？" "团队50人，使用 Spring Boot 3年"')
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
        output_file = "reports/debate-report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"\n📄 报告已保存至: {output_file}")


if __name__ == "__main__":
    main()
