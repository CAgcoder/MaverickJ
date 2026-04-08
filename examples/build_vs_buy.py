"""Example: Build vs. Buy a data analytics platform"""
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

question = "Should we build an in-house data analytics platform, or purchase an existing commercial analytics tool (e.g. Tableau / Power BI)?"
context = """
We are a 200-person SaaS company with a data team of 15 (5 data engineers + 10 data analysts).
Current situation:
1. Mixed solution: some use Metabase (open-source), some use Excel
2. Data volume: ~5 TB processed daily
3. Primary needs: real-time dashboards, self-service queries, recurring reports
4. Budget constraint: annual IT budget $420K; ~$110K available for this project
5. Time constraint: need a working solution within 6 months
6. High data security requirements (fintech industry)
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
        print("\n📄 Report saved to: example-build-vs-buy.md")


if __name__ == "__main__":
    asyncio.run(main())
