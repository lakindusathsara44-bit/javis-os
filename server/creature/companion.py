"""Provider-neutral conversation, initiative and action proposal contracts.

These are domain contracts only. A trusted host must authenticate callers,
persist records, enforce capabilities and execute approved actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,79}$")


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be 3-80 safe identifier characters")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ActionClass(StrEnum):
    READ_ONLY = "read_only"
    REVERSIBLE_LOCAL = "reversible_local"
    CONSEQUENTIAL = "consequential"
    RESTRICTED = "restricted"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ConversationSession:
    session_id: str
    owner_id: str
    created_at: str
    updated_at: str
    status: SessionStatus = SessionStatus.ACTIVE

    @classmethod
    def create(cls, owner_id: str) -> "ConversationSession":
        _validate_id(owner_id, "owner_id")
        now = _now()
        return cls(str(uuid4()), owner_id, now, now)


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    message_id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: str
    provider: str | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        role: MessageRole,
        content: str,
        *,
        provider: str | None = None,
    ) -> "ConversationMessage":
        _validate_id(session_id, "session_id")
        if not isinstance(role, MessageRole):
            raise ValueError("role must be a supported MessageRole")
        if not isinstance(content, str) or not content.strip() or len(content) > 20_000:
            raise ValueError("content must contain 1-20000 characters")
        if provider is not None and (
            not isinstance(provider, str) or not provider.strip() or len(provider) > 80
        ):
            raise ValueError("provider must be a non-empty string of at most 80 characters")
        return cls(str(uuid4()), session_id, role, content, _now(), provider)


@dataclass(frozen=True, slots=True)
class InitiativeSettings:
    """User-owned proactive notification preferences; disabled by default."""

    enabled: bool = False
    paused: bool = False
    timezone: str = "Asia/Colombo"
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    max_notifications_per_day: int = 3
    minimum_priority: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool) or not isinstance(self.paused, bool):
            raise ValueError("enabled and paused must be booleans")
        if not isinstance(self.timezone, str) or len(self.timezone) > 64:
            raise ValueError("timezone must be a valid IANA timezone")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a valid IANA timezone") from None
        for name, value in (
            ("quiet_hours_start", self.quiet_hours_start),
            ("quiet_hours_end", self.quiet_hours_end),
        ):
            if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                raise ValueError(f"{name} must use HH:MM 24-hour format")
        if isinstance(self.max_notifications_per_day, bool) or not isinstance(
            self.max_notifications_per_day, int
        ) or not 0 <= self.max_notifications_per_day <= 50:
            raise ValueError("max_notifications_per_day must be between 0 and 50")
        if isinstance(self.minimum_priority, bool) or not isinstance(
            self.minimum_priority, int
        ) or not 1 <= self.minimum_priority <= 5:
            raise ValueError("minimum_priority must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class ActionProposal:
    """Immutable description of a proposed action, not an execution capability."""

    proposal_id: str
    action_type: str
    target: str
    summary: str
    action_class: ActionClass
    payload_json: str
    payload_sha256: str
    created_at: str
    status: ProposalStatus = ProposalStatus.PROPOSED

    @classmethod
    def create(
        cls,
        action_type: str,
        target: str,
        summary: str,
        action_class: ActionClass,
        payload: dict[str, Any] | None = None,
    ) -> "ActionProposal":
        for value, label, limit in (
            (action_type, "action_type", 100),
            (target, "target", 500),
            (summary, "summary", 2000),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{label} must contain 1-{limit} characters")
        if not isinstance(action_class, ActionClass):
            raise ValueError("action_class must be a supported ActionClass")
        data = {} if payload is None else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dictionary")
        try:
            payload_json = json.dumps(
                data, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            )
        except (TypeError, ValueError):
            raise ValueError("payload must contain JSON-safe values") from None
        if len(payload_json) > 20_000:
            raise ValueError("payload must not exceed 20000 encoded characters")
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        return cls(
            str(uuid4()), action_type.strip(), target.strip(), summary.strip(),
            action_class, payload_json, digest, _now(),
        )

    @property
    def approval_fingerprint(self) -> str:
        """Bind approval to the exact action description and payload digest."""
        material = "|".join((
            self.proposal_id, self.action_type, self.target,
            self.action_class.value, self.payload_sha256,
        ))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @property
    def requires_explicit_approval(self) -> bool:
        return self.action_class in {
            ActionClass.CONSEQUENTIAL,
            ActionClass.RESTRICTED,
        }
