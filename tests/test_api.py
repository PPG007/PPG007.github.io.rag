"""集成测试 — 需要 .env 中配置有效的 DOCS_REPO_URL 和 API key。"""
import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.main import app

client = TestClient(app)


def test_health():
    """验证服务可正常启动。"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "VuePress RAG Backend"


def test_cors_allows_any_origin():
    response = client.options(
        "/search",
        headers={
            "Origin": "https://example-client.test",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example-client.test"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_token_auth_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(settings, "token_auth_enabled", True)
    monkeypatch.setattr(settings, "api_token", "secret-token")

    response = client.get("/openapi.json")

    assert response.status_code == 401


def test_token_auth_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "token_auth_enabled", True)
    monkeypatch.setattr(settings, "api_token", "secret-token")

    response = client.get("/openapi.json", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_token_auth_accepts_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "token_auth_enabled", True)
    monkeypatch.setattr(settings, "api_token", "secret-token")

    response = client.get("/openapi.json", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200


def test_token_auth_accepts_x_api_token(monkeypatch):
    monkeypatch.setattr(settings, "token_auth_enabled", True)
    monkeypatch.setattr(settings, "api_token", "secret-token")

    response = client.get("/openapi.json", headers={"X-API-Token": "secret-token"})

    assert response.status_code == 200


def test_token_auth_returns_500_when_token_missing_in_config(monkeypatch):
    monkeypatch.setattr(settings, "token_auth_enabled", True)
    monkeypatch.setattr(settings, "api_token", "")

    response = client.get("/openapi.json")

    assert response.status_code == 500


def test_search_empty_query():
    """空查询应返回合理响应。"""
    response = client.post("/search", json={"query": "", "top_k": 3})
    assert response.status_code == 200
    assert "results" in response.json()


def test_ingest_status_not_found():
    """不存在的任务返回 404。"""
    response = client.get("/ingest/status?task_id=nonexistent")
    assert response.status_code == 404
