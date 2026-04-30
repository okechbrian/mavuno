"""Farmer Training & Certification Logic.

Refactored to use SQLAlchemy 2.0.
"""
from __future__ import annotations
import secrets
import time
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from . import database, ledger
from .models import TrainingModule, FarmerCertification

def list_modules(db: Session) -> list[dict]:
    rows = db.execute(select(TrainingModule)).scalars().all()
    return [{
        "id": m.id, "title": m.title, "description": m.description,
        "category": m.category, "xp_reward": m.xp_reward, "content_url": m.content_url
    } for m in rows]

def complete_module(db: Session, farm_id: str, module_id: str) -> dict:
    """Records module completion and issues a verifiable certification."""
    # Check if already certified
    existing = db.execute(
        select(FarmerCertification).where(
            FarmerCertification.farm_id == farm_id,
            FarmerCertification.module_id == module_id
        )
    ).first()
    if existing: return {"error": "already_certified"}

    # Fetch module info
    module = db.execute(select(TrainingModule).where(TrainingModule.id == module_id)).scalar_one_or_none()
    if not module: return {"error": "unknown_module"}

    now = int(time.time())
    cert_id = "CERT-" + secrets.token_hex(4).upper()
    ledger_hash = secrets.token_hex(32) 
    
    cert = FarmerCertification(
        id=cert_id, farm_id=farm_id, module_id=module_id,
        issued_at=now, ledger_hash=ledger_hash
    )
    db.add(cert)
    db.commit()
    
    ledger.write("CERTIFICATION_ISSUED", {
        "cert_id": cert_id,
        "farm_id": farm_id,
        "module_id": module_id,
        "xp_reward": module.xp_reward
    })
    
    return {
        "ok": True,
        "cert_id": cert_id,
        "module_title": module.title,
        "issued_at": now
    }

def get_farmer_certifications(db: Session, farm_id: str) -> list[dict]:
    # Join with modules to get details
    stmt = (
        select(FarmerCertification, TrainingModule)
        .join(TrainingModule, FarmerCertification.module_id == TrainingModule.id)
        .where(FarmerCertification.farm_id == farm_id)
        .order_by(FarmerCertification.issued_at.desc())
    )
    rows = db.execute(stmt).all()
    
    out = []
    for cert, mod in rows:
        d = {
            "id": cert.id, "farm_id": cert.farm_id, "module_id": cert.module_id,
            "issued_at": cert.issued_at, "ledger_hash": cert.ledger_hash,
            "title": mod.title, "category": mod.category, "xp_reward": mod.xp_reward
        }
        out.append(d)
    return out

def seed_training_data(db: Session):
    """Initial modules for the prototype."""
    modules_data = [
        ("TM-01", "Regenerative Mushroom Cultivation", "Learn high-yield, zero-waste oyster mushroom techniques.", "Mushrooms", 150),
        ("TM-02", "Smart Irrigation with Trade Priority", "Optimize your water usage using Mavuno's Yield Prioritys.", "Technology", 100),
        ("TM-03", "Marketplace Best Practices", "Build buyer trust through accurate listings and verified harvests.", "Business", 80),
        ("TM-04", "Organic Fertilizer Production", "Turn farm waste into high-quality compost and liquid fertilizer.", "Sustainability", 120),
    ]
    
    for mid, title, desc, cat, xp in modules_data:
        existing = db.execute(select(TrainingModule).where(TrainingModule.id == mid)).first()
        if not existing:
            m = TrainingModule(id=mid, title=title, description=desc, category=cat, xp_reward=xp)
            db.add(m)
    db.commit()

