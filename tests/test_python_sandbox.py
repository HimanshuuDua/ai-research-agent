import pytest

from agent.tools.python_repl import _run_sandboxed


def test_sandbox_allows_basic_math():
    result = _run_sandboxed("print(2 + 2)")
    assert "4" in result


def test_sandbox_blocks_imports():
    with pytest.raises(ValueError, match="Imports are not allowed"):
        _run_sandboxed("import os")


def test_sandbox_blocks_open():
    with pytest.raises(ValueError, match="open"):
        _run_sandboxed("open('secret.txt')")
