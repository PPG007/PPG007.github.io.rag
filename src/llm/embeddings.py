from langchain_core.embeddings import Embeddings

from src.config import Settings


def get_embeddings(settings: Settings) -> Embeddings:
    backend = settings.embedding_backend

    if backend == "openai":
        from langchain_openai import OpenAIEmbeddings

        kwargs = {
            "model": settings.openai_embedding_model,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return OpenAIEmbeddings(**kwargs)

    if backend == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )

    if backend == "bge":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=settings.bge_model_name,
        )

    raise ValueError(f"不支持的 embedding 后端: {backend}")
