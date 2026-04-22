"""Energy Credit Token engine.

A token represents a kWh allocation that:
  - expires in 72h
  - is redeemable only within 5 km of the issuing farm's GPS
  - is HMAC-signed
  - is non-cashable (no route ever returns currency)

Every state change writes to the hash ledger.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
import threading
import time
from pathlib import Path

from . import ledger
from .config import DATA_DIR, ECT_EXPIRY_HOURS, ECT_GPS_RADIUS_KM, HMAC_SECRET

TOKENS_PATH = DATA_DIR / "tokens.jsonl"
_lock = threading.Lock()


def _farms() -> dict:
    return json.loads((DATA_DIR / "farms.json").read_text(encoding="utf-8"))


def _sign(payload: str) -> str:
    return hmac.new(HMAC_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _read_tokens() -> list[dict]:
    if not TOKENS_PATH.exists():
        return []
    with TOKENS_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _write_token(t: dict) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TOKENS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(t) + "\n")


def _rewrite_tokens(tokens: list[dict]) -> None:
    tmp = TOKENS_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for t in tokens:
            f.write(json.dumps(t) + "\n")
    tmp.replace(TOKENS_PATH)


def issue(farm_id: str, yps: int, kwh: int) -> dict:
    farms = _farms()
    if farm_id not in farms:
        return {"error": "unknown_farm"}
    if kwh <= 0:
        return {"error": "yps_below_threshold", "yps": yps}
    farm = farms[farm_id]
    now = int(time.time())
    token = {
        "token_id": "ECT-" + secrets.token_hex(6).upper(),
        "farm_id": farm_id,
        "yps": yps,
        "kwh_allocated": kwh,
        "kwh_remaining": kwh,
        "issued_at": now,
        "expires_at": now + ECT_EXPIRY_HOURS * 3600,
        "gps_lat": farm["gps"]["lat"],
        "gps_lng": farm["gps"]["lng"],
        "radius_km": ECT_GPS_RADIUS_KM,
        "pump_node": farm["pump"]["name"],
        "redeemed": False,
    }
    token["issuer_sig"] = _sign(
        f"{token['token_id']}|{farm_id}|{kwh}|{now}|{token['expires_at']}"
    )
    with _lock:
        _write_token(token)
        ledger.append("ECT_ISSUE", {
            "token_id": token["token_id"],
            "farm_id": farm_id,
            "yps": yps,
            "kwh": kwh,
            "pump_node": token["pump_node"],
        })
    return token


def get(token_id: str) -> dict | None:
    for t in _read_tokens():
        if t["token_id"] == token_id:
            return t
    return None


def farm_balance(farm_id: str) -> dict:
    """Active (unredeemed + unexpired) kWh for a farm."""
    now = int(time.time())
    active = [
        t for t in _read_tokens()
        if t["farm_id"] == farm_id and not t["redeemed"] and t["expires_at"] > now
    ]
    return {
        "farm_id": farm_id,
        "active_tokens": len(active),
        "kwh_remaining": sum(t["kwh_remaining"] for t in active),
        "tokens": active,
    }


def redeem(token_id: str, lat: float, lng: float, kwh: int) -> dict:
    now = int(time.time())
    with _lock:
        tokens = _read_tokens()
        idx = next((i for i, t in enumerate(tokens) if t["token_id"] == token_id), -1)
        if idx < 0:
            return {"error": "token_not_found"}
        t = tokens[idx]
        expected_sig = _sign(
            f"{t['token_id']}|{t['farm_id']}|{t['kwh_allocated']}|{t['issued_at']}|{t['expires_at']}"
        )
        if not hmac.compare_digest(expected_sig, t.get("issuer_sig", "")):
            ledger.append("ECT_REJECT", {"token_id": token_id, "reason": "invalid_signature"})
            return {"error": "invalid_signature"}
        if t["redeemed"]:
            return {"error": "already_redeemed"}
        if t["expires_at"] < now:
            ledger.append("ECT_EXPIRE", {"token_id": token_id, "reason": "expired_on_redeem"})
            return {"error": "expired"}
        dist = _haversine_km((t["gps_lat"], t["gps_lng"]), (lat, lng))
        if dist > t["radius_km"]:
            ledger.append("ECT_REJECT", {
                "token_id": token_id, "reason": "out_of_range", "distance_km": round(dist, 2)
            })
            return {"error": "out_of_range", "distance_km": round(dist, 2)}
        if kwh > t["kwh_remaining"]:
            return {"error": "insufficient_balance", "remaining": t["kwh_remaining"]}

        t["kwh_remaining"] -= kwh
        if t["kwh_remaining"] == 0:
            t["redeemed"] = True
        tokens[idx] = t
        _rewrite_tokens(tokens)
        ledger.append("ECT_REDEEM", {
            "token_id": token_id,
            "kwh": kwh,
            "remaining": t["kwh_remaining"],
            "pump_node": t["pump_node"],
            "distance_km": round(dist, 2),
        })
        return {"ok": True, "token_id": token_id, "kwh_redeemed": kwh, "remaining": t["kwh_remaining"]}


def sweep_expired() -> int:
    """Mark expired tokens in the ledger (idempotent; called from a demo button)."""
    now = int(time.time())
    count = 0
    for t in _read_tokens():
        if not t["redeemed"] and t["expires_at"] < now:
            ledger.append("ECT_EXPIRE", {"token_id": t["token_id"], "reason": "ttl"})
            count += 1
    return count
