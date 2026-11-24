"""Invitation-only access primitives for the WEB CREATURE online platform.

Only token hashes belong in persistent storage. The raw invite token is returned
once at creation time and must be delivered through a trusted owner-only channel.
Authentication, rate limiting, persistence and session issuance remain host duties.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from uuid import uuid4


def _utc(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Invitation:
    invitation_id: str
    token_sha256: str
    created_by: str
    created_at: str
    expires_at: str
    max_uses: int = 1
    uses: int = 0
    revoked_at: str | None = None

    @classmethod
    def issue(
        cls,
        created_by: str,
        *,
        lifetime: timedelta = timedelta(days=7),
        max_uses: int = 1,
        now: datetime | None = None,
    ) -> tuple["Invitation", str]:
        if not isinstance(created_by, str) or not created_by.strip() or len(created_by) > 128:
            raise ValueError("created_by must contain 1-128 characters")
        if not isinstance(lifetime, timedelta) or lifetime <= timedelta(0) or lifetime > timedelta(days=90):
            raise ValueError("lifetime must be greater than zero and no more than 90 days")
        if isinstance(max_uses, bool) or not isinstance(max_uses, int) or not 1 <= max_uses <= 100:
            raise ValueError("max_uses must be an integer between 1 and 100")
        issued_at = _utc(now or datetime.now(timezone.utc), "now")
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        record = cls(
            invitation_id=str(uuid4()),
            token_sha256=digest,
            created_by=created_by.strip(),
            created_at=issued_at.isoformat(),
            expires_at=(issued_at + lifetime).isoformat(),
            max_uses=max_uses,
        )
        return record, token

    def is_usable(self, now: datetime | None = None) -> bool:
        current = _utc(now or datetime.now(timezone.utc), "now")
        expires = datetime.fromisoformat(self.expires_at)
        return (
            self.revoked_at is None
            and self.uses < self.max_uses
            and current < expires
        )

    def consume(self, token: str, *, now: datetime | None = None) -> "Invitation":
        if not isinstance(token, str) or not token:
            raise PermissionError("invalid or unavailable invitation")
        candidate = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(candidate, self.token_sha256) or not self.is_usable(now):
            raise PermissionError("invalid or unavailable invitation")
        return replace(self, uses=self.uses + 1)

    def revoke(self, *, now: datetime | None = None) -> "Invitation":
        if self.revoked_at is not None:
            return self
        revoked = _utc(now or datetime.now(timezone.utc), "now")
        return replace(self, revoked_at=revoked.isoformat())
