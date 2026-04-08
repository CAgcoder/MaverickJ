"""Example: Migrating Java services to Go"""
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

question = "Should our team migrate our existing Java backend services to Go?"
context = """
We are a 50-person backend team primarily using a Java + Spring Boot stack; services have been running for 3 years.
Current pain points:
1. High deployment costs (large JVM memory footprint)
2. Slow cold starts, affecting Serverless scenarios
3. Some team members are interested in Go
4. Services are mainly API Gateways and microservices
5. Annual revenue ~$7M; tech budget ~$1.1M
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
        print("\n📄 Report saved to: example-java-to-go.md")


if __name__ == "__main__":
    asyncio.run(main())
