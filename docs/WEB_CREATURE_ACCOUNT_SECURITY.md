# WEB CREATURE — Private Account System

**Scope:** Alpha 0.6 account and invitation persistence foundation  
**Product access:** Private, invitation-only  
**Storage:** Dedicated SQLite database supplied by the trusted host

## Implemented domain capabilities

- One-time first-owner bootstrap, disabled unless the trusted setup caller explicitly enables it.
- Email normalization and uniqueness.
- Password hashing with PBKDF2-HMAC-SHA256, random 128-bit salts and 600,000 iterations.
- Owner-issued invitation tokens generated from 256 bits of randomness.
- Only SHA-256 invitation token hashes are persisted.
- Invitation expiry, revocation, usage limits and atomic single-use consumption.
- Registration and invitation consumption occur in one SQLite write transaction.
- Member accounts cannot issue or revoke invitations.
- Opaque 256-bit session tokens; only token hashes are stored.
- Session expiry, individual revocation and owner-controlled account-wide session revocation.
- SQLite foreign keys, busy timeout, WAL mode and best-effort restrictive database file permissions.

## First-owner bootstrap

`AccountStore.bootstrap_owner(..., bootstrap_enabled=True)` is a domain-level one-time setup primitive. It is not an HTTP endpoint and must never be exposed to unauthenticated web requests.

The repository provides `scripts/web_creature_bootstrap_owner.py`. Run it only from a trusted local/administrative setup context:

```bash
python scripts/web_creature_bootstrap_owner.py --enable-bootstrap --database /secure/path/creature-auth.sqlite3
```

The command requires an explicit flag and an interactive confirmation, obtains the password through a hidden prompt, refuses to create a second owner, and does not accept passwords as command-line arguments or environment variables. It must be run against a database path outside public/static directories.

No default owner, password, invitation or secret is committed to the repository.

## Required host/API controls — not yet implemented

This module does **not** provide a production web authentication service. Before public deployment, the host must implement and test:

- HTTPS-only deployment and trusted proxy configuration;
- secure, HttpOnly, SameSite cookies; cookie-based sessions must include CSRF protection;
- login, registration and invitation endpoints with strict request schemas;
- per-IP and per-account rate limits, login backoff and abuse monitoring;
- email verification, password reset and account recovery;
- session rotation after login/privilege changes and logout-all;
- per-user authorization on every account, conversation, memory and device resource;
- invitation delivery through a verified channel; raw invite token is shown only once;
- secret-safe logs, database backup protection, retention and incident recovery;
- production database location outside public/static directories;
- security review and integration tests before enabling remote access.

The host must never trust an account ID supplied by the browser as the authenticated identity. Resolve the account from the server-validated session token.

## Boundaries

- No public self-registration.
- No shared accounts or implicit access to another user's data.
- Invitations grant membership only; they do not pair or authorize a Windows Desktop Agent.
- Session tokens and invitation tokens are bearer secrets and must not appear in logs, analytics, URLs after initial delivery, or client-side persistent storage.
- WEB CREATURE remains an independent project. This account store has no dependency on ApoloniaAI or the Apokolips website.
