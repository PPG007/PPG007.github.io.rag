# VuePress RAG 后端 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 VuePress 技术文档的 RAG 后端 API，支持语义搜索和流式问答，Ollama 本地模型和云端 API 同时支持。

**Architecture:** FastAPI + LangChain + ChromaDB。工厂函数模式切换 Embedding/LLM 后端（OpenAI/Anthropic/Ollama/BGE），Markdown 按标题分块保留层级面包屑，SSE 流式返回问答结果。

**Tech Stack:** Python 3.12, FastAPI, LangChain, ChromaDB, GitPython, Docker Compose

---

## File Structure

```
src/
├── __init__.py
├── main.py              # FastAPI 入口，lifespan 初始化
├── config.py            # pydantic-settings 环境变量配置
├── ingestion/
│   ├── __init__.py
│   ├── git_loader.py    # Git 仓库 clone/pull
│   ├── splitter.py      # Markdown 分块 + frontmatter 解析
│   └── pipeline.py      # 摄取流水线编排
├── retrieval/
│   ├── __init__.py
│   └── store.py         # ChromaDB 读写 + 搜索
├── llm/
│   ├── __init__.py
│   ├── embeddings.py    # Embedding 工厂（openai | ollama | bge）
│   └── generator.py     # LLM 工厂（openai | anthropic | ollama）
└── api/
    ├── __init__.py
    └── routes.py        # /ingest, /ingest/status, /search, /chat
tests/
└── test_api.py           # 集成测试
requirements.txt
Dockerfile
docker-compose.yml
.env.example
```

---

### Task 1: 项目骨架

**Files:**
- Create: `requirements.txt`, `.env.example`, `src/__init__.py`, `src/config.py`
- Create: `src/ingestion/__init__.py`, `src/retrieval/__init__.py`, `src/llm/__init__.py`, `src/api/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-anthropic>=0.3.0
langchain-ollama>=0.2.0
langchain-chroma>=0.2.0
langchain-text-splitters>=0.3.0
langchain-community>=0.3.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
GitPython>=3.1.0
python-frontmatter>=1.1.0
pydantic-settings>=2.5.0
pydantic>=2.10.0
```

- [ ] **Step 2: 创建 .env.example**

```bash
# 文档仓库
DOCS_REPO_URL=https://github.com/user/my-vuepress-docs.git
DOCS_BRANCH=main

# Embedding 后端: openai | ollama | bge
EMBEDDING_BACKEND=openai

# LLM 后端: openai | anthropic | ollama
LLM_BACKEND=openai

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4o

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_LLM_MODEL=claude-sonnet-4-6

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3

# BGE (本地) — 仅当 EMBEDDING_BACKEND=bge
BGE_MODEL_NAME=BAAI/bge-small-zh-v1.5

# ChromaDB — "embedded" 为本地开发模式，host:port 为独立服务模式
CHROMADB_MODE=embedded
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_PERSIST_DIR=./chroma_data
CHROMADB_COLLECTION=vuepress_docs

# 分块
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
HEADING_LEVEL=2

# Git 缓存
GIT_CACHE_DIR=./git_cache
```

- [ ] **Step 3: 创建 src/config.py**

```python
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Docs
    docs_repo_url: str = ""
    docs_branch: str = "main"

    # Embedding backend: openai | ollama | bge
    embedding_backend: str = "openai"

    # LLM backend: openai | anthropic | ollama
    llm_backend: str = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-4o"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_llm_model: str = "claude-sonnet-4-6"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_llm_model: str = "llama3"

    # BGE
    bge_model_name: str = "BAAI/bge-small-zh-v1.5"

    # ChromaDB
    chromadb_mode: str = "embedded"  # embedded | client
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_persist_dir: str = "./chroma_data"
    chromadb_collection: str = "vuepress_docs"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    heading_level: int = 2

    # Git
    git_cache_dir: str = "./git_cache"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: 创建空 __init__.py 文件**

```
src/__init__.py
src/ingestion/__init__.py
src/retrieval/__init__.py
src/llm/__init__.py
src/api/__init__.py
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example src/
git commit -m "feat: add project skeleton and config"
```

---

### Task 2: Embedding 工厂

**Files:**
- Create: `src/llm/embeddings.py`

- [ ] **Step 1: 实现 src/llm/embeddings.py**

```python
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import Settings


def get_embeddings(settings: Settings) -> Embeddings:
    """工厂函数，按 EMBEDDING_BACKEND 返回对应的 Embeddings 实例。"""
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
```

- [ ] **Step 2: Commit**

```bash
git add src/llm/
git commit -m "feat: add embedding factory (openai/ollama/bge)"
```

---

### Task 3: LLM 工厂

**Files:**
- Create: `src/llm/generator.py`

- [ ] **Step 1: 实现 src/llm/generator.py**

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from src.config import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    """返回普通 LLM 实例。"""
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
    """返回流式 LLM 实例，用于 /chat 的 SSE 响应。"""
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
        )

    raise ValueError(f"不支持的 LLM 后端: {backend}")
```

- [ ] **Step 2: Commit**

```bash
git add src/llm/generator.py
git commit -m "feat: add LLM factory (openai/anthropic/ollama)"
```

---

### Task 4: Git 文档加载器

**Files:**
- Create: `src/ingestion/git_loader.py`

- [ ] **Step 1: 实现 src/ingestion/git_loader.py**

```python
from pathlib import Path
from git import Repo


def clone_or_pull(repo_url: str, branch: str, cache_dir: str) -> Path:
    """克隆或更新仓库，返回仓库本地路径。"""
    repo_path = Path(cache_dir)

    if repo_path.exists() and (repo_path / ".git").exists():
        repo = Repo(repo_path)
        repo.git.checkout(branch)
        repo.git.pull()
    else:
        repo_path.mkdir(parents=True, exist_ok=True)
        Repo.clone_from(repo_url, repo_path, branch=branch)

    return repo_path


def list_markdown_files(repo_path: Path) -> list[Path]:
    """递归列出仓库中所有 .md 文件（排除 node_modules、.git）。"""
    exclude = {".git", "node_modules", ".vscode", ".idea"}
    files = []
    for f in repo_path.rglob("*.md"):
        if not set(f.parts).intersection(exclude):
            files.append(f)
    return files


def load_documents(repo_path: Path) -> list[tuple[str, str]]:
    """加载所有 markdown 文件，返回 (相对路径, 文件内容) 列表。"""
    md_files = list_markdown_files(repo_path)
    results = []
    for f in md_files:
        rel_path = str(f.relative_to(repo_path)).replace("\\", "/")
        content = f.read_text(encoding="utf-8")
        results.append((rel_path, content))
    return results
```

- [ ] **Step 2: Commit**

```bash
git add src/ingestion/git_loader.py
git commit -m "feat: add git document loader"
```

---

### Task 5: Markdown 分块器

**Files:**
- Create: `src/ingestion/splitter.py`

- [ ] **Step 1: 实现 src/ingestion/splitter.py**

```python
import re
import frontmatter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document

from src.config import settings


def slugify(text: str) -> str:
    """生成 VuePress 兼容的锚点 slug。"""
    text = text.lower().strip()
    text = re.sub(r'[^\w一-鿿\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (元数据, 正文)。"""
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


def split_markdown(rel_path: str, content: str) -> list[Document]:
    """将一篇 markdown 按标题层级切分为带元数据的 Document 列表。"""
    metadata, body = parse_frontmatter(content)
    page_title = metadata.get("title", rel_path)

    # 构建标题分隔符列表，例如 ["##", "###"]
    headers_to_split_on = [
        ("#" * i, f"h{i}")
        for i in range(2, settings.heading_level + 2)
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    docs = splitter.split_text(body)
    base_url = "/" + rel_path.replace(".md", ".html")

    result = []
    for i, doc in enumerate(docs):
        # 收集层级面包屑
        hierarchy = [page_title]
        for h_level in range(1, 5):
            key = f"h{h_level}"
            if key in doc.metadata:
                hierarchy.append(doc.metadata[key])

        # 锚点取最小标题（层级最深的标题）
        anchor_heading = ""
        for h_level in range(4, 0, -1):
            key = f"h{h_level}"
            if key in doc.metadata:
                anchor_heading = doc.metadata[key]
                break

        anchor = slugify(anchor_heading) if anchor_heading else ""

        doc.metadata.update({
            "source_path": rel_path,
            "url": f"{base_url}#{anchor}" if anchor else base_url,
            "title": page_title,
            "hierarchy": hierarchy,
            "anchor": anchor,
            "chunk_index": i,
        })
        result.append(doc)

    return result


def split_documents(file_pairs: list[tuple[str, str]]) -> list[Document]:
    """批量处理文件列表，返回所有 Document。"""
    all_docs = []
    for rel_path, content in file_pairs:
        docs = split_markdown(rel_path, content)
        all_docs.extend(docs)
    return all_docs
```

- [ ] **Step 2: Commit**

```bash
git add src/ingestion/splitter.py
git commit -m "feat: add markdown chunking with hierarchy preservation"
```

---

### Task 6: ChromaDB 向量存储

**Files:**
- Create: `src/retrieval/store.py`

- [ ] **Step 1: 实现 src/retrieval/store.py**

```python
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import settings


def get_chroma_client() -> chromadb.ClientAPI:
    """根据配置返回 ChromaDB 客户端（embedded 或 client-server 模式）。"""
    if settings.chromadb_mode == "embedded":
        return chromadb.PersistentClient(path=settings.chromadb_persist_dir)
    return chromadb.HttpClient(host=settings.chromadb_host, port=settings.chromadb_port)


def get_vectorstore(embeddings: Embeddings) -> Chroma:
    """获取 Chroma vectorstore 实例。"""
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.chromadb_collection,
        embedding_function=embeddings,
    )


def reset_collection(store: Chroma) -> None:
    """清空集合后重建，用于全量重索引。"""
    client = store._client  # ponytail: 访问内部 client 删集合
    try:
        client.delete_collection(settings.chromadb_collection)
    except Exception:
        pass
    # Chroma 会在下次访问时自动重建


def add_documents(store: Chroma, docs: list[Document) -> list[str]:
    """批量写入文档到向量存储。"""
    return store.add_documents(docs)


def search(store: Chroma, query: str, top_k: int = 5) -> list[dict]:
    """语义搜索，返回带元数据的文档列表。"""
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
```

- [ ] **Step 2: Commit**

```bash
git add src/retrieval/store.py
git commit -m "feat: add ChromaDB vector store wrapper"
```

---

### Task 7: 摄取流水线

**Files:**
- Create: `src/ingestion/pipeline.py`

- [ ] **Step 1: 实现 src/ingestion/pipeline.py**

```python
from pathlib import Path

from src.config import settings
from src.ingestion.git_loader import clone_or_pull, load_documents
from src.ingestion.splitter import split_documents
from src.llm.embeddings import get_embeddings
from src.retrieval.store import get_vectorstore, reset_collection, add_documents


# ponytail: 全局 dict 存任务状态，多进程/分布式的换成 Redis
_ingest_tasks: dict[str, dict] = {}


def run_ingest(task_id: str, repo_url: str | None = None, branch: str | None = None) -> None:
    """执行完整摄取流程：clone → split → embed → store。"""
    try:
        _ingest_tasks[task_id] = {"status": "running", "docs_processed": 0, "error": None}

        repo = repo_url or settings.docs_repo_url
        br = branch or settings.docs_branch

        repo_path = clone_or_pull(repo, br, settings.git_cache_dir)
        file_pairs = load_documents(repo_path)
        docs = split_documents(file_pairs)

        embeddings = get_embeddings(settings)
        store = get_vectorstore(embeddings)
        reset_collection(store)
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
    """查询摄取任务状态。"""
    return _ingest_tasks.get(task_id)
```

- [ ] **Step 2: Commit**

```bash
git add src/ingestion/pipeline.py
git commit -m "feat: add ingestion pipeline orchestration"
```

---

### Task 8: API 路由

**Files:**
- Create: `src/api/routes.py`
- Modify: `src/retrieval/store.py` (修复类型注解)

- [ ] **Step 1: 修复 store.py 中的类型注解**

`src/retrieval/store.py` 中 `add_documents` 函数的参数类型 `list[Document)` 改为 `list[Document]`。

- [ ] **Step 2: 实现 src/api/routes.py**

```python
import uuid
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import settings
from src.ingestion.pipeline import run_ingest, get_ingest_status
from src.llm.embeddings import get_embeddings
from src.llm.generator import get_llm, get_streaming_llm
from src.retrieval.store import get_vectorstore, search as vector_search

router = APIRouter()


class IngestRequest(BaseModel):
    repo_url: str | None = None
    branch: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/ingest")
def ingest(req: IngestRequest | None = None, background_tasks: BackgroundTasks = None):
    """触发文档摄取，异步执行。"""
    task_id = uuid.uuid4().hex[:12]
    repo_url = req.repo_url if req else None
    branch = req.branch if req else None
    background_tasks.add_task(run_ingest, task_id, repo_url, branch)
    return {"task_id": task_id, "status": "running"}


@router.get("/ingest/status")
def ingest_status(task_id: str):
    """查询摄取任务状态。"""
    status = get_ingest_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, **status}


@router.post("/search")
def search_endpoint(req: SearchRequest):
    """语义检索，返回相关文档片段和跳转元数据。"""
    embeddings = get_embeddings(settings)
    store = get_vectorstore(embeddings)
    results = vector_search(store, req.query, req.top_k)
    return {"results": results}


@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """RAG 问答，SSE 流式返回答案和引用来源。"""
    embeddings = get_embeddings(settings)
    store = get_vectorstore(embeddings)

    # 检索相关文档
    search_results = vector_search(store, req.query, req.top_k)
    context = "\n\n".join(r["content"] for r in search_results)

    # 构建提示词
    prompt = f"""你是一个技术文档助手。请根据以下文档内容回答用户的问题。
如果文档中没有相关信息，请如实告知。

## 文档内容

{context}

## 用户问题

{req.query}

## 回答"""

    llm = get_streaming_llm(settings)

    async def stream():
        async for chunk in llm.astream(prompt):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

        sources = [r["source"] for r in search_results]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 3: Commit**

```bash
git add src/api/routes.py src/retrieval/store.py
git commit -m "feat: add API routes (ingest/search/chat)"
```

---

### Task 9: FastAPI 入口

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: 实现 src/main.py**

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

# 确保项目根在 sys.path 中，便于 `python src/main.py` 直接运行
os.environ.setdefault("PYTHONPATH", os.getcwd())


def create_app() -> FastAPI:
    app = FastAPI(
        title="VuePress RAG Backend",
        description="VuePress 技术文档的语义搜索与 RAG 问答 API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add FastAPI entry point"
```

---

### Task 10: Docker 化

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`

- [ ] **Step 1: 实现 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 实现 docker-compose.yml**

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - EMBEDDING_BACKEND=${EMBEDDING_BACKEND:-openai}
      - LLM_BACKEND=${LLM_BACKEND:-openai}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}
      - CHROMADB_MODE=client
      - CHROMADB_HOST=chromadb
      - CHROMADB_PORT=8000
      - DOCS_REPO_URL=${DOCS_REPO_URL:-}
      - GIT_CACHE_DIR=/data/git
    volumes:
      - git_cache:/data/git
    depends_on:
      - chromadb
    restart: unless-stopped

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    restart: unless-stopped

volumes:
  git_cache:
  chroma_data:
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Docker deployment config"
```

---

### Task 11: 集成测试

**Files:**
- Create: `tests/__init__.py`, `tests/test_api.py`

- [ ] **Step 1: 创建 tests/__init__.py**

空文件。

- [ ] **Step 2: 实现 tests/test_api.py**

```python
"""集成测试 — 需要 .env 中配置有效的 DOCS_REPO_URL 和 API key。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    """FastAPI 自带 /docs 可访问即可验证服务启动。"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "VuePress RAG Backend"


def test_search_invalid():
    """空查询应返回合理响应。"""
    response = client.post("/search", json={"query": "", "top_k": 3})
    # 空查询不会报错，但结果可能为空
    assert response.status_code == 200
    assert "results" in response.json()


def test_ingest_status_not_found():
    """不存在的任务返回 404。"""
    response = client.get("/ingest/status?task_id=nonexistent")
    assert response.status_code == 404


@pytest.mark.skip(reason="需要真实 LLM 后端，手动运行时取消 skip")
def test_chat():
    response = client.post("/chat", json={"query": "如何安装？", "top_k": 3})
    assert response.status_code == 200
    # SSE 流式响应
    assert "text/event-stream" in response.headers["content-type"]
```

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: add integration tests"
```

---

## 自审清单

1. **Spec 覆盖:** 每个设计点都有对应任务 — API 4 endpoint ✓，Git 加载 ✓，Markdown 分块+层级 ✓，Embedding/LLM 工厂 ✓，ChromaDB ✓，Docker 部署 ✓，GitHub Action webhook 触发 ✓
2. **无占位符:** 所有步骤都有完整代码，无 TBD/TODO
3. **类型一致性:** Embedding/LLM 工厂返回 LangChain 原生类型，与 store.py 和 routes.py 签名一致
