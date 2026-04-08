"""示例：Java 迁移 Go"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.main import load_config, run_debate
from src.output.renderer import render_report_to_markdown
from src.schemas.report import DecisionReport

load_dotenv()

question = "我们团队应该将现有的 Java 后端服务迁移到 Go 语言吗？"
context = """
我们是一个 50 人的后端团队，主要使用 Java + Spring Boot 技术栈，服务已运行 3 年。
当前面临的问题：
1. 部署成本高（JVM 内存占用大）
2. 冷启动慢，影响 Serverless 场景
3. 部分团队成员对 Go 有兴趣
4. 服务主要是 API Gateway 和微服务
5. 年营收约 5000 万，技术投入预算约 800 万
"""


async def main():
    config = load_config()
    state = await run_debate(question, config, context)

    if state and state.final_report:
        report = state.final_report
        if isinstance(report, dict):
            report = DecisionReport(**report)
        markdown = render_report_to_markdown(report, state)
        with open("example-java-to-go.md", "w", encoding="utf-8") as f:
            f.write(markdown)
        print("\n📄 报告已保存至: example-java-to-go.md")


if __name__ == "__main__":
    asyncio.run(main())
