# VuePress RAG 后端 — 设计文档

## 概述

为 VuePress 技术文档构建的 RAG（检索增强生成）后端。Python 实现，纯 API，Docker 部署。提供语义搜索和 AI 生成答案，返回带原文跳转链接的结果，供 VuePress 插件调用。

## 架构

```
Git 仓库（VuePress 文档源）
    │
    │  git push → GitHub Action → POST /ingest
    ▼
FastAPI（REST + SSE 流式）
    ├── Embedding（OpenAI / Ollama / BGE）
    ├── LLM（OpenAI / Anthropic / Ollama）
    └── ChromaDB（持久化卷）
```

## 项目结构

```
src/
├── main.py              # FastAPI 入口
├── config.py            # 环境变量配置
├── ingestion/
│   ├── git_loader.py    # Git 仓库拉取与更新
│   ├── splitter.py      # Markdown 按标题分块
│   └── pipeline.py      # 摄取流水线编排
├── retrieval/
│   ├── store.py         # ChromaDB 读写
│   └── retriever.py     # 语义检索逻辑
├── llm/
│   ├── embeddings.py    # Embedding 工厂（OpenAI | Ollama | BGE）
│   └── generator.py     # LLM 工厂（OpenAI | Anthropic | Ollama）
└── api/
    └── routes.py        # API 路由
```

## API 设计

### `POST /ingest`
触发文档摄取。支持可选的 `repo_url` / `branch` 参数覆盖默认配置。异步执行，返回任务 ID。

```
POST /ingest
Body: { "repo_url": "...", "branch": "main" }  // 均为可选
Response: 202 { "task_id": "...", "status": "running" }
```

### `GET /ingest/status?task_id=...`
查询摄取进度。返回状态、已处理文档数、错误信息。

```
Response: 200 { "task_id": "...", "status": "running|done|failed", "docs_processed": 42, "error": null }
```

### `POST /search`
语义检索，返回带跳转元数据的文档片段，不经过 LLM。

```
POST /search
Body: { "query": "如何安装", "top_k": 5 }

Response: 200 {
    "results": [
        {
            "content": "npm install -D vuepress@next",
            "score": 0.92,
            "source": {
                "path": "/guide/getting-started.html",
                "title": "快速上手",
                "hierarchy": ["指南", "安装", "npm 方式"],
                "anchor": "#npm-方式"
            }
        }
    ]
}
```

### `POST /chat`
RAG 问答，SSE 流式返回。逐 token 输出生成的答案，最后返回引用来源。

```
POST /chat
Body: { "query": "如何部署 VuePress？", "top_k": 5 }

Response: SSE stream
  data: {"token": "部署"}
  data: {"token": " VuePress"}
  ...
  data: {"type": "sources", "sources": [...]}
  data: [DONE]
```

## 分块策略

- 以 `##` 标题为边界切分（切分级别可配置）
- 每条 chunk 附加上下文前缀：页面标题 + 一级标题
- 保留层级关系为面包屑数组：`["指南", "安装", "npm 方式"]`
- 代码块不拆分，整体保留在所属段落中
- 每条 chunk 元数据包含：
  - `source_path`：文档源文件相对路径（如 `guide/getting-started.md`）
  - `url`：VuePress 输出的跳转 URL（如 `/guide/getting-started.html#npm-方式`）
  - `hierarchy`：面包屑层级数组
  - `anchor`：锚点字符串
  - `chunk_index`：同文件内的顺序编号

## Embedding & LLM 抽象

工厂模式 + 统一接口，通过环境变量切换后端。

### Embedding

```python
class BaseEmbedding(ABC):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

# 后端：OpenAIEmbedding、OllamaEmbedding、LocalBGE
# 切换：EMBEDDING_BACKEND=openai|ollama|bge
```

### LLM

```python
class BaseLLM(ABC):
    async def generate(self, prompt: str) -> str: ...
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...

# 后端：OpenAIGenerator、AnthropicGenerator、OllamaGenerator
# 切换：LLM_BACKEND=openai|anthropic|ollama
```

## 摄取触发

文档仓库配置 GitHub Action，push 时自动触发重新索引：

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

RAG 后端接口兼容无 body 的 webhook 调用（使用默认仓库配置）。

## 部署

Docker Compose，两个服务：

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
      - ./data/git:/data/git   # 文档仓库缓存
    depends_on: [chromadb]

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - ./data/chroma:/chroma/chroma
```

**暂不包含（YAGNI）：** 多副本扩容、API 鉴权、消息队列（长摄取任务）、rerank 重排序、关键词+向量混合检索。

## 关键决策

| 决策 | 选型 | 原因 |
|------|------|------|
| RAG 框架 | LangChain | 生态最丰富，中文文档支持成熟 |
| Web 框架 | FastAPI | 原生 async，SSE 流式，自动接口文档 |
| 向量数据库 | ChromaDB | 嵌入式优先，运维负担最轻，Docker 友好 |
| 后端抽象 | 工厂模式 | 统一接口，多后端可切换，环境变量控制 |
| 分块边界 | Markdown `##` | 与 VuePress 标题结构天然对齐 |
| 触发方式 | GitHub Action webhook | 零额外基础设施，文档仓库自主控制重索引 |
