import logging

from src.config import settings
from src.ingestion.git_loader import clone_or_pull, load_documents
from src.ingestion.splitter import split_documents
from src.llm.embeddings import get_embeddings
from src.retrieval.store import get_vectorstore, reset_collection, add_documents

logger = logging.getLogger("rag.ingestion")

# ponytail: 全局 dict 存任务状态，多进程/分布式的换成 Redis
_ingest_tasks: dict[str, dict] = {}


def run_ingest(task_id: str, repo_url: str | None = None, branch: str | None = None) -> None:
    try:
        _ingest_tasks[task_id] = {"status": "running", "docs_processed": 0, "error": None}

        repo = repo_url or settings.docs_repo_url
        br = branch or settings.docs_branch

        logger.info("[ingest] 拉取仓库 %s (%s)", repo, br)
        repo_path = clone_or_pull(repo, br, settings.git_cache_dir)
        logger.info("[ingest] 仓库路径: %s", repo_path)

        logger.info("[ingest] 扫描 Markdown 文件...")
        file_pairs = load_documents(repo_path)
        logger.info("[ingest] 发现 %d 个 .md 文件", len(file_pairs))

        logger.info("[ingest] 分块处理...")
        docs = split_documents(file_pairs, str(repo_path))
        logger.info("[ingest] 生成 %d 个 chunk", len(docs))

        logger.info("[ingest] 初始化 embedding 模型...")
        embeddings = get_embeddings(settings)
        store = get_vectorstore(embeddings)
        reset_collection(store)
        store = get_vectorstore(embeddings)  # 重建，适配新 embedding 维度

        logger.info("[ingest] 向量化并入库...")
        add_documents(store, docs)

        logger.info("[ingest] 完成: %d 文档, %d chunk", len(file_pairs), len(docs))
        _ingest_tasks[task_id] = {
            "status": "done",
            "docs_processed": len(file_pairs),
            "error": None,
        }
    except Exception as e:
        logger.exception("[ingest] 失败")
        _ingest_tasks[task_id] = {
            "status": "failed",
            "docs_processed": 0,
            "error": str(e),
        }


def get_ingest_status(task_id: str) -> dict | None:
    return _ingest_tasks.get(task_id)
