from langchain_core.language_models import BaseChatModel

from maverickj.schemas.config import ModelAssignment


def create_model(assignment: ModelAssignment) -> BaseChatModel:
    """根据配置创建对应的 LangChain 模型实例"""
    provider = assignment.provider.lower()
    temperature = assignment.temperature if assignment.temperature is not None else 0.7
    max_tokens = assignment.max_tokens or 4096

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=assignment.model,
            temperature=temperature,
            max_tokens=max_tokens,
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
        raise ValueError(f"不支持的模型 provider: {provider}")
