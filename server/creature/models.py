"""Small immutable domain records used by WEB CREATURE."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from typing import Any


class CreatureState(StrEnum):
    DORMANT = "dormant"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CreatureEvent:
    event_type: str
    payload: dict[str, Any]
    created_at: str

    @classmethod
    def create(cls, event_type: str, payload: dict[str, Any] | None = None) -> "CreatureEvent":
        if not isinstance(event_type, str) or not event_type.strip() or len(event_type) > 100:
            raise ValueError("event_type must be a non-empty string of at most 100 characters")
        data = {} if payload is None else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dictionary")
        # Copy and validate before the event reaches persistent storage.
        snapshot = dict(data)
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        return cls(
            event_type=event_type,
            payload=snapshot,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CreatureMemory:
    memory_type: str
    content: str
    source: str
    confidence: float
    created_at: str

    @classmethod
    def create(
        cls,
        memory_type: str,
        content: str,
        source: str,
        confidence: float = 0.5,
    ) -> "CreatureMemory":
        allowed = {"episodic", "semantic", "procedural", "experimental"}
        if not isinstance(memory_type, str) or memory_type not in allowed:
            raise ValueError("unsupported memory_type")
        if not isinstance(content, str) or not content.strip() or len(content) > 100_000:
            raise ValueError("content must contain 1-100000 characters")
        if not isinstance(source, str) or not source.strip() or len(source) > 2048:
            raise ValueError("source must contain 1-2048 characters")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            memory_type=memory_type,
            content=content,
            source=source,
            confidence=float(confidence),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
