import ast
import contextlib
import io

from langchain_core.tools import tool

BLOCKED_NAMES = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}
ALLOWED_BUILTINS = {
    "print": print,
    "len": len,
    "range": range,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "sum": sum,
    "min": min,
    "max": max,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "round": round,
    "abs": abs,
    "True": True,
    "False": False,
    "None": None,
}


def _validate_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Imports are not allowed in the sandbox.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_NAMES:
                raise ValueError(f"{node.func.id}() is not allowed in the sandbox.")


def _run_sandboxed(code: str) -> str:
    _validate_code(code)
    stdout = io.StringIO()
    globals_dict = {"__builtins__": ALLOWED_BUILTINS}
    with contextlib.redirect_stdout(stdout):
        exec(compile(code, "<sandbox>", "exec"), globals_dict, globals_dict)
    output = stdout.getvalue().strip()
    return output or "Code executed successfully (no printed output)."


@tool
def python_repl(code: str) -> str:
    """Execute Python for analysis, calculations, or formatting after research."""
    try:
        return _run_sandboxed(code)
    except Exception as exc:
        return f"Python sandbox error: {exc}"


def get_python_repl_tool():
    return python_repl
