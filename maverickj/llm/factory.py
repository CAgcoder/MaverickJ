from langchain_core.language_models import BaseChatModel

from maverickj.llm.prompt_cache import ANTHROPIC_MESSAGES_CACHE_CONTROL
from maverickj.schemas.config import ModelAssignment


def create_model(assignment: ModelAssignment) -> BaseChatModel:
    """Create the corresponding LangChain model instance from config."""
    provider = assignment.provider.lower()
    temperature = assignment.temperature if assignment.temperature is not None else 0.7
    max_tokens = assignment.max_tokens or 8192

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        # Same as anthropic.messages.create(..., cache_control={"type": "ephemeral"}, ...)
        return ChatAnthropic(
            model=assignment.model,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"cache_control": ANTHROPIC_MESSAGES_CACHE_CONTROL},
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=assignment.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=assignment.model,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
