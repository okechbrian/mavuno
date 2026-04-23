"""FastAPI app for Mavuno Prototype v2 - Agent Edition."""
from __future__ import annotations
import json
import time
import secrets
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import crp, ect, ledger, scorer, ussd, database

app = FastAPI(title="Mavuno Agent Cockpit")
app.mount("/static", StaticFiles(directory=database.ROOT / "app" / "static"), name="static")

@app.get("/health")
def health(): return {"ok": True, "mode": "agent-cockpit"}

@app.get("/farms")
def farms():
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM farms")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    res = {}
    for r in rows:
        res[r['id']] = {
            "farmer_name": r['farmer_name'], "district": r['district'], "crop": r['crop'],
            "phone": r['phone'], "acres": r['acres'], "gps": {"lat": r['lat'], "lng": r['lng']},
            "pump": {"name": r['pump_name'], "lat": r['pump_lat'], "lng": r['pump_lng']}
        }
    return res

@app.get("/buyers")
def buyers():
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, region, floor_ugx, crops_json FROM buyers")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r['crops'] = json.loads(r['crops_json'])
    conn.close()
    return rows

@app.post("/farms/onboard")
async def onboard(req: dict):
    conn = database.get_db()
    cur = conn.cursor()
    fid = f"UG-{req['district'][:3].upper()}-{secrets.token_hex(2).upper()}"
    cur.execute('''INSERT INTO farms (id, farmer_name, district, crop, phone, acres, pump_name) 
                   VALUES (?,?,?,?,?,?,?)''', 
                (fid, req['name'], req['district'], req['crop'], req['phone'], req['acres'], "EASP-Node-01"))
    conn.commit()
    conn.close()
    ledger.write("ONBOARD", {"farm_id": fid, "name": req['name']})
    return {"ok": True, "farm_id": fid}

@app.post("/buyers/onboard")
async def onboard_buyer(req: dict):
    conn = database.get_db()
    cur = conn.cursor()
    bid = f"BY-{secrets.token_hex(2).upper()}"
    crops_json = json.dumps([c.strip().lower() for c in req.get('crops', '').split(',') if c.strip()])
    
    # We use a default radius of 50km and a default lat/lng based on the region
    lat, lng = 0.0, 32.0 # Fallback
    if req['region'] == "Mbale": lat, lng = 1.08, 34.18
    if req['region'] == "Mbarara": lat, lng = -0.61, 30.65
    if req['region'] == "Gulu": lat, lng = 2.77, 32.30

    cur.execute('''INSERT INTO buyers (id, name, region, crops_json, floor_ugx, radius_km, lat, lng, contact)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (bid, req['name'], req['region'], crops_json, req['floor_ugx'], 50, lat, lng, req['contact']))
    conn.commit()
    conn.close()
    ledger.write("BUYER_ONBOARD", {"buyer_id": bid, "name": req['name']})
    return {"ok": True, "buyer_id": bid}

@app.post("/sensor/telemetry")
async def sensor_telemetry(req: dict):
    """IoT endpoint for physical sensor nodes to transmit the 7 crucial soil signals."""
    conn = database.get_db()
    cur = conn.cursor()
    fid = req.get("farm_id")
    ts = int(time.time())
    
    # 7 Crucial Signals
    sm = req.get("soil_moisture")
    temp = req.get("temp_c")
    rain = req.get("rainfall_mm")
    hum = req.get("humidity_pct")
    n = req.get("n_mg_kg")
    p = req.get("p_mg_kg")
    k = req.get("k_mg_kg")
    
    cur.execute('''INSERT INTO sensor_history 
                   (farm_id, timestamp, soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (fid, ts, sm, temp, rain, hum, n, p, k))
    conn.commit()
    conn.close()
    
    # Update the ledger with an anonymized hash of the telemetry
    ledger.write("SENSOR_PING", {"farm_id": fid, "timestamp": ts, "signals": 7})
    
    # Re-evaluate the farm's score immediately based on new data
    new_score = scorer.score_farm(fid)
    return {"ok": True, "farm_id": fid, "new_yps": new_score.get("yps")}

@app.get("/score/{farm_id}")
def score(farm_id: str): return scorer.score_farm(farm_id)

@app.get("/ect/balance/{farm_id}")
def ect_balance(farm_id: str): return ect.farm_balance(farm_id)

@app.post("/ect/issue")
def ect_issue(req: dict):
    fid = req.get("farm_id")
    s = scorer.score_farm(fid)
    return ect.issue(fid, s['yps'], s['kwh_allocated'])

@app.get("/crp/prices")
def crp_prices(crop: str, region: str = "Eastern"):
    return crp.market_prices(crop, region)

@app.get("/crp/offers")
def crp_offers_list(limit: int = 50):
    return crp.list_open_offers(limit=limit)

@app.post("/crp/ask")
def crp_ask(req: dict):
    return crp.advisor(req.get("farm_id"), req.get("question"))

@app.post("/demo/cycle")
def demo_cycle(req: dict):
    fid = req.get("farm_id")
    s = scorer.score_farm(fid)
    if "error" in s: return s
    t = ect.issue(fid, s['yps'], s['kwh_allocated'])
    if "error" in t: return {"score": s, "ect": t}
    
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT pump_lat, pump_lng FROM farms WHERE id = ?", (fid,))
    f = cur.fetchone()
    conn.close()
    
    r = ect.redeem(t['token_id'], f['pump_lat'], f['pump_lng'], min(10, t['kwh_allocated']))
    return {"score": s, "ect": t, "redeem": r}

@app.post("/ect/bulk-issue")
def bulk_issue():
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms")
    fids = [r["id"] for r in cur.fetchall()]
    conn.close()

    issued = 0
    total_ugx = 0
    for fid in fids:
        s = scorer.score_farm(fid)
        if "error" not in s and s.get("credit_health") == "Excellent":
            t = ect.issue(fid, s["yps"], s["kwh_allocated"])
            if "error" not in t:
                issued += 1
                total_ugx += s.get("credit_ceiling_ugx", 0)

    return {"issued": issued, "total_ugx": total_ugx}

@app.post("/agent/alert")
def agent_alert(req: dict):
    ledger.write("AGENT_ALERT", {"farm_id": req['farm_id'], "type": req['type']})
    return {"ok": True}

@app.get("/ledger")
def ledger_view(): return {"rows": ledger.read_all()}

@app.get("/ledger/verify")
def ledger_verify(): return ledger.verify()

@app.post("/ussd/local")
def ussd_local(req: dict):
    resp = ussd.route(req.get("phone"), req.get("text", ""))
    kind, _, body = resp.partition(" ")
    return {"kind": kind, "body": body}

class LoginReq(BaseModel):
    role: str
    id_or_phone: str
    pin_or_password: str

@app.post("/login")
def login(req: LoginReq):
    conn = database.get_db()
    cur = conn.cursor()
    if req.role == "agent":
        if req.pin_or_password == "mavuno2026":
            return {"ok": True, "redirect": "/agent"}
        return {"error": "Invalid password"}
    elif req.role == "farmer":
        search_id = req.id_or_phone.strip().upper()
        if search_id.startswith("UG-") and len(search_id.split("-")) == 3:
            prefix, region, num = search_id.split("-")
            search_id = f"{prefix}-{region}-{num.zfill(4)}"
        
        cur.execute("SELECT id FROM farms WHERE id = ? OR phone = ?", (search_id, req.id_or_phone))
        f = cur.fetchone()
        if f:
            if req.pin_or_password == "1234":
                return {"ok": True, "redirect": f"/farmer/{f['id']}"}
            return {"error": "Invalid PIN (hint: 1234)"}
        return {"error": "Farmer not found"}
    elif req.role == "buyer":
        search_id = req.id_or_phone.strip().upper()
        if search_id.startswith("BY-") and len(search_id.split("-")) == 2:
            prefix, num = search_id.split("-")
            search_id = f"{prefix}-{num.zfill(3)}"

        cur.execute("SELECT id FROM buyers WHERE id = ? OR contact = ?", (search_id, req.id_or_phone))
        b = cur.fetchone()
        if b:
            if req.pin_or_password == "1234":
                return {"ok": True, "redirect": f"/buyer/{b['id']}"}
            return {"error": "Invalid PIN (hint: 1234)"}
        return {"error": "Buyer not found"}
    return {"error": "Invalid role"}

@app.get("/", response_class=HTMLResponse)
def root(): return FileResponse(database.ROOT / "app" / "static" / "index.html")

@app.get("/agent", response_class=HTMLResponse)
def agent_dash(): return FileResponse(database.ROOT / "app" / "static" / "agent_dashboard.html")

@app.get("/farmer/{farm_id}", response_class=HTMLResponse)
def farmer_dash(farm_id: str): return FileResponse(database.ROOT / "app" / "static" / "farmer_dashboard.html")

@app.get("/buyer/{buyer_id}", response_class=HTMLResponse)
def buyer_dash(buyer_id: str): return FileResponse(database.ROOT / "app" / "static" / "buyer_dashboard.html")

@app.get("/phone", response_class=HTMLResponse)
def phone(): return FileResponse(database.ROOT / "app" / "static" / "phone.html")

@app.get("/terms", response_class=HTMLResponse)
def terms(): return FileResponse(database.ROOT / "app" / "static" / "terms.html")
