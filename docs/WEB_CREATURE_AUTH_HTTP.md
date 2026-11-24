# WEB CREATURE — Private Authentication HTTP Adapter

This module provides a host-mountable FastAPI router at:

`/api/creature/auth`

It is intentionally a router factory, not a standalone public server. The host must mount it inside the independent WEB CREATURE application and supply exact trusted origins plus a production rate-limiter callback.

## Routes

| Method | Path | Purpose |
|---|---|---|
| POST | `/register` | Accept a valid invitation, create a member account and issue a session cookie |
| POST | `/login` | Verify credentials and issue a session cookie |
| POST | `/logout` | Revoke the current session and clear its cookie |
| GET | `/me` | Resolve the authenticated account from the session cookie |
| POST | `/invitations` | Owner-only invitation creation; raw token returned once |
| POST | `/invitations/revoke` | Owner-only invitation revocation |

There is deliberately no HTTP owner-bootstrap route and no public self-registration route.

## Required host configuration

Create the router explicitly:

```python
router = create_auth_router(
    account_store,
    trusted_origins={"https://your-private-web-creature-origin.example"},
    rate_limiter=host_rate_limiter,
    cookie_secure=True,
)
app.include_router(router)
```

The example origin is a placeholder, not a configured deployment URL.

- `trusted_origins` must contain exact origins only; wildcards and paths are rejected.
- Non-local origins must use HTTPS.
- `rate_limiter(request, action, subject)` is mandatory. It must enforce limits using both the trusted client IP (after correctly configured proxy handling) and the account/email/operation subject. If the limiter fails, the router fails closed with HTTP 503.
- Production session cookies use the `__Host-wc_session` prefix, Secure, HttpOnly, SameSite=Strict, Path=/ and no Domain attribute.
- Local development may explicitly set `cookie_secure=False`, but only with localhost origins.
- Every mutating browser request must include its exact allowed `Origin` and `X-Web-Creature-Request: 1`. Keep CORS disabled unless a separately reviewed cross-origin design is required.
- GET `/me` authenticates from the HttpOnly cookie; browser code never reads the session token.
- Keep the SQLite database outside public/static directories.

## Still required before production

- Deploy behind HTTPS and configure trusted proxy handling.
- Implement and test a distributed rate limiter (for example, shared Redis or database-backed limits), not a per-process in-memory counter.
- Add email verification and secure account recovery/password reset.
- Add security headers, request/body size limits, logging redaction, monitoring and backup/restore tests.
- Add per-user authorization to every conversation, memory, device and task endpoint.
- Add a separately reviewed invitation delivery flow; never put raw invitation tokens in analytics or server logs.
- Add deployment-specific integration, abuse, concurrency and penetration tests.

This adapter does not connect an AI model, provide a conversation UI, pair a Windows Agent or authorize local computer control.
