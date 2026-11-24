"""SQLite-backed private account and invitation service for WEB CREATURE.

This module is deliberately framework-neutral. The host must protect these
methods behind authenticated owner routes, secure cookies, CSRF protection,
TLS, rate limits and a trusted one-time owner bootstrap procedure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4


_EMAIL_RE = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,190}$")
_DUMMY_SALT = bytes.fromhex("8f3a4b5c6d7e8091a2b3c4d5e6f70819")
_DUMMY_PASSWORD_HASH = hashlib.scrypt(
    b"not-a-real-user-password", salt=_DUMMY_SALT,
    n=2**14, r=8, p=1, dklen=64,
)


@dataclass(frozen=True, slots=True)
class Account:
    user_id: str
    email: str
    display_name: str
    role: str
    created_at: str


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    invitation_id: str
    token: str
    expires_at: str
    max_uses: int


class AccountStore:
    """Explicitly initialized SQLite account store; no module-level DB effects."""

    def __init__(self, database_path: str | Path, *, session_lifetime: timedelta = timedelta(days=14)):
        if not isinstance(session_lifetime, timedelta) or not timedelta(minutes=5) <= session_lifetime <= timedelta(days=30):
            raise ValueError("session_lifetime must be between 5 minutes and 30 days")
        self._path = Path(database_path)
        self._session_lifetime = session_lifetime

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS creature_accounts (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('owner', 'member')),
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    disabled_at TEXT
                );
                CREATE TABLE IF NOT EXISTS creature_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    token_sha256 TEXT NOT NULL UNIQUE,
                    created_by TEXT NOT NULL REFERENCES creature_accounts(user_id),
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    max_uses INTEGER NOT NULL CHECK(max_uses BETWEEN 1 AND 100),
                    uses INTEGER NOT NULL DEFAULT 0 CHECK(uses >= 0),
                    revoked_at TEXT
                );
                CREATE TABLE IF NOT EXISTS creature_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES creature_accounts(user_id) ON DELETE CASCADE,
                    token_sha256 TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_creature_sessions_user
                    ON creature_sessions(user_id, expires_at);
                CREATE INDEX IF NOT EXISTS idx_creature_invitations_creator
                    ON creature_invitations(created_by, created_at);
                """
            )

    def bootstrap_owner(self, email: str, password: str, display_name: str) -> Account:
        """Create the first owner exactly once; call only from trusted local setup."""
        normalized = self._email(email)
        name = self._display_name(display_name)
        salt, digest = self._password_hash(password)
        now = self._now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM creature_accounts LIMIT 1").fetchone():
                raise PermissionError("owner bootstrap is already closed")
            user_id = str(uuid4())
            db.execute(
                """INSERT INTO creature_accounts
                   (user_id,email,display_name,role,password_salt,password_hash,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (user_id, normalized, name, "owner", salt, digest, now),
            )
            return self._account(db.execute(
                "SELECT * FROM creature_accounts WHERE user_id=?", (user_id,)
            ).fetchone())

    def issue_invitation(
        self, actor_user_id: str, *,
        lifetime: timedelta = timedelta(days=7), max_uses: int = 1,
    ) -> IssuedInvitation:
        if not isinstance(lifetime, timedelta) or lifetime <= timedelta(0) or lifetime > timedelta(days=90):
            raise ValueError("lifetime must be greater than zero and no more than 90 days")
        if isinstance(max_uses, bool) or not isinstance(max_uses, int) or not 1 <= max_uses <= 100:
            raise ValueError("max_uses must be an integer between 1 and 100")
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + lifetime
        invitation_id = str(uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actor = db.execute(
                "SELECT role, disabled_at FROM creature_accounts WHERE user_id=?",
                (actor_user_id,),
            ).fetchone()
            if actor is None or actor["role"] != "owner" or actor["disabled_at"] is not None:
                raise PermissionError("owner permission required")
            db.execute(
                """INSERT INTO creature_invitations
                   (invitation_id,token_sha256,created_by,created_at,expires_at,max_uses)
                   VALUES(?,?,?,?,?,?)""",
                (invitation_id, self._sha256(token), actor_user_id,
                 now.isoformat(), expires.isoformat(), max_uses),
            )
        return IssuedInvitation(invitation_id, token, expires.isoformat(), max_uses)

    def revoke_invitation(self, actor_user_id: str, invitation_id: str) -> bool:
        now = self._now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actor = db.execute(
                "SELECT role, disabled_at FROM creature_accounts WHERE user_id=?",
                (actor_user_id,),
            ).fetchone()
            if actor is None or actor["role"] != "owner" or actor["disabled_at"] is not None:
                raise PermissionError("owner permission required")
            cursor = db.execute(
                """UPDATE creature_invitations SET revoked_at=?
                   WHERE invitation_id=? AND revoked_at IS NULL""",
                (now, invitation_id),
            )
            return cursor.rowcount == 1

    def register_with_invitation(
        self, email: str, password: str, display_name: str, invitation_token: str,
    ) -> Account:
        normalized = self._email(email)
        name = self._display_name(display_name)
        salt, digest = self._password_hash(password)
        if not isinstance(invitation_token, str) or not 32 <= len(invitation_token) <= 256:
            raise PermissionError("invalid or unavailable invitation")
        token_hash = self._sha256(invitation_token)
        now = datetime.now(timezone.utc)
        user_id = str(uuid4())
        with self._connect() as db:
            # Serialize invitation use and account creation to prevent concurrent
            # requests from consuming the same last invitation slot twice.
            db.execute("BEGIN IMMEDIATE")
            invite = db.execute(
                "SELECT * FROM creature_invitations WHERE token_sha256=?",
                (token_hash,),
            ).fetchone()
            if invite is None:
                raise PermissionError("invalid or unavailable invitation")
            expires = datetime.fromisoformat(invite["expires_at"])
            if (
                invite["revoked_at"] is not None
                or invite["uses"] >= invite["max_uses"]
                or now >= expires
            ):
                raise PermissionError("invalid or unavailable invitation")
            if db.execute(
                "SELECT 1 FROM creature_accounts WHERE email=? COLLATE NOCASE",
                (normalized,),
            ).fetchone():
                raise ValueError("account could not be created with the supplied details")
            db.execute(
                """UPDATE creature_invitations SET uses=uses+1
                   WHERE invitation_id=? AND uses < max_uses AND revoked_at IS NULL""",
                (invite["invitation_id"],),
            )
            db.execute(
                """INSERT INTO creature_accounts
                   (user_id,email,display_name,role,password_salt,password_hash,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (user_id, normalized, name, "member", salt, digest, now.isoformat()),
            )
            return self._account(db.execute(
                "SELECT * FROM creature_accounts WHERE user_id=?", (user_id,)
            ).fetchone())

    def authenticate(self, email: str, password: str) -> Account | None:
        try:
            normalized = self._email(email)
        except ValueError:
            normalized = "invalid@example.invalid"
        if not isinstance(password, str) or len(password) > 1024:
            password = ""
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM creature_accounts WHERE email=? COLLATE NOCASE",
                (normalized,),
            ).fetchone()
        if row is None:
            self._verify_password(password, _DUMMY_SALT, _DUMMY_PASSWORD_HASH)
            return None
        if row["disabled_at"] is not None:
            self._verify_password(password, row["password_salt"], row["password_hash"])
            return None
        if not self._verify_password(password, row["password_salt"], row["password_hash"]):
            return None
        return self._account(row)

    def create_session(self, user_id: str) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + self._session_lifetime
        session_id = str(uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute(
                "SELECT 1 FROM creature_accounts WHERE user_id=? AND disabled_at IS NULL",
                (user_id,),
            ).fetchone()
            if user is None:
                raise PermissionError("account unavailable")
            db.execute(
                """INSERT INTO creature_sessions
                   (session_id,user_id,token_sha256,created_at,expires_at)
                   VALUES(?,?,?,?,?)""",
                (session_id, user_id, self._sha256(token), now.isoformat(), expires.isoformat()),
            )
        return token, expires.isoformat()

    def resolve_session(self, token: str) -> Account | None:
        if not isinstance(token, str) or not 32 <= len(token) <= 256:
            return None
        now = self._now()
        with self._connect() as db:
            row = db.execute(
                """SELECT a.* FROM creature_sessions s
                   JOIN creature_accounts a ON a.user_id=s.user_id
                   WHERE s.token_sha256=? AND s.revoked_at IS NULL
                     AND s.expires_at>? AND a.disabled_at IS NULL""",
                (self._sha256(token), now),
            ).fetchone()
        return self._account(row) if row is not None else None

    def revoke_session(self, token: str) -> bool:
        if not isinstance(token, str) or not 32 <= len(token) <= 256:
            return False
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE creature_sessions SET revoked_at=?
                   WHERE token_sha256=? AND revoked_at IS NULL""",
                (self._now(), self._sha256(token)),
            )
            return cursor.rowcount == 1

    def revoke_all_sessions(self, actor_user_id: str, target_user_id: str) -> int:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actor = db.execute(
                "SELECT role, disabled_at FROM creature_accounts WHERE user_id=?",
                (actor_user_id,),
            ).fetchone()
            if actor is None or actor["disabled_at"] is not None:
                raise PermissionError("account unavailable")
            if actor["role"] != "owner" and actor_user_id != target_user_id:
                raise PermissionError("cannot revoke another account's sessions")
            cursor = db.execute(
                """UPDATE creature_sessions SET revoked_at=?
                   WHERE user_id=? AND revoked_at IS NULL""",
                (self._now(), target_user_id),
            )
            return cursor.rowcount

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self._path), timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    @staticmethod
    def _email(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("valid email required")
        normalized = value.strip().casefold()
        if len(normalized) > 254 or not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("valid email required")
        return normalized

    @staticmethod
    def _display_name(value: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
            raise ValueError("display_name must contain 1-80 characters")
        return value.strip()

    @staticmethod
    def _password_hash(password: str) -> tuple[bytes, bytes]:
        if not isinstance(password, str) or not 12 <= len(password) <= 1024:
            raise ValueError("password must contain 12-1024 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt,
            n=2**14, r=8, p=1, dklen=64,
        )
        return salt, digest

    @staticmethod
    def _verify_password(password: str, salt: bytes, expected: bytes) -> bool:
        try:
            actual = hashlib.scrypt(
                password.encode("utf-8"), salt=salt,
                n=2**14, r=8, p=1, dklen=64,
            )
        except (ValueError, MemoryError):
            return False
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _account(row: Any) -> Account:
        return Account(
            user_id=row["user_id"],
            email=row["email"],
            display_name=row["display_name"],
            role=row["role"],
            created_at=row["created_at"],
        )
