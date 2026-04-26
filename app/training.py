"""Farmer Training & Certification Logic."""
from __future__ import annotations
import secrets
import time
from . import database, ledger

def list_modules() -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM training_modules")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def complete_module(farm_id: str, module_id: str) -> dict:
    """Records module completion and issues a verifiable certification."""
    conn = database.get_db()
    cur = conn.cursor()
    
    # Check if already certified
    cur.execute(
        "SELECT id FROM farmer_certifications WHERE farm_id = ? AND module_id = ?",
        (farm_id, module_id)
    )
    if cur.fetchone():
        conn.close()
        return {"error": "already_certified"}

    # Fetch module info
    cur.execute("SELECT * FROM training_modules WHERE id = ?", (module_id,))
    module = cur.fetchone()
    if not module:
        conn.close()
        return {"error": "unknown_module"}

    now = int(time.time())
    cert_id = "CERT-" + secrets.token_hex(4).upper()
    
    # In a real system, we'd hash the cert data
    ledger_hash = secrets.token_hex(32) 
    
    cur.execute(
        """INSERT INTO farmer_certifications (id, farm_id, module_id, issued_at, ledger_hash)
           VALUES (?, ?, ?, ?, ?)""",
        (cert_id, farm_id, module_id, now, ledger_hash)
    )
    
    conn.commit()
    conn.close()
    
    ledger.write("CERTIFICATION_ISSUED", {
        "cert_id": cert_id,
        "farm_id": farm_id,
        "module_id": module_id,
        "xp_reward": module['xp_reward']
    })
    
    return {
        "ok": True,
        "cert_id": cert_id,
        "module_title": module['title'],
        "issued_at": now
    }

def get_farmer_certifications(farm_id: str) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT c.*, m.title, m.category, m.xp_reward 
           FROM farmer_certifications c
           JOIN training_modules m ON c.module_id = m.id
           WHERE c.farm_id = ?
           ORDER BY c.issued_at DESC""",
        (farm_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def seed_training_data():
    """Initial modules for the prototype."""
    modules = [
        ("TM-01", "Regenerative Mushroom Cultivation", "Learn high-yield, zero-waste oyster mushroom techniques.", "Mushrooms", 150),
        ("TM-02", "Smart Irrigation with ECT", "Optimize your water usage using Mavuno's Energy Credit Tokens.", "Technology", 100),
        ("TM-03", "Marketplace Best Practices", "Build buyer trust through accurate listings and verified harvests.", "Business", 80),
        ("TM-04", "Organic Fertilizer Production", "Turn farm waste into high-quality compost and liquid fertilizer.", "Sustainability", 120),
    ]
    conn = database.get_db()
    cur = conn.cursor()
    for m in modules:
        cur.execute(
            "INSERT OR IGNORE INTO training_modules (id, title, description, category, xp_reward) VALUES (?,?,?,?,?)",
            m
        )
    conn.commit()
    conn.close()
