import urllib.request

from langchain_core.documents import Document

from src.ingestion.splitter import split_markdown
from src.retrieval import store


def test_split_markdown_filters_placeholder_chunks():
    content = """# Demo

## 配置
TODO:

## 什么是 SSO
SSO(Single Sign On) 单点登录是一种身份验证机制，用户只需要登录一次就可以访问多个相互信任的系统。
"""

    docs = split_markdown("docs/demo.md", content)

    assert len(docs) == 1
    assert "TODO" not in docs[0].page_content
    assert docs[0].metadata["url"] == "/demo.html#什么是-sso"
    assert docs[0].metadata["raw_content"].startswith("## 什么是 SSO")
    assert "docs/demo.md / 什么是 SSO" in docs[0].page_content


def test_split_markdown_keeps_urls_outside_docs_root():
    content = """# Guide

## Install
Install details are meaningful enough to keep this chunk.
"""

    docs = split_markdown("guide/install.md", content)

    assert len(docs) == 1
    assert docs[0].metadata["url"] == "/guide/install.html#install"


def test_doc_to_result_returns_raw_content():
    doc = Document(
        page_content="docs/demo.md / 什么是 SSO\n\n## 什么是 SSO\nSSO definition",
        metadata={
            "raw_content": "## 什么是 SSO\nSSO definition",
            "url": "/docs/demo.html#什么是-sso",
            "title": "docs/demo.md",
            "hierarchy": ["docs/demo.md", "什么是 SSO"],
            "anchor": "什么是-sso",
        },
    )

    result = store._doc_to_result(doc)

    assert result["content"] == "## 什么是 SSO\nSSO definition"
    assert result["source"]["anchor"] == "#什么是-sso"


def test_rerank_uses_relevance_score_order(monkeypatch):
    docs = [
        Document(page_content="first"),
        Document(page_content="second"),
        Document(page_content="third"),
    ]

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"results":[{"index":0,"relevance_score":0.1},{"index":2,"relevance_score":0.9},{"index":1,"relevance_score":0.4}]}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse())

    ranked = store._rerank("query", docs, 3)

    assert [doc.page_content for doc in ranked] == ["third", "second", "first"]
