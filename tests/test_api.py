"""集成测试 — 需要 .env 中配置有效的 DOCS_REPO_URL 和 API key。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    """验证服务可正常启动。"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "VuePress RAG Backend"


def test_search_empty_query():
    """空查询应返回合理响应。"""
    response = client.post("/search", json={"query": "", "top_k": 3})
    assert response.status_code == 200
    assert "results" in response.json()


def test_ingest_status_not_found():
    """不存在的任务返回 404。"""
    response = client.get("/ingest/status?task_id=nonexistent")
    assert response.status_code == 404
