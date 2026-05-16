"""Yield Priorities for Prototype."""
import time
import secrets
from .security import sign_token
from . import ledger

def issue(farm_id: str, yps: int, kg: int):
    from sqlalchemy import text
    from .database import SessionLocal
    with SessionLocal() as db:
        # Check for active priorities
        active = db.execute(text("SELECT id FROM yield_priorities WHERE farm_id = :farm_id AND status = 'active'"), {"farm_id": farm_id}).fetchone()
        if active:
            return {"error": "active_priority_exists"}
            
        f = db.execute(text("SELECT collection_hub FROM farms WHERE id = :id"), {"id": farm_id}).fetchone()
        if not f: 
            return {"error": "unknown_farm"}
        f_dict = dict(f._mapping)
        
        priority_id = f"YPS-{secrets.token_hex(4).upper()}"
        sig = sign_token(priority_id, farm_id, kg)
        ts = int(time.time())
        expires = ts + (72 * 3600)
        
        db.execute(text('''INSERT INTO yield_priorities (id, farm_id, yps, kg_allocated, kg_remaining, aggregation_point, created_at, expires_at, signature) VALUES (:id, :farm_id, :yps, :kg_allocated, :kg_remaining, :aggregation_point, :created_at, :expires_at, :signature)'''),
                   {"id": priority_id, "farm_id": farm_id, "yps": yps, "kg_allocated": kg, "kg_remaining": kg, "aggregation_point": f_dict['collection_hub'], "created_at": ts, "expires_at": expires, "signature": sig})
        db.commit()
    
    ledger.write("PRIORITY_ISSUE", {"priority_id": priority_id, "farm_id": farm_id, "kg": kg})
    return {"priority_id": priority_id, "kg": kg, "hub": f_dict['collection_hub'], "expires_at": expires}

def farm_balance(farm_id: str):
    from sqlalchemy import text
    from .database import SessionLocal
    with SessionLocal() as db:
        rows = db.execute(text("SELECT * FROM yield_priorities WHERE farm_id = :farm_id AND status = 'active'"), {"farm_id": farm_id}).fetchall()
    priorities = [dict(r._mapping) for r in rows]
    return {
        "active_priorities": len(priorities), 
        "kg_remaining": sum(p['kg_remaining'] for p in priorities), 
        "priorities": priorities
    }

def redeem(priority_id: str, lat: float, lng: float, kg: int):
    from sqlalchemy import text
    from .database import SessionLocal
    with SessionLocal() as db:
        p = db.execute(text("SELECT * FROM yield_priorities WHERE id = :id"), {"id": priority_id}).fetchone()
        if not p: return {"error": "invalid_priority"}
        p_dict = dict(p._mapping)
        if p_dict['status'] != 'active': return {"error": "invalid_priority"}
        
        new_bal = max(0, p_dict['kg_remaining'] - kg)
        status = 'redeemed' if new_bal == 0 else 'active'
        db.execute(text("UPDATE yield_priorities SET kg_remaining = :kg_remaining, status = :status WHERE id = :id"), 
                   {"kg_remaining": new_bal, "status": status, "id": priority_id})
        db.commit()
    
    ledger.write("PRIORITY_REDEEM", {"priority_id": priority_id, "kg": kg, "remaining": new_bal})
    return {"priority_id": priority_id, "remaining": new_bal, "status": status}
