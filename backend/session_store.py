"""SQLite-backed persistent storage for EchoMind sessions."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    source_device TEXT NOT NULL DEFAULT '',
    duration REAL NOT NULL DEFAULT 0.0,
    language TEXT NOT NULL DEFAULT 'en',
    transcript TEXT NOT NULL DEFAULT '',
    action_items TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]'
);
"""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@dataclass
class SessionRecord:
    """Minimal DTO matching the sessions table shape."""

    id: int | None = None
    title: str = ""
    date: str = ""
    source_device: str = ""
    duration: float = 0.0
    language: str = "en"
    transcript: str = ""
    action_items: list[str] | None = None
    tags: list[str] | None = None

    @staticmethod
    def from_row(row: sqlite3.Row) -> "SessionRecord":
        return SessionRecord(
            id=row["id"],
            title=row["title"],
            date=row["date"],
            source_device=row["source_device"],
            duration=row["duration"],
            language=row["language"],
            transcript=row["transcript"],
            action_items=json.loads(row["action_items"] or "[]"),
            tags=json.loads(row["tags"] or "[]"),
        )

    def as_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "source_device": self.source_device,
            "duration": self.duration,
            "language": self.language,
            "transcript": self.transcript,
            "action_items": json.dumps(self.action_items or []),
            "tags": json.dumps(self.tags or []),
        }


def init_db(db_path: str | Path) -> str:
    """Create schema at *db_path* and return the resolved path string."""
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(p)) as conn:
        conn.execute(_DB_SCHEMA)
        conn.commit()
    return str(p)


def create_session(db_path: str, **fields: Any) -> SessionRecord:
    now = _utc_iso()
    row = {
        "title": fields.get("title", ""),
        "date": fields.get("date") or now,
        "source_device": fields.get("source_device", ""),
        "duration": float(fields.get("duration", 0.0)),
        "language": fields.get("language", "en"),
        "transcript": fields.get("transcript", ""),
        "action_items": json.dumps(fields.get("action_items", [])),
        "tags": json.dumps(fields.get("tags", [])),
    }
    with _conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO sessions (title, date, source_device, duration, language, transcript, action_items, tags) "
            "VALUES (:title, :date, :source_device, :duration, :language, :transcript, :action_items, :tags)",
            row,
        )
        row["id"] = cur.lastrowid
    return SessionRecord(
        id=row["id"],
        title=row["title"],
        date=row["date"],
        source_device=row["source_device"],
        duration=row["duration"],
        language=row["language"],
        transcript=row["transcript"],
        action_items=json.loads(row["action_items"]),
        tags=json.loads(row["tags"]),
    )


def get_session(db_path: str, session_id: int) -> SessionRecord | None:
    with _conn(db_path) as conn:
        cur = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
    if row is None:
        return None
    return SessionRecord.from_row(row)


def update_session(db_path: str, session_id: int, **fields: Any) -> SessionRecord | None:
    existing = get_session(db_path, session_id)
    if existing is None:
        return None
    data = existing.as_row()
    data.update(fields)
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET title=:title, date=:date, source_device=:source_device, "
            "duration=:duration, language=:language, transcript=:transcript, "
            "action_items=:action_items, tags=:tags WHERE id=:id",
            data,
        )
    return get_session(db_path, session_id)


def list_sessions(db_path: str) -> list[SessionRecord]:
    with _conn(db_path) as conn:
        cur = conn.execute("SELECT * FROM sessions ORDER BY date DESC")
        rows = cur.fetchall()
    return [SessionRecord.from_row(r) for r in rows]
