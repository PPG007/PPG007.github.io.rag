from langchain_core.language_models.chat_models import BaseChatModel

from src.config import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    backend = settings.llm_backend

    if backend == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": settings.openai_llm_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    raise ValueError(f"不支持的 LLM 后端: {backend}")


def get_streaming_llm(settings: Settings) -> BaseChatModel:
    backend = settings.llm_backend

    if backend == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": settings.openai_llm_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
            "streaming": True,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            streaming=True,
        )

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            streaming=True,
        )

    raise ValueError(f"不支持的 LLM 后端: {backend}")
