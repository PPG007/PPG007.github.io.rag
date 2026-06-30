from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from src.config import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    backend = settings.llm_backend

    if backend == "openai":
        return ChatOpenAI(
            model=settings.openai_llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )

    if backend == "anthropic":
        return ChatAnthropic(
            model=settings.anthropic_llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )

    if backend == "ollama":
        return ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    raise ValueError(f"不支持的 LLM 后端: {backend}")


def get_streaming_llm(settings: Settings) -> BaseChatModel:
    backend = settings.llm_backend

    if backend == "openai":
        return ChatOpenAI(
            model=settings.openai_llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
            streaming=True,
        )

    if backend == "anthropic":
        return ChatAnthropic(
            model=settings.anthropic_llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            streaming=True,
        )

    if backend == "ollama":
        return ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            streaming=True,
        )

    raise ValueError(f"不支持的 LLM 后端: {backend}")
