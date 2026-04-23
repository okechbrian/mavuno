"""FastAPI app for Mavuno — agent cockpit, farmer/buyer dashboards, USSD demo.

Auth model
----------
- Public:   /, /login, /logout, /terms, /phone, /static/*, /health,
            /crp/prices (public market data), /ussd/local (USSD demo only)
- Auth'd:   every dashboard route + every data/write endpoint
- Owner-scoped: /farmer/{id}, /buyer/{id} and their data routes — the URL
  subject must match the cookie subject (agents bypass via require_owner_or_agent).
"""
from __future__ import annotations
import json
import time
import secrets
import hmac
from collections import deque
from typing import Deque

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import crp, ect, ledger, scorer, ussd, database
from .config import HMAC_SECRET
from .session import (
    COOKIE_NAME,
    clear as session_clear,
    current_user,
    issue as session_issue,
    require_owner_or_agent,
    require_user,
)

app = FastAPI(title="Mavuno")
app.mount("/static", StaticFiles(directory=database.ROOT / "app" / "static"), name="static")

# --- Demo credentials (overridable via env in production) -------------------
import os as _os
_AGENT_PASSWORD = _os.getenv("AGENT_PASSWORD", "mavuno2026")
_FARMER_DEFAULT_PIN = _os.getenv("FARMER_DEFAULT_PIN", "1234")
_BUYER_DEFAULT_PIN = _os.getenv("BUYER_DEFAULT_PIN", "1234")

# --- Lightweight per-IP login throttle (best-effort, in-memory) -------------
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 8
_login_attempts: dict[str, Deque[float]] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_throttle(ip: str) -> None:
    now = time.time()
    bucket = _login_attempts.setdefault(ip, deque())
    while bucket and now - bucket[0] > _LOGIN_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="too_many_attempts")
    bucket.append(now)


# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@app.get("/health")
def health(): return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    user = current_user(request)
    if user:
        if user["role"] == "agent":
            return RedirectResponse("/agent")
        if user["role"] == "farmer":
            return RedirectResponse(f"/farmer/{user['subject']}")
        if user["role"] == "buyer":
            return RedirectResponse(f"/buyer/{user['subject']}")
    return FileResponse(database.ROOT / "app" / "static" / "index.html")


@app.get("/terms", response_class=HTMLResponse)
def terms(): return FileResponse(database.ROOT / "app" / "static" / "terms.html")


@app.get("/phone", response_class=HTMLResponse)
def phone(): return FileResponse(database.ROOT / "app" / "static" / "phone.html")


@app.get("/crp/prices")
def crp_prices(crop: str, region: str = "Eastern"):
    return crp.market_prices(crop, region)


@app.post("/ussd/local")
def ussd_local(req: dict):
    """USSD simulator endpoint — public so the demo phone works without sign-in."""
    resp = ussd.route(req.get("phone"), req.get("text", ""))
    kind, _, body = resp.partition(" ")
    return {"kind": kind, "body": body}


# ============================================================================
# AUTH
# ============================================================================

class LoginReq(BaseModel):
    role: str = Field(..., max_length=16)
    id_or_phone: str = Field("", max_length=64)
    pin_or_password: str = Field("", max_length=128)


@app.post("/login")
def login(req: LoginReq, request: Request, response: Response):
    _check_login_throttle(_client_ip(request))

    if req.role == "agent":
        if hmac.compare_digest(req.pin_or_password, _AGENT_PASSWORD):
            session_issue(response, "agent", "admin")
            return {"ok": True, "redirect": "/agent"}
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    if req.role == "farmer":
        conn = database.get_db()
        cur = conn.cursor()
        search_id = req.id_or_phone.strip().upper()
        if search_id.startswith("UG-") and len(search_id.split("-")) == 3:
            prefix, region, num = search_id.split("-")
            search_id = f"{prefix}-{region}-{num.zfill(4)}"
        cur.execute("SELECT id FROM farms WHERE id = ? OR phone = ?", (search_id, req.id_or_phone.strip()))
        row = cur.fetchone()
        conn.close()
        if row and hmac.compare_digest(req.pin_or_password, _FARMER_DEFAULT_PIN):
            session_issue(response, "farmer", row["id"])
            return {"ok": True, "redirect": f"/farmer/{row['id']}"}
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    if req.role == "buyer":
        conn = database.get_db()
        cur = conn.cursor()
        search_id = req.id_or_phone.strip().upper()
        if search_id.startswith("BY-") and len(search_id.split("-")) == 2:
            prefix, num = search_id.split("-")
            search_id = f"{prefix}-{num.zfill(3)}"
        cur.execute("SELECT id FROM buyers WHERE id = ? OR contact = ?", (search_id, req.id_or_phone.strip()))
        row = cur.fetchone()
        conn.close()
        if row and hmac.compare_digest(req.pin_or_password, _BUYER_DEFAULT_PIN):
            session_issue(response, "buyer", row["id"])
            return {"ok": True, "redirect": f"/buyer/{row['id']}"}
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    return JSONResponse({"error": "Invalid role"}, status_code=400)


@app.post("/logout")
def logout(response: Response):
    session_clear(response)
    return {"ok": True}


@app.get("/logout")
def logout_get():
    """Convenience GET so a plain link can sign out."""
    resp = RedirectResponse("/")
    session_clear(resp)
    return resp


@app.get("/me")
def me(user: dict = Depends(require_user())):
    return {"role": user["role"], "subject": user["subject"], "exp": user["exp"]}


# ============================================================================
# DASHBOARDS (HTML pages — owner-scoped)
# ============================================================================

@app.get("/agent", response_class=HTMLResponse)
def agent_dash(user: dict = Depends(require_user("agent"))):
    return FileResponse(database.ROOT / "app" / "static" / "agent_dashboard.html")


@app.get("/farmer/{farm_id}", response_class=HTMLResponse)
def farmer_dash(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return FileResponse(database.ROOT / "app" / "static" / "farmer_dashboard.html")


@app.get("/buyer/{buyer_id}", response_class=HTMLResponse)
def buyer_dash(buyer_id: str, user: dict = Depends(require_user("buyer", "agent"))):
    require_owner_or_agent("buyer", buyer_id, user)
    return FileResponse(database.ROOT / "app" / "static" / "buyer_dashboard.html")


# ============================================================================
# DATA / WRITE ENDPOINTS — all auth gated
# ============================================================================

@app.get("/farms")
def farms(user: dict = Depends(require_user("agent", "farmer"))):
    """Agents see all farms; farmers see only their own."""
    conn = database.get_db()
    cur = conn.cursor()
    if user["role"] == "agent":
        cur.execute("SELECT * FROM farms")
    else:
        cur.execute("SELECT * FROM farms WHERE id = ?", (user["subject"],))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    res = {}
    for r in rows:
        res[r["id"]] = {
            "farmer_name": r["farmer_name"], "district": r["district"], "crop": r["crop"],
            "phone": r["phone"], "acres": r["acres"],
            "gps": {"lat": r["lat"], "lng": r["lng"]},
            "pump": {"name": r["pump_name"], "lat": r["pump_lat"], "lng": r["pump_lng"]},
        }
    return res


@app.get("/buyers")
def buyers(user: dict = Depends(require_user("agent", "buyer"))):
    """Agents see all buyers; buyers see only themselves."""
    conn = database.get_db()
    cur = conn.cursor()
    if user["role"] == "agent":
        cur.execute("SELECT id, name, region, floor_ugx, crops_json, contact, lat, lng, radius_km FROM buyers")
    else:
        cur.execute(
            "SELECT id, name, region, floor_ugx, crops_json, contact, lat, lng, radius_km FROM buyers WHERE id = ?",
            (user["subject"],),
        )
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["crops"] = json.loads(r["crops_json"])
    conn.close()
    return rows


@app.post("/farms/onboard")
async def onboard(req: dict, user: dict = Depends(require_user("agent"))):
    conn = database.get_db()
    cur = conn.cursor()
    fid = f"UG-{req['district'][:3].upper()}-{secrets.token_hex(2).upper()}"
    cur.execute(
        """INSERT INTO farms (id, farmer_name, district, crop, phone, acres, pump_name)
           VALUES (?,?,?,?,?,?,?)""",
        (fid, req["name"], req["district"], req["crop"], req["phone"], req["acres"], "EASP-Node-01"),
    )
    conn.commit()
    conn.close()
    ledger.write("ONBOARD", {"farm_id": fid, "name": req["name"]})
    return {"ok": True, "farm_id": fid}


@app.post("/buyers/onboard")
async def onboard_buyer(req: dict, user: dict = Depends(require_user("agent"))):
    conn = database.get_db()
    cur = conn.cursor()
    bid = f"BY-{secrets.token_hex(2).upper()}"
    crops_json = json.dumps([c.strip().lower() for c in req.get("crops", "").split(",") if c.strip()])

    lat, lng = 0.0, 32.0
    if req["region"] == "Mbale": lat, lng = 1.08, 34.18
    if req["region"] == "Mbarara": lat, lng = -0.61, 30.65
    if req["region"] == "Gulu": lat, lng = 2.77, 32.30

    cur.execute(
        """INSERT INTO buyers (id, name, region, crops_json, floor_ugx, radius_km, lat, lng, contact)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (bid, req["name"], req["region"], crops_json, req["floor_ugx"], 50, lat, lng, req["contact"]),
    )
    conn.commit()
    conn.close()
    ledger.write("BUYER_ONBOARD", {"buyer_id": bid, "name": req["name"]})
    return {"ok": True, "buyer_id": bid}


@app.post("/sensor/telemetry")
async def sensor_telemetry(req: dict, user: dict = Depends(require_user())):
    """IoT endpoint. In production swap to device API-key auth — for the demo the
    operator (agent or farmer) clicking 'Ping Sensor' is signed in already."""
    conn = database.get_db()
    cur = conn.cursor()
    fid = req.get("farm_id")
    require_owner_or_agent("farmer", fid, user)
    ts = int(time.time())
    cur.execute(
        """INSERT INTO sensor_history
           (farm_id, timestamp, soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fid, ts, req.get("soil_moisture"), req.get("temp_c"), req.get("rainfall_mm"),
         req.get("humidity_pct"), req.get("n_mg_kg"), req.get("p_mg_kg"), req.get("k_mg_kg")),
    )
    conn.commit()
    conn.close()
    ledger.write("SENSOR_PING", {"farm_id": fid, "timestamp": ts, "signals": 7})
    new_score = scorer.score_farm(fid)
    return {"ok": True, "farm_id": fid, "new_yps": new_score.get("yps")}


@app.get("/score/{farm_id}")
def score(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return scorer.score_farm(farm_id)


@app.get("/ect/balance/{farm_id}")
def ect_balance(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return ect.farm_balance(farm_id)


@app.post("/ect/issue")
def ect_issue(req: dict, user: dict = Depends(require_user("agent"))):
    fid = req.get("farm_id")
    s = scorer.score_farm(fid)
    return ect.issue(fid, s["yps"], s["kwh_allocated"])


@app.get("/crp/offers")
def crp_offers_list(limit: int = 50, user: dict = Depends(require_user("buyer", "agent"))):
    return crp.list_open_offers(limit=limit)


@app.post("/crp/ask")
def crp_ask(req: dict, user: dict = Depends(require_user("farmer", "agent"))):
    fid = req.get("farm_id")
    require_owner_or_agent("farmer", fid, user)
    question = (req.get("question") or "")[:500]  # hard input cap before reaching Groq
    return crp.advisor(fid, question)


@app.post("/demo/cycle")
def demo_cycle(req: dict, user: dict = Depends(require_user("agent"))):
    fid = req.get("farm_id")
    s = scorer.score_farm(fid)
    if "error" in s:
        return s
    t = ect.issue(fid, s["yps"], s["kwh_allocated"])
    if "error" in t:
        return {"score": s, "ect": t}

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT pump_lat, pump_lng FROM farms WHERE id = ?", (fid,))
    f = cur.fetchone()
    conn.close()

    r = ect.redeem(t["token_id"], f["pump_lat"], f["pump_lng"], min(10, t["kwh_allocated"]))
    return {"score": s, "ect": t, "redeem": r}


@app.post("/ect/bulk-issue")
def bulk_issue(user: dict = Depends(require_user("agent"))):
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms")
    fids = [r["id"] for r in cur.fetchall()]
    conn.close()

    issued, total_ugx = 0, 0
    for fid in fids:
        s = scorer.score_farm(fid)
        if "error" not in s and s.get("credit_health") == "Excellent":
            t = ect.issue(fid, s["yps"], s["kwh_allocated"])
            if "error" not in t:
                issued += 1
                total_ugx += s.get("credit_ceiling_ugx", 0)
    return {"issued": issued, "total_ugx": total_ugx}


@app.post("/agent/alert")
def agent_alert(req: dict, user: dict = Depends(require_user("agent"))):
    ledger.write("AGENT_ALERT", {"farm_id": req["farm_id"], "type": req["type"]})
    return {"ok": True}


@app.get("/ledger")
def ledger_view(user: dict = Depends(require_user("agent"))):
    return {"rows": ledger.read_all()}


@app.get("/ledger/verify")
def ledger_verify(user: dict = Depends(require_user("agent"))):
    return ledger.verify()
