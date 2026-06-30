"""Usage logs and per-session chat history.

Two backends:
- Supabase (Postgres via REST) when SUPABASE_URL + SUPABASE_SERVICE_KEY are set — persistent,
  viewable in the Supabase Table Editor. Recommended for Vercel.
- SQLite fallback for local development (data/usage.db).

All writes are best-effort: a storage failure never breaks a chat response.
"""

import hashlib
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_HISTORY_MESSAGES = 80

SB_SESSIONS = "sessions"
SB_MESSAGES = "messages"
SB_USAGE = "usage_logs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_key_from_request(ip: str, user_agent: str = "") -> str:
    raw = f"{ip.strip()}|{user_agent[:160]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def _supabase_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def use_supabase() -> bool:
    return bool(_supabase_url() and _supabase_key())


# ---------------------------------------------------------------------------
# Supabase REST backend (PostgREST)
# ---------------------------------------------------------------------------

def _sb_headers(extra: dict | None = None) -> dict:
    key = _supabase_key()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _sb_request(method: str, table: str, *, body=None, params: dict | None = None, headers: dict | None = None):
    url = f"{_supabase_url()}/rest/v1/{table}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=_sb_headers(headers), method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else None


def _sb_touch_session(session_key: str, ip_hash: str) -> None:
    now = _now_iso()
    _sb_request(
        "POST",
        SB_SESSIONS,
        body={
            "session_key": session_key,
            "ip_hash": ip_hash,
            "first_seen": now,
            "last_seen": now,
        },
        headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        params={"on_conflict": "session_key"},
    )


def _sb_append_message(session_key, ip_hash, role, content, mode, model_used) -> None:
    _sb_touch_session(session_key, ip_hash)
    _sb_request(
        "POST",
        SB_MESSAGES,
        body={
            "session_key": session_key,
            "role": role,
            "content": content,
            "mode": mode,
            "model_used": model_used,
            "created_at": _now_iso(),
        },
        headers={"Prefer": "return=minimal"},
    )


def _sb_log_usage(session_key, ip_hash, prompt, output, mode, model_used, email_status) -> None:
    _sb_touch_session(session_key, ip_hash)
    _sb_request(
        "POST",
        SB_USAGE,
        body={
            "session_key": session_key,
            "ip_hash": ip_hash,
            "prompt": prompt,
            "output": output,
            "mode": mode,
            "model_used": model_used,
            "email_status": json.dumps(email_status) if email_status else None,
            "created_at": _now_iso(),
        },
        headers={"Prefer": "return=minimal"},
    )


def _sb_get_session_messages(session_key: str, limit: int) -> list[dict]:
    rows = _sb_request(
        "GET",
        "messages",
        params={
            "session_key": f"eq.{session_key}",
            "select": "role,content,mode,model_used,created_at",
            "order": "id.desc",
            "limit": str(limit),
        },
    )
    rows = rows or []
    return list(reversed(rows))


def supabase_ping() -> dict:
    """Lightweight connectivity check for /api/health."""
    if not use_supabase():
        return {"configured": False}
    try:
        _sb_request("GET", "sessions", params={"select": "session_key", "limit": "1"})
        return {"configured": True, "ok": True}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:160]
        return {"configured": True, "ok": False, "error": f"{exc.code}: {detail}"}
    except Exception as exc:  # noqa: BLE001
        return {"configured": True, "ok": False, "error": str(exc)[:160]}


# ---------------------------------------------------------------------------
# SQLite backend (local fallback)
# ---------------------------------------------------------------------------

def _db_path() -> str:
    explicit = os.getenv("STORAGE_PATH", "").strip()
    if explicit:
        return explicit
    if os.getenv("VERCEL"):
        return "/tmp/ai_research_agent.db"
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / "usage.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_init() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_key TEXT PRIMARY KEY,
                ip_hash TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                message_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT,
                model_used TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                output TEXT NOT NULL,
                mode TEXT,
                model_used TEXT,
                email_status TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_key, id);
            CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_logs(session_key, id);
            """
        )


def _sqlite_touch_session(session_key: str, ip_hash: str) -> None:
    now = _now_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_key, ip_hash, first_seen, last_seen, message_count)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(session_key) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (session_key, ip_hash, now, now),
        )


def _sqlite_append_message(session_key, ip_hash, role, content, mode, model_used) -> None:
    _sqlite_touch_session(session_key, ip_hash)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (session_key, role, content, mode, model_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_key, role, content, mode, model_used, _now_iso()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1, last_seen = ? WHERE session_key = ?",
            (_now_iso(), session_key),
        )


def _sqlite_log_usage(session_key, ip_hash, prompt, output, mode, model_used, email_status) -> None:
    _sqlite_touch_session(session_key, ip_hash)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage_logs
            (session_key, ip_hash, prompt, output, mode, model_used, email_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_key,
                ip_hash,
                prompt,
                output,
                mode,
                model_used,
                json.dumps(email_status) if email_status else None,
                _now_iso(),
            ),
        )


def _sqlite_get_session_messages(session_key: str, limit: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, mode, model_used, created_at
            FROM messages
            WHERE session_key = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_key, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


# ---------------------------------------------------------------------------
# Public API (dispatches to the active backend; writes are best-effort)
# ---------------------------------------------------------------------------

def init_db() -> None:
    if use_supabase():
        return  # tables are created once via the Supabase SQL editor
    try:
        _sqlite_init()
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] init_db failed: {exc}")


def touch_session(session_key: str, ip_hash: str) -> None:
    try:
        if use_supabase():
            _sb_touch_session(session_key, ip_hash)
        else:
            _sqlite_touch_session(session_key, ip_hash)
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] touch_session failed: {exc}")


def append_message(
    session_key: str,
    ip_hash: str,
    role: str,
    content: str,
    *,
    mode: str | None = None,
    model_used: str | None = None,
) -> None:
    try:
        if use_supabase():
            _sb_append_message(session_key, ip_hash, role, content, mode, model_used)
        else:
            _sqlite_append_message(session_key, ip_hash, role, content, mode, model_used)
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] append_message failed: {exc}")


def log_usage(
    session_key: str,
    ip_hash: str,
    prompt: str,
    output: str,
    *,
    mode: str,
    model_used: str | None = None,
    email_status: dict | None = None,
) -> None:
    try:
        if use_supabase():
            _sb_log_usage(session_key, ip_hash, prompt, output, mode, model_used, email_status)
        else:
            _sqlite_log_usage(session_key, ip_hash, prompt, output, mode, model_used, email_status)
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] log_usage failed: {exc}")


def get_session_messages(session_key: str, limit: int = MAX_HISTORY_MESSAGES) -> list[dict]:
    try:
        if use_supabase():
            return _sb_get_session_messages(session_key, limit)
        return _sqlite_get_session_messages(session_key, limit)
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] get_session_messages failed: {exc}")
        return []
