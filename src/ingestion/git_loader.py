from pathlib import Path
from git import Repo


def clone_or_pull(repo_url: str, branch: str, cache_dir: str) -> Path:
    repo_path = Path(cache_dir)

    if repo_path.exists() and (repo_path / ".git").exists():
        repo = Repo(repo_path)
        repo.git.checkout(branch)
        repo.git.pull()
    else:
        repo_path.mkdir(parents=True, exist_ok=True)
        Repo.clone_from(repo_url, repo_path, branch=branch)

    return repo_path


def list_markdown_files(repo_path: Path) -> list[Path]:
    exclude = {".git", "node_modules", ".vscode", ".idea"}
    files = []
    for f in repo_path.rglob("*.md"):
        if not set(f.parts).intersection(exclude):
            files.append(f)
    return files


def load_documents(repo_path: Path) -> list[tuple[str, str]]:
    md_files = list_markdown_files(repo_path)
    results = []
    for f in md_files:
        rel_path = str(f.relative_to(repo_path)).replace("\\", "/")
        content = f.read_text(encoding="utf-8")
        results.append((rel_path, content))
    return results
