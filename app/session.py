"""Signed cookie sessions for Mavuno.

Format: base64url(role|subject|exp_unix) + "." + base64url(hmac_sha256(payload))
- Stateless, no DB lookup per request.
- Cookies are HttpOnly + SameSite=Lax. Secure flag is set when not on localhost.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os
import time
from typing import Optional

from fastapi import Cookie, HTTPException, Request, Response, status

from .config import HMAC_SECRET, PUBLIC_BASE_URL

COOKIE_NAME = "mavuno_session"
SESSION_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_VALID_ROLES = {"farmer", "buyer", "agent"}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign(payload: bytes) -> str:
    return _b64url(hmac.new(HMAC_SECRET, payload, hashlib.sha256).digest())


def issue(response: Response, role: str, subject: str) -> str:
    """Set a fresh session cookie on the response and return the encoded value."""
    if role not in _VALID_ROLES:
        raise ValueError("invalid_role")
    exp = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{role}|{subject}|{exp}".encode("utf-8")
    token = f"{_b64url(payload)}.{_sign(payload)}"
    is_https = PUBLIC_BASE_URL.startswith("https://") or os.getenv("VERCEL") is not None
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=is_https,
        samesite="lax",
        path="/",
    )
    return token


def clear(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _decode(token: str) -> Optional[dict]:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        return None
    payload = _b64url_decode(payload_b64)
    expected = _sign(payload)
    if not hmac.compare_digest(expected, sig_b64):
        return None
    try:
        role, subject, exp_str = payload.decode("utf-8").split("|", 2)
        exp = int(exp_str)
    except (ValueError, UnicodeDecodeError):
        return None
    if exp < int(time.time()):
        return None
    if role not in _VALID_ROLES:
        return None
    return {"role": role, "subject": subject, "exp": exp}


def current_user(request: Request) -> Optional[dict]:
    """Return the decoded session dict, or None. Never raises."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return _decode(token)


def require_user(*allowed_roles: str):
    """Dependency factory. Raises 401 if not signed in or role not allowed."""
    allowed = set(allowed_roles) if allowed_roles else _VALID_ROLES

    def _dep(request: Request) -> dict:
        user = current_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="not_signed_in",
            )
        if user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="role_not_allowed",
            )
        return user

    return _dep


def require_owner_or_agent(role: str, subject: str, user: dict) -> None:
    """Authorise resource access: agents can see anything; others only their own."""
    if user["role"] == "agent":
        return
    if user["role"] != role or user["subject"] != subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not_resource_owner",
        )
