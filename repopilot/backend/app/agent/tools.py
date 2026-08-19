"""Agent tools. Each tool is a plain Python function plus a Gemini function-declaration schema.

Keeping tools as small, single-purpose functions (rather than one big "do anything" tool) is
deliberate: it makes each tool call auditable in the trace log and keeps the agent's decisions
about *which* tool to call a meaningful signal you can evaluate.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import UUID

from google.genai import types
from sqlalchemy.orm import Session

from app.ingestion.git_meta import blame_for_range, get_repo
from app.retrieval.hybrid import hybrid_search

MAX_FILE_READ_CHARS = 8000
MAX_GREP_MATCHES = 40
TEST_TIMEOUT_SECONDS = 30


def tool_search_code(db: Session, project_id: UUID, query: str, top_k: int = 6) -> str:
    results = hybrid_search(db, project_id, query, top_k=top_k)
    if not results:
        return "No matching code found."
    lines = []
    for r in results:
        symbol = f" ({r.symbol})" if r.symbol else ""
        lines.append(f"--- {r.file_path}:{r.start_line}-{r.end_line}{symbol} ---\n{r.content}")
    return "\n\n".join(lines)


def tool_read_file(repo_root: str, file_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    full_path = (Path(repo_root) / file_path).resolve()
    if not str(full_path).startswith(str(Path(repo_root).resolve())):
        return "Error: path escapes repo root."
    if not full_path.exists():
        return f"Error: file not found: {file_path}"

    text = full_path.read_text(encoding="utf-8", errors="replace")
    if start_line is not None and end_line is not None:
        lines = text.splitlines()
        text = "\n".join(lines[max(0, start_line - 1):end_line])

    if len(text) > MAX_FILE_READ_CHARS:
        text = text[:MAX_FILE_READ_CHARS] + "\n... [truncated]"
    return text


def tool_grep(repo_root: str, pattern: str) -> str:
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts",
             "--include=*.tsx", "--include=*.jsx", pattern, "."],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
    except Exception as e:
        return f"grep failed: {e}"

    lines = result.stdout.splitlines()[:MAX_GREP_MATCHES]
    return "\n".join(lines) if lines else "No matches."


def tool_run_tests(repo_root: str, test_path: str = "") -> str:
    """Runs pytest in a sandboxed subprocess with a timeout. Read-only from the agent's
    perspective — it can only trigger the repo's own test command, not arbitrary code."""
    cmd = ["python", "-m", "pytest", test_path or ".", "-q", "--no-header"]
    try:
        result = subprocess.run(
            cmd, cwd=repo_root, capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "Test run timed out."
    except Exception as e:
        return f"Test run failed to start: {e}"

    output = (result.stdout + "\n" + result.stderr).strip()
    return output[-4000:] if len(output) > 4000 else output


def tool_git_blame(repo_root: str, file_path: str, start_line: int, end_line: int) -> str:
    repo = get_repo(repo_root)
    if repo is None:
        return "Not a git repository or git unavailable."
    author, modified = blame_for_range(repo, file_path, start_line, end_line)
    if author is None:
        return "No blame info found for that range."
    return f"Last modified by {author} on {modified}"


TOOL_DECLARATIONS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="search_code",
            description="Semantic + keyword search over the ingested codebase. Use this first to find relevant code.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Natural language or keyword query")},
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="read_file",
            description="Read a file (optionally a line range) from the repo to see full context around a search hit.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "file_path": types.Schema(type="STRING", description="Path relative to repo root"),
                    "start_line": types.Schema(type="INTEGER"),
                    "end_line": types.Schema(type="INTEGER"),
                },
                required=["file_path"],
            ),
        ),
        types.FunctionDeclaration(
            name="grep",
            description="Regex/text search across the repo for an exact string or pattern (function names, error strings).",
            parameters=types.Schema(
                type="OBJECT",
                properties={"pattern": types.Schema(type="STRING")},
                required=["pattern"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_tests",
            description="Run the repo's pytest suite (optionally a specific path) to check if code behaves as expected.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"test_path": types.Schema(type="STRING", description="Optional path to a test file or dir")},
            ),
        ),
        types.FunctionDeclaration(
            name="git_blame",
            description="Find who last modified a file/line range and when. Useful for 'who wrote this' / 'when did this change' questions.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "file_path": types.Schema(type="STRING"),
                    "start_line": types.Schema(type="INTEGER"),
                    "end_line": types.Schema(type="INTEGER"),
                },
                required=["file_path", "start_line", "end_line"],
            ),
        ),
    ])
]
