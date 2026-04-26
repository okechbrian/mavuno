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

from . import crp, ect, ledger, scorer, ussd, database, payments, chat, social
from .config import HMAC_SECRET

# Idempotent — ensures any newly added tables (e.g. payments) exist on disk.
database.init_db()
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


# --- Chat send rate limit (per sender_id, in-memory) ------------------------
_CHAT_MIN_GAP_SECONDS = 2.0
_chat_last_send: dict[str, float] = {}


def _check_chat_throttle(sender_key: str) -> None:
    now = time.time()
    last = _chat_last_send.get(sender_key, 0.0)
    if now - last < _CHAT_MIN_GAP_SECONDS:
        raise HTTPException(status_code=429, detail="too_many_messages")
    _chat_last_send[sender_key] = now


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
def crp_offers_list(
    limit: int = 50,
    farm_id: str | None = None,
    include_closed: bool = False,
    user: dict = Depends(require_user("buyer", "agent", "farmer")),
):
    """Buyers/agents see all open offers. Farmers may pass ?farm_id= to see
    their own listings, including closed ones via include_closed=true."""
    if user["role"] == "farmer":
        if not farm_id or farm_id != user["subject"]:
            raise HTTPException(status_code=403, detail="not_resource_owner")
    return crp.list_open_offers(limit=limit, farm_id=farm_id, include_closed=include_closed)


class OfferReq(BaseModel):
    farm_id: str = Field(..., max_length=64)
    crop: str = Field(..., max_length=32)
    kg: int = Field(..., gt=0, le=50_000)
    floor_ugx: int = Field(..., gt=0, le=10_000_000)


_ALLOWED_CROPS = {
    "coffee", "maize", "beans", "cassava", "rice", "matoke", "groundnuts",
    "soybeans", "sorghum", "millet", "sweet_potato", "irish_potato",
}


@app.post("/crp/offers")
def crp_offer_create(req: OfferReq, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", req.farm_id, user)
    crop = req.crop.strip().lower().replace(" ", "_")
    if crop not in _ALLOWED_CROPS:
        raise HTTPException(status_code=400, detail="unknown_crop")
    return crp.list_offer(req.farm_id, crop, req.kg, req.floor_ugx)


@app.post("/crp/ask")
def crp_ask(req: dict, user: dict = Depends(require_user("farmer", "agent"))):
    fid = req.get("farm_id")
    require_owner_or_agent("farmer", fid, user)
    question = (req.get("question") or "")[:500]  # hard input cap before reaching Groq
    make_public = bool(req.get("make_public", False))
    return crp.advisor(fid, question, make_public=make_public)


# ============================================================================
# PAYMENTS — Mavuno Pay
# ============================================================================

class PaymentInitiateReq(BaseModel):
    offer_id: str = Field(..., max_length=64)
    msisdn: str = Field(..., max_length=20)
    method: str = Field("mavuno-pay", max_length=16)


@app.post("/payments/initiate")
def payments_initiate(
    req: PaymentInitiateReq,
    request: Request,
    user: dict = Depends(require_user("buyer")),
):
    _check_login_throttle(_client_ip(request))  # reuse the per-IP burst guard
    res = payments.initiate(user["subject"], req.offer_id, req.msisdn, req.method)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.post("/payments/confirm")
async def payments_confirm(request: Request):
    """PSP callback. Body is signed with HMAC_SECRET; we re-sign and compare."""
    body = await request.body()
    sig = request.headers.get("x-mavuno-sig", "")
    expected = payments.callback_signature(body)
    if not hmac.compare_digest(expected, sig):
        return JSONResponse({"error": "bad_signature"}, status_code=401)
    try:
        data = json.loads(body.decode("utf-8"))
        pid = data["payment_id"]
        success = bool(data.get("success", False))
    except (ValueError, KeyError):
        return JSONResponse({"error": "bad_body"}, status_code=400)
    return payments.confirm(pid, success)


def _payment_party_check(p: dict, user: dict) -> None:
    if user["role"] == "agent":
        return
    if user["role"] == "buyer" and user["subject"] == p["buyer_id"]:
        return
    if user["role"] == "farmer" and user["subject"] == p["farm_id"]:
        return
    raise HTTPException(status_code=403, detail="not_payment_party")


@app.get("/payments/status/{payment_id}")
def payments_status(payment_id: str, user: dict = Depends(require_user())):
    p = payments.get(payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return {
        "payment_id": p["id"], "status": p["status"],
        "amount_ugx": p["amount_ugx"], "method": p["method"],
        "created_at": p["created_at"], "settled_at": p["settled_at"],
    }


@app.get("/payments/farmer/{farm_id}")
def payments_for_farm(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return {"payments": payments.for_farm(farm_id)}


@app.get("/payments/buyer/{buyer_id}")
def payments_for_buyer(buyer_id: str, user: dict = Depends(require_user("buyer", "agent"))):
    require_owner_or_agent("buyer", buyer_id, user)
    return {"payments": payments.for_buyer(buyer_id)}


@app.get("/payments/receipt/{payment_id}")
def payments_receipt(payment_id: str, user: dict = Depends(require_user())):
    p = payments.get(payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return payments.receipt(payment_id)


# ============================================================================
# CHAT — offer-scoped buyer <-> farmer messaging (long-poll transport)
# ============================================================================

import asyncio  # noqa: E402  -- local import keeps the top clean for readers


class ChatThreadReq(BaseModel):
    farm_id: str = Field(..., max_length=64)
    offer_id: str | None = Field(default=None, max_length=64)


class ChatMessageReq(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)


def _chat_party_check(thread: dict, user: dict) -> None:
    if user["role"] == "agent":
        return
    if user["role"] == "buyer" and user["subject"] == thread["buyer_id"]:
        return
    if user["role"] == "farmer" and user["subject"] == thread["farm_id"]:
        return
    raise HTTPException(status_code=403, detail="not_chat_party")


@app.post("/chat/threads")
def chat_open_thread(req: ChatThreadReq, user: dict = Depends(require_user("buyer", "agent"))):
    """Idempotent open-or-fetch. Buyers open threads against a farm (optionally
    pinned to an offer). Agents may open on behalf of any buyer for audit."""
    if user["role"] == "buyer":
        buyer_id = user["subject"]
    else:
        # Agent-mode requires an explicit buyer hint in the offer; keep narrow.
        raise HTTPException(status_code=400, detail="agent_open_not_supported")
    res = chat.open_thread(buyer_id, req.farm_id, req.offer_id)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/chat/threads")
def chat_list_threads(user: dict = Depends(require_user())):
    if user["role"] == "farmer":
        return {"threads": chat.threads_for_farm(user["subject"])}
    if user["role"] == "buyer":
        return {"threads": chat.threads_for_buyer(user["subject"])}
    return {"threads": chat.threads_for_agent()}


@app.get("/chat/{thread_id}/messages")
async def chat_get_messages(
    thread_id: str,
    request: Request,
    since: int = 0,
    wait: int = 25,
    user: dict = Depends(require_user()),
):
    """Long-poll read. If `since` is given and no new messages exist yet,
    hold the request up to `wait` seconds (capped at 25 s) before returning.

    The handler breaks out early if the client disconnects, so a closed drawer
    doesn't keep the function warm longer than needed."""
    thread = chat.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)

    wait = max(0, min(int(wait), 25))
    deadline = time.time() + wait
    msgs = chat.messages(thread_id, since_ts=since)
    while not msgs and time.time() < deadline:
        if await request.is_disconnected():
            break
        await asyncio.sleep(1.0)
        msgs = chat.messages(thread_id, since_ts=since)

    # Reader has implicitly seen everything up to "now"; advance their cursor
    # so unread counts settle down without a separate call.
    chat.mark_read(thread_id, user["role"], user["subject"])
    return {"thread_id": thread_id, "messages": msgs}


@app.post("/chat/{thread_id}/messages")
def chat_post_message(
    thread_id: str,
    req: ChatMessageReq,
    user: dict = Depends(require_user()),
):
    thread = chat.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)
    _check_chat_throttle(f"{user['role']}:{user['subject']}")
    res = chat.send(thread_id, user["role"], user["subject"], req.body)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/chat/unread/count")
def chat_unread(user: dict = Depends(require_user())):
    return {"count": chat.unread_count(user["role"], user["subject"])}


# ============================================================================
# MAVUNO SOCIAL — public feed (Tier 2, text-only for demo)
# ============================================================================

class PostCreateReq(BaseModel):
    body: str = Field(..., min_length=1, max_length=300)
    photo_url: str | None = Field(default=None, max_length=500)
    is_verified: bool = Field(default=False)


class ReactReq(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=8)


class FlagReq(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


@app.get("/feed-page", response_class=HTMLResponse)
def feed_page(user: dict = Depends(require_user())):
    return FileResponse(database.ROOT / "app" / "static" / "feed.html")


@app.post("/feed")
def feed_create(req: PostCreateReq, user: dict = Depends(require_user("farmer"))):
    """Only farmers post to the feed — buyers browse and react."""
    res = social.create_post(user["subject"], req.body, req.photo_url, req.is_verified)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/feed")
def feed_list(limit: int = 50, district: str | None = None, user: dict = Depends(require_user())):
    return {"posts": social.feed(limit=max(1, min(int(limit), 100)), district=district)}


@app.get("/feed/{post_id}")
def feed_get(post_id: str, user: dict = Depends(require_user())):
    p = social.get_post(post_id)
    if not p:
        raise HTTPException(status_code=404, detail="post_not_found")
    return p


@app.get("/feed/verified/gallery")
def feed_verified_gallery(user: dict = Depends(require_user())):
    """Returns only posts with verified harvest photos."""
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM posts WHERE hidden = 0 AND is_verified = 1 AND photo_url IS NOT NULL ORDER BY created_at DESC LIMIT 20"
    )
    rows = cur.fetchall()
    conn.close()
    return {"posts": [social._hydrate(r) for r in rows]}


@app.get("/notifications")
def notifications_list(user: dict = Depends(require_user())):
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user["subject"],),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"notifications": rows}


@app.post("/notifications/read")
def notifications_mark_read(user: dict = Depends(require_user())):
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE notifications SET read = 1 WHERE user_id = ?",
        (user["subject"],),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/feed/{post_id}/react")
def feed_react(post_id: str, req: ReactReq, user: dict = Depends(require_user("farmer", "buyer"))):
    res = social.react(post_id, user["role"], user["subject"], req.emoji)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.post("/feed/{post_id}/flag")
def feed_flag(post_id: str, req: FlagReq, user: dict = Depends(require_user())):
    res = social.flag(post_id, user["role"], user["subject"], req.reason)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


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
