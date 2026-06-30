import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import settings


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


# ponytail: 通过内部 client 删除集合，langchain-chroma 不直接暴露 drop
def reset_collection(store: Chroma) -> None:
    client = store._client
    try:
        client.delete_collection(settings.chromadb_collection)
    except Exception:
        pass


def add_documents(store: Chroma, docs: list[Document]) -> list[str]:
    return store.add_documents(docs)


def search(store: Chroma, query: str, top_k: int = 5) -> list[dict]:
    docs_with_scores = store.similarity_search_with_score(query, k=top_k)
    results = []
    for doc, score in docs_with_scores:
        results.append({
            "content": doc.page_content,
            "score": round(float(score), 4),
            "source": {
                "path": doc.metadata.get("url", ""),
                "title": doc.metadata.get("title", ""),
                "hierarchy": doc.metadata.get("hierarchy", []),
                "anchor": f"#{doc.metadata.get('anchor', '')}" if doc.metadata.get("anchor") else "",
            },
        })
    return results
