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
                # If the output was truncated due to max_tokens, retrying won't help.
                # Raise immediately so the caller sees a clear error instead of looping.
                if self._is_max_tokens_error(e):
                    raise RuntimeError(
                        f"[{self.role}] Output truncated (max_tokens stop reason). "
                        "Increase 'default_max_tokens' in config.yaml or shorten your prompts."
                    ) from e
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
    def _is_max_tokens_error(e: ValidationError) -> bool:
        """Check whether a ValidationError was caused by a truncated (max_tokens) LLM output."""
        error_str = str(e).lower()
        if "max_tokens" in error_str or "maximum context length" in error_str:
            return True
        # LangChain's openai_tools parser raises "field required" errors when the JSON
        # output is truncated mid-stream. Detect this by checking if ALL errors are
        # "missing" type and at least one input_value is an empty dict.
        try:
            errors = e.errors()
            if errors and all(err.get("type") == "missing" for err in errors):
                if any(err.get("input") == {} for err in errors):
                    return True
        except Exception:
            pass
        return False

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
