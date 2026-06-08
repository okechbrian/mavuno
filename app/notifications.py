"""Unified Notification Engine for Mavuno.

Handles in-app alerts and SMS fallbacks for multi-channel engagement.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Notification, User
from .gateways import send_sms

def notify(db: Session, user_id: str, title: str, body: str, n_type: str = "general", sms_fallback: bool = False):
    """
    Creates an in-app notification and optionally sends an SMS fallback.
    """
    # 1. Create in-app record
    n = Notification(
        user_id=user_id,
        title=title,
        body=body,
        type=n_type,
        read=False
    )
    db.add(n)
    db.commit()
    
    # 2. SMS Fallback for rural/offline users
    if sms_fallback:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.phone:
            # Shorten message for SMS if needed (standard is 160 chars)
            sms_msg = f"Mavuno Alert: {title}\n{body}"
            if len(sms_msg) > 160:
                sms_msg = sms_msg[:157] + "..."
            send_sms(user.phone, sms_msg)

    return {"ok": True, "id": n.id}

def broadcast_district(db: Session, district: str, title: str, body: str, n_type: str = "broadcast"):
    """
    Sends a notification to all farmers in a specific district.
    Used for price alerts or collection route announcements.
    """
    from .models import FarmerProfile
    farmers = db.query(FarmerProfile).filter(FarmerProfile.district == district).all()
    count = 0
    for f in farmers:
        notify(db, f.user_id, title, body, n_type, sms_fallback=True)
        count += 1
    return {"ok": True, "broadcast_count": count}
