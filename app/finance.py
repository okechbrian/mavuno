"""Yield Priorities (Trade Priorities) for Mavuno Protocol.

Handles YPS-based allocation of tradeable harvest volume.
Refactored for SQLAlchemy 2.0 and FarmerProfile schema.
"""
from __future__ import annotations
import time
import secrets
from sqlalchemy import select, update, text
from sqlalchemy.orm import Session
from .security import sign_token
from . import ledger
from .models import YieldPriority, FarmerProfile

def issue(db: Session, farm_id: str, yps: int, kg: int) -> dict:
    """Issues a new Yield Priority to a farmer."""
    # Check for active priorities
    existing = db.execute(
        select(YieldPriority).where(YieldPriority.farm_id == farm_id, YieldPriority.status == 'active')
    ).first()
    if existing:
        return {"error": "active_priority_exists"}
        
    f = db.execute(
        select(FarmerProfile).where(FarmerProfile.user_id == farm_id)
    ).scalar_one_or_none()
    if not f: 
        return {"error": "unknown_farm"}
    
    priority_id = f"YPS-{secrets.token_hex(4).upper()}"
    sig = sign_token(priority_id, farm_id, kg)
    ts = int(time.time())
    expires = ts + (72 * 3600)
    
    new_p = YieldPriority(
        id=priority_id, 
        farm_id=farm_id, 
        yps=yps, 
        kg_allocated=kg, 
        kg_remaining=kg, 
        aggregation_point=f.collection_hub or "Main Hub", 
        created_at=ts, 
        expires_at=expires, 
        signature=sig
    )
    db.add(new_p)
    db.commit()
    
    ledger.write("PRIORITY_ISSUE", {"priority_id": priority_id, "farm_id": farm_id, "kg": kg})
    return {"priority_id": priority_id, "kg": kg, "hub": f.collection_hub or "Main Hub", "expires_at": expires}

def farm_balance(db: Session, farm_id: str) -> dict:
    """Returns the total remaining KG across all active priorities."""
    rows = db.execute(
        select(YieldPriority).where(YieldPriority.farm_id == farm_id, YieldPriority.status == 'active')
    ).scalars().all()
    
    priorities = []
    for p in rows:
        priorities.append({
            "id": p.id,
            "kg_allocated": p.kg_allocated,
            "kg_remaining": p.kg_remaining,
            "status": p.status,
            "created_at": p.created_at,
            "expires_at": p.expires_at
        })
        
    return {
        "active_priorities": len(priorities), 
        "kg_remaining": sum(p['kg_remaining'] for p in priorities), 
        "priorities": priorities
    }

def redeem(db: Session, priority_id: str, lat: float, lng: float, kg: int) -> dict:
    """Redeems a portion of a Yield Priority (typically at a collection hub)."""
    p = db.execute(
        select(YieldPriority).where(YieldPriority.id == priority_id)
    ).scalar_one_or_none()
    
    if not p: return {"error": "invalid_priority"}
    if p.status != 'active': return {"error": "invalid_priority"}
    
    new_bal = max(0, p.kg_remaining - kg)
    p.kg_remaining = new_bal
    if new_bal == 0:
        p.status = 'redeemed'
    
    db.commit()
    
    ledger.write("PRIORITY_REDEEM", {"priority_id": priority_id, "kg": kg, "remaining": new_bal})
    return {"priority_id": priority_id, "remaining": new_bal, "status": p.status}
