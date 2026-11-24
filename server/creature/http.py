"""Host-mountable FastAPI routes for WEB CREATURE private accounts.

The router deliberately requires exact trusted origins and a host-supplied
rate limiter. It does not create an application, configure CORS, bootstrap an
owner, or enable any computer-control capability.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .accounts import Account, AccountStore, AuthenticatedSession


RateLimiter = Callable[[Request, str, str], None]
_COOKIE_NAME = "__Host-wc_session"
_COOKIE_NAME_INSECURE_DEV = "wc_session"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invitation_token: str = Field(min_length=20, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class InvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lifetime_seconds: int = Field(default=604800, ge=300, le=2_592_000)
    max_uses: int = Field(default=1, ge=1, le=100)


class RevokeInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invitation_id: str = Field(min_length=36, max_length=36)


def _validate_origin(origin: str) -> str:
    if not isinstance(origin, str):
        raise ValueError("trusted origins must be strings")
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or origin.endswith("/")
    ):
        raise ValueError("each trusted origin must be an exact scheme://host[:port] origin")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("non-local trusted origins must use HTTPS")
    return origin


def _public_account(account: Account) -> dict[str, str]:
    return {
        "account_id": account.account_id,
        "email": account.email,
        "role": account.role,
        "status": account.status,
        "created_at": account.created_at,
    }


def create_auth_router(
    store: AccountStore,
    *,
    trusted_origins: Iterable[str],
    rate_limiter: RateLimiter,
    cookie_secure: bool = True,
) -> APIRouter:
    """Build a router only when trusted origins and host rate limiting are supplied.

    The host must mount this router under HTTPS, avoid permissive CORS, protect
    the SQLite database, and implement email verification/recovery separately.
    """
    if not isinstance(store, AccountStore):
        raise TypeError("store must be an AccountStore")
    if not callable(rate_limiter):
        raise TypeError("a host-provided rate_limiter callback is required")
    if not isinstance(cookie_secure, bool):
        raise ValueError("cookie_secure must be a boolean")
    origins = frozenset(_validate_origin(value) for value in trusted_origins)
    if not origins:
        raise ValueError("at least one exact trusted origin is required")
    if not cookie_secure and any(
        urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1"}
        for origin in origins
    ):
        raise ValueError("insecure cookies are permitted only for local development origins")

    cookie_name = _COOKIE_NAME if cookie_secure else _COOKIE_NAME_INSECURE_DEV
    router = APIRouter(prefix="/api/creature/auth", tags=["WEB CREATURE authentication"])

    def require_browser_request(request: Request, action: str, subject: str) -> None:
        origin = request.headers.get("origin")
        if origin not in origins:
            raise HTTPException(status_code=403, detail="request origin is not allowed")
        if request.headers.get("x-web-creature-request") != "1":
            raise HTTPException(status_code=403, detail="required request header is missing")
        try:
            rate_limiter(request, action, subject)
        except HTTPException:
            raise
        except Exception:
            # Fail closed if the host's rate limiter is unavailable.
            raise HTTPException(status_code=503, detail="request protection is unavailable") from None

    def current_session(request: Request) -> AuthenticatedSession:
        token = request.cookies.get(cookie_name)
        if not token:
            raise HTTPException(status_code=401, detail="authentication required")
        try:
            return store.resolve_session(token)
        except PermissionError:
            raise HTTPException(status_code=401, detail="authentication required") from None

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            key=cookie_name,
            value=token,
            max_age=int(store.session_lifetime.total_seconds()),
            httponly=True,
            secure=cookie_secure,
            samesite="strict",
            path="/",
        )

    def clear_session_cookie(response: Response) -> None:
        response.delete_cookie(
            key=cookie_name,
            path="/",
            secure=cookie_secure,
            httponly=True,
            samesite="strict",
        )

    @router.post("/register", status_code=status.HTTP_201_CREATED)
    def register(payload: RegisterRequest, request: Request, response: Response):
        require_browser_request(request, "register", payload.email.casefold())
        try:
            account = store.accept_invitation(
                payload.invitation_token, payload.email, payload.password
            )
            token, _ = store.create_session(account.account_id)
        except PermissionError:
            raise HTTPException(status_code=400, detail="invitation is invalid or unavailable") from None
        except ValueError:
            raise HTTPException(status_code=400, detail="account could not be created") from None
        set_session_cookie(response, token)
        return {"account": _public_account(account)}

    @router.post("/login")
    def login(payload: LoginRequest, request: Request, response: Response):
        require_browser_request(request, "login", payload.email.casefold())
        try:
            account = store.authenticate(payload.email, payload.password)
            token, _ = store.create_session(account.account_id)
        except (PermissionError, ValueError):
            raise HTTPException(status_code=401, detail="email or password is incorrect") from None
        set_session_cookie(response, token)
        return {"account": _public_account(account)}

    @router.post("/logout")
    def logout(request: Request, response: Response):
        require_browser_request(request, "logout", "current-session")
        token = request.cookies.get(cookie_name)
        if token:
            store.revoke_session(token)
        clear_session_cookie(response)
        return {"ok": True}

    @router.get("/me")
    def me(request: Request):
        session = current_session(request)
        return {"account": _public_account(session.account), "session_expires_at": session.expires_at}

    @router.post("/invitations", status_code=status.HTTP_201_CREATED)
    def create_invitation(payload: InvitationRequest, request: Request):
        session = current_session(request)
        require_browser_request(request, "invitation.create", session.account.account_id)
        try:
            invite = store.issue_invitation(
                session.account.account_id,
                lifetime=timedelta(seconds=payload.lifetime_seconds),
                max_uses=payload.max_uses,
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="owner permission required") from None
        return {
            "invitation_id": invite.invitation_id,
            "token": invite.token,
            "expires_at": invite.expires_at,
            "max_uses": invite.max_uses,
            "notice": "Copy this token now; it is not stored in plaintext and cannot be retrieved later.",
        }

    @router.post("/invitations/revoke")
    def revoke_invitation(payload: RevokeInvitationRequest, request: Request):
        session = current_session(request)
        require_browser_request(request, "invitation.revoke", session.account.account_id)
        try:
            revoked = store.revoke_invitation(
                session.account.account_id, payload.invitation_id
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="owner permission required") from None
        if not revoked:
            raise HTTPException(status_code=404, detail="invitation not found")
        return {"revoked": True}

    return router
