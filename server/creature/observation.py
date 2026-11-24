"""Policy-bound local and web observation primitives.

The module performs no I/O at import time. Network access is only possible through
an explicitly injected host transport that must pin DNS results and block private IPs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class LocalFilePolicy:
    allowed_roots: tuple[Path, ...]
    max_file_bytes: int = 1_000_000
    allowed_suffixes: tuple[str, ...] = (".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".py", ".html", ".xml")

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_roots, tuple) or not self.allowed_roots:
            raise ValueError("allowed_roots must be a non-empty tuple of paths")
        if isinstance(self.max_file_bytes, bool) or not isinstance(self.max_file_bytes, int) or not 1 <= self.max_file_bytes <= 10_000_000:
            raise ValueError("max_file_bytes must be between 1 and 10000000")
        if not self.allowed_suffixes or any(
            not isinstance(suffix, str) or not suffix.startswith(".") or suffix.lower() != suffix
            for suffix in self.allowed_suffixes
        ):
            raise ValueError("allowed_suffixes must contain lowercase extensions")
        for root in self.allowed_roots:
            if not isinstance(root, Path):
                raise TypeError("allowed_roots entries must be pathlib.Path values")


@dataclass(frozen=True, slots=True)
class LocalObservation:
    relative_path: str
    content: str
    content_hash: str
    size_bytes: int
    observed_at: str


class LocalFileObserver:
    """Reads explicitly approved text files; resolves symlinks before containment checks."""

    def __init__(self, policy: LocalFilePolicy) -> None:
        if not isinstance(policy, LocalFilePolicy):
            raise TypeError("policy must be a LocalFilePolicy")
        self.policy = policy

    def read_text(self, candidate: str | Path) -> LocalObservation:
        if not isinstance(candidate, (str, Path)) or not str(candidate).strip():
            raise ValueError("candidate must be a non-empty path")
        target = Path(candidate).expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError("observation target must be a regular file")
        root_match: Path | None = None
        for configured in self.policy.allowed_roots:
            root = configured.expanduser().resolve(strict=True)
            try:
                target.relative_to(root)
                root_match = root
                break
            except ValueError:
                continue
        if root_match is None:
            raise PermissionError("file is outside configured observation roots")
        if target.suffix.lower() not in self.policy.allowed_suffixes:
            raise PermissionError("file extension is not approved for text observation")
        size = target.stat().st_size
        if size > self.policy.max_file_bytes:
            raise ValueError("file exceeds configured observation size limit")
        raw = target.read_bytes()
        if len(raw) > self.policy.max_file_bytes:
            raise ValueError("file grew beyond configured observation size limit")
        content = raw.decode("utf-8", errors="strict")
        return LocalObservation(
            relative_path=target.relative_to(root_match).as_posix(),
            content=content,
            content_hash=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            observed_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True, slots=True)
class WebObservationPolicy:
    allowed_domains: frozenset[str]
    max_sources: int = 5
    max_response_bytes: int = 1_000_000
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_domains, frozenset) or not self.allowed_domains:
            raise ValueError("allowed_domains must be a non-empty frozenset")
        cleaned = set()
        for domain in self.allowed_domains:
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError("domains must be non-empty strings")
            value = domain.strip().lower().rstrip(".")
            if value.startswith("*."):
                value = value[2:]
            if "/" in value or ":" in value or "@" in value:
                raise ValueError("allowlist entries must be bare DNS hostnames")
            try:
                ipaddress.ip_address(value)
            except ValueError:
                pass
            else:
                raise ValueError("IP addresses are not valid allowlist entries")
            if "." not in value or len(value) > 253:
                raise ValueError("allowlist entries must be valid public DNS hostnames")
            cleaned.add(value)
        object.__setattr__(self, "allowed_domains", frozenset(cleaned))
        if isinstance(self.max_sources, bool) or not isinstance(self.max_sources, int) or not 1 <= self.max_sources <= 20:
            raise ValueError("max_sources must be between 1 and 20")
        if isinstance(self.max_response_bytes, bool) or not isinstance(self.max_response_bytes, int) or not 1 <= self.max_response_bytes <= 5_000_000:
            raise ValueError("max_response_bytes must be between 1 and 5000000")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not 0.1 <= self.timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0.1 and 30")

    def validate_url(self, value: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 2048:
            raise ValueError("URL must contain 1-2048 characters")
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() != "https":
            raise PermissionError("only HTTPS web observations are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise PermissionError("URLs containing credentials are not allowed")
        if parsed.port not in (None, 443):
            raise PermissionError("non-standard ports are not allowed")
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            raise ValueError("URL must contain a hostname")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise PermissionError("IP-literal destinations are not allowed")
        if not any(host == domain or host.endswith("." + domain) for domain in self.allowed_domains):
            raise PermissionError("destination host is not in the configured allowlist")
        return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """Response returned by a trusted host transport.

    The transport MUST disable automatic redirects, validate and pin DNS answers
    at connection time, reject loopback/private/link-local/reserved IPs, enforce
    TLS hostname validation, and cap bytes while streaming. The engine independently
    checks the reported redirect chain and final URL against the domain allowlist.
    """
    status_code: int
    final_url: str
    headers: Mapping[str, str]
    body: bytes
    redirect_chain: tuple[str, ...] = ()
