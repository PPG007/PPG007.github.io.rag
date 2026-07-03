import logging
import re

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import settings

logger = logging.getLogger("rag.store")
BATCH_SIZE = 200  # ponytail: ChromaDB HTTP 单次上限，超了报 413
KEYWORD_FETCH_LIMIT = 50


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
    """删除集合，切换 embedding 模型时维度自动适配。调用后需重建 store。"""
    try:
        store._client.delete_collection(settings.chromadb_collection)
    except Exception:
        pass


def add_documents(store: Chroma, docs: list[Document]) -> list[str]:
    ids = []
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        ids.extend(store.add_documents(batch))
        logger.info("[store] 入库 %d/%d chunk", min(i + BATCH_SIZE, len(docs)), len(docs))
    return ids


def _result_content(doc: Document) -> str:
    return doc.metadata.get("raw_content") or doc.page_content


def _doc_to_result(doc: Document) -> dict:
    return {
        "content": _result_content(doc),
        "source": {
            "path": doc.metadata.get("url", ""),
            "title": doc.metadata.get("title", ""),
            "hierarchy": doc.metadata.get("hierarchy", []),
            "anchor": f"#{doc.metadata.get('anchor', '')}" if doc.metadata.get("anchor") else "",
        },
    }


def _query_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_.+-]{1,}|\d+|[\u4e00-\u9fff]{2,}", query)
    seen = set()
    strong_terms = []
    other_terms = []
    for term in terms:
        normalized = term.lower()
        if normalized not in seen:
            seen.add(normalized)
            if re.search(r"[A-Za-z0-9]", term):
                strong_terms.append(term)
            else:
                other_terms.append(term)
    return strong_terms + other_terms


def _doc_key(doc: Document) -> tuple[str, str, str]:
    return (
        doc.metadata.get("source_path", ""),
        str(doc.metadata.get("header_index", "")),
        str(doc.metadata.get("chunk_index", "")),
    )


def _merge_docs(*doc_groups: list[Document]) -> list[Document]:
    merged = []
    seen = set()
    for docs in doc_groups:
        for doc in docs:
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            merged.append(doc)
    return merged


def _keyword_search(store: Chroma, query: str, limit: int) -> list[Document]:
    docs = []
    for term in _query_terms(query):
        try:
            found = store._collection.get(
                where_document={"$contains": term},
                limit=limit,
                include=["documents", "metadatas"],
            )
        except Exception:
            logger.exception("[store] keyword search failed for term: %s", term)
            continue

        for content, metadata in zip(found.get("documents", []), found.get("metadatas", [])):
            docs.append(Document(page_content=content, metadata=metadata or {}))

    return _merge_docs(docs)


def _rerank(query: str, docs: list[Document], top_k: int) -> list[Document]:
    """调硅基流动 rerank API 精排。"""
    import json
    import urllib.request

    base = (settings.openai_base_url or "https://api.siliconflow.cn/v1").rstrip("/")
    body = json.dumps({
        "model": settings.rerank_model,
        "query": query,
        "documents": [_result_content(d) for d in docs],
        "top_n": top_k,
    }, ensure_ascii=False).encode()

    req = urllib.request.Request(f"{base}/rerank", data=body, headers={
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        logger.exception("[store] rerank failed; fallback to initial retrieval")
        return docs[:top_k]

    ranked = []
    ranked_results = sorted(
        data.get("results", []),
        key=lambda x: x.get("relevance_score", 0),
        reverse=True,
    )
    for r in ranked_results:
        index = r.get("index")
        if index is None or index >= len(docs):
            continue
        ranked.append(docs[index])
    return ranked[:top_k]


def search(store: Chroma, query: str, top_k: int = 5) -> list[dict]:
    fetch_k = max(top_k * settings.rerank_fetch_multiplier, top_k)
    if settings.rerank_enabled:
        fetch_k = max(fetch_k, top_k * 10, 100)
        vector_docs = store.similarity_search(query, k=fetch_k)
        keyword_docs = _keyword_search(store, query, KEYWORD_FETCH_LIMIT)
        docs = _merge_docs(keyword_docs, vector_docs)
        docs = _rerank(query, docs, top_k)
    else:
        vector_docs = store.similarity_search(query, k=fetch_k)
        keyword_docs = _keyword_search(store, query, min(KEYWORD_FETCH_LIMIT, top_k * 2))
        docs = _merge_docs(keyword_docs, vector_docs)[:top_k]

    return [_doc_to_result(d) for d in docs]
