"""Mavuno Pay — buyer→farmer mobile-money settlement.

State machine: pending → settled | failed.

The PSP integration is mocked for the demo: `_psp_initiate` schedules a
delayed callback to `/payments/confirm`. Swapping to Flutterwave / MTN MoMo
in production is one function — the rest of the flow (DB writes, ledger,
HMAC receipts, owner-scoped reads) is identical.

Receipts are HMAC-SHA256-signed with the same key that protects the ECT
ledger and session cookies, so a holder can verify a receipt offline using
the operator's shared key.
"""
from __future__ import annotations
import asyncio
import hashlib
import hmac
import secrets
import time
from typing import Optional

import httpx

from . import database, ledger
from .config import HMAC_SECRET, PUBLIC_BASE_URL

VALID_METHODS = {"mtn", "airtel", "mavuno-pay"}
PSP_DELAY_SECONDS = 2.0  # simulated mobile-money round-trip
PSP_FAILURE_RATE = 0.0   # demo determinism — flip up only when stress-testing


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


def initiate(buyer_id: str, offer_id: str, msisdn: str, method: str) -> dict:
    """Create a pending payment row, write the ledger event, and trigger the
    (mocked) PSP. Amount is computed server-side from the offer — never trust
    a client-supplied amount."""
    if method not in VALID_METHODS:
        return {"error": "invalid_method"}
    msisdn = (msisdn or "").strip()
    if not msisdn or len(msisdn) > 20:
        return {"error": "invalid_msisdn"}

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
    offer = cur.fetchone()
    if not offer:
        conn.close()
        return {"error": "offer_not_found"}
    if offer["status"] != "open":
        conn.close()
        return {"error": "offer_not_open", "status": offer["status"]}

    cur.execute(
        "SELECT id FROM payments WHERE offer_id = ? AND status IN ('pending','settled')",
        (offer_id,),
    )
    if cur.fetchone():
        conn.close()
        return {"error": "payment_already_in_progress"}

    cur.execute("SELECT id FROM buyers WHERE id = ?", (buyer_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_buyer"}

    amount = int(offer["kg"]) * int(offer["floor_ugx"])
    pid = _new_payment_id()
    now = int(time.time())
    sig = _sign(_receipt_payload(pid, offer_id, amount, "pending"))

    cur.execute(
        """INSERT INTO payments
           (id, offer_id, buyer_id, farm_id, amount_ugx, method, msisdn,
            status, hmac_sig, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (pid, offer_id, buyer_id, offer["farm_id"], amount, method, msisdn, sig, now),
    )
    conn.commit()
    conn.close()

    ledger.write("PAYMENT_INITIATED", {
        "payment_id": pid, "offer_id": offer_id, "buyer_id": buyer_id,
        "farm_id": offer["farm_id"], "amount_ugx": amount, "method": method,
    })

    # Fire-and-forget the PSP callback. In production swap this for a real
    # provider HTTP call; the rest of the flow is unchanged.
    try:
        asyncio.get_running_loop().create_task(_psp_initiate(pid, amount, offer_id))
    except RuntimeError:
        # No running loop — caller is sync (e.g. a test). Caller handles confirm.
        pass

    return {
        "payment_id": pid, "offer_id": offer_id, "amount_ugx": amount,
        "status": "pending", "method": method,
    }


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
        # Even if the callback dispatch fails, /payments/confirm can be
        # retried manually by the buyer dashboard's status poller.
        pass


def confirm(payment_id: str, success: bool) -> dict:
    """Settle or fail a pending payment. Closes the offer on success."""
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "payment_not_found"}
    if row["status"] != "pending":
        conn.close()
        return {"payment_id": payment_id, "status": row["status"], "no_op": True}

    new_status = "settled" if success else "failed"
    now = int(time.time())
    new_sig = _sign(_receipt_payload(payment_id, row["offer_id"], row["amount_ugx"], new_status))
    cur.execute(
        "UPDATE payments SET status=?, hmac_sig=?, settled_at=? WHERE id=?",
        (new_status, new_sig, now, payment_id),
    )
    if success:
        cur.execute("UPDATE offers SET status='accepted' WHERE id=?", (row["offer_id"],))
    conn.commit()
    conn.close()

    ledger.write("PAYMENT_SETTLED", {
        "payment_id": payment_id, "offer_id": row["offer_id"],
        "amount_ugx": row["amount_ugx"], "status": new_status,
    })
    if success:
        ledger.write("OFFER_ACCEPTED", {
            "offer_id": row["offer_id"], "buyer_id": row["buyer_id"],
            "farm_id": row["farm_id"], "payment_id": payment_id,
        })

    return {"payment_id": payment_id, "status": new_status}


def get(payment_id: str) -> Optional[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def for_farm(farm_id: str, limit: int = 20) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM payments WHERE farm_id = ? ORDER BY created_at DESC LIMIT ?",
        (farm_id, limit),
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def for_buyer(buyer_id: str, limit: int = 20) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM payments WHERE buyer_id = ? ORDER BY created_at DESC LIMIT ?",
        (buyer_id, limit),
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def receipt(payment_id: str) -> Optional[dict]:
    """An offline-verifiable JSON receipt. Holder can recompute the HMAC with
    the shared operator key (HMAC_SECRET) over `payload` and compare to `sig`."""
    row = get(payment_id)
    if not row:
        return None
    payload = _receipt_payload(row["id"], row["offer_id"], row["amount_ugx"], row["status"]).decode()
    return {
        "payment_id": row["id"],
        "offer_id": row["offer_id"],
        "buyer_id": row["buyer_id"],
        "farm_id": row["farm_id"],
        "amount_ugx": row["amount_ugx"],
        "method": row["method"],
        "status": row["status"],
        "created_at": row["created_at"],
        "settled_at": row["settled_at"],
        "payload": payload,
        "sig": row["hmac_sig"],
        "alg": "HMAC-SHA256",
    }
