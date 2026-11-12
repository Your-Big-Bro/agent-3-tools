"""Память диалога на SQLite.

Одна таблица ``turns``: каждая реплика пользователя и агента пишется с ключом сессии.
Этого достаточно, чтобы контекст переживал перезапуск процесса,
и чтобы в LLM-режиме подмешивать историю в промпт.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT    NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL,
    tool    TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns (session, id);

CREATE TABLE IF NOT EXISTS facts (
    session TEXT NOT NULL,
    key     TEXT NOT NULL,
    value   TEXT NOT NULL,
    PRIMARY KEY (session, key)
);
"""


class SqliteHistory:
    """История реплик по сессиям."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, session: str, role: str, content: str, tool: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO turns (session, role, content, tool, created_at) VALUES (?, ?, ?, ?, ?)",
                (session, role, content, tool, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )

    def history(self, session: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, tool, created_at FROM turns WHERE session = ? ORDER BY id DESC LIMIT ?",
                (session, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def questions(self, session: str, limit: int = 10) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT content FROM turns WHERE session = ? AND role = 'user' ORDER BY id DESC LIMIT ?",
                (session, limit),
            ).fetchall()
        return [row["content"] for row in reversed(rows)]

    def count(self, session: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM turns WHERE session = ?", (session,)).fetchone()
        return int(row["c"])

    def reset(self, session: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM turns WHERE session = ?", (session,))
        return cursor.rowcount

    def sessions(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT session FROM turns ORDER BY session").fetchall()
        return [row["session"] for row in rows]

    # --- факты (используются mock-агентом для демонстрации памяти) ---------
    def set_fact(self, session: str, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO facts (session, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(session, key) DO UPDATE SET value = excluded.value",
                (session, key, value),
            )

    def get_fact(self, session: str, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM facts WHERE session = ? AND key = ?", (session, key)
            ).fetchone()
        return row["value"] if row else None

    def clear_facts(self, session: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM facts WHERE session = ?", (session,))
