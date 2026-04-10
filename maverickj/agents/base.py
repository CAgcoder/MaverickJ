import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from maverickj.llm.router import ModelRouter

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class BaseAgent:
    """Base agent class: handles prompt assembly, LLM invocation, and response parsing (with retry)."""

    role: str = ""

    def __init__(self, router: ModelRouter):
        self.router = router

    async def invoke(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: type[BaseModel],
    ) -> tuple[Any, dict]:
        """
        Invoke the LLM and return a structured response (with automatic retry).
        - LLM call failure: retry up to MAX_RETRIES times
        - Pydantic validation failure: retry once with a stricter format instruction
        Returns: (parsed_response, usage_metadata)
        """
        model = self.router.get_structured_model(self.role, output_schema)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[{self.role}] Invoking LLM (attempt {attempt}/{MAX_RETRIES})...")
                response = await model.ainvoke(messages)
                logger.info(f"[{self.role}] LLM response received")

                # Extract usage metadata if available
                usage = self._extract_usage(response)
                return response, usage

            except ValidationError as e:
                last_error = e
                logger.warning(f"[{self.role}] Pydantic validation failed (attempt {attempt}): {e}")
                # Append stricter format instruction for retry
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=user_message
                        + f"\n\n⚠️ Previous output format was invalid. Please strictly follow the schema. Error: {e}"
                    ),
                ]
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.role}] LLM call failed (attempt {attempt}): {e}")
                if attempt == MAX_RETRIES:
                    break

        raise RuntimeError(
            f"[{self.role}] Failed after {MAX_RETRIES} retries. Last error: {last_error}"
        )

    @staticmethod
    def _extract_usage(response: Any) -> dict:
        """Extract token usage from LLM response."""
        usage = {}
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "usage" in metadata:
                usage = metadata["usage"]
            elif "token_usage" in metadata:
                usage = metadata["token_usage"]
        return usage
