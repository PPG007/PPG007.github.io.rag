from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import Settings


def get_embeddings(settings: Settings) -> Embeddings:
    backend = settings.embedding_backend

    if backend == "openai":
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

    if backend == "ollama":
        return OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )

    if backend == "bge":
        return HuggingFaceEmbeddings(
            model_name=settings.bge_model_name,
        )

    raise ValueError(f"不支持的 embedding 后端: {backend}")
