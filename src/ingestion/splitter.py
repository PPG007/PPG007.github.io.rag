import re

import frontmatter
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.config import settings

PLACEHOLDER_RE = re.compile(r"^(todo|tbd|待补充|待完善|coming soon)[:：。.!\s-]*$", re.I)
MIN_MEANINGFUL_CHARS = 12


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w一-鿿\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text


def parse_frontmatter(content: str) -> tuple[dict, str]:
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


def _build_hierarchy(metadata: dict, page_title: str) -> list[str]:
    hierarchy = [page_title]
    for h_level in range(1, 5):
        key = f"h{h_level}"
        if key in metadata:
            hierarchy.append(metadata[key])
    return hierarchy


def _build_anchor(metadata: dict) -> str:
    for h_level in range(4, 0, -1):
        key = f"h{h_level}"
        if key in metadata:
            return slugify(metadata[key])
    return ""


def _strip_docs_prefix(url: str) -> str:
    if url == "/docs":
        return "/"
    if url.startswith("/docs/"):
        return url[len("/docs"):]
    return url


def _base_metadata(rel_path: str, page_title: str | None = None) -> dict:
    base_url = _strip_docs_prefix("/" + rel_path.replace(".md", ".html"))
    title = page_title or rel_path
    return {
        "source_path": rel_path,
        "url": base_url,
        "title": title,
    }


def _plain_text(content: str) -> str:
    text = re.sub(r"```.*?```", " ", content, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_low_value_chunk(content: str) -> bool:
    lines = [
        re.sub(r"^\s{0,3}#{1,6}\s*", "", line).strip()
        for line in content.splitlines()
        if line.strip()
    ]
    if lines and all(PLACEHOLDER_RE.match(line) for line in lines):
        return True

    plain = _plain_text(content)
    if not plain:
        return True
    if PLACEHOLDER_RE.match(plain):
        return True
    return len(plain) < MIN_MEANINGFUL_CHARS


def _with_context(content: str, hierarchy: list[str]) -> str:
    context = " / ".join(item for item in hierarchy if item)
    if not context:
        return content
    return f"{context}\n\n{content}"


def split_markdown(rel_path: str, content: str, repo_path: str = "") -> list[Document]:
    metadata, body = parse_frontmatter(content)
    page_title = metadata.get("title", rel_path)
    base = _base_metadata(rel_path, page_title)

    # 第一遍：按标题切
    headers_to_split_on = [
        ("#" * i, f"h{i}")
        for i in range(2, settings.heading_level + 2)
    ]
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    docs = header_splitter.split_text(body)

    # 第二遍：超大 chunk 按 size 二次切
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", ". ", " ", ""],
    )

    result = []
    for header_idx, doc in enumerate(docs):
        hierarchy = _build_hierarchy(doc.metadata, page_title)
        anchor = _build_anchor(doc.metadata)
        url = f"{base['url']}#{anchor}" if anchor else base["url"]

        sub_docs = char_splitter.split_text(doc.page_content)
        for j, sub_doc in enumerate(sub_docs):
            if _is_low_value_chunk(sub_doc):
                continue

            meta = {
                **base,
                "url": url,
                "hierarchy": hierarchy,
                "anchor": anchor,
                "chunk_index": j,
                "header_index": header_idx,
                "raw_content": sub_doc,
            }
            result.append(Document(page_content=_with_context(sub_doc, hierarchy), metadata=meta))

    return result


def split_documents(file_pairs: list[tuple[str, str]], repo_path: str = "") -> list[Document]:
    all_docs = []
    for rel_path, content in file_pairs:
        docs = split_markdown(rel_path, content, repo_path)
        all_docs.extend(docs)
    return all_docs
