"""SQLite-backed Community Resource Platform (CRP) with restored AI Advisor."""
from __future__ import annotations
import json
import math
import os
import re
import secrets
import time
import httpx
from sqlalchemy import text
from . import ledger, scorer, database

_PII_PATTERNS = (
    re.compile(r"\+?256\s?\d{9}"),
    re.compile(r"\b0\d{9}\b"),
    re.compile(r"\b\d{10,}\b"),
    re.compile(r"\bUG-[A-Z]{3}-\d{3,}\b", re.IGNORECASE),
    re.compile(r"\bCM[A-Z0-9]{8,}\b"),
)

def _redact_pii(text: str) -> str:
    if not text:
        return text
    redacted = text
    for pat in _PII_PATTERNS:
        redacted = pat.sub("[redacted]", redacted)
    return redacted

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

def check_price_fluctuations():
    """System-wide check of market prices vs farmer crops. Generates notifications on trend changes."""
    with database.SessionLocal() as db:
        farms = db.execute(text("SELECT user_id as id, crop, district FROM farmer_profiles")).fetchall()
        
        notifications_sent = 0
        for f in farms:
            f_dict = dict(f._mapping)
            p = market_prices(f_dict['crop'], f_dict['district'])
            if "error" in p: continue
            
            if p['trend'] != "flat":
                title = "Price Alert: " + f_dict['crop'].upper()
                direction = "surged to" if p['trend'] == "up" else "dropped to"
                msg = f"Market prices in {f_dict['district']} have {direction} UGX {p['today']['ugx']}/kg. Average is UGX {p['last7_avg']}/kg."
                
                # Check if we already sent this specific alert today (optional for prototype, but good practice)
                now = int(time.time())
                db.execute(
                    text("""INSERT INTO notifications (user_id, title, body, type, created_at)
                       VALUES (:user_id, :title, :body, 'price_alert', :created_at)"""),
                    {"user_id": f_dict['id'], "title": title, "body": msg, "created_at": now},
                )
                notifications_sent += 1
                
        db.commit()
    return {"ok": True, "notifications_sent": notifications_sent}

def list_offer(farm_id: str, crop: str, kg: int, floor_ugx: int) -> dict:
    with database.SessionLocal() as db:
        farm = db.execute(text("SELECT farmer_name, district, lat, lng FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
        if not farm:
            return {"error": "unknown_farm"}
        farm_dict = dict(farm._mapping)
        
        offer_id = "OF-" + secrets.token_hex(3).upper()
        ts = int(time.time())
        db.execute(text('''
            INSERT INTO market_offers (id, farm_id, crop, kg, floor_ugx, created_at)
            VALUES (:id, :farm_id, :crop, :kg, :floor_ugx, :created_at)
        '''), {"id": offer_id, "farm_id": farm_id, "crop": crop.lower(), "kg": kg, "floor_ugx": floor_ugx, "created_at": ts})
        db.commit()
    
    ledger.write("OFFER", {"offer_id": offer_id, "farm_id": farm_id, "kg": kg})
    return {"offer_id": offer_id, "status": "open"}

def match_buyers(offer_id: str) -> dict:
    with database.SessionLocal() as db:
        offer = db.execute(text("SELECT o.*, f.farmer_name, f.district as region, f.lat, f.lng FROM market_offers o JOIN farmer_profiles f ON o.farm_id = f.user_id WHERE o.id = :id"), {"id": offer_id}).fetchone()
        if not offer:
            return {"error": "not_found"}
        offer_dict = dict(offer._mapping)
        
        buyers = db.execute(text("SELECT user_id as id, name, crops_json, floor_ugx, radius_km, lat, lng, contact FROM buyer_profiles")).fetchall()
        
    candidates = []
    for b in buyers:
        b_dict = dict(b._mapping)
        crops = json.loads(b_dict['crops_json'])
        if offer_dict['crop'] not in crops: continue
        if b_dict['floor_ugx'] < offer_dict['floor_ugx']: continue
        
        dist = _haversine_km(offer_dict['lat'], offer_dict['lng'], b_dict['lat'], b_dict['lng'])
        if dist > b_dict['radius_km'] * 2: continue
        candidates.append({
            "buyer_id": b_dict['id'], "name": b_dict['name'], "price_offered": b_dict['floor_ugx'],
            "distance_km": dist, "contact": b_dict['contact']
        })
    candidates.sort(key=lambda x: x['distance_km'])
    top = candidates[:3]
    ledger.write("MATCH", {"offer_id": offer_id, "matches": [b['buyer_id'] for b in top]})
    return {"offer_id": offer_id, "matches": top}

def list_open_offers(limit: int = 10, farm_id: str | None = None,
                     include_closed: bool = False) -> dict:
    """List offers, newest first. Each row carries `payment_status`
    (none|pending|settled|failed) joined from the payments table so the buyer
    UI can show real fulfilment state without a second round-trip.

    - farm_id: restrict to one farm (used by the farmer dashboard).
    - include_closed: include accepted/closed offers (used by the farmer's
      own listings view so they can see history).
    """
    with database.SessionLocal() as db:
        where = []
        params = {}
        if not include_closed:
            where.append("o.status = 'open'")
        if farm_id:
            where.append("o.farm_id = :farm_id")
            params["farm_id"] = farm_id
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
            SELECT o.id, o.farm_id, o.crop, o.kg, o.floor_ugx, o.status, o.created_at,
                   f.farmer_name, f.district as region, f.lat, f.lng,
                   (SELECT status FROM settlements p
                      WHERE p.offer_id = o.id
                      ORDER BY (CASE p.status WHEN 'settled' THEN 0
                                              WHEN 'pending' THEN 1
                                              ELSE 2 END), p.created_at DESC
                      LIMIT 1) AS payment_status,
                   (SELECT COALESCE(y.yps, 0) FROM yield_priorities y
                      WHERE y.farm_id = o.farm_id
                      ORDER BY y.created_at DESC LIMIT 1) AS yps
              FROM market_offers o
              JOIN farmer_profiles f ON o.farm_id = f.user_id
              {where_sql}
              ORDER BY o.created_at DESC LIMIT :limit
        """
        params["limit"] = limit
        rows = [dict(r._mapping) for r in db.execute(text(sql), params).fetchall()]
    
        total = db.execute(text("SELECT count(*) as total FROM market_offers WHERE status = 'open'")).scalar()
        
    return {"offers": rows, "total_open": total}

_RULE_BANK = {
    "pest": "Inspect leaves for holes. Neem spray every 7 days. Report to extension officer if >20% affected.",
    "water": "Irrigate early morning. Target 25-35%. Mulch to retain.",
    "price": "Check menu 4 for today's price. Offers on menu 5 auto-match 3 buyers.",
    "coffee": "Coffee: prune after harvest, use shade trees.",
    "maize": "Maize: side-dress N at knee-high, weed early."
}

def _gemini_advise(question: str, ctx: dict) -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key: return None
    safe_q = _redact_pii(question or "")[:500]
    
    diagnostics = "\n- ".join(ctx.get('diagnostics', []))
    system_instruction = (
        "You are Mavuno, an expert Ugandan agronomist AI advisor specializing in East African crops. "
        "Your goal is to provide high-quality, actionable advice based on live soil telemetry. "
        f"Farmer Context: {ctx.get('crop')} in {ctx.get('district')}. YPS: {ctx.get('yps')}, Health: {ctx.get('health')}.\n"
        f"Soil State: N:{ctx.get('n')}, P:{ctx.get('p')}, K:{ctx.get('k')} mg/kg.\n"
        f"Recent Alerts:\n- {diagnostics}\n"
        "Be specific about Ugandan pests (e.g. Coffee Berry Borer, Fall Armyworm) and regional rain patterns. "
        "Keep advice concise (under 400 characters) and use **bold** for key actions."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": safe_q}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 600}
    }
    
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def _groq_advise(question: str, ctx: dict) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key: return None
    safe_q = _redact_pii(question or "")[:500]
    
    diagnostics = "\n- ".join(ctx.get('diagnostics', []))
    system = (
        "You are Mavuno, an expert Ugandan agronomist. Advice must be specific to Uganda. "
        f"Crop: {ctx.get('crop')}. District: {ctx.get('district')}. YPS: {ctx.get('yps')}.\n"
        f"Soil: N:{ctx.get('n')}, P:{ctx.get('p')}, K:{ctx.get('k')} mg/kg.\n"
        f"Alerts: {diagnostics}\n"
        "Concise, actionable, **bold** actions. Max 350 chars."
    )
    
    try:
        with httpx.Client(timeout=6.0) as client:
            r = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": safe_q}],
                    "max_tokens": 150, "temperature": 0.2
                }
            )
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

def logistics_advisor(pending_loads: list, market_context: str) -> str:
    """Provides strategic logistics coordination advice using AI."""
    key = os.getenv("GROQ_API_KEY")
    if not key: return "AI Coordinator offline. Please check connectivity."
    
    system = (
        "You are the Mavuno Logistics Coordinator AI. "
        "Analyze the provided pending loads and market context to suggest optimal dispatch strategies. "
        "Focus on fuel efficiency, load consolidation, and urgent pickups. Keep it under 250 characters."
    )
    prompt = f"Pending Loads: {json.dumps(pending_loads)}\nMarket Context: {market_context}"
    
    try:
        with httpx.Client(timeout=4.0) as client:
            r = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    "max_tokens": 100, "temperature": 0.3
                }
            )
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Coordination AI temporarily unavailable. (Err: {str(e)[:20]})"

def advisor(farm_id: str, question: str, make_public: bool = False) -> dict:
    with database.SessionLocal() as db:
        farm = db.execute(text("SELECT crop, district FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
        if not farm: return {"error": "unknown_farm"}
        farm_dict = dict(farm._mapping)
    
    score = scorer.score_farm(farm_id)
    # Extract averages for AI context
    n_avg = sum(score['nutrients']['n']) / len(score['nutrients']['n']) if score.get('nutrients') else 0
    p_avg = sum(score['nutrients']['p']) / len(score['nutrients']['p']) if score.get('nutrients') else 0
    k_avg = sum(score['nutrients']['k']) / len(score['nutrients']['k']) if score.get('nutrients') else 0

    ctx = {
        "crop": farm_dict['crop'], "district": farm_dict['district'],
        "yps": score.get('yps'), "health": score.get('trade_health'),
        "n": round(n_avg, 1), "p": round(p_avg, 1), "k": round(k_avg, 1),
        "diagnostics": score.get('diagnostics', [])
    }
    
    answer = _gemini_advise(question, ctx)
    source = "gemini"
    
    if not answer:
        answer = _groq_advise(question, ctx)
        source = "groq"
    
    if not answer:
        source = "ai-fallback"
        q = (question or "").lower()
        # Advanced Fallback AI
        for k, v in _RULE_BANK.items():
            if k in q: 
                answer = v
                break
        
        if not answer:
            crop = ctx.get('crop', 'crop')
            if 'water' in q or 'irrigate' in q or 'dry' in q:
                answer = f"Based on your YPS {ctx.get('yps')}, {crop} needs consistent moisture. Use your Trade Priority to power the pump early morning."
            elif 'fertilizer' in q or 'npk' in q or 'grow' in q:
                answer = f"Your {crop} health is {ctx.get('health')}. Consider adding organic compost to boost Nitrogen and improve yield."
            elif 'harvest' in q or 'yield' in q:
                answer = f"With a score of {ctx.get('yps')}, your {crop} yield is tracking {ctx.get('health')}. Prepare for harvest securely."
            elif 'disease' in q or 'rot' in q or 'brown' in q or 'yellow' in q:
                answer = f"Watch out for signs of fungal rot in {crop} during humid weeks. Remove affected leaves immediately."
            else:
                answer = f"For {crop} in {ctx.get('district')} (Health: {ctx.get('health')}), ensure consistent monitoring. Dial *165*0# for local extension support."

    if make_public:
        from . import social
        safe_q = _redact_pii(question)
        post_body = f"ðŸŒ± Public Query:\nQ: {safe_q}\nA: {answer}"
        social.create_post(farm_id, post_body)

    ledger.write("ADVISE", {"farm_id": farm_id, "source": source, "public": make_public})
    return {"farm_id": farm_id, "answer": answer, "source": source, "context": ctx}
