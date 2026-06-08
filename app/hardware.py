"""Hardware Monitoring & Sentinel Node Management for Mavuno."""
from __future__ import annotations
import time
from sqlalchemy.orm import Session
from .models import HardwareAudit, FarmerProfile

def log_heartbeat(db: Session, farm_id: str, device_id: str, firmware: str, battery: float, rssi: int):
    """
    Logs a health heartbeat from a Sentinel Node.
    """
    # 1. Determine status
    status = "nominal"
    if battery < 15:
        status = "low_battery"
    
    # 2. Add audit entry
    log = HardwareAudit(
        farm_id=farm_id,
        device_id=device_id,
        firmware_v=firmware,
        battery_pct=battery,
        signal_rssi=rssi,
        status=status,
        last_ping_at=int(time.time())
    )
    db.add(log)
    db.commit()
    
    return {"ok": True, "status": status}

def get_latest_health(db: Session, farm_id: str):
    """Returns the most recent heartbeat for a specific farm."""
    from sqlalchemy import select
    stmt = select(HardwareAudit).where(HardwareAudit.farm_id == farm_id).order_by(HardwareAudit.last_ping_at.desc()).limit(1)
    return db.execute(stmt).scalar_one_or_none()

def list_system_health(db: Session):
    """Returns the latest heartbeat for every registered device."""
    from sqlalchemy import text
    # SQLite-specific query to get the latest per group
    query = text("""
        SELECT h.* FROM hardware_audit h
        INNER JOIN (
            SELECT device_id, MAX(last_ping_at) as max_ping 
            FROM hardware_audit GROUP BY device_id
        ) latest ON h.device_id = latest.device_id AND h.last_ping_at = latest.max_ping
    """)
    rows = db.execute(query).fetchall()
    return [dict(r._mapping) for r in rows]
