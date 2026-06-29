import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.25)
    raise RuntimeError(f"Server did not start on {host}:{port}")


@pytest.fixture(scope="session")
def live_server():
    port = 8765
    host = "127.0.0.1"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["STORAGE_PATH"] = str(ROOT / "data" / "e2e-test.db")
    (ROOT / "data" / "e2e-test.db").unlink(missing_ok=True)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.index:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_port(host, port)
        yield f"http://{host}:{port}"
    except RuntimeError:
        err = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        if err:
            raise RuntimeError(f"Server did not start on {host}:{port}\n{err}") from None
        raise
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 800}}
