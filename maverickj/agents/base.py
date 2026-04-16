import json
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
        model = self.router.get_model(self.role)
        supports_include_raw = True
        try:
            model = model.with_structured_output(output_schema, include_raw=True)
        except TypeError:
            supports_include_raw = False
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

                parsed_response, usage = self._parse_response(
                    response,
                    output_schema,
                    supports_include_raw,
                )
                return parsed_response, usage

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

    def _parse_response(
        self,
        response: Any,
        output_schema: type[BaseModel],
        supports_include_raw: bool,
    ) -> tuple[Any, dict]:
        """Parse a structured response and salvage malformed tool arguments when possible."""
        if not supports_include_raw or not isinstance(response, dict) or "raw" not in response:
            return response, self._extract_usage(response)

        raw_response = response["raw"]
        usage = self._extract_usage(raw_response)
        parsed_response = response.get("parsed")
        parsing_error = response.get("parsing_error")

        if parsed_response is not None and parsing_error is None:
            return parsed_response, usage

        repaired_response = self._repair_raw_structured_output(raw_response, output_schema)
        if repaired_response is not None:
            logger.warning(f"[{self.role}] Repaired malformed structured output locally before validation")
            return repaired_response, usage

        if parsing_error is None:
            raise RuntimeError(f"[{self.role}] Structured output parsing failed without parser error details")

        if isinstance(parsing_error, ValidationError):
            raise parsing_error

        raise RuntimeError(f"[{self.role}] Structured output parsing failed: {parsing_error}") from parsing_error

    @classmethod
    def _repair_raw_structured_output(
        cls,
        raw_response: Any,
        output_schema: type[BaseModel],
    ) -> BaseModel | None:
        raw_args = cls._extract_tool_args(raw_response)
        if not isinstance(raw_args, dict):
            return None

        repaired_args = dict(raw_args)
        repaired_fields: list[str] = []
        for field_name, field_value in raw_args.items():
            repaired_value = cls._repair_json_collection_field(field_value)
            if type(repaired_value) is not type(field_value) or repaired_value != field_value:
                repaired_args[field_name] = repaired_value
                repaired_fields.append(field_name)

        if not repaired_fields:
            return None

        try:
            return output_schema.model_validate(repaired_args)
        except ValidationError as e:
            logger.warning(
                f"Structured output repair did not fully recover fields {repaired_fields}: {e}"
            )
            return None

    @classmethod
    def _repair_json_collection_field(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        candidate = cls._strip_markdown_fences(value)
        if not candidate or candidate[0] not in "[{":
            return value

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired_candidate = cls._escape_bare_quotes_in_json_strings(candidate)
            if repaired_candidate == candidate:
                return value

            try:
                return json.loads(repaired_candidate)
            except json.JSONDecodeError as e:
                logger.warning(f"Unable to repair malformed JSON collection field: {e}")
                return value

    @staticmethod
    def _strip_markdown_fences(value: str) -> str:
        cleaned = value.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    @staticmethod
    def _escape_bare_quotes_in_json_strings(value: str) -> str:
        repaired: list[str] = []
        in_string = False
        escaped = False

        for index, char in enumerate(value):
            if not in_string:
                if char == '"':
                    in_string = True
                repaired.append(char)
                continue

            if escaped:
                repaired.append(char)
                escaped = False
                continue

            if char == "\\":
                repaired.append(char)
                escaped = True
                continue

            if char == '"':
                next_non_whitespace = BaseAgent._next_non_whitespace_char(value, index + 1)
                if next_non_whitespace in {",", "}", "]", ":", None}:
                    in_string = False
                    repaired.append(char)
                else:
                    repaired.append(r'\"')
                continue

            repaired.append(char)

        return "".join(repaired)

    @staticmethod
    def _next_non_whitespace_char(value: str, start_index: int) -> str | None:
        for char in value[start_index:]:
            if not char.isspace():
                return char
        return None

    @classmethod
    def _extract_tool_args(cls, raw_response: Any) -> dict[str, Any] | None:
        tool_calls = getattr(raw_response, "tool_calls", None)
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue

                args = tool_call.get("args")
                if isinstance(args, dict):
                    return args

                parsed_args = cls._try_parse_json_text(args)
                if isinstance(parsed_args, dict):
                    return parsed_args

        content = getattr(raw_response, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue

                block_input = block.get("input")
                if isinstance(block_input, dict):
                    return block_input

                parsed_input = cls._try_parse_json_text(block_input)
                if isinstance(parsed_input, dict):
                    return parsed_input

        additional_kwargs = getattr(raw_response, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            openai_tool_calls = additional_kwargs.get("tool_calls")
            if isinstance(openai_tool_calls, list):
                for tool_call in openai_tool_calls:
                    if not isinstance(tool_call, dict):
                        continue

                    function_block = tool_call.get("function")
                    if not isinstance(function_block, dict):
                        continue

                    parsed_input = cls._try_parse_json_text(function_block.get("arguments"))
                    if isinstance(parsed_input, dict):
                        return parsed_input

        return None

    @staticmethod
    def _try_parse_json_text(value: Any) -> Any:
        if not isinstance(value, str):
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

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
