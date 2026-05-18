"""Mavuno Hardware Store — device inventory and orders.
"""
from __future__ import annotations
import secrets
import time
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import User, FarmerProfile, Notification
from . import ledger

CATALOG = {
    "YPS-MN-2.1": {"name": "Mavuno Node v2.1", "price_ugx": 120000, "desc": "Soil Telemetry Node (NPK + Moisture)"},
    "SLR-EXT-01": {"name": "Solar Extension Kit", "price_ugx": 45000, "desc": "High-capacity battery for low-light regions"},
    "BSTR-PRO": {"name": "Signal Booster Pro", "price_ugx": 35000, "desc": "External antenna for weak cellular coverage"}
}

def list_products():
    return [{"id": k, **v} for k, v in CATALOG.items()]

def purchase(db: Session, user_id: str, product_id: str, phone: str) -> dict:
    if product_id not in CATALOG:
        return {"error": "invalid_product"}
    
    prod = CATALOG[product_id]
    order_id = "ORD-" + secrets.token_hex(4).upper()
    now = int(time.time())
    
    # Write to ledger
    ledger.write("HARDWARE_ORDER", {
        "order_id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "amount_ugx": prod["price_ugx"],
        "phone": phone
    })
    
    # Notify Agent for installation
    # (In production, this would trigger an agent dispatch system)
    
    return {
        "ok": True,
        "order_id": order_id,
        "product": prod["name"],
        "price": prod["price_ugx"]
    }
