import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import verify_token_middleware
from src.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="VuePress RAG Backend",
        description="VuePress 技术文档的语义搜索与 RAG 问答 API",
        version="0.1.0",
    )

    app.middleware("http")(verify_token_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
