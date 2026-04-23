"""SQLite-backed Community Resource Platform (CRP) with restored AI Advisor."""
from __future__ import annotations
import json
import math
import os
import secrets
import time
import httpx
from . import ledger, scorer, database

def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlat = phi2 - phi1
    dlng = math.radians(lng2 - lng1)
    s = math.sin(dlat / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(s)), 1)

def market_prices(crop: str, region: str) -> dict:
    from .config import DATA_DIR
    data = json.loads((DATA_DIR / "market_prices.json").read_text())
    crop = crop.lower()
    if crop not in data["crops"]: return {"error": f"unknown_crop:{crop}"}
    regions = data["crops"][crop]["regions"]
    if region not in regions: region = next(iter(regions))
    series = regions[region]
    today = series[-1]
    last7 = [p["ugx"] for p in series[-7:]]
    avg7 = int(sum(last7) / len(last7))
    trend = "up" if today["ugx"] > avg7 * 1.01 else "down" if today["ugx"] < avg7 * 0.99 else "flat"
    return {
        "crop": crop, "region": region, "unit": data["crops"][crop]["unit"],
        "today": today, "last7_min": min(last7), "last7_max": max(last7),
        "last7_avg": avg7, "trend": trend, "series": series
    }

def list_offer(farm_id: str, crop: str, kg: int, floor_ugx: int) -> dict:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT farmer_name, district, lat, lng FROM farms WHERE id = ?", (farm_id,))
    farm = cur.fetchone()
    if not farm:
        conn.close()
        return {"error": "unknown_farm"}
    
    offer_id = "OF-" + secrets.token_hex(3).upper()
    ts = int(time.time())
    cur.execute('''
        INSERT INTO offers (id, farm_id, farmer_name, crop, kg, floor_ugx, region, lat, lng, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (offer_id, farm_id, farm['farmer_name'], crop.lower(), kg, floor_ugx, farm['district'], farm['lat'], farm['lng'], ts))
    conn.commit()
    conn.close()
    
    ledger.write("OFFER", {"offer_id": offer_id, "farm_id": farm_id, "kg": kg})
    return {"offer_id": offer_id, "status": "open"}

def match_buyers(offer_id: str) -> dict:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
    offer = cur.fetchone()
    if not offer:
        conn.close()
        return {"error": "not_found"}
    
    cur.execute("SELECT * FROM buyers")
    buyers = cur.fetchall()
    conn.close()
    
    candidates = []
    for b in buyers:
        crops = json.loads(b['crops_json'])
        if offer['crop'] not in crops: continue
        if b['floor_ugx'] < offer['floor_ugx']: continue
        
        dist = _haversine_km(offer['lat'], offer['lng'], b['lat'], b['lng'])
        if dist > b['radius_km'] * 2: continue
        candidates.append({
            "buyer_id": b['id'], "name": b['name'], "price_offered": b['floor_ugx'],
            "distance_km": dist, "contact": b['contact']
        })
    candidates.sort(key=lambda x: x['distance_km'])
    top = candidates[:3]
    ledger.write("MATCH", {"offer_id": offer_id, "matches": [b['buyer_id'] for b in top]})
    return {"offer_id": offer_id, "matches": top}

def list_open_offers(limit: int = 10) -> dict:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM offers WHERE status = 'open' ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    cur.execute("SELECT count(*) as total FROM offers WHERE status = 'open'")
    total = cur.fetchone()['total']
    conn.close()
    return {"offers": [dict(r) for r in rows], "total_open": total}

_RULE_BANK = {
    "pest": "Inspect leaves for holes. Neem spray every 7 days. Report to extension officer if >20% affected.",
    "water": "Irrigate early morning. Target 25-35%. Mulch to retain.",
    "price": "Check menu 4 for today's price. Offers on menu 5 auto-match 3 buyers.",
    "coffee": "Coffee: prune after harvest, use shade trees.",
    "maize": "Maize: side-dress N at knee-high, weed early."
}

def _groq_advise(question: str, ctx: dict) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key: return None
    system = (
        "You are Mavuno, a Ugandan smallholder farm advisor. "
        "Answer in 1-2 short sentences, max 140 characters. "
        f"Context: Farmer grows {ctx.get('crop')}, YPS {ctx.get('yps')}, Health {ctx.get('health')}, District {ctx.get('district')}."
    )
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": question}],
                    "max_tokens": 60, "temperature": 0.2
                }
            )
            return r.json()["choices"][0]["message"]["content"].strip()[:140]
    except: return None

def advisor(farm_id: str, question: str) -> dict:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT crop, district FROM farms WHERE id = ?", (farm_id,))
    farm = cur.fetchone()
    conn.close()
    if not farm: return {"error": "unknown_farm"}
    
    score = scorer.score_farm(farm_id)
    ctx = {
        "crop": farm['crop'], "district": farm['district'],
        "yps": score.get('yps'), "health": score.get('credit_health')
    }
    
    answer = _groq_advise(question, ctx)
    source = "groq" if answer else "ai-fallback"
    if not answer:
        q = (question or "").lower()
        # Advanced Fallback AI
        for k, v in _RULE_BANK.items():
            if k in q: 
                answer = v
                break
        
        if not answer:
            crop = ctx.get('crop', 'crop')
            if 'water' in q or 'irrigate' in q or 'dry' in q:
                answer = f"Based on your YPS {ctx.get('yps')}, {crop} needs consistent moisture. Use your ECT to power the pump early morning."
            elif 'fertilizer' in q or 'npk' in q or 'grow' in q:
                answer = f"Your {crop} health is {ctx.get('health')}. Consider adding organic compost to boost Nitrogen and improve yield."
            elif 'harvest' in q or 'yield' in q:
                answer = f"With a score of {ctx.get('yps')}, your {crop} yield is tracking {ctx.get('health')}. Prepare for harvest securely."
            elif 'disease' in q or 'rot' in q or 'brown' in q or 'yellow' in q:
                answer = f"Watch out for signs of fungal rot in {crop} during humid weeks. Remove affected leaves immediately."
            else:
                answer = f"For {crop} in {ctx.get('district')} (Health: {ctx.get('health')}), ensure consistent monitoring. Dial *165*0# for local extension support."

    ledger.write("ADVISE", {"farm_id": farm_id, "source": source})
    return {"farm_id": farm_id, "answer": answer, "source": source, "context": ctx}
