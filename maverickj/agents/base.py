import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from maverickj.llm.router import ModelRouter

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class BaseAgent:
    """Agent 基类：负责 prompt 组装、模型调用、响应处理（含重试）"""

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
        调用 LLM 并返回结构化响应（含自动重试）。
        - LLM 调用失败：重试最多 MAX_RETRIES 次
        - Pydantic 校验失败：重试一次并附带更严格的格式指令
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
                logger.info(f"[{self.role}] 调用 LLM (attempt {attempt}/{MAX_RETRIES})...")
                response = await model.ainvoke(messages)
                logger.info(f"[{self.role}] LLM 响应完成")

                # Extract usage metadata if available
                usage = self._extract_usage(response)
                return response, usage

            except ValidationError as e:
                last_error = e
                logger.warning(f"[{self.role}] Pydantic 校验失败 (attempt {attempt}): {e}")
                # Append stricter format instruction for retry
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=user_message
                        + f"\n\n⚠️ 上次输出格式有误，请严格按照 schema 输出。错误: {e}"
                    ),
                ]
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.role}] LLM 调用失败 (attempt {attempt}): {e}")
                if attempt == MAX_RETRIES:
                    break

        raise RuntimeError(
            f"[{self.role}] 调用失败，已重试 {MAX_RETRIES} 次。最后错误: {last_error}"
        )

    @staticmethod
    def _extract_usage(response: Any) -> dict:
        """从 LLM 响应中提取 token 使用量"""
        usage = {}
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "usage" in metadata:
                usage = metadata["usage"]
            elif "token_usage" in metadata:
                usage = metadata["token_usage"]
        return usage
