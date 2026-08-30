import pytest

from app.ingestion.chunker import chunk_generic, chunk_python_source, should_skip_path


def test_python_chunking_splits_on_function_boundaries():
    source = '''
import os

def foo():
    return 1

class Bar:
    def method(self):
        return 2
'''
    chunks = chunk_python_source(source, "sample.py")
    symbols = {c.symbol for c in chunks}
    assert "foo" in symbols
    assert "Bar" in symbols


def test_python_chunking_falls_back_on_syntax_error():
    chunks = chunk_python_source("def broken(:\n  pass", "broken.py")
    assert len(chunks) >= 1  # falls back to generic chunking instead of raising


def test_generic_chunking_handles_empty_file():
    assert chunk_generic("", "empty.txt") == []


def test_should_skip_vendored_dirs():
    assert should_skip_path(["node_modules", "pkg"], "index.js") is True
    assert should_skip_path(["src"], "main.py") is False


def test_should_skip_binary_extensions():
    assert should_skip_path([], "logo.png") is True
    assert should_skip_path([], "app.py") is False


@pytest.mark.parametrize(
    "filename",
    [".env", ".env.production", ".env.local", "credentials.json", "server.key", "cert.pem"],
)
def test_secret_files_are_never_ingested(filename):
    # Chunks are retrievable via search_code and handed to the model as tool output, so
    # ingesting a credential file would ship its contents to the LLM provider.
    assert should_skip_path([], filename) is True


@pytest.mark.parametrize("filename", [".env.example", ".env.sample", ".env.template"])
def test_env_templates_are_still_ingested(filename):
    # These are documentation (placeholder values), and useful for answering setup questions.
    assert should_skip_path([], filename) is False


@pytest.mark.parametrize(
    "filename", ["package-lock.json", "yarn.lock", "poetry.lock", "go.sum", "Cargo.lock"]
)
def test_lock_files_are_skipped(filename):
    # Machine-generated dependency graphs: large, useless for code Q&A, and they crowd out
    # real source in retrieval results.
    assert should_skip_path([], filename) is True


def test_ordinary_manifests_are_not_treated_as_lock_files():
    assert should_skip_path([], "package.json") is False
    assert should_skip_path([], "pyproject.toml") is False
