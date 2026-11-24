"""Validated, immutable domain records used by WEB CREATURE."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any


class CreatureState(StrEnum):
    DORMANT = "dormant"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class GoalStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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
        snapshot = dict(data)
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        return cls(event_type, snapshot, datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, slots=True)
class CreatureMemory:
    memory_type: str
    content: str
    source: str
    confidence: float
    created_at: str
    source_kind: str = "owner_input"
    verification_status: str = "unverified"
    content_hash: str = ""
    tags: tuple[str, ...] = ()
    expires_at: str | None = None

    @classmethod
    def create(
        cls,
        memory_type: str,
        content: str,
        source: str,
        confidence: float = 0.5,
        *,
        source_kind: str = "owner_input",
        verification_status: str = "unverified",
        tags: tuple[str, ...] | list[str] = (),
        expires_at: str | None = None,
    ) -> "CreatureMemory":
        allowed_types = {"episodic", "semantic", "procedural", "experimental"}
        allowed_sources = {"owner_input", "user_input", "local_file", "web", "agent"}
        allowed_verification = {"unverified", "verified", "rejected"}
        if not isinstance(memory_type, str) or memory_type not in allowed_types:
            raise ValueError("unsupported memory_type")
        if not isinstance(content, str) or not content.strip() or len(content) > 100_000:
            raise ValueError("content must contain 1-100000 characters")
        if not isinstance(source, str) or not source.strip() or len(source) > 2048:
            raise ValueError("source must contain 1-2048 characters")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if source_kind not in allowed_sources:
            raise ValueError("unsupported source_kind")
        if verification_status not in allowed_verification:
            raise ValueError("unsupported verification_status")
        if not isinstance(tags, (tuple, list)) or len(tags) > 20:
            raise ValueError("tags must be a list or tuple containing at most 20 items")
        clean_tags = tuple(dict.fromkeys(
            tag.strip().lower() for tag in tags
            if isinstance(tag, str) and tag.strip() and len(tag) <= 40
        ))
        if len(clean_tags) != len(tags):
            raise ValueError("every tag must be a non-empty string of at most 40 characters")
        if expires_at is not None and (not isinstance(expires_at, str) or len(expires_at) > 40):
            raise ValueError("expires_at must be an ISO timestamp string or None")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return cls(
            memory_type=memory_type,
            content=content,
            source=source,
            confidence=float(confidence),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_kind=source_kind,
            verification_status=verification_status,
            content_hash=digest,
            tags=clean_tags,
            expires_at=expires_at,
        )


@dataclass(frozen=True, slots=True)
class CreatureGoal:
    title: str
    description: str
    success_criteria: str
    priority: int
    created_at: str
    updated_at: str
    status: GoalStatus = GoalStatus.PROPOSED

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        success_criteria: str = "",
        priority: int = 3,
    ) -> "CreatureGoal":
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise ValueError("title must contain 1-160 characters")
        for value, label, limit in (
            (description, "description", 4000),
            (success_criteria, "success_criteria", 2000),
        ):
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f"{label} must be a string of at most {limit} characters")
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            raise ValueError("priority must be an integer between 1 and 5")
        now = datetime.now(timezone.utc).isoformat()
        return cls(title.strip(), description, success_criteria, priority, now, now)
