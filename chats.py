"""Saved conversations, stored in PostgreSQL."""

import psycopg
from psycopg.types.json import Jsonb

from auth import _connect

DEFAULT_TITLE = "New conversation"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL DEFAULT 'New conversation',
    plugin_zip TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversations_user_idx ON conversations (user_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    download        BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_conv_idx ON messages (conversation_id, id);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS report JSONB;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS attachment TEXT;
"""


def init_schema() -> None:
    with _connect() as conn:
        conn.execute(SCHEMA)


def create_conversation(conv_id: str, user_id: int) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO conversations (id, user_id) VALUES (%s, %s)", (conv_id, user_id))


def owner(conv_id: str) -> int | None:
    with _connect() as conn:
        row = conn.execute("SELECT user_id FROM conversations WHERE id = %s", (conv_id,)).fetchone()
    return row[0] if row else None


def add_message(conv_id: str, role: str, content: str, download: bool = False, report: dict | None = None, attachment: str | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, download, report, attachment) VALUES (%s, %s, %s, %s, %s, %s)",
            (conv_id, role, content, download, Jsonb(report) if report else None, attachment),
        )
        conn.execute("UPDATE conversations SET updated_at = now() WHERE id = %s", (conv_id,))


def set_title_from(conv_id: str, text: str) -> None:
    """Name a conversation after its first user message."""
    title = " ".join(text.split())[:60] or DEFAULT_TITLE
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET title = %s WHERE id = %s AND title = %s",
            (title, conv_id, DEFAULT_TITLE),
        )


def set_plugin(conv_id: str, path: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE conversations SET plugin_zip = %s WHERE id = %s", (path, conv_id))


def plugin_path(conv_id: str, user_id: int) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT plugin_zip FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id)
        ).fetchone()
    return row[0] if row else None


def list_conversations(user_id: int, limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at, plugin_zip IS NOT NULL FROM conversations "
            "WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
            (user_id, limit),
        ).fetchall()
    return [{"id": r[0], "title": r[1], "updated_at": r[2].isoformat(), "has_plugin": r[3]} for r in rows]


def get_conversation(conv_id: str, user_id: int) -> dict | None:
    with _connect() as conn:
        conv = conn.execute(
            "SELECT id, title FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id)
        ).fetchone()
        if not conv:
            return None
        rows = conn.execute(
            "SELECT role, content, download, report FROM messages WHERE conversation_id = %s ORDER BY id", (conv_id,)
        ).fetchall()
    return {
        "id": conv[0],
        "title": conv[1],
        "messages": [{"role": r[0], "content": r[1], "download": r[2], "report": r[3]} for r in rows],
    }
