"""Stateless JWT-like sessions for Mavuno.

Format: header.payload.signature (standard JWT-inspired)
- stateless, signed with HMAC-SHA256.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os
import time
import json
from typing import Optional, List

from fastapi import Cookie, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import HMAC_SECRET, PUBLIC_BASE_URL

COOKIE_NAME = "mavuno_session"
SESSION_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_VALID_ROLES = {"farmer", "buyer", "agent", "logistics", "supervisor"}

bearer_scheme = HTTPBearer(auto_error=False)

def _b64url_encode(data: dict) -> str:
    j = json.dumps(data, separators=(',', ':')).encode("utf-8")
    return base64.urlsafe_b64encode(j).rstrip(b"=").decode("ascii")

def _b64url_decode(data: str) -> dict:
    pad = "=" * (-len(data) % 4)
    j = base64.urlsafe_b64decode(data + pad).decode("utf-8")
    return json.loads(j)

def _sign(header_b64: str, payload_b64: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(HMAC_SECRET, msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")

def create_token(role: str, subject: str) -> str:
    if role not in _VALID_ROLES:
        raise ValueError("invalid_role")
    
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + SESSION_TTL_SECONDS
    }
    
    h_b64 = _b64url_encode(header)
    p_b64 = _b64url_encode(payload)
    sig = _sign(h_b64, p_b64)
    
    return f"{h_b64}.{p_b64}.{sig}"

def decode_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        h_b64, p_b64, sig = parts
        expected_sig = _sign(h_b64, p_b64)
        if not hmac.compare_digest(expected_sig, sig):
            return None
        
        payload = _b64url_decode(p_b64)
        if payload.get("exp", 0) < time.time():
            return None
            
        return {
            "role": payload.get("role"),
            "subject": payload.get("sub"),
            "exp": payload.get("exp")
        }
    except Exception:
        return None

def issue_session(response: Response, role: str, subject: str) -> str:
    token = create_token(role, subject)
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

def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")

async def get_current_user(
    request: Request,
    token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[dict]:
    # Check Bearer header first
    if token:
        return decode_token(token.credentials)
    
    # Fallback to Cookie
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return decode_token(cookie_token)
        
    return None

def require_user(*allowed_roles: str):
    allowed = set(allowed_roles) if allowed_roles else _VALID_ROLES

    async def _dep(user: Optional[dict] = Depends(get_current_user)) -> dict:
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
    if user["role"] in ("agent", "supervisor"):
        return
    if user["role"] != role or user["subject"] != subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not_resource_owner",
        )
