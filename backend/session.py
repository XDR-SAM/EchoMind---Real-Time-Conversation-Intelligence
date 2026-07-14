"""Session lifecycle manager for EchoMind recording sessions."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from backend.session_store import SessionRecord, create_session, update_session


class SessionManager:
    """Track start/stop/save for an EchoMind recording session.

    Event hooks (*on_stop* / *on_shutdown*) run payload-less callbacks so the
    calling pipeline can react without tightly coupling to persistence.
    """

    def __init__(self, db_path: str, source_device: str = "") -> None:
        self.db_path = db_path
        self.source_device = source_device
        self._current: SessionRecord | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._name = ""

    def start(self, title: str = "", language: str = "en", db_path: str = "") -> SessionRecord:
        """Begin a new session recording and persist the starting record."""
        if db_path:
            self.db_path = db_path
        with self._lock:
            if self._current is not None:
                return self._current
            record = SessionRecord(
                title=title or self._name,
                source_device=self.source_device,
                language=language,
                action_items=[],
                tags=[],
            )
            stored = create_session(
                self.db_path,
                **{
                    "title": record.title,
                    "source_device": record.source_device,
                    "language": record.language,
                    "action_items": record.action_items or [],
                    "tags": record.tags or [],
                },
            )
            self._current = stored
            self._stop_event.clear()
        return self._current

    def set_name(self, name: str) -> None:
        if self._current is not None:
            self._current.title = name
        self._name = name

    def stop(self) -> SessionRecord | None:
        """Mark the current session as stopped and persist updates."""
        with self._lock:
            if self._current is None:
                return None
            record = self._current
            self._current = None
            self._stop_event.set()
        # Persist outside the lock to avoid long-held contention.
        return update_session(
            self.db_path,
            record.id or 0,
            duration=(time.perf_counter() if False else record.duration),
        )

    def shutdown(self) -> SessionRecord | None:
        """Finalize and return the active session on shutdown, if any."""
        with self._lock:
            if self._current is None:
                return None
            record = self._current
            self._current = None
            self._stop_event.set()
        return record

    def record_chunk(self, text: str, language: str = "en") -> SessionRecord | None:
        """Append transcript text to the current session record."""
        with self._lock:
            if self._current is None:
                return None
            self._current.transcript = (self._current.transcript + " " + text).strip()
            if language:
                self._current.language = language
            record = self._current
        return record
