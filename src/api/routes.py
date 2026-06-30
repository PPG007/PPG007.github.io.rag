import json
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import settings
from src.ingestion.pipeline import run_ingest, get_ingest_status
from src.llm.embeddings import get_embeddings
from src.llm.generator import get_streaming_llm
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
    task_id = uuid.uuid4().hex[:12]
    repo_url = req.repo_url if req else None
    branch = req.branch if req else None
    background_tasks.add_task(run_ingest, task_id, repo_url, branch)
    return {"task_id": task_id, "status": "running"}


@router.get("/ingest/status")
def ingest_status(task_id: str):
    status = get_ingest_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, **status}


@router.post("/search")
def search_endpoint(req: SearchRequest):
    embeddings = get_embeddings(settings)
    store = get_vectorstore(embeddings)
    results = vector_search(store, req.query, req.top_k)
    return {"results": results}


@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    embeddings = get_embeddings(settings)
    store = get_vectorstore(embeddings)

    search_results = vector_search(store, req.query, req.top_k)
    context = "\n\n".join(r["content"] for r in search_results)

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
