"""Offer-scoped 1:1 messaging between buyers and farmers.

Mirrors the shape of `app/payments.py`: thin data-layer module, no FastAPI
coupling, all routes live in `app/main.py`. Persistence is SQLite through
`app.database.get_db()`. Every message body is PII-redacted at write time
using `crp._redact_pii`. Ledger events (`CHAT_OPEN`, `CHAT_MSG`) never carry
the body — only structural identifiers.
"""
from __future__ import annotations
import secrets
import time
from typing import Optional

from . import crp, database, ledger

BODY_MAX = 500


def _new_thread_id() -> str:
    return "TH-" + secrets.token_hex(3).upper()


def _new_message_id() -> str:
    return "MSG-" + secrets.token_hex(3).upper()


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, or_
from .database import engine, get_session
from .models import Conversation, Message, User, FarmerProfile, BuyerProfile, MarketOffer
from . import crp, ledger

BODY_MAX = 500

def open_thread(db: Session, buyer_id: str, farm_id: str, offer_id: Optional[str] = None) -> dict:
    """Get-or-create a thread. Idempotent on (farm_id, buyer_id, offer_id)."""
    # Validation
    if not db.execute(select(User).where(User.id == farm_id)).first():
        return {"error": "unknown_farm"}
    if not db.execute(select(User).where(User.id == buyer_id)).first():
        return {"error": "unknown_buyer"}
    if offer_id and not db.execute(select(MarketOffer).where(MarketOffer.id == offer_id)).first():
        return {"error": "unknown_offer"}

    # Lookup existing
    stmt = select(Conversation).where(Conversation.farm_id == farm_id, Conversation.buyer_id == buyer_id)
    if offer_id:
        stmt = stmt.where(Conversation.offer_id == offer_id)
    else:
        stmt = stmt.where(Conversation.offer_id == None)
    
    thread = db.execute(stmt).scalar_one_or_none()
    if thread:
        return _obj_to_dict(thread)

    tid = _new_thread_id()
    now = int(time.time())
    thread = Conversation(
        id=tid, farm_id=farm_id, buyer_id=buyer_id, offer_id=offer_id,
        created_at=now, last_msg_at=now
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    ledger.write("CHAT_OPEN", {
        "thread_id": tid, "farm_id": farm_id,
        "buyer_id": buyer_id, "offer_id": offer_id,
    })
    return _obj_to_dict(thread)

def get_thread(db: Session, thread_id: str) -> Optional[dict]:
    t = db.execute(select(Conversation).where(Conversation.id == thread_id)).scalar_one_or_none()
    return _obj_to_dict(t) if t else None

def send(db: Session, thread_id: str, sender_role: str, sender_id: str, body: str) -> dict:
    """Append a message to a thread. Body is PII-redacted before persist."""
    if sender_role not in ("farmer", "buyer", "agent"):
        return {"error": "invalid_role"}
    body = (body or "").strip()
    if not body: return {"error": "empty_body"}
    if len(body) > BODY_MAX: return {"error": "body_too_long"}

    thread = db.execute(select(Conversation).where(Conversation.id == thread_id)).scalar_one_or_none()
    if not thread:
        return {"error": "unknown_thread"}

    safe_body = crp._redact_pii(body)
    mid = _new_message_id()
    now = int(time.time())
    
    msg = Message(id=mid, conversation_id=thread_id, sender_id=sender_id, body=safe_body, created_at=now)
    db.add(msg)
    
    thread.last_msg_at = now
    db.commit()

    ledger.write("CHAT_MSG", {
        "thread_id": thread_id, "sender_role": sender_role,
        "sender_id": sender_id, "msg_id": mid,
    })
    return {"id": mid, "thread_id": thread_id, "sender_role": sender_role,
            "sender_id": sender_id, "body": safe_body, "created_at": now}

def messages(db: Session, thread_id: str, since_ts: int = 0, limit: int = 200) -> list[dict]:
    rows = db.execute(
        select(Message).where(Message.conversation_id == thread_id, Message.created_at > since_ts)
        .order_by(Message.created_at.asc()).limit(limit)
    ).scalars().all()
    return [{
        "id": m.id, "thread_id": m.conversation_id, "sender_id": m.sender_id,
        "body": m.body, "created_at": m.created_at
    } for m in rows]

def threads_for_farm(db: Session, farm_id: str, limit: int = 50) -> list[dict]:
    rows = db.execute(
        select(Conversation).where(Conversation.farm_id == farm_id)
        .order_by(Conversation.last_msg_at.desc()).limit(limit)
    ).scalars().all()
    return [_hydrate_preview(db, r) for r in rows]

def threads_for_buyer(db: Session, buyer_id: str, limit: int = 50) -> list[dict]:
    rows = db.execute(
        select(Conversation).where(Conversation.buyer_id == buyer_id)
        .order_by(Conversation.last_msg_at.desc()).limit(limit)
    ).scalars().all()
    return [_hydrate_preview(db, r) for r in rows]

def threads_for_agent(db: Session, limit: int = 200) -> list[dict]:
    rows = db.execute(
        select(Conversation).order_by(Conversation.last_msg_at.desc()).limit(limit)
    ).scalars().all()
    return [_hydrate_preview(db, r) for r in rows]

def _hydrate_preview(db: Session, thread: Conversation) -> dict:
    d = _obj_to_dict(thread)
    # Counterpart names
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == thread.farm_id)).scalar_one_or_none()
    d["farmer_name"] = f.farmer_name if f else thread.farm_id
    b = db.execute(select(BuyerProfile).where(BuyerProfile.user_id == thread.buyer_id)).scalar_one_or_none()
    d["buyer_name"] = b.name if b else thread.buyer_id
    
    # Last msg preview
    last = db.execute(
        select(Message).where(Message.conversation_id == thread.id).order_by(Message.created_at.desc()).limit(1)
    ).scalar_one_or_none()
    d["last_preview"] = last.body[:120] if last else ""
    return d

def _obj_to_dict(obj: Conversation) -> dict:
    return {
        "id": obj.id, "farm_id": obj.farm_id, "buyer_id": obj.buyer_id,
        "offer_id": obj.offer_id, "created_at": obj.created_at, "last_msg_at": obj.last_msg_at
    }

def unread_count(db: Session, role: str, subject_id: str) -> int:
    # Simplified for now: just return total message count if needed, 
    # or implement proper read cursors in models later.
    return 0 

def mark_read(db: Session, thread_id: str, role: str, subject_id: str) -> dict:
    return {"thread_id": thread_id, "ok": True}
