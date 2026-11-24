"""SQLite persistence for WEB CREATURE's private metadata, memory and goals."""
from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import CreatureEvent, CreatureGoal, CreatureMemory, GoalStatus


_MEMORY_TYPES = {"episodic", "semantic", "procedural", "experimental"}
_VERIFICATION = {"unverified", "verified", "rejected"}
_GOAL_TRANSITIONS = {
    GoalStatus.PROPOSED: {GoalStatus.ACTIVE, GoalStatus.CANCELLED},
    GoalStatus.ACTIVE: {GoalStatus.PAUSED, GoalStatus.COMPLETED, GoalStatus.CANCELLED},
    GoalStatus.PAUSED: {GoalStatus.ACTIVE, GoalStatus.CANCELLED},
    GoalStatus.COMPLETED: set(),
    GoalStatus.CANCELLED: set(),
}
_SCHEMA = """
CREATE TABLE IF NOT EXISTS creature_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creature_events_created ON creature_events(created_at DESC);
CREATE TABLE IF NOT EXISTS creature_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('episodic','semantic','procedural','experimental')),
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    created_at TEXT NOT NULL,
    source_kind TEXT NOT NULL DEFAULT 'owner_input',
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    content_hash TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_creature_memory_type_created ON creature_memory(memory_type, created_at DESC);
CREATE TABLE IF NOT EXISTS creature_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    success_criteria TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5),
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creature_goals_status_priority ON creature_goals(status, priority, id);
"""


class CreatureStore:
    """A small file-backed local store with explicit, repeatable schema migration."""

    def __init__(self, database_path: str | Path) -> None:
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("database_path must be a non-empty filesystem path")
        self.database_path = Path(database_path)
        if str(self.database_path) == ":memory:":
            raise ValueError("CreatureStore requires a file-backed database for durable connections")

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(_SCHEMA)
            # Upgrade databases created by foundation v0.1 without dropping data.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(creature_memory)")}
            migrations = {
                "source_kind": "TEXT NOT NULL DEFAULT 'owner_input'",
                "verification_status": "TEXT NOT NULL DEFAULT 'unverified'",
                "content_hash": "TEXT NOT NULL DEFAULT ''",
                "tags_json": "TEXT NOT NULL DEFAULT '[]'",
                "expires_at": "TEXT",
            }
            for name, declaration in migrations.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE creature_memory ADD COLUMN {name} {declaration}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def append_event(self, event: CreatureEvent) -> int:
        if not isinstance(event, CreatureEvent):
            raise TypeError("event must be a CreatureEvent")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO creature_events(event_type, payload_json, created_at) VALUES (?, ?, ?)",
                (event.event_type, json.dumps(event.payload, ensure_ascii=False, allow_nan=False), event.created_at),
            )
            return int(cursor.lastrowid)

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, event_type, payload_json, created_at FROM creature_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": row["id"], "event_type": row["event_type"],
             "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}
            for row in rows
        ]

    def save_memory(self, memory: CreatureMemory) -> int:
        if not isinstance(memory, CreatureMemory):
            raise TypeError("memory must be a CreatureMemory")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO creature_memory
                   (memory_type, content, source, confidence, created_at, source_kind,
                    verification_status, content_hash, tags_json, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (memory.memory_type, memory.content, memory.source, memory.confidence,
                 memory.created_at, memory.source_kind, memory.verification_status,
                 memory.content_hash, json.dumps(memory.tags), memory.expires_at),
            )
            return int(cursor.lastrowid)

    def list_memory(
        self,
        memory_type: str | None = None,
        limit: int = 100,
        query: str | None = None,
        verification_status: str | None = None,
    ) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        if memory_type is not None and memory_type not in _MEMORY_TYPES:
            raise ValueError("unsupported memory_type")
        if verification_status is not None and verification_status not in _VERIFICATION:
            raise ValueError("unsupported verification_status")
        if query is not None and (not isinstance(query, str) or not query.strip() or len(query) > 200):
            raise ValueError("query must contain 1-200 characters")
        clauses: list[str] = []
        params: list[Any] = []
        if memory_type is not None:
            clauses.append("memory_type = ?")
            params.append(memory_type)
        if verification_status is not None:
            clauses.append("verification_status = ?")
            params.append(verification_status)
        if query is not None:
            clauses.append("instr(lower(content), lower(?)) > 0")
            params.append(query.strip())
        sql = "SELECT id, memory_type, content, source, confidence, created_at, source_kind, "               "verification_status, content_hash, tags_json, expires_at FROM creature_memory"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json"))
            result.append(item)
        return result

    def create_goal(self, goal: CreatureGoal) -> int:
        if not isinstance(goal, CreatureGoal):
            raise TypeError("goal must be a CreatureGoal")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO creature_goals
                   (title, description, success_criteria, priority, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (goal.title, goal.description, goal.success_criteria, goal.priority,
                 goal.status.value, goal.created_at, goal.updated_at),
            )
            return int(cursor.lastrowid)

    def get_goal(self, goal_id: int) -> dict[str, Any] | None:
        self._validate_goal_id(goal_id)
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM creature_goals WHERE id = ?", (goal_id,)).fetchone()
        return dict(row) if row else None

    def list_goals(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        if status is not None and status not in {item.value for item in GoalStatus}:
            raise ValueError("unsupported goal status")
        with closing(self._connect()) as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM creature_goals ORDER BY priority ASC, id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM creature_goals WHERE status = ? ORDER BY priority ASC, id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def transition_goal(self, goal_id: int, target: GoalStatus) -> dict[str, Any]:
        self._validate_goal_id(goal_id)
        if not isinstance(target, GoalStatus):
            raise TypeError("target must be a GoalStatus")
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT status FROM creature_goals WHERE id = ?", (goal_id,)).fetchone()
            if row is None:
                raise KeyError(f"goal not found: {goal_id}")
            current = GoalStatus(row["status"])
            if target not in _GOAL_TRANSITIONS[current]:
                raise ValueError(f"invalid goal transition: {current.value} -> {target.value}")
            from datetime import datetime, timezone
            updated_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE creature_goals SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
                (target.value, updated_at, goal_id, current.value),
            )
            updated = connection.execute("SELECT * FROM creature_goals WHERE id = ?", (goal_id,)).fetchone()
        return dict(updated)

    @staticmethod
    def _validate_goal_id(goal_id: int) -> None:
        if isinstance(goal_id, bool) or not isinstance(goal_id, int) or goal_id < 1:
            raise ValueError("goal_id must be a positive integer")
