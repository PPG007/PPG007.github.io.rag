# VuePress RAG Backend

中文 | [English](README.md)

VuePress RAG Backend 是一个基于 FastAPI 的 RAG 服务，用于把 VuePress 文档仓库转换成可检索、可问答的 API。它会克隆或更新文档仓库，按 Markdown 标题和长度切分内容，把 embedding 写入 ChromaDB，并提供文档入库、语义搜索和流式问答接口。

## 项目介绍

- 从 Git 文档仓库读取 Markdown，并维护本地 Git 缓存。
- 面向 VuePress 文档生成带来源 URL 和标题锚点的上下文 chunk。
- 支持本地 embedded ChromaDB，也支持连接独立 ChromaDB 服务。
- 支持 OpenAI、Ollama、本地 BGE embedding。
- 支持 OpenAI 兼容接口、Anthropic、Ollama 作为聊天模型。
- 支持可选 token 鉴权，可使用 `Authorization: Bearer <token>` 或 `X-API-Token`。
- 支持可选 rerank，提升检索结果质量。

## 所需依赖

- 推荐 Python 3.12。
- Git，用于克隆和更新文档仓库。
- 至少配置一个 embedding 后端：
  - OpenAI 兼容 embedding；或
  - Ollama，例如 `nomic-embed-text`；或
  - 基于 `sentence-transformers` 的本地 BGE。
- 如需使用 `/chat`，至少配置一个聊天模型后端：
  - OpenAI 兼容聊天模型；或
  - Anthropic；或
  - Ollama。
- Docker 与 Docker Compose 可选，推荐用于部署。

Python 依赖见 [requirements.txt](requirements.txt)。

## 环境变量解释

复制 [.env.example](.env.example) 为 `.env`，再按实际环境修改。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DOCS_REPO_URL` | 空 | 要入库的 VuePress 文档 Git 仓库地址。也可以在 `/ingest` 请求中传入。 |
| `DOCS_BRANCH` | `main` | 文档仓库分支。也可以在 `/ingest` 请求中传入。 |
| `EMBEDDING_BACKEND` | `openai` | Embedding 后端：`openai`、`ollama` 或 `bge`。 |
| `LLM_BACKEND` | `openai` | 聊天模型后端：`openai`、`anthropic` 或 `ollama`。 |
| `TOKEN_AUTH_ENABLED` | `false` | 是否开启 token 鉴权。开启后所有非 `OPTIONS` 请求都需要 token。 |
| `API_TOKEN` | 空 | `TOKEN_AUTH_ENABLED=true` 时必填。 |
| `OPENAI_API_KEY` | 空 | OpenAI 或 OpenAI 兼容服务的 API key。 |
| `OPENAI_BASE_URL` | 空 | OpenAI 兼容服务 base URL，例如硅基流动接口；留空使用 OpenAI 官方接口。 |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI 兼容 embedding 模型。 |
| `OPENAI_LLM_MODEL` | `gpt-4o` | OpenAI 兼容聊天模型。 |
| `ANTHROPIC_API_KEY` | 空 | Anthropic API key。 |
| `ANTHROPIC_LLM_MODEL` | `claude-sonnet-4-6` | Anthropic 聊天模型。 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址。 |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding 模型。 |
| `OLLAMA_LLM_MODEL` | `llama3` | Ollama 聊天模型。 |
| `BGE_MODEL_NAME` | `BAAI/bge-small-zh-v1.5` | `EMBEDDING_BACKEND=bge` 时使用的本地 BGE 模型。 |
| `CHROMADB_MODE` | `embedded` | ChromaDB 模式：`embedded` 表示本地持久化，`client` 表示连接独立 ChromaDB 服务。 |
| `CHROMADB_HOST` | `localhost` | `CHROMADB_MODE=client` 时的 ChromaDB 主机。 |
| `CHROMADB_PORT` | `8000` | `CHROMADB_MODE=client` 时的 ChromaDB 端口。 |
| `CHROMADB_PERSIST_DIR` | `./chroma_data` | `CHROMADB_MODE=embedded` 时的本地持久化目录。 |
| `CHROMADB_COLLECTION` | `vuepress_docs` | ChromaDB collection 名称。 |
| `CHUNK_SIZE` | `1000` | 文本 chunk 最大长度。 |
| `CHUNK_OVERLAP` | `200` | chunk 之间的字符重叠长度。 |
| `HEADING_LEVEL` | `2` | Markdown 标题切分的主要层级。 |
| `RERANK_ENABLED` | `false` | 是否在初步检索后启用 rerank。 |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | OpenAI 兼容 rerank 接口使用的模型名。 |
| `GIT_CACHE_DIR` | `./git_cache` | Git 仓库本地缓存目录。 |

## 启动方式

1. 创建并激活虚拟环境。

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell：

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. 安装依赖。

   ```bash
   pip install -r requirements.txt
   ```

3. 创建环境变量文件。

   ```bash
   cp .env.example .env
   ```

4. 启动 API 服务。

   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. 触发文档入库。

   ```bash
   curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{"repo_url":"https://github.com/user/my-vuepress-docs.git","branch":"main"}'
   ```

6. 查询入库状态。

   ```bash
   curl "http://localhost:8000/ingest/status?task_id=<task_id>"
   ```

7. 搜索或问答。

   ```bash
   curl -X POST http://localhost:8000/search \
     -H "Content-Type: application/json" \
     -d '{"query":"如何配置 SSO？","top_k":5}'
   ```

   ```bash
   curl -N -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"query":"如何配置 SSO？","top_k":5}'
   ```

如果开启了 token 鉴权，请带上下面任意一种请求头：

```bash
Authorization: Bearer <API_TOKEN>
X-API-Token: <API_TOKEN>
```

## 部署方法

### Docker Compose

Docker Compose 会同时启动 FastAPI 应用和 ChromaDB 服务。

```bash
docker compose up -d --build
```

Compose 配置会设置 `CHROMADB_MODE=client`，并让应用连接到 `chromadb` 服务。启动前可以通过 shell 环境变量或 `.env` 文件传入生产配置：

```bash
DOCS_REPO_URL=https://github.com/user/my-vuepress-docs.git \
OPENAI_API_KEY=sk-... \
docker compose up -d --build
```

### Docker 镜像

也可以直接构建并运行 API 镜像：

```bash
docker build -t vuepress-rag-backend .
docker run --rm -p 8000:8000 --env-file .env vuepress-rag-backend
```

如果不使用 Compose，但希望连接独立 ChromaDB 服务，请设置 `CHROMADB_MODE=client`、`CHROMADB_HOST` 和 `CHROMADB_PORT`。

### 生产建议

- 对外暴露 API 前，建议设置 `TOKEN_AUTH_ENABLED=true` 并配置强 `API_TOKEN`。
- 使用 volume 持久化 `GIT_CACHE_DIR` 和 ChromaDB 数据。
- 通过反向代理或平台负载均衡处理 TLS。
- 将模型供应商 API key 放在密钥管理系统中，不要提交到仓库。
- 部署后或文档仓库更新后，调用 `/ingest` 重新入库。
