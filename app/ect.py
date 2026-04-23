"""Energy Credit Tokens for Prototype."""
import time
import secrets
from .database import get_db
from .security import sign_token
from . import ledger

def issue(farm_id: str, yps: int, kwh: int):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM tokens WHERE farm_id = ? AND status = 'active'", (farm_id,))
    if cur.fetchone():
        conn.close()
        return {"error": "active_token_exists"}
        
    cur.execute("SELECT pump_name FROM farms WHERE id = ?", (farm_id,))
    f = cur.fetchone()
    if not f: 
        conn.close()
        return {"error": "unknown_farm"}
    
    token_id = f"ECT-{secrets.token_hex(4).upper()}"
    sig = sign_token(token_id, farm_id, kwh)
    ts = int(time.time())
    expires = ts + (72 * 3600)
    
    cur.execute('INSERT INTO tokens (id, farm_id, yps, kwh_allocated, kwh_remaining, pump_node, created_at, expires_at, signature) VALUES (?,?,?,?,?,?,?,?,?)',
               (token_id, farm_id, yps, kwh, kwh, f['pump_name'], ts, expires, sig))
    conn.commit()
    conn.close()
    ledger.write("ECT_ISSUE", {"token_id": token_id, "farm_id": farm_id, "kwh": kwh})
    return {"token_id": token_id, "kwh": kwh, "pump": f['pump_name'], "expires_at": expires}

def farm_balance(farm_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tokens WHERE farm_id = ? AND status = 'active'", (farm_id,))
    rows = cur.fetchall()
    conn.close()
    tokens = [dict(r) for r in rows]
    return {"active_tokens": len(tokens), "kwh_remaining": sum(t['kwh_remaining'] for t in tokens), "tokens": tokens}

def redeem(token_id: str, lat: float, lng: float, kwh: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tokens WHERE id = ?", (token_id,))
    t = cur.fetchone()
    if not t or t['status'] != 'active': return {"error": "invalid_token"}
    
    new_bal = max(0, t['kwh_remaining'] - kwh)
    status = 'redeemed' if new_bal == 0 else 'active'
    cur.execute("UPDATE tokens SET kwh_remaining = ?, status = ? WHERE id = ?", (new_bal, status, token_id))
    conn.commit()
    conn.close()
    ledger.write("ECT_REDEEM", {"token_id": token_id, "kwh": kwh, "remaining": new_bal})
    return {"token_id": token_id, "remaining": new_bal, "status": status}
