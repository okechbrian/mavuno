"""SQLite Audit Ledger for Prototype."""
import json
import time
from .database import get_db
from .security import hash_payload, chain_hash

def write(entry_type: str, payload: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT curr_hash FROM ledger ORDER BY id DESC LIMIT 1')
    row = cur.fetchone()
    prev_hash = row['curr_hash'] if row else "0" * 64
    
    ts = int(time.time())
    entry = {"type": entry_type, "payload": payload, "ts": ts}
    p_hash = hash_payload(entry)
    c_hash = chain_hash(prev_hash, p_hash)
    
    cur.execute('INSERT INTO ledger (prev_hash, curr_hash, type, payload, timestamp) VALUES (?,?,?,?,?)',
               (prev_hash, c_hash, entry_type, json.dumps(entry), ts))
    conn.commit()
    conn.close()
    return c_hash

def read_all():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT payload, curr_hash as hash FROM ledger ORDER BY id ASC')
    rows = cur.fetchall()
    conn.close()
    return [{"entry": json.loads(r['payload']), "hash": r['hash']} for r in rows]

def verify():
    rows = read_all()
    if not rows: return {"ok": True, "length": 0}
    prev = "0" * 64
    for i, r in enumerate(rows):
        p_hash = hash_payload(r['entry'])
        if r['hash'] != chain_hash(prev, p_hash): return {"ok": False, "bad_line": i+1}
        prev = r['hash']
    return {"ok": True, "length": len(rows)}
