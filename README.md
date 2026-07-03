# VuePress RAG Backend

[中文](README_zh.md) | English

VuePress RAG Backend is a FastAPI service that turns a VuePress documentation repository into a searchable retrieval-augmented generation API. It clones or updates a docs repo, splits Markdown by heading-aware chunks, stores embeddings in ChromaDB, and exposes ingestion, semantic search, and streaming chat endpoints.

## Features

- Ingest Markdown content from a Git repository and keep a local Git cache.
- Split VuePress-style Markdown into contextual chunks with source URLs and anchors.
- Store vectors in embedded ChromaDB for local development or a ChromaDB server for deployment.
- Support OpenAI, Ollama, and local BGE embeddings.
- Support OpenAI-compatible, Anthropic, and Ollama chat models.
- Optional API token authentication with `Authorization: Bearer <token>` or `X-API-Token`.
- Optional reranking for better retrieval quality.

## Requirements

- Python 3.12 is recommended.
- Git, required for cloning and updating the documentation repository.
- One embedding backend:
  - OpenAI-compatible embeddings, or
  - Ollama with an embedding model such as `nomic-embed-text`, or
  - local BGE via `sentence-transformers`.
- One chat backend for `/chat`:
  - OpenAI-compatible chat model, or
  - Anthropic, or
  - Ollama.
- Docker and Docker Compose are optional, but recommended for deployment.

Python dependencies are listed in [requirements.txt](requirements.txt).

## Environment Variables

Copy [.env.example](.env.example) to `.env` and adjust the values for your environment.

| Variable | Default | Description |
| --- | --- | --- |
| `DOCS_REPO_URL` | empty | Git URL of the VuePress documentation repository to ingest. Can also be supplied per `/ingest` request. |
| `DOCS_BRANCH` | `main` | Documentation repository branch. Can also be supplied per `/ingest` request. |
| `EMBEDDING_BACKEND` | `openai` | Embedding backend: `openai`, `ollama`, or `bge`. |
| `LLM_BACKEND` | `openai` | Chat backend: `openai`, `anthropic`, or `ollama`. |
| `TOKEN_AUTH_ENABLED` | `false` | Enables token authentication for all non-`OPTIONS` requests. |
| `API_TOKEN` | empty | Required token when `TOKEN_AUTH_ENABLED=true`. |
| `OPENAI_API_KEY` | empty | API key for OpenAI or an OpenAI-compatible provider. |
| `OPENAI_BASE_URL` | empty | Optional OpenAI-compatible base URL, for example a SiliconFlow endpoint. Leave empty for the official OpenAI API. |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI-compatible embedding model. |
| `OPENAI_LLM_MODEL` | `gpt-4o` | OpenAI-compatible chat model. |
| `ANTHROPIC_API_KEY` | empty | Anthropic API key. |
| `ANTHROPIC_LLM_MODEL` | `claude-sonnet-4-6` | Anthropic chat model. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL. |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model. |
| `OLLAMA_LLM_MODEL` | `llama3` | Ollama chat model. |
| `BGE_MODEL_NAME` | `BAAI/bge-small-zh-v1.5` | Local BGE embedding model used when `EMBEDDING_BACKEND=bge`. |
| `CHROMADB_MODE` | `embedded` | ChromaDB mode: `embedded` for local persistent storage or `client` for a ChromaDB server. |
| `CHROMADB_HOST` | `localhost` | ChromaDB server host when `CHROMADB_MODE=client`. |
| `CHROMADB_PORT` | `8000` | ChromaDB server port when `CHROMADB_MODE=client`. |
| `CHROMADB_PERSIST_DIR` | `./chroma_data` | Local ChromaDB persistence directory when `CHROMADB_MODE=embedded`. |
| `CHROMADB_COLLECTION` | `vuepress_docs` | ChromaDB collection name. |
| `CHUNK_SIZE` | `1000` | Maximum text chunk size. |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks. |
| `HEADING_LEVEL` | `2` | Markdown heading level used as the primary split boundary. |
| `RERANK_ENABLED` | `false` | Enables reranking after initial retrieval. |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | Reranking model name used by the OpenAI-compatible rerank endpoint. |
| `GIT_CACHE_DIR` | `./git_cache` | Local directory for cached Git repositories. |

## Start Locally

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Create your environment file.

   ```bash
   cp .env.example .env
   ```

4. Start the API server.

   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Ingest documentation.

   ```bash
   curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{"repo_url":"https://github.com/user/my-vuepress-docs.git","branch":"main"}'
   ```

6. Check ingestion status.

   ```bash
   curl "http://localhost:8000/ingest/status?task_id=<task_id>"
   ```

7. Search or chat.

   ```bash
   curl -X POST http://localhost:8000/search \
     -H "Content-Type: application/json" \
     -d '{"query":"How do I configure SSO?","top_k":5}'
   ```

   ```bash
   curl -N -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"query":"How do I configure SSO?","top_k":5}'
   ```

When token auth is enabled, include one of these headers:

```bash
Authorization: Bearer <API_TOKEN>
X-API-Token: <API_TOKEN>
```

## Deployment

### Docker Compose

Docker Compose starts the FastAPI app and a ChromaDB service.

```bash
docker compose up -d --build
```

The Compose file sets `CHROMADB_MODE=client` and connects the app to the `chromadb` service. Pass production values through your shell environment or an `.env` file before starting:

```bash
DOCS_REPO_URL=https://github.com/user/my-vuepress-docs.git \
OPENAI_API_KEY=sk-... \
docker compose up -d --build
```

### Docker Image

Build and run the API container directly:

```bash
docker build -t vuepress-rag-backend .
docker run --rm -p 8000:8000 --env-file .env vuepress-rag-backend
```

If you run the app container without Compose and want a separate ChromaDB server, set `CHROMADB_MODE=client`, `CHROMADB_HOST`, and `CHROMADB_PORT`.

### Production Notes

- Set `TOKEN_AUTH_ENABLED=true` and provide a strong `API_TOKEN` before exposing the API.
- Persist `GIT_CACHE_DIR` and ChromaDB data with volumes.
- Use a reverse proxy or platform load balancer for TLS termination.
- Keep model provider API keys in secret storage rather than committing them to the repository.
- Run `/ingest` after deployment or whenever the documentation repository changes.
