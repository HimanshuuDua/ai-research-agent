"""SQLite usage logs and per-session chat history (keyed by hashed IP + user agent)."""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_HISTORY_MESSAGES = 80


def _db_path() -> str:
    explicit = os.getenv("STORAGE_PATH", "").strip()
    if explicit:
        return explicit
    if os.getenv("VERCEL"):
        return "/tmp/ai_research_agent.db"
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / "usage.db")


def session_key_from_request(ip: str, user_agent: str = "") -> str:
    raw = f"{ip.strip()}|{user_agent[:160]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
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
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_key) REFERENCES sessions(session_key)
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def touch_session(session_key: str, ip_hash: str) -> None:
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


def append_message(
    session_key: str,
    ip_hash: str,
    role: str,
    content: str,
    *,
    mode: str | None = None,
    model_used: str | None = None,
) -> None:
    touch_session(session_key, ip_hash)
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
    touch_session(session_key, ip_hash)
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


def get_session_messages(session_key: str, limit: int = MAX_HISTORY_MESSAGES) -> list[dict]:
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
    items = [dict(row) for row in reversed(rows)]
    return items


def replace_session_messages(session_key: str, ip_hash: str, messages: list[dict]) -> None:
    """Sync full chat thread from client (e.g. after restore)."""
    touch_session(session_key, ip_hash)
    trimmed = messages[-MAX_HISTORY_MESSAGES:]
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE session_key = ?", (session_key,))
        for msg in trimmed:
            conn.execute(
                """
                INSERT INTO messages (session_key, role, content, mode, model_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_key,
                    msg.get("role", "user"),
                    msg.get("content", ""),
                    msg.get("mode"),
                    msg.get("model_used"),
                    _now_iso(),
                ),
            )
        conn.execute(
            "UPDATE sessions SET message_count = ?, last_seen = ? WHERE session_key = ?",
            (len(trimmed), _now_iso(), session_key),
        )
