"""Chunking strategies for code ingestion.

Python files are chunked at function/class boundaries using the `ast` module, which gives
much more coherent retrieval units than fixed-size windows (a function body doesn't get cut
in half). Everything else falls back to a sliding line-window chunker.
"""
import ast
from dataclasses import dataclass

WINDOW_LINES = 60
WINDOW_OVERLAP = 10

# Skip vendored / generated / binary-ish content.
SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".pytest_cache", "vendor", "target", ".mypy_cache",
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".woff", ".woff2",
    ".ttf", ".eot", ".zip", ".gz", ".lock", ".min.js", ".map",
}
MAX_FILE_BYTES = 500_000  # skip huge generated files


@dataclass
class RawChunk:
    file_path: str
    symbol: str | None
    start_line: int
    end_line: int
    content: str


def should_skip_path(path_parts: list[str], filename: str) -> bool:
    if any(part in SKIP_DIR_NAMES for part in path_parts):
        return True
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in SKIP_EXTENSIONS)


def chunk_python_source(source: str, file_path: str) -> list[RawChunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_generic(source, file_path)

    lines = source.splitlines()
    chunks: list[RawChunk] = []
    top_level_nodes = [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    if not top_level_nodes:
        return chunk_generic(source, file_path)

    covered_lines: set[int] = set()

    for node in top_level_nodes:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        symbol = node.name
        content = "\n".join(lines[start - 1:end])
        if content.strip():
            chunks.append(RawChunk(file_path, symbol, start, end, content))
        covered_lines.update(range(start, end + 1))

    # Module-level code (imports, constants, top-of-file docstring) not covered above.
    uncovered = [i + 1 for i in range(len(lines)) if (i + 1) not in covered_lines]
    if uncovered:
        module_content = "\n".join(
            line for i, line in enumerate(lines) if (i + 1) in uncovered
        ).strip()
        if module_content:
            chunks.append(
                RawChunk(file_path, "<module-level>", min(uncovered), max(uncovered), module_content)
            )

    return chunks


def chunk_generic(source: str, file_path: str) -> list[RawChunk]:
    lines = source.splitlines()
    if not lines:
        return []

    chunks: list[RawChunk] = []
    step = WINDOW_LINES - WINDOW_OVERLAP
    i = 0
    while i < len(lines):
        window = lines[i:i + WINDOW_LINES]
        content = "\n".join(window).strip()
        if content:
            chunks.append(RawChunk(file_path, None, i + 1, min(i + WINDOW_LINES, len(lines)), content))
        i += step
    return chunks


def chunk_file(source: str, file_path: str) -> list[RawChunk]:
    if file_path.endswith(".py"):
        return chunk_python_source(source, file_path)
    return chunk_generic(source, file_path)
