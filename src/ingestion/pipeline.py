from src.config import settings
from src.ingestion.git_loader import clone_or_pull, load_documents
from src.ingestion.splitter import split_documents
from src.llm.embeddings import get_embeddings
from src.retrieval.store import get_vectorstore, reset_collection, add_documents, add_documents_vision


# ponytail: 全局 dict 存任务状态，多进程/分布式的换成 Redis
_ingest_tasks: dict[str, dict] = {}


def run_ingest(task_id: str, repo_url: str | None = None, branch: str | None = None) -> None:
    try:
        _ingest_tasks[task_id] = {"status": "running", "docs_processed": 0, "error": None}

        repo = repo_url or settings.docs_repo_url
        br = branch or settings.docs_branch

        repo_path = clone_or_pull(repo, br, settings.git_cache_dir)
        file_pairs = load_documents(repo_path)
        docs = split_documents(file_pairs, str(repo_path))

        embeddings = get_embeddings(settings)
        store = get_vectorstore(embeddings)
        reset_collection(store)

        if settings.vision_enabled:
            add_documents_vision(store, docs)
        else:
            add_documents(store, docs)

        _ingest_tasks[task_id] = {
            "status": "done",
            "docs_processed": len(file_pairs),
            "error": None,
        }
    except Exception as e:
        _ingest_tasks[task_id] = {
            "status": "failed",
            "docs_processed": 0,
            "error": str(e),
        }


def get_ingest_status(task_id: str) -> dict | None:
    return _ingest_tasks.get(task_id)
