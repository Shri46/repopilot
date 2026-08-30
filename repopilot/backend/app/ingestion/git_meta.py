"""Best-effort git blame metadata. Ingestion must not fail if the repo isn't a git repo
or if git isn't available — metadata is a nice-to-have, not a dependency."""
from __future__ import annotations

try:
    from git import InvalidGitRepositoryError, Repo
except ImportError:  # pragma: no cover
    Repo = None
    InvalidGitRepositoryError = Exception


def get_repo(path: str):
    if Repo is None:
        return None
    try:
        return Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None
    except Exception:
        return None


def blame_spans(repo, file_path: str, cache: dict | None = None) -> list:
    """Returns [(commit, line_count), ...] covering the file, in order.

    `repo.blame()` blames the entire file, so calling it per chunk re-does identical work
    for every chunk of the same file — the dominant cost of ingestion before this was
    cached (roughly twice the embedding time on a mid-size repo). Pass a dict to reuse one
    blame per file instead of one per chunk.
    """
    if cache is not None and file_path in cache:
        return cache[file_path]

    try:
        spans = [(commit, len(lines)) for commit, lines in repo.blame("HEAD", file_path)]
    except Exception:
        spans = []

    if cache is not None:
        cache[file_path] = spans
    return spans


def blame_for_range(
    repo, file_path: str, start_line: int, end_line: int, cache: dict | None = None
) -> tuple[str | None, str | None]:
    """Returns (author, last_modified_iso) for the most recent commit touching this line range."""
    if repo is None:
        return None, None

    spans = blame_spans(repo, file_path, cache)

    line_no = 1
    latest_commit = None
    for commit, n in spans:
        chunk_start, chunk_end = line_no, line_no + n - 1
        if chunk_end >= start_line and chunk_start <= end_line:
            if latest_commit is None or commit.committed_datetime > latest_commit.committed_datetime:
                latest_commit = commit
        line_no += n

    if latest_commit is None:
        return None, None
    return latest_commit.author.name, latest_commit.committed_datetime.isoformat()
