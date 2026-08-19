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
