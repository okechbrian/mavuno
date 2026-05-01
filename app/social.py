"""Mavuno Social — public feed posts, reactions, and flag-and-hide moderation.

Refactored to use SQLAlchemy 2.0 and Pydantic.
"""
from __future__ import annotations
import json
import secrets
import time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func

from . import crp, database, ledger, scorer
from .models import Post, Reaction, PostFlag, FarmerProfile

BODY_MAX = 300
ALLOWED_EMOJI = {"\U0001f331", "\U0001f525", "❤️", "\U0001f44f", "❤"}

from .config import DATA_DIR
_BANNED_PATH = DATA_DIR / "banned_words.json"
try:
    _BANNED_WORDS = [
        w.lower() for w in json.loads(_BANNED_PATH.read_text()).get("banned", []) if w
    ]
except (FileNotFoundError, json.JSONDecodeError):
    _BANNED_WORDS = []

def _new_post_id() -> str:
    return "P-" + secrets.token_hex(3).upper()

def _contains_banned(text: str) -> bool:
    t = text.lower()
    return any(b in t for b in _BANNED_WORDS)

def create_post(db: Session, farm_id: str, body: str, photo_url: Optional[str] = None, is_verified: bool = False) -> dict:
    body = (body or "").strip()
    if not body: return {"error": "empty_body"}
    if len(body) > BODY_MAX: return {"error": "body_too_long"}
    if _contains_banned(body): return {"error": "banned_word"}

    if not db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).first():
        return {"error": "unknown_farm"}

    safe_body = crp._redact_pii(body)
    pid = _new_post_id()
    now = int(time.time())
    
    post = Post(
        id=pid, farm_id=farm_id, body=safe_body, photo_url=photo_url,
        is_verified=is_verified, created_at=now, hidden=False
    )
    db.add(post)
    db.commit()

    ledger.write("POST_CREATED", {"post_id": pid, "farm_id": farm_id})
    if is_verified:
        ledger.write("VERIFIED_HARVEST", {"post_id": pid, "farm_id": farm_id, "timestamp": now})

    return _obj_to_dict(post)

def feed(db: Session, limit: int = 50, district: Optional[str] = None) -> list[dict]:
    stmt = select(Post).where(Post.hidden == False).order_by(Post.created_at.desc()).limit(limit)
    if district:
        stmt = stmt.join(FarmerProfile).where(FarmerProfile.district == district)
    
    rows = db.execute(stmt).scalars().all()
    return [_hydrate(db, r) for r in rows]

def get_post(db: Session, post_id: str) -> Optional[dict]:
    p = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    return _hydrate(db, p) if p else None

def react(db: Session, post_id: str, reactor_role: str, reactor_id: str, emoji: str) -> dict:
    if emoji not in ALLOWED_EMOJI: return {"error": "invalid_emoji"}

    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if not post: return {"error": "unknown_post"}
    if post.hidden: return {"error": "post_hidden"}

    existing = db.execute(select(Reaction).where(
        Reaction.post_id == post_id, Reaction.user_id == reactor_id, Reaction.emoji == emoji
    )).first()
    
    if not existing:
        reaction = Reaction(post_id=post_id, user_id=reactor_id, emoji=emoji)
        db.add(reaction)
        db.commit()
        ledger.write("POST_REACTED", {
            "post_id": post_id, "reactor_role": reactor_role,
            "reactor_id": reactor_id, "emoji": emoji,
        })
    return {"ok": True, "post_id": post_id, "emoji": emoji}

def flag(db: Session, post_id: str, flagger_role: str, flagger_id: str, reason: Optional[str] = None) -> dict:
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if not post: return {"error": "unknown_post"}

    existing = db.execute(select(PostFlag).where(PostFlag.post_id == post_id, PostFlag.user_id == flagger_id)).first()
    if not existing:
        pf = PostFlag(post_id=post_id, user_id=flagger_id, reason=reason)
        db.add(pf)
        post.hidden = True
        db.commit()
        ledger.write("POST_FLAGGED", {
            "post_id": post_id, "flagger_role": flagger_role, "flagger_id": flagger_id,
        })
    return {"ok": True, "post_id": post_id, "hidden": True}

def _hydrate(db: Session, post: Post) -> dict:
    d = _obj_to_dict(post)
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == post.farm_id)).scalar_one_or_none()
    d["farmer_name"] = f.farmer_name if f else post.farm_id
    d["district"] = f.district if f else ""
    d["crop"] = f.crop if f else ""
    
    try:
        d["yps"] = scorer.score_farm(post.farm_id).get("yps")
    except: d["yps"] = None

    counts = db.execute(
        select(Reaction.emoji, func.count(Reaction.emoji)).where(Reaction.post_id == post.id).group_by(Reaction.emoji)
    ).all()
    d["reactions"] = {r[0]: r[1] for r in counts}
    return d

def _obj_to_dict(obj: Post) -> dict:
    return {
        "id": obj.id, "farm_id": obj.farm_id, "body": obj.body,
        "photo_url": obj.photo_url, "is_verified": obj.is_verified,
        "created_at": obj.created_at, "hidden": obj.hidden
    }
