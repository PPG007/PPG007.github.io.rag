import re
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


def split_markdown(rel_path: str, content: str) -> list[Document]:
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

        doc.metadata.update({
            "source_path": rel_path,
            "url": f"{base_url}#{anchor}" if anchor else base_url,
            "title": page_title,
            "hierarchy": hierarchy,
            "anchor": anchor,
            "chunk_index": i,
        })
        result.append(doc)

    return result


def split_documents(file_pairs: list[tuple[str, str]]) -> list[Document]:
    all_docs = []
    for rel_path, content in file_pairs:
        docs = split_markdown(rel_path, content)
        all_docs.extend(docs)
    return all_docs
