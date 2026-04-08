"""示例：自建 vs 采购数据分析平台"""
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

question = "我们应该自建内部数据分析平台，还是采购现有的商业分析工具（如 Tableau / Power BI）？"
context = """
我们是一家 200 人的 SaaS 公司，数据团队 15 人（5 数据工程师 + 10 数据分析师）。
当前状况：
1. 使用混合方案：部分用 Metabase（开源），部分用 Excel
2. 数据量：日均处理约 5TB 数据
3. 主要需求：实时仪表盘、自助查询、定期报告
4. 预算约束：年度 IT 预算 300 万，可分配给此项目约 80 万
5. 时间约束：希望 6 个月内有可用方案
6. 数据安全要求高（金融行业）
"""


async def main():
    config = load_config()
    state = await run_debate(question, config, context)

    if state and state.final_report:
        report = state.final_report
        if isinstance(report, dict):
            report = DecisionReport(**report)
        markdown = render_report_to_markdown(report, state)
        with open("example-build-vs-buy.md", "w", encoding="utf-8") as f:
            f.write(markdown)
        print("\n📄 报告已保存至: example-build-vs-buy.md")


if __name__ == "__main__":
    asyncio.run(main())
