"""SQLite persistence for WEB CREATURE's private metadata and memory."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import CreatureEvent, CreatureMemory


_SCHEMA = """
CREATE TABLE IF NOT EXISTS creature_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creature_events_created
    ON creature_events(created_at DESC);
CREATE TABLE IF NOT EXISTS creature_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('episodic','semantic','procedural','experimental')),
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creature_memory_type_created
    ON creature_memory(memory_type, created_at DESC);
"""


class CreatureStore:
    """A small local store. Initialization is explicit and never runs on import."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        if str(self.database_path) != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def append_event(self, event: CreatureEvent) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO creature_events(event_type, payload_json, created_at) VALUES (?, ?, ?)",
                (event.event_type, json.dumps(event.payload, ensure_ascii=False, allow_nan=False), event.created_at),
            )
            return int(cursor.lastrowid)

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, event_type, payload_json, created_at FROM creature_events "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"id": row["id"], "event_type": row["event_type"],
             "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}
            for row in rows
        ]

    def save_memory(self, memory: CreatureMemory) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO creature_memory(memory_type, content, source, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (memory.memory_type, memory.content, memory.source, memory.confidence, memory.created_at),
            )
            return int(cursor.lastrowid)

    def list_memory(self, memory_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        if memory_type is not None and memory_type not in {"episodic", "semantic", "procedural", "experimental"}:
            raise ValueError("unsupported memory_type")
        query = "SELECT id, memory_type, content, source, confidence, created_at FROM creature_memory"
        params: tuple[Any, ...] = ()
        if memory_type is not None:
            query += " WHERE memory_type = ?"
            params = (memory_type,)
        query += " ORDER BY id DESC LIMIT ?"
        params += (limit,)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
