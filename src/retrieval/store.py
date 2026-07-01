import logging
import uuid

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import settings

logger = logging.getLogger("rag.store")
BATCH_SIZE = 200  # ponytail: ChromaDB HTTP 单次上限，超了报 413


def get_chroma_client() -> chromadb.ClientAPI:
    if settings.chromadb_mode == "embedded":
        return chromadb.PersistentClient(path=settings.chromadb_persist_dir)
    return chromadb.HttpClient(host=settings.chromadb_host, port=settings.chromadb_port)


def get_vectorstore(embeddings: Embeddings) -> Chroma:
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.chromadb_collection,
        embedding_function=embeddings,
    )


def reset_collection(store: Chroma) -> None:
    """清空集合中所有文档，保留集合本身避免 Chroma 对象内部引用失效。"""
    collection = store._collection
    ids = collection.get()["ids"]
    if ids:
        for i in range(0, len(ids), BATCH_SIZE):
            batch = ids[i:i + BATCH_SIZE]
            collection.delete(ids=batch)


def add_documents(store: Chroma, docs: list[Document]) -> list[str]:
    ids = []
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        ids.extend(store.add_documents(batch))
        logger.info("[store] 入库 %d/%d chunk", min(i + BATCH_SIZE, len(docs)), len(docs))
    return ids


def add_documents_vision(store: Chroma, docs: list[Document]) -> list[str]:
    """多模态入库：含图片的 chunk 用 text+image embedding，分批写入。"""
    from src.llm.embeddings import embed_multimodal_batch

    all_ids = []
    for batch_start in range(0, len(docs), BATCH_SIZE):
        batch = docs[batch_start:batch_start + BATCH_SIZE]

        items: list[tuple[str, list[str]]] = []
        for doc in batch:
            images = doc.metadata.pop("_images", [])
            items.append((doc.page_content, images))

        embeddings = embed_multimodal_batch(items, settings)

        ids = [uuid.uuid4().hex[:16] for _ in batch]
        texts = [d.page_content for d in batch]
        metadatas = [{k: v for k, v in d.metadata.items()} for d in batch]

        collection = store._collection
        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

        all_ids.extend(ids)
        logger.info("[store] 入库 %d/%d chunk", min(batch_start + BATCH_SIZE, len(docs)), len(docs))

    return all_ids


def _doc_to_result(doc: Document) -> dict:
    return {
        "content": doc.page_content,
        "source": {
            "path": doc.metadata.get("url", ""),
            "title": doc.metadata.get("title", ""),
            "hierarchy": doc.metadata.get("hierarchy", []),
            "anchor": f"#{doc.metadata.get('anchor', '')}" if doc.metadata.get("anchor") else "",
        },
    }


def _rerank(query: str, docs: list[Document], top_k: int) -> list[Document]:
    """调硅基流动 rerank API 精排。"""
    import json
    import urllib.request

    base = (settings.openai_base_url or "https://api.siliconflow.cn/v1").rstrip("/")
    body = json.dumps({
        "model": settings.rerank_model,
        "query": query,
        "documents": [d.page_content for d in docs],
        "top_n": top_k,
    }).encode()

    req = urllib.request.Request(f"{base}/rerank", data=body, headers={
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    ranked = []
    for r in sorted(data.get("results", []), key=lambda x: x["index"]):
        if r["relevance_score"] > 0:
            ranked.append(docs[r["index"]])
    return ranked[:top_k]


def search(store: Chroma, query: str, top_k: int = 5) -> list[dict]:
    if settings.rerank_enabled:
        fetch_k = top_k * settings.rerank_fetch_multiplier
        docs = store.max_marginal_relevance_search(query, k=fetch_k, lambda_mult=0.7)
        docs = _rerank(query, docs, top_k)
    else:
        docs = store.max_marginal_relevance_search(query, k=top_k, lambda_mult=0.7)

    return [_doc_to_result(d) for d in docs]
