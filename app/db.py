import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    telegram_user_id INTEGER,
    username TEXT,
    first_seen TEXT NOT NULL,
    last_active TEXT NOT NULL,
    followup_stage INTEGER NOT NULL DEFAULT 0,
    followup_enabled INTEGER NOT NULL DEFAULT 1,
    next_followup_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages (chat_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(SCHEMA)


def upsert_user(chat_id: int, telegram_user_id: Optional[int], username: Optional[str]) -> None:
    now = _now()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO users (chat_id, telegram_user_id, username, first_seen, last_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                telegram_user_id = excluded.telegram_user_id,
                username = excluded.username,
                last_active = excluded.last_active
            """,
            (chat_id, telegram_user_id, username, now, now),
        )


def get_user(chat_id: int) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        return row


def get_all_enabled_users() -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE followup_enabled = 1"
        ).fetchall()


def reset_followup(chat_id: int) -> None:
    """Called whenever the user sends a new message: cancel escalation and start over."""
    with _conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET followup_stage = 0, followup_enabled = 1, next_followup_at = NULL, last_active = ?
            WHERE chat_id = ?
            """,
            (_now(), chat_id),
        )


def set_followup_enabled(chat_id: int, enabled: bool) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET followup_enabled = ?, next_followup_at = NULL WHERE chat_id = ?",
            (1 if enabled else 0, chat_id),
        )


def set_next_followup(chat_id: int, stage: int, next_at: datetime) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET followup_stage = ?, next_followup_at = ? WHERE chat_id = ?",
            (stage, next_at.isoformat(), chat_id),
        )


def add_message(chat_id: int, role: str, content: str, history_limit: Optional[int] = None) -> None:
    limit = history_limit if history_limit is not None else config.HISTORY_LIMIT
    with _conn() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, _now()),
        )
        # Keep only the most recent `limit` messages per chat.
        conn.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?
            )
            """,
            (chat_id, chat_id, limit),
        )


def get_history(chat_id: int, limit: Optional[int] = None) -> list[dict]:
    limit = limit if limit is not None else config.HISTORY_LIMIT
    with _conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    rows.reverse()
    return [{"role": row["role"], "content": row["content"]} for row in rows]
