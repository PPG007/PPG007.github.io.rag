import re
from pathlib import Path
from urllib.parse import urlparse

import frontmatter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document

from src.config import settings


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w一-鿿\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text


def parse_frontmatter(content: str) -> tuple[dict, str]:
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


def _collect_images(content: str, rel_path: str, repo_path: str) -> tuple[str, list[str]]:
    """提取文档中的本地图片路径，返回 (清理后的文本, 图片绝对路径列表)。"""
    if not settings.vision_enabled:
        return content, []

    doc_dir = Path(repo_path) / Path(rel_path).parent
    image_paths: list[str] = []

    def record_img(match):
        img_path = match.group(1).strip()
        if urlparse(img_path).scheme:
            return match.group(0)
        resolved = (doc_dir / img_path).resolve()
        if resolved.exists():
            image_paths.append(str(resolved))
        return match.group(0)

    content = re.sub(r'!\[.*?\]\(([^)]+)\)', record_img, content)
    content = re.sub(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', record_img, content, flags=re.I)
    return content, image_paths


def split_markdown(rel_path: str, content: str, repo_path: str = "") -> list[Document]:
    metadata, body = parse_frontmatter(content)
    page_title = metadata.get("title", rel_path)

    headers_to_split_on = [
        ("#" * i, f"h{i}")
        for i in range(2, settings.heading_level + 2)
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    docs = splitter.split_text(body)
    base_url = "/" + rel_path.replace(".md", ".html")

    result = []
    for i, doc in enumerate(docs):
        hierarchy = [page_title]
        for h_level in range(1, 5):
            key = f"h{h_level}"
            if key in doc.metadata:
                hierarchy.append(doc.metadata[key])

        anchor_heading = ""
        for h_level in range(4, 0, -1):
            key = f"h{h_level}"
            if key in doc.metadata:
                anchor_heading = doc.metadata[key]
                break

        anchor = slugify(anchor_heading) if anchor_heading else ""

        # 收集该 chunk 中的图片
        clean_text, images = _collect_images(doc.page_content, rel_path, repo_path)

        doc.metadata.update({
            "source_path": rel_path,
            "url": f"{base_url}#{anchor}" if anchor else base_url,
            "title": page_title,
            "hierarchy": hierarchy,
            "anchor": anchor,
            "chunk_index": i,
        })
        if images:
            doc.metadata["_images"] = images
        result.append(doc)

    return result


def split_documents(file_pairs: list[tuple[str, str]], repo_path: str = "") -> list[Document]:
    all_docs = []
    for rel_path, content in file_pairs:
        docs = split_markdown(rel_path, content, repo_path)
        all_docs.extend(docs)
    return all_docs
