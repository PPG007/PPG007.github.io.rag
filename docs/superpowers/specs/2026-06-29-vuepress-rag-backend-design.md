# VuePress RAG Backend — Design

## Overview

A RAG (Retrieval-Augmented Generation) backend for VuePress technical documentation. Python, API-only, Docker-deployed. Serves semantic search and AI-generated answers with jump-to-source links, consumable by a VuePress plugin.

## Architecture

```
Git Repo (VuePress docs)
    │
    │  git push → GitHub Action → POST /ingest
    ▼
FastAPI (REST + SSE streaming)
    ├── Embedding (OpenAI / Ollama / BGE)
    ├── LLM (OpenAI / Anthropic / Ollama)
    └── ChromaDB (persistent volume)
```

## Project Structure

```
src/
├── main.py              # FastAPI entry point
├── config.py            # Env-based configuration
├── ingestion/
│   ├── git_loader.py    # Git repo clone/pull
│   ├── splitter.py      # Markdown heading-based chunking
│   └── pipeline.py      # Ingest orchestration
├── retrieval/
│   ├── store.py         # ChromaDB read/write
│   └── retriever.py     # Semantic search logic
├── llm/
│   ├── embeddings.py    # Embedding factory (OpenAI | Ollama | BGE)
│   └── generator.py     # LLM factory (OpenAI | Anthropic | Ollama)
└── api/
    └── routes.py        # API routes
```

## API Design

### `POST /ingest`
Trigger documentation ingestion. Accepts optional `repo_url` / `branch` overrides (defaults from config). Runs async, returns task ID.

```
POST /ingest
Body: { "repo_url": "...", "branch": "main" }  // both optional
Response: 202 { "task_id": "...", "status": "running" }
```

### `GET /ingest/status?task_id=...`
Poll ingestion progress. Returns status, document count, error if any.

```
Response: 200 { "task_id": "...", "status": "running|done|failed", "docs_processed": 42, "error": null }
```

### `POST /search`
Semantic search returning document chunks with jump metadata.

```
POST /search
Body: { "query": "how to install", "top_k": 5 }

Response: 200 {
    "results": [
        {
            "content": "npm install -D vuepress@next",
            "score": 0.92,
            "source": {
                "path": "/guide/getting-started.html",
                "title": "Getting Started",
                "hierarchy": ["Guide", "Installation", "npm"],
                "anchor": "#npm"
            }
        }
    ]
}
```

### `POST /chat`
RAG Q&A with SSE streaming. Returns generated answer token-by-token, followed by source references.

```
POST /chat
Body: { "query": "how to deploy VuePress?", "top_k": 5 }

Response: SSE stream
  data: {"token": "To"}
  data: {"token": " deploy"}
  ...
  data: {"type": "sources", "sources": [...]}
  data: [DONE]
```

## Chunking Strategy

- Split by `##` heading boundaries (configurable level)
- Prefix each chunk with context: page title + `h1` heading
- Preserve hierarchy as breadcrumb array: `["Guide", "Installation", "npm"]`
- Code blocks are NOT split — kept whole within their parent section
- Each chunk metadata includes:
  - `source_path`: relative path in docs repo (e.g., `guide/getting-started.md`)
  - `url`: VuePress output URL (e.g., `/guide/getting-started.html#npm`)
  - `hierarchy`: breadcrumb array
  - `anchor`: target anchor string
  - `chunk_index`: position within the source file

## Embedding & LLM Abstraction

Factory pattern with unified interfaces, selectable via environment variables.

### Embedding

```python
class BaseEmbedding(ABC):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

# Backends: OpenAIEmbedding, OllamaEmbedding, LocalBGE
# Select via: EMBEDDING_BACKEND=openai|ollama|bge
```

### LLM

```python
class BaseLLM(ABC):
    async def generate(self, prompt: str) -> str: ...
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...

# Backends: OpenAIGenerator, AnthropicGenerator, OllamaGenerator
# Select via: LLM_BACKEND=openai|anthropic|ollama
```

## Ingest Trigger

Document repo configures a GitHub Action workflow:

```yaml
on:
  push:
    branches: [main]
jobs:
  reindex:
    runs-on: ubuntu-latest
    steps:
      - run: curl -X POST https://<rag-host>/ingest
```

The RAG backend endpoint is compatible — accepts webhook calls with no body (uses default repo config).

## Deployment

Docker Compose, two services:

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      - EMBEDDING_BACKEND=openai
      - LLM_BACKEND=openai
      - CHROMADB_HOST=chromadb
      - DOCS_REPO_URL=...
    volumes:
      - ./data/git:/data/git   # cloned docs cache
    depends_on: [chromadb]

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - ./data/chroma:/chroma/chroma
```

**Excluded for now (YAGNI):** multi-replica scaling, API auth, message queue for long ingest, reranking, hybrid keyword+vector search.

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| RAG Framework | LangChain | Largest ecosystem, mature Chinese doc support |
| Web Framework | FastAPI | Native async, SSE streaming, auto docs |
| Vector DB | ChromaDB | Embedded-first, minimal ops, Docker-friendly |
| Abstraction | Factory pattern | One interface, multi backend, env-switchable |
| Chunk boundary | Markdown `##` | Natural fit for VuePress heading structure |
| Trigger | GitHub Action webhook | Zero infra; docs repo owns its own reindex |
