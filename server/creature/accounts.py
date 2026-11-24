"""Invitation-only account, invitation and opaque session persistence.

This is a domain persistence layer, not an HTTP authentication server. The
hosting application must add TLS, CSRF protection, rate limiting, secure
cookies, email verification/recovery and per-user authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager
from uuid import uuid4


_PASSWORD_ITERATIONS = 600_000
_PASSWORD_MIN_LENGTH = 12
_PASSWORD_MAX_LENGTH = 1_024
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TOKEN_BYTES = 32


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValueError("email must be a string")
    value = email.strip().casefold()
    if len(value) > 254 or not _EMAIL_RE.fullmatch(value):
        raise ValueError("email address is invalid")
    return value


@dataclass(frozen=True, slots=True)
class Account:
    account_id: str
    email: str
    role: str
    status: str
    created_at: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    account: Account
    session_id: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    invitation_id: str
    token: str
    expires_at: str
    max_uses: int


class PasswordHasher:
    """PBKDF2-HMAC-SHA256 password hashing using only the Python standard library."""

    @staticmethod
    def hash_password(password: str) -> tuple[str, str, int]:
        if not isinstance(password, str) or not _PASSWORD_MIN_LENGTH <= len(password) <= _PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"password must contain {_PASSWORD_MIN_LENGTH}-{_PASSWORD_MAX_LENGTH} characters"
            )
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
        )
        return (
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
            _PASSWORD_ITERATIONS,
        )

    @staticmethod
    def verify(password: str, salt_b64: str, digest_b64: str, iterations: int) -> bool:
        if not isinstance(password, str) or len(password) > _PASSWORD_MAX_LENGTH:
            return False
        if isinstance(iterations, bool) or not isinstance(iterations, int) or not 100_000 <= iterations <= 2_000_000:
            return False
        try:
            salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        except (ValueError, UnicodeError):
            return False
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)


class AccountStore:
    """SQLite-backed invitation-only accounts and hashed opaque sessions.

    Each operation opens its own connection and uses BEGIN IMMEDIATE for writes.
    The caller must provide a local durable path, protect backups and keep this
    database outside any public/static web directory.
    """

    def __init__(self, database_path: str | Path, *, session_lifetime: timedelta = timedelta(days=7)) -> None:
        if not isinstance(session_lifetime, timedelta) or not timedelta(minutes=5) <= session_lifetime <= timedelta(days=30):
            raise ValueError("session_lifetime must be between 5 minutes and 30 days")
        self.database_path = Path(database_path).expanduser().resolve()
        self.session_lifetime = session_lifetime
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            str(self.database_path), timeout=10, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _account(row: sqlite3.Row) -> Account:
        return Account(
            account_id=row["account_id"],
            email=row["email"],
            role=row["role"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def _initialize(self) -> None:
        with self._connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS creature_accounts (
                    account_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_iterations INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
                    status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS creature_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    token_sha256 TEXT NOT NULL UNIQUE,
                    created_by TEXT NOT NULL REFERENCES creature_accounts(account_id),
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    max_uses INTEGER NOT NULL CHECK (max_uses BETWEEN 1 AND 100),
                    uses INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
                    revoked_at TEXT
                );
                CREATE TABLE IF NOT EXISTS creature_sessions (
                    session_id TEXT PRIMARY KEY,
                    token_sha256 TEXT NOT NULL UNIQUE,
                    account_id TEXT NOT NULL REFERENCES creature_accounts(account_id),
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_creature_sessions_account
                    ON creature_sessions(account_id);
                CREATE INDEX IF NOT EXISTS idx_creature_invitations_owner
                    ON creature_invitations(created_by);
                """
            )
        # Best-effort restrictive mode on POSIX. Production deployments should
        # additionally enforce ownership/ACLs at the host and backup layers.
        try:
            self.database_path.chmod(0o600)
        except OSError:
            pass

    def bootstrap_owner(
        self, email: str, password: str, *, bootstrap_enabled: bool = False
    ) -> Account:
        """Create the first owner only; intended for a one-time trusted CLI setup."""
        if bootstrap_enabled is not True:
            raise PermissionError("owner bootstrap is disabled")
        normalized = normalize_email(email)
        salt, digest, iterations = PasswordHasher.hash_password(password)
        now = _iso(_now())
        account_id = str(uuid4())
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM creature_accounts LIMIT 1").fetchone():
                db.rollback()
                raise PermissionError("owner bootstrap is already closed")
            db.execute(
                """INSERT INTO creature_accounts
                   (account_id,email,password_salt,password_hash,password_iterations,role,status,created_at)
                   VALUES (?,?,?,?,?,'owner','active',?)""",
                (account_id, normalized, salt, digest, iterations, now),
            )
            db.commit()
            row = db.execute(
                "SELECT * FROM creature_accounts WHERE account_id=?", (account_id,)
            ).fetchone()
        return self._account(row)

    def issue_invitation(
        self,
        owner_id: str,
        *,
        lifetime: timedelta = timedelta(days=7),
        max_uses: int = 1,
    ) -> IssuedInvitation:
        if not isinstance(lifetime, timedelta) or not timedelta(minutes=5) <= lifetime <= timedelta(days=30):
            raise ValueError("invitation lifetime must be between 5 minutes and 30 days")
        if isinstance(max_uses, bool) or not isinstance(max_uses, int) or not 1 <= max_uses <= 100:
            raise ValueError("max_uses must be between 1 and 100")
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        now = _now()
        invitation_id = str(uuid4())
        expires = now + lifetime
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            owner = db.execute(
                "SELECT role,status FROM creature_accounts WHERE account_id=?",
                (owner_id,),
            ).fetchone()
            if owner is None or owner["role"] != "owner" or owner["status"] != "active":
                db.rollback()
                raise PermissionError("active owner account required")
            db.execute(
                """INSERT INTO creature_invitations
                   (invitation_id,token_sha256,created_by,created_at,expires_at,max_uses)
                   VALUES (?,?,?,?,?,?)""",
                (
                    invitation_id,
                    hashlib.sha256(token.encode("utf-8")).hexdigest(),
                    owner_id,
                    _iso(now),
                    _iso(expires),
                    max_uses,
                ),
            )
            db.commit()
        return IssuedInvitation(invitation_id, token, _iso(expires), max_uses)

    def accept_invitation(self, token: str, email: str, password: str) -> Account:
        if not isinstance(token, str) or not 20 <= len(token) <= 200:
            raise PermissionError("invalid or unavailable invitation")
        normalized = normalize_email(email)
        salt, digest, iterations = PasswordHasher.hash_password(password)
        now = _now()
        account_id = str(uuid4())
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            invite = db.execute(
                """SELECT * FROM creature_invitations
                   WHERE token_sha256=? AND revoked_at IS NULL AND uses < max_uses""",
                (token_hash,),
            ).fetchone()
            if invite is None or now >= _parse_time(invite["expires_at"]):
                db.rollback()
                raise PermissionError("invalid or unavailable invitation")
            try:
                db.execute(
                    """INSERT INTO creature_accounts
                       (account_id,email,password_salt,password_hash,password_iterations,role,status,created_at)
                       VALUES (?,?,?,?,?,'member','active',?)""",
                    (account_id, normalized, salt, digest, iterations, _iso(now)),
                )
            except sqlite3.IntegrityError:
                db.rollback()
                raise ValueError("account could not be created") from None
            changed = db.execute(
                """UPDATE creature_invitations SET uses=uses+1
                   WHERE invitation_id=? AND revoked_at IS NULL AND uses < max_uses""",
                (invite["invitation_id"],),
            ).rowcount
            if changed != 1:
                db.rollback()
                raise PermissionError("invalid or unavailable invitation")
            db.commit()
            row = db.execute(
                "SELECT * FROM creature_accounts WHERE account_id=?", (account_id,)
            ).fetchone()
        return self._account(row)

    def revoke_invitation(self, owner_id: str, invitation_id: str) -> bool:
        now = _iso(_now())
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            owner = db.execute(
                "SELECT role,status FROM creature_accounts WHERE account_id=?",
                (owner_id,),
            ).fetchone()
            if owner is None or owner["role"] != "owner" or owner["status"] != "active":
                db.rollback()
                raise PermissionError("active owner account required")
            changed = db.execute(
                """UPDATE creature_invitations SET revoked_at=?
                   WHERE invitation_id=? AND created_by=? AND revoked_at IS NULL""",
                (now, invitation_id, owner_id),
            ).rowcount
            db.commit()
        return changed == 1

    def authenticate(self, email: str, password: str) -> Account:
        normalized = normalize_email(email)
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM creature_accounts WHERE email=?", (normalized,)
            ).fetchone()
        if row is None:
            # Perform a comparable PBKDF2 operation to reduce account enumeration
            # through large timing differences. API callers must still rate-limit.
            dummy_salt = base64.urlsafe_b64encode(b"0" * 16).decode("ascii")
            dummy_hash = base64.urlsafe_b64encode(b"0" * 32).decode("ascii")
            PasswordHasher.verify(password, dummy_salt, dummy_hash, _PASSWORD_ITERATIONS)
            raise PermissionError("email or password is incorrect")
        valid = PasswordHasher.verify(
            password,
            row["password_salt"],
            row["password_hash"],
            row["password_iterations"],
        )
        if not valid or row["status"] != "active":
            raise PermissionError("email or password is incorrect")
        return self._account(row)

    def create_session(self, account_id: str) -> tuple[str, AuthenticatedSession]:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        now = _now()
        expires = now + self.session_lifetime
        session_id = str(uuid4())
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            account = db.execute(
                "SELECT * FROM creature_accounts WHERE account_id=? AND status='active'",
                (account_id,),
            ).fetchone()
            if account is None:
                db.rollback()
                raise PermissionError("active account required")
            db.execute(
                """INSERT INTO creature_sessions
                   (session_id,token_sha256,account_id,created_at,expires_at)
                   VALUES (?,?,?,?,?)""",
                (
                    session_id,
                    hashlib.sha256(token.encode("utf-8")).hexdigest(),
                    account_id,
                    _iso(now),
                    _iso(expires),
                ),
            )
            db.commit()
        return token, AuthenticatedSession(
            self._account(account), session_id, _iso(expires)
        )

    def resolve_session(self, token: str) -> AuthenticatedSession:
        if not isinstance(token, str) or not 20 <= len(token) <= 200:
            raise PermissionError("session is invalid or expired")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = _now()
        with self._connection() as db:
            row = db.execute(
                """SELECT s.session_id,s.expires_at,a.*
                   FROM creature_sessions s
                   JOIN creature_accounts a ON a.account_id=s.account_id
                   WHERE s.token_sha256=? AND s.revoked_at IS NULL""",
                (token_hash,),
            ).fetchone()
        if (
            row is None
            or row["status"] != "active"
            or now >= _parse_time(row["expires_at"])
        ):
            raise PermissionError("session is invalid or expired")
        return AuthenticatedSession(
            self._account(row), row["session_id"], row["expires_at"]
        )

    def revoke_session(self, token: str) -> bool:
        if not isinstance(token, str) or not token:
            return False
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute(
                """UPDATE creature_sessions SET revoked_at=?
                   WHERE token_sha256=? AND revoked_at IS NULL""",
                (_iso(_now()), token_hash),
            ).rowcount
            db.commit()
        return changed == 1

    def revoke_all_sessions(self, owner_id: str, account_id: str) -> int:
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            owner = db.execute(
                "SELECT role,status FROM creature_accounts WHERE account_id=?",
                (owner_id,),
            ).fetchone()
            if owner is None or owner["role"] != "owner" or owner["status"] != "active":
                db.rollback()
                raise PermissionError("active owner account required")
            changed = db.execute(
                """UPDATE creature_sessions SET revoked_at=?
                   WHERE account_id=? AND revoked_at IS NULL""",
                (_iso(_now()), account_id),
            ).rowcount
            db.commit()
        return changed
