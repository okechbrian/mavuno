"""End-to-end verification for Mavuno Pay + self-listing.

Walks the full user flow against an in-process TestClient:
  1. farmer signs in
  2. farmer posts an offer (POST /crp/offers)
  3. buyer signs in (separate TestClient, separate cookies)
  4. buyer sees the offer (GET /crp/offers)
  5. buyer initiates a payment (POST /payments/initiate)
  6. wait for the mocked PSP callback
  7. verify settled status, offer closed, receipt HMAC valid, ledger events present

Run:  .venv-verify/Scripts/python scripts/verify_payments_e2e.py
"""
from __future__ import annotations
import hashlib
import hmac as _hmac
import json
import os
import sys
import time
import sqlite3

# Make absolute-import of `app` work when running as a script.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from fastapi.testclient import TestClient

from app import database, payments  # noqa: E402
from app.config import HMAC_SECRET  # noqa: E402
from app.main import app  # noqa: E402


def ok(label: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {label}" + (f" -- {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def main() -> int:
    print("== Mavuno Pay end-to-end verification ==\n")

    # Ensure there's a farmer + buyer to work with.
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms LIMIT 1")
    farm_row = cur.fetchone()
    cur.execute("SELECT id, crops_json, floor_ugx FROM buyers LIMIT 1")
    buyer_row = cur.fetchone()
    conn.close()
    ok("Seed farm exists", bool(farm_row))
    ok("Seed buyer exists", bool(buyer_row))
    farm_id = farm_row["id"]
    buyer_id = buyer_row["id"]
    buyer_crops = json.loads(buyer_row["crops_json"])
    crop = buyer_crops[0] if buyer_crops else "coffee"
    print(f"  using farm={farm_id} · buyer={buyer_id} · crop={crop}")

    farmer = TestClient(app)
    buyer = TestClient(app)

    # 1. Farmer login
    r = farmer.post("/login", json={"role": "farmer", "id_or_phone": farm_id, "pin_or_password": "1234"})
    ok("farmer /login 200", r.status_code == 200, str(r.status_code))

    # 2. Farmer posts a new offer
    kg = 120
    floor_ugx = max(5000, int(buyer_row["floor_ugx"]))  # satisfy buyer budget so it becomes a match
    r = farmer.post("/crp/offers", json={"farm_id": farm_id, "crop": crop, "kg": kg, "floor_ugx": floor_ugx})
    ok("POST /crp/offers 200", r.status_code == 200, str(r.status_code))
    offer = r.json()
    ok("offer has offer_id", "offer_id" in offer, offer.get("offer_id", ""))
    offer_id = offer["offer_id"]

    # Farmer sees own listings including the new one
    r = farmer.get(f"/crp/offers?farm_id={farm_id}&include_closed=true&limit=10")
    ok("GET /crp/offers (farmer, own) 200", r.status_code == 200)
    listings = r.json()
    got_new = any(o["id"] == offer_id for o in listings.get("offers", []))
    ok("farmer sees own new listing", got_new)
    ok("payment_status is null", all(o.get("payment_status") in (None, "") for o in listings["offers"] if o["id"] == offer_id))

    # 3. Buyer login
    r = buyer.post("/login", json={"role": "buyer", "id_or_phone": buyer_id, "pin_or_password": "1234"})
    ok("buyer /login 200", r.status_code == 200, str(r.status_code))

    # 4. Buyer sees the offer in the marketplace
    r = buyer.get("/crp/offers?limit=50")
    ok("GET /crp/offers (buyer) 200", r.status_code == 200)
    buyer_offers = r.json().get("offers", [])
    visible = any(o["id"] == offer_id for o in buyer_offers)
    ok("buyer sees the new offer", visible)

    # 5. Buyer initiates payment
    r = buyer.post("/payments/initiate", json={"offer_id": offer_id, "msisdn": "+256700000001", "method": "mavuno-pay"})
    ok("POST /payments/initiate 200", r.status_code == 200, r.text[:200])
    pay = r.json()
    ok("payment is pending", pay.get("status") == "pending", pay.get("status", ""))
    expected_amount = kg * floor_ugx
    ok("server-computed amount matches kg*floor_ugx", pay.get("amount_ugx") == expected_amount,
       f"got {pay.get('amount_ugx')}, want {expected_amount}")
    pid = pay["payment_id"]

    # Status polling from buyer perspective
    r = buyer.get(f"/payments/status/{pid}")
    ok("GET /payments/status 200 (pending)", r.status_code == 200)
    ok("status is pending", r.json()["status"] == "pending")

    # 6. The mocked PSP callback needs a running loop; in TestClient the asyncio
    # task couldn't be scheduled from a sync request. Simulate the callback by
    # posting to /payments/confirm with a valid signature.
    body = json.dumps({"payment_id": pid, "success": True}).encode()
    sig = payments.callback_signature(body)
    r = buyer.post("/payments/confirm", content=body, headers={"Content-Type": "application/json", "X-Mavuno-Sig": sig})
    ok("POST /payments/confirm 200", r.status_code == 200, str(r.status_code))
    ok("confirm returns settled", r.json().get("status") == "settled", str(r.json()))

    # Negative control: bad signature
    bad = buyer.post("/payments/confirm", content=body, headers={"Content-Type": "application/json", "X-Mavuno-Sig": "deadbeef"})
    ok("confirm with bad sig -> 401", bad.status_code == 401, str(bad.status_code))

    # 7. Verify post-settlement state
    r = buyer.get(f"/payments/status/{pid}")
    ok("status is settled", r.json()["status"] == "settled")

    # Offer status is 'accepted', and payment_status is 'settled' in joined feed
    r = buyer.get("/crp/offers?limit=50")
    # Offer is now closed → not in open-only default. Use farmer-side include_closed=true instead.
    r = farmer.get(f"/crp/offers?farm_id={farm_id}&include_closed=true&limit=10")
    listings = r.json()["offers"]
    row = next((o for o in listings if o["id"] == offer_id), None)
    ok("offer appears in farmer history", row is not None)
    ok("offer.status == accepted", row["status"] == "accepted", row["status"])
    ok("joined payment_status == settled", row["payment_status"] == "settled", str(row["payment_status"]))

    # Receipt HMAC round-trip
    r = buyer.get(f"/payments/receipt/{pid}")
    ok("GET /payments/receipt 200", r.status_code == 200)
    receipt = r.json()
    payload = receipt["payload"].encode()
    recomputed = _hmac.new(HMAC_SECRET, payload, hashlib.sha256).hexdigest()
    ok("receipt HMAC verifies offline", _hmac.compare_digest(recomputed, receipt["sig"]))
    expected_payload = f"{pid}|{offer_id}|{expected_amount}|settled"
    ok("receipt payload canonical", receipt["payload"] == expected_payload, receipt["payload"])

    # Ledger contains all four events for this payment — needs agent role.
    agent = TestClient(app)
    r = agent.post("/login", json={"role": "agent", "id_or_phone": "", "pin_or_password": "mavuno2026"})
    ok("agent /login 200", r.status_code == 200)
    r = agent.get("/ledger")
    ok("GET /ledger 200 (agent)", r.status_code == 200, str(r.status_code))
    events = r.json().get("rows", [])
    relevant = []
    for ev in events:
        entry = ev.get("entry") or {}
        payload = entry.get("payload") or {}
        etype = entry.get("type")
        if payload.get("offer_id") == offer_id or payload.get("payment_id") == pid:
            relevant.append(etype)
    expected_events = {"OFFER", "PAYMENT_INITIATED", "PAYMENT_SETTLED", "OFFER_ACCEPTED"}
    missing = expected_events - set(relevant)
    ok("ledger contains all four events", not missing,
       f"missing: {missing}" if missing else f"got: {relevant}")

    # Dedupe: cannot pay the already-settled offer again
    r = buyer.post("/payments/initiate", json={"offer_id": offer_id, "msisdn": "+256700000001", "method": "mavuno-pay"})
    ok("dedupe: second initiate rejected", r.status_code == 400, str(r.status_code))
    ok("dedupe reason is offer_not_open or already", "not_open" in r.text or "already" in r.text, r.text[:120])

    # Farmer sees payment in their feed
    r = farmer.get(f"/payments/farmer/{farm_id}")
    ok("GET /payments/farmer 200", r.status_code == 200)
    feed = r.json().get("payments", [])
    ok("farmer payments feed has our payment", any(p["id"] == pid for p in feed))

    print("\nAll checks passed. Mavuno Pay + self-listing verified end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
