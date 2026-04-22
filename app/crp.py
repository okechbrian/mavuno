"""Community Resource Platform (CRP) — market prices, buyer match, AI advisor.

Fills the same role as the 2012 Oxfam Novib "Internet Now!" / ALIN Maarifa kiosks
and the 2009-2014 Grameen Foundation Community Knowledge Worker program, but
without the failure modes that sank them: no kiosk power, no agent payroll,
no stale content library.

Public surface:
    market_prices(crop, region) -> dict
    list_offer(farm_id, crop, kg, floor_ugx) -> dict
    match_buyers(offer_id) -> dict
    advisor(farm_id, question) -> dict

AI advisor tries Groq's llama-3.3-70b-versatile when GROQ_API_KEY is set, with
a 2-second hard timeout. On miss (no key, network error, timeout, parse error)
it falls back to a deterministic rule-based responder so the USSD flow stays
alive on stage.
"""
from __future__ import annotations

import json
import math
import os
import secrets
import threading
import time
from pathlib import Path

import httpx

from . import ledger, scorer
from .config import DATA_DIR

_PRICES = DATA_DIR / "market_prices.json"
_BUYERS = DATA_DIR / "buyers.json"
_OFFERS = DATA_DIR / "offers.json"
_FARMS = DATA_DIR / "farms.json"

_offers_lock = threading.Lock()

# District -> region map (only 3 farms ship, but keep the table extensible)
_DISTRICT_REGION = {
    "Mbale": "Eastern",
    "Gulu": "Northern",
    "Mbarara": "Western",
    "Kampala": "Central",
    "Jinja": "Eastern",
    "Lira": "Northern",
    "Fort Portal": "Western",
}


# ---- helpers -------------------------------------------------------------

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _farm(farm_id: str) -> dict | None:
    farms = _load(_FARMS)
    return farms.get(farm_id)


def _region_for(farm: dict) -> str:
    return _DISTRICT_REGION.get(farm.get("district", ""), "Central")


def _haversine_km(a: dict, b: dict) -> float:
    R = 6371.0
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlng = math.radians(b["lng"] - a["lng"])
    s = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(s)), 1)


# ---- 1. Market prices ----------------------------------------------------

def market_prices(crop: str, region: str) -> dict:
    """Today's price + 7-day min/avg/max + trend + 30-day sparkline series."""
    data = _load(_PRICES)
    crop = crop.lower()
    if crop not in data["crops"]:
        return {"error": f"unknown_crop:{crop}"}
    regions = data["crops"][crop]["regions"]
    if region not in regions:
        # Fall back to the nearest region we have for this crop
        region = next(iter(regions))
    series = regions[region]
    today = series[-1]
    last7 = [p["ugx"] for p in series[-7:]]
    avg7 = int(sum(last7) / len(last7))
    # Trend: compare today vs 7d avg
    if today["ugx"] > avg7 * 1.01:
        trend = "up"
    elif today["ugx"] < avg7 * 0.99:
        trend = "down"
    else:
        trend = "flat"
    return {
        "crop": crop,
        "region": region,
        "unit": data["crops"][crop]["unit"],
        "today": today,
        "last7_min": min(last7),
        "last7_max": max(last7),
        "last7_avg": avg7,
        "trend": trend,
        "series": series,
        "as_of": data["as_of"],
    }


# ---- 2. Offers & buyer match --------------------------------------------

def _read_offers() -> dict:
    if not _OFFERS.exists():
        return {"offers": []}
    return _load(_OFFERS)


def _write_offers(data: dict) -> None:
    _OFFERS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_offer(farm_id: str, crop: str, kg: int, floor_ugx: int) -> dict:
    """Farmer posts produce for sale. Writes to offers.json + ledger."""
    farm = _farm(farm_id)
    if farm is None:
        return {"error": "unknown_farm"}
    if kg <= 0 or floor_ugx <= 0:
        return {"error": "bad_input"}
    offer_id = "OF-" + secrets.token_hex(3).upper()
    offer = {
        "offer_id": offer_id,
        "farm_id": farm_id,
        "farmer_name": farm["farmer_name"],
        "crop": crop.lower(),
        "kg": int(kg),
        "floor_ugx_per_kg": int(floor_ugx),
        "region": _region_for(farm),
        "gps": farm["gps"],
        "status": "open",
        "created_ts": int(time.time()),
    }
    with _offers_lock:
        data = _read_offers()
        data["offers"].append(offer)
        _write_offers(data)
    ledger.append("offer", {"offer_id": offer_id, "farm_id": farm_id,
                             "crop": offer["crop"], "kg": offer["kg"],
                             "floor_ugx": offer["floor_ugx_per_kg"]})
    return offer


def match_buyers(offer_id: str) -> dict:
    """Find top-3 buyers for an open offer: same crop, region preferred,
    price >= floor, distance ascending."""
    data = _read_offers()
    offer = next((o for o in data["offers"] if o["offer_id"] == offer_id), None)
    if offer is None:
        return {"error": "offer_not_found"}
    buyers = _load(_BUYERS)["buyers"]
    candidates = []
    for b in buyers:
        if offer["crop"] not in b["crops"]:
            continue
        if b["floor_ugx_per_kg"] < offer["floor_ugx_per_kg"]:
            continue
        dist = _haversine_km(offer["gps"], b["gps"])
        if dist > b["radius_km"] * 2:  # allow some slack
            continue
        region_bonus = 0 if b["region"] == offer["region"] else 15
        candidates.append({**b, "distance_km": dist, "rank_key": dist + region_bonus})
    candidates.sort(key=lambda x: x["rank_key"])
    top = candidates[:3]
    ledger.append("match", {"offer_id": offer_id, "matches": [b["buyer_id"] for b in top]})
    return {"offer_id": offer_id, "matches": [
        {"buyer_id": b["buyer_id"], "name": b["name"], "price_offered": b["floor_ugx_per_kg"],
         "distance_km": b["distance_km"], "contact": b["contact"]}
        for b in top
    ]}


def list_open_offers(limit: int = 10) -> dict:
    data = _read_offers()
    rows = [o for o in data["offers"] if o["status"] == "open"]
    rows.sort(key=lambda o: o["created_ts"], reverse=True)
    return {"offers": rows[:limit], "total_open": len(rows)}


# ---- 3. Advisor (Groq + rule-based fallback) ----------------------------

_RULE_BANK = {
    "pest": "Inspect leaves for holes & discoloration. Neem spray every 7 days. Report to extension officer if >20% affected.",
    "water": "Irrigate early morning. Soil moisture target 25-35%. Mulch to retain.",
    "irrig": "Irrigate early morning. Soil moisture target 25-35%. Mulch to retain.",
    "price": "Check menu 4 for today's price. Offers on menu 5 auto-match 3 buyers.",
    "fertil": "Split N application: 1/3 at planting, 1/3 at knee-high, 1/3 at tasseling.",
    "coffee": "Coffee: prune after main harvest, mulch, shade trees reduce heat stress.",
    "maize": "Maize: plant with first rains, weed by day 20, side-dress N at knee-high.",
    "bean": "Beans: inoculate seed, avoid waterlogging, harvest when pods rattle.",
    "disease": "Remove & burn diseased plants. Verify with extension officer before spraying.",
    "weather": "Dial *254# for Met dept 10-day forecast. Plant after 2 days of rain.",
}


def _rule_based(question: str, ctx: dict) -> str:
    q = question.lower()
    for key, answer in _RULE_BANK.items():
        if key in q:
            return answer
    crop = ctx.get("crop", "crop")
    return f"Talk to your nearest extension officer about {crop}. Dial *165*0# for help line."


def _groq_advise(question: str, ctx: dict) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    system = (
        "You are Mavuno, a Ugandan smallholder farm advisor. "
        "Answer in 1-2 short sentences, max 140 characters total. "
        "Use plain English suitable for feature-phone USSD. "
        "If uncertain, say 'Check with extension officer.' "
        f"Farmer grows {ctx.get('crop')}, YPS {ctx.get('yps')}, tier {ctx.get('tier')}, "
        f"soil moisture {ctx.get('sm')}%, region {ctx.get('region')}."
    )
    try:
        with httpx.Client(timeout=2.0) as c:
            r = c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": question[:200]},
                    ],
                    "max_tokens": 80,
                    "temperature": 0.3,
                },
            )
            if r.status_code != 200:
                return None
            text = r.json()["choices"][0]["message"]["content"].strip()
            return text[:140]
    except Exception:
        return None


def advisor(farm_id: str, question: str) -> dict:
    farm = _farm(farm_id)
    if farm is None:
        return {"error": "unknown_farm"}
    question = (question or "").strip()
    if not question:
        return {"error": "empty_question"}
    score = scorer.score_farm(farm_id)
    ctx = {
        "crop": farm["crop"],
        "region": _region_for(farm),
        "yps": score.get("yps", 0),
        "tier": score.get("tier_label", "n/a"),
        "sm": score.get("features", {}).get("sm_avg_7d", 0),
    }
    answer = _groq_advise(question, ctx)
    source = "groq" if answer else "rules"
    if not answer:
        answer = _rule_based(question, ctx)
    ledger.append("advise", {"farm_id": farm_id, "q_tokens": len(question.split()),
                              "source": source})
    return {"farm_id": farm_id, "question": question, "answer": answer,
            "source": source, "context": ctx}
