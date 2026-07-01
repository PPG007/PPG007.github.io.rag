import json
import base64
import urllib.request
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import Settings


def get_embeddings(settings: Settings) -> Embeddings:
    backend = settings.embedding_backend

    if backend == "openai":
        kwargs = {
            "model": settings.openai_embedding_model,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return OpenAIEmbeddings(**kwargs)

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


def embed_multimodal_batch(texts_and_images: list[tuple[str, list[str]]], settings: Settings) -> list[list[float]]:
    """多模态 embedding：文本和图片一起向量化。仅 openai backend 支持。"""
    base = settings.openai_base_url.rstrip("/") if settings.openai_base_url else "https://api.openai.com/v1"
    url = f"{base}/embeddings"
    embeddings = []

    for text, image_paths in texts_and_images:
        if not image_paths:
            # 纯文本，调普通 embedding
            body = json.dumps({
                "model": settings.openai_embedding_model,
                "input": text,
            }).encode()
        else:
            # 多模态输入
            content: list[dict] = [{"type": "text", "text": text}]
            for img_path in image_paths:
                img_data = Path(img_path).read_bytes()
                b64 = base64.b64encode(img_data).decode()
                ext = Path(img_path).suffix.lower()
                mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/png")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            body = json.dumps({
                "model": settings.openai_embedding_model,
                "input": content,
            }).encode()

        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        embeddings.append(data["data"][0]["embedding"])

    return embeddings
