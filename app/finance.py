"""Yield Priorities for Prototype."""
import time
import secrets
from .database import get_db
from .security import sign_token
from . import ledger

def issue(farm_id: str, yps: int, kg: int):
    conn = get_db()
    cur = conn.cursor()
    
    # Check for active priorities
    cur.execute("SELECT id FROM yield_priorities WHERE farm_id = ? AND status = 'active'", (farm_id,))
    if cur.fetchone():
        conn.close()
        return {"error": "active_priority_exists"}
        
    cur.execute("SELECT collection_hub FROM farms WHERE id = ?", (farm_id,))
    f = cur.fetchone()
    if not f: 
        conn.close()
        return {"error": "unknown_farm"}
    
    priority_id = f"YPS-{secrets.token_hex(4).upper()}"
    sig = sign_token(priority_id, farm_id, kg)
    ts = int(time.time())
    expires = ts + (72 * 3600)
    
    cur.execute('INSERT INTO yield_priorities (id, farm_id, yps, kg_allocated, kg_remaining, aggregation_point, created_at, expires_at, signature) VALUES (?,?,?,?,?,?,?,?,?)',
               (priority_id, farm_id, yps, kg, kg, f['collection_hub'], ts, expires, sig))
    conn.commit()
    conn.close()
    ledger.write("PRIORITY_ISSUE", {"priority_id": priority_id, "farm_id": farm_id, "kg": kg})
    return {"priority_id": priority_id, "kg": kg, "hub": f['collection_hub'], "expires_at": expires}

def farm_balance(farm_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM yield_priorities WHERE farm_id = ? AND status = 'active'", (farm_id,))
    rows = cur.fetchall()
    conn.close()
    priorities = [dict(r) for r in rows]
    return {
        "active_priorities": len(priorities), 
        "kg_remaining": sum(p['kg_remaining'] for p in priorities), 
        "priorities": priorities
    }

def redeem(priority_id: str, lat: float, lng: float, kg: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM yield_priorities WHERE id = ?", (priority_id,))
    p = cur.fetchone()
    if not p or p['status'] != 'active': return {"error": "invalid_priority"}
    
    new_bal = max(0, p['kg_remaining'] - kg)
    status = 'redeemed' if new_bal == 0 else 'active'
    cur.execute("UPDATE yield_priorities SET kg_remaining = ?, status = ? WHERE id = ?", (new_bal, status, priority_id))
    conn.commit()
    conn.close()
    ledger.write("PRIORITY_REDEEM", {"priority_id": priority_id, "kg": kg, "remaining": new_bal})
    return {"priority_id": priority_id, "remaining": new_bal, "status": status}
