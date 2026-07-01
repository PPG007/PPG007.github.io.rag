import base64
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from src.config import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    backend = settings.llm_backend

    if backend == "openai":
        kwargs = {
            "model": settings.openai_llm_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

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


def describe_image(image_path: str, settings: Settings) -> str:
    """用多模态 LLM 描述图片内容。"""
    llm = get_llm(settings)
    img_data = Path(image_path).read_bytes()
    ext = Path(image_path).suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp"}
    mime = mime_map.get(ext, "image/png")
    b64 = base64.b64encode(img_data).decode()

    if settings.llm_backend == "anthropic":
        message = HumanMessage(content=[
            {"type": "text", "text": "请用一句话描述这张图片的内容，不要超过50个字。"},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
        ])
    else:
        message = HumanMessage(content=[
            {"type": "text", "text": "请用一句话描述这张图片的内容，不要超过50个字。"},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ])

    response = llm.invoke([message])
    return response.content if hasattr(response, "content") else str(response)
