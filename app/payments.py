"""Mavuno Pay â€” buyerâ†’farmer mobile-money settlement.

State machine: pending â†’ settled | failed.

The PSP integration is mocked for the demo: `_psp_initiate` schedules a
delayed callback to `/payments/confirm`. Swapping to Flutterwave / MTN MoMo
in production is one function â€” the rest of the flow (DB writes, ledger,
HMAC receipts, owner-scoped reads) is identical.

Receipts are HMAC-SHA256-signed with the same key that protects the Trade Priority
ledger and session cookies, so a holder can verify a receipt offline using
the operator's shared key.
"""
from __future__ import annotations
import asyncio
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from . import database, ledger
from .config import HMAC_SECRET, PUBLIC_BASE_URL
from .models import MarketOffer, Settlement, User, Notification, PaymentBatch, BuyerProfile, FarmerProfile

VALID_METHODS = {"mtn", "airtel", "mavuno-pay", "mavuno-pay-batch"}
PSP_DELAY_SECONDS = 2.0  # simulated mobile-money round-trip
PSP_FAILURE_RATE = 0.0   # demo determinism â€” flip up only when stress-testing


def _new_payment_id() -> str:
    return "PAY-" + secrets.token_hex(4).upper()


def _receipt_payload(payment_id: str, offer_id: str, amount_ugx: int, status: str) -> bytes:
    return f"{payment_id}|{offer_id}|{amount_ugx}|{status}".encode("utf-8")


def _sign(payload: bytes) -> str:
    return hmac.new(HMAC_SECRET, payload, hashlib.sha256).hexdigest()


def callback_signature(body: bytes) -> str:
    """HMAC of the raw callback body. The /payments/confirm route checks this
    so the simulated PSP cannot be spoofed by a random caller."""
    return _sign(body)


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def initiate(db: Session, buyer_id: str, offer_id: str, msisdn: str, method: str) -> dict:
    """Create a pending payment row, write the ledger event, and trigger the
    (mocked) PSP. Amount is computed server-side from the offer."""
    if method not in VALID_METHODS:
        return {"error": "invalid_method"}
    msisdn = (msisdn or "").strip()
    if not msisdn or len(msisdn) > 20:
        return {"error": "invalid_msisdn"}

    offer = db.execute(select(MarketOffer).where(MarketOffer.id == offer_id)).scalar_one_or_none()
    if not offer:
        return {"error": "offer_not_found"}
    if offer.status != "open":
        return {"error": "offer_not_open", "status": offer.status}

    # Check for existing pending/settled payments for this offer
    existing = db.execute(select(Settlement).where(Settlement.offer_id == offer_id, Settlement.status.in_(['pending', 'settled']))).first()
    if existing:
        return {"error": "payment_already_in_progress"}

    buyer = db.execute(select(BuyerProfile).where(BuyerProfile.user_id == buyer_id)).scalar_one_or_none()
    if not buyer:
        return {"error": "unknown_buyer"}

    amount = int(offer.kg) * int(offer.floor_ugx)
    pid = _new_payment_id()
    now = int(time.time())
    sig = _sign(_receipt_payload(pid, offer_id, amount, "pending"))

    settlement = Settlement(
        id=pid, offer_id=offer_id, buyer_id=buyer_id, farm_id=offer.farm_id,
        amount_ugx=amount, status='pending', ledger_hash=sig, 
        settled_at=None, created_at=now
    )
    db.add(settlement)
    
    # Create notification for farmer
    notif = Notification(
        user_id=offer.farm_id, title="New Procurement Bid",
        body=f"A buyer has initiated a payment of UGX {amount:,} for your {offer.crop} listing.",
        type='payment_alert', created_at=now
    )
    db.add(notif)
    db.commit()

    ledger.write("PAYMENT_INITIATED", {
        "payment_id": pid, "offer_id": offer_id, "buyer_id": buyer_id,
        "farm_id": offer.farm_id, "amount_ugx": amount, "method": method,
    })

    if method != "mavuno-pay-batch":
        try:
            asyncio.get_running_loop().create_task(_psp_initiate(pid, amount, offer_id))
        except RuntimeError: pass

    return {
        "payment_id": pid, "offer_id": offer_id, "amount_ugx": amount,
        "status": "pending", "method": method,
    }


def _create_farmer_notification(farm_id: str, title: str, body: str, now: int):
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO notifications (user_id, title, body, type, created_at)
           VALUES (?, ?, ?, 'payment_alert', ?)""",
        (farm_id, title, body, now),
    )
    conn.commit()
    conn.close()


async def _psp_initiate(payment_id: str, amount_ugx: int, offer_id: str) -> None:
    """Mocked PSP. Sleeps, then POSTs an HMAC-signed callback to /payments/confirm."""
    await asyncio.sleep(PSP_DELAY_SECONDS)
    success = secrets.SystemRandom().random() >= PSP_FAILURE_RATE
    body = f'{{"payment_id":"{payment_id}","success":{str(success).lower()}}}'.encode("utf-8")
    sig = callback_signature(body)
    url = f"{PUBLIC_BASE_URL.rstrip('/')}/payments/confirm"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, content=body, headers={
                "Content-Type": "application/json",
                "X-Mavuno-Sig": sig,
            })
    except Exception:
        pass


def confirm(db: Session, payment_id: str, success: bool) -> dict:
    """Settle or fail a pending payment. Closes the offer on success."""
    settlement = db.execute(select(Settlement).where(Settlement.id == payment_id)).scalar_one_or_none()
    if not settlement:
        return {"error": "payment_not_found"}
    if settlement.status != "pending":
        return {"payment_id": payment_id, "status": settlement.status, "no_op": True}

    new_status = "settled" if success else "failed"
    now = int(time.time())
    new_sig = _sign(_receipt_payload(payment_id, settlement.offer_id, settlement.amount_ugx, new_status))
    
    settlement.status = new_status
    settlement.ledger_hash = new_sig
    settlement.settled_at = now
    
    if success:
        # Update offer status
        db.execute(update(MarketOffer).where(MarketOffer.id == settlement.offer_id).values(status='accepted'))
    
    # Create notification for farmer
    title = "Payment Settled" if success else "Payment Failed"
    msg = f"Payment of UGX {settlement.amount_ugx:,} for your {settlement.offer_id} listing has been {new_status}."
    notif = Notification(user_id=settlement.farm_id, title=title, body=msg, type='payment_alert', created_at=now)
    db.add(notif)
    db.commit()

    ledger.write("PAYMENT_SETTLED", {
        "payment_id": payment_id, "offer_id": settlement.offer_id,
        "amount_ugx": settlement.amount_ugx, "status": new_status,
    })
    if success:
        ledger.write("OFFER_ACCEPTED", {
            "offer_id": settlement.offer_id, "buyer_id": settlement.buyer_id,
            "farm_id": settlement.farm_id, "payment_id": payment_id,
        })

    return {"payment_id": payment_id, "status": new_status}

def initiate_batch(db: Session, buyer_id: str, offer_ids: list[str], msisdn: str) -> dict:
    """Initiates a bulk payment for multiple offers."""
    total_amount = 0
    pids = []
    
    for oid in offer_ids:
        # Create individual pending payment
        res = initiate(db, buyer_id, oid, msisdn, "mavuno-pay-batch")
        if "payment_id" in res:
            pids.append(res["payment_id"])
            total_amount += res["amount_ugx"]

    if not pids:
        return {"error": "no_valid_offers"}

    bid = "BTH-" + secrets.token_hex(4).upper()
    now = int(time.time())
    
    batch = PaymentBatch(
        id=bid, buyer_id=buyer_id, total_amount_ugx=total_amount,
        payment_ids_json=json.dumps(pids), created_at=now
    )
    db.add(batch)
    db.commit()
    
    ledger.write("BATCH_INITIATED", {"batch_id": bid, "count": len(pids), "total": total_amount})
    
    # Simulate batch PSP callback
    try:
        asyncio.get_running_loop().create_task(_psp_initiate_batch(bid))
    except RuntimeError:
        pass

    return {"ok": True, "batch_id": bid, "total_ugx": total_amount, "payment_ids": pids}

async def _psp_initiate_batch(batch_id: str) -> None:
    await asyncio.sleep(PSP_DELAY_SECONDS)
    success = True
    body = f'{{"batch_id":"{batch_id}","success":{str(success).lower()}}}'.encode("utf-8")
    sig = callback_signature(body)
    url = f"{PUBLIC_BASE_URL.rstrip('/')}/payments/batch/confirm"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, content=body, headers={
                "Content-Type": "application/json",
                "X-Mavuno-Sig": sig,
            })
    except Exception:
        pass

def confirm_batch(db: Session, batch_id: str, success: bool) -> dict:
    """Settles all individual payments in a batch."""
    batch = db.execute(select(PaymentBatch).where(PaymentBatch.id == batch_id)).scalar_one_or_none()
    if not batch:
        return {"error": "unknown_batch"}
    
    pids = json.loads(batch.payment_ids_json)
    for pid in pids:
        confirm(db, pid, success)
        
    now = int(time.time())
    status = "settled" if success else "failed"
    batch.status = status
    batch.settled_at = now
    db.commit()
    
    ledger.write("BATCH_SETTLED", {"batch_id": batch_id, "status": status})
    return {"ok": True, "batch_id": batch_id, "status": status}


def get(db: Session, payment_id: str) -> Optional[dict]:
    s = db.execute(select(Settlement).where(Settlement.id == payment_id)).scalar_one_or_none()
    return _obj_to_dict(s) if s else None


def for_farm(db: Session, farm_id: str, limit: int = 20) -> list[dict]:
    rows = db.execute(
        select(Settlement).where(Settlement.farm_id == farm_id).order_by(Settlement.created_at.desc()).limit(limit)
    ).scalars().all()
    return [_obj_to_dict(r) for r in rows]


def for_buyer(db: Session, buyer_id: str, limit: int = 20) -> list[dict]:
    rows = db.execute(
        select(Settlement).where(Settlement.buyer_id == buyer_id).order_by(Settlement.created_at.desc()).limit(limit)
    ).scalars().all()
    return [_obj_to_dict(r) for r in rows]


def _obj_to_dict(obj) -> dict:
    if not obj: return {}
    return {
        "id": obj.id, "offer_id": obj.offer_id, "buyer_id": obj.buyer_id,
        "farm_id": obj.farm_id, "amount_ugx": obj.amount_ugx,
        "status": obj.status, "hmac_sig": obj.ledger_hash,
        "created_at": obj.created_at, "settled_at": obj.settled_at,
        "method": "mavuno-pay" # Standardized
    }


def receipt(db: Session, payment_id: str) -> Optional[dict]:
    """An offline-verifiable JSON receipt."""
    row = get(db, payment_id)
    if not row: return None
    payload = _receipt_payload(row["id"], row["offer_id"], row["amount_ugx"], row["status"]).decode()
    return {
        "payment_id": row["id"], "offer_id": row["offer_id"],
        "buyer_id": row["buyer_id"], "farm_id": row["farm_id"],
        "amount_ugx": row["amount_ugx"], "method": row["method"],
        "status": row["status"], "created_at": row["created_at"],
        "settled_at": row["settled_at"], "payload": payload,
        "sig": row["hmac_sig"], "alg": "HMAC-SHA256",
    }

