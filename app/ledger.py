"""Audit Ledger for Mavuno Protocol.

Refactored to use SQLAlchemy 2.0.
"""
from __future__ import annotations
import json
import time
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import engine, get_session, SessionLocal
from .security import hash_payload, chain_hash
from .models import LedgerEntry

def write(entry_type: str, payload: dict):
    """Writes a new entry to the immutable ledger. 
    Synchronous and uses a standalone session for immediate persistence."""
    with SessionLocal() as db:
        # Get the latest entry to compute the next chain link
        last = db.execute(select(LedgerEntry).order_by(LedgerEntry.id.desc())).scalars().first()
        prev_h = last.curr_hash if last else "0" * 64
        
        p_hash = hash_payload(payload)
        curr_h = chain_hash(prev_h, p_hash)
        
        entry = LedgerEntry(
            prev_hash=prev_h,
            curr_hash=curr_h,
            type=entry_type,
            payload=json.dumps(payload),
            timestamp=int(time.time())
        )
        db.add(entry)
        db.commit()

def read_all(db: Session) -> list[dict]:
    rows = db.execute(select(LedgerEntry).order_by(LedgerEntry.id.asc())).scalars().all()
    return [{
        "id": r.id, "prev_hash": r.prev_hash, "hash": r.curr_hash,
        "type": r.type, "entry": json.loads(r.payload), "ts": r.timestamp
    } for r in rows]

def verify(db: Session) -> dict:
    """Cryptographically verifies the entire hash chain."""
    rows = db.execute(select(LedgerEntry).order_by(LedgerEntry.id.asc())).scalars().all()
    prev = "0" * 64
    for i, r in enumerate(rows):
        p_hash = hash_payload(json.loads(r.payload))
        if r.curr_hash != chain_hash(prev, p_hash):
            return {"ok": False, "bad_id": r.id, "error": "hash_mismatch"}
        prev = r.curr_hash
    return {"ok": True, "length": len(rows)}
