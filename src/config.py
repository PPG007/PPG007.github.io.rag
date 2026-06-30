from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Docs
    docs_repo_url: str = ""
    docs_branch: str = "main"

    # Embedding backend: openai | ollama | bge
    embedding_backend: str = "openai"

    # LLM backend: openai | anthropic | ollama
    llm_backend: str = "openai"

    # OpenAI — 设置 base_url 可切换至硅基流动等兼容平台
    openai_api_key: str = ""
    openai_base_url: str = ""
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
