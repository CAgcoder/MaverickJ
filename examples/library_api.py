"""
Example: Using the DebateEngine high-level API (library usage).

This example shows how a third-party developer would use maverickj
after installing it with `pip install maverickj`.

Run:
    python examples/library_api.py
"""
import asyncio
import sys
from pathlib import Path

# Only needed when running from the project root without pip install.
# Remove this block if maverickj is installed as a package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from maverickj import DebateEngine

load_dotenv()

question = "Should we adopt a microservices architecture or stay monolithic?"
context = """
We run a B2B SaaS product with ~80,000 active users.
Current stack: Python Django monolith, 8 backend engineers, 2 DevOps.
Pain points: long CI/CD cycles (~45 min), difficulty scaling specific features independently.
Constraint: 6-month roadmap is already packed with product features.
"""


async def main() -> None:
    # --- Minimal usage (Rich terminal output) ---
    engine = DebateEngine(max_rounds=3)
    result = await engine.debate(question, context=context)

    # Access the structured report
    rec = result.report.recommendation
    print(f"\nRecommendation: {rec.direction} (confidence: {rec.confidence.value})")
    print(f"Conditions: {', '.join(rec.conditions[:2])}")

    # Save Markdown report
    output_path = Path("example-library-api.md")
    output_path.write_text(result.to_markdown(), encoding="utf-8")
    print(f"Report saved to: {output_path}")

    # --- Silent mode with custom event callback ---
    events_log: list[str] = []

    def on_event(event) -> None:
        events_log.append(f"[Round {event.round_number}] {event.type.value}")

    silent_engine = DebateEngine(max_rounds=2, on_event=on_event)
    silent_result = await silent_engine.debate(
        "Should we sunset our legacy REST API in favour of GraphQL?",
        context="12-person frontend team, 5 backend engineers, 3 mobile apps consuming the API.",
    )
    print(f"\nSilent debate finished. Events captured: {len(events_log)}")
    for entry in events_log:
        print(f"  {entry}")


if __name__ == "__main__":
    asyncio.run(main())
