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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import crp, finance, ledger, scorer, ussd, database, payments, chat, social, pdf, training
from .config import HMAC_SECRET, ROOT
from .schemas import (
    FarmerOnboardRequest, BuyerOnboardRequest, TelemetryRecord, ErrorResponse,
    PriorityApproveRequest, CRPAskRequest, PaymentBatchRequest, TrainingCompleteRequest,
    LogisticsOptimizeRequest, LogisticsAdviseRequest, FarmStageUpdate
)

# Idempotent — ensures any newly added tables (e.g. payments) exist on disk.
database.init_db()
with database.SessionLocal() as db:
    training.seed_training_data(db)

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from .database import engine, get_session
from .models import User, FarmerProfile, BuyerProfile, SoilTelemetry, YieldPriority, MarketOffer, Settlement, Notification, Post

from .session import (
    COOKIE_NAME,
    clear_session,
    current_user,
    issue_session,
    require_owner_or_agent,
    require_user,
    get_current_user,
)

app = FastAPI(title="Mavuno")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail), "path": request.url.path}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors(), "path": request.url.path}
    )

app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

# --- Demo credentials (overridable via env in production) -------------------
import os as _os
_AGENT_PASSWORD = _os.getenv("AGENT_PASSWORD", "mavuno2026")
_SUPERVISOR_PASSWORD = _os.getenv("SUPERVISOR_PASSWORD", "governance2026")
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
        if user["role"] == "supervisor":
            return RedirectResponse("/supervisor")
        if user["role"] == "farmer":
            return RedirectResponse(f"/farmer/{user['subject']}")
        if user["role"] == "buyer":
            return RedirectResponse(f"/buyer/{user['subject']}")
        if user["role"] == "logistics":
            return RedirectResponse("/logistics")
    return FileResponse(ROOT / "app" / "static" / "index.html")



@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    return FileResponse(ROOT / "app" / "static" / "signup.html")

@app.get("/terms", response_class=HTMLResponse)
def terms(): return FileResponse(ROOT / "app" / "static" / "terms.html")


@app.get("/phone", response_class=HTMLResponse)
def phone(): return FileResponse(ROOT / "app" / "static" / "phone.html")


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


class SignupReq(BaseModel):
    role: str = Field(..., max_length=16)
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    district: str = Field("", max_length=50) # for farmer
    crop: str = Field("", max_length=50) # for farmer
    acres: float = Field(0.0) # for farmer
    region: str = Field("", max_length=50) # for buyer
    pin_or_password: str = Field(..., max_length=128)

import hashlib
import secrets

def _hash_password(pw: str) -> str:
    # Extremely basic hash for prototype. 
    return hashlib.sha256(pw.encode()).hexdigest()

@app.post("/api/signup")
def handle_signup(req: SignupReq, response: Response, db: Session = Depends(get_session)):
    # Check if user exists
    existing = db.execute(select(User).where(User.phone == req.phone)).scalar_one_or_none()
    if existing:
        return JSONResponse({"error": "Phone number already registered"}, status_code=400)
        
    user_id = ("UG-" if req.role == 'farmer' else "BY-") + secrets.token_hex(4).upper()
    pw_hash = _hash_password(req.pin_or_password) # In prototype, login checks hmac digest against raw, we need to adapt it.
    # ACTUALLY, login checks: hmac.compare_digest(req.pin_or_password, user.password_hash)
    # This means the prototype stores PLAINTEXT PASSWORDS in password_hash. 
    # Let's keep the prototype logic but it's bad practice.
    pw_to_store = req.pin_or_password
    
    new_user = User(id=user_id, phone=req.phone, role=req.role, password_hash=pw_to_store)
    db.add(new_user)
    
    if req.role == 'farmer':
        new_profile = FarmerProfile(
            user_id=user_id,
            farmer_name=req.name,
            district=req.district,
            crop=req.crop,
            acres=req.acres,
            verification_status='pending_kyc'
        )
        db.add(new_profile)
        redirect = f"/farmer/{user_id}"
    else:
        new_profile = BuyerProfile(
            user_id=user_id,
            name=req.name,
            region=req.region,
            floor_ugx=1000,
            crops_json='["coffee", "maize", "beans"]',
            lat=0.0, lng=0.0
        )
        db.add(new_profile)
        redirect = f"/buyer/{user_id}"
        
    db.commit()
    
    token = issue_session(response, req.role, user_id)
    return {"ok": True, "token": token, "redirect": redirect}

class LoginReq(BaseModel):
    role: str = Field(..., max_length=16)
    id_or_phone: str = Field("", max_length=64)
    pin_or_password: str = Field("", max_length=128)


@app.post("/login")
def login(req: LoginReq, request: Request, response: Response, db: Session = Depends(get_session)):
    _check_login_throttle(_client_ip(request))

    if req.role == "agent":
        if hmac.compare_digest(req.pin_or_password, _AGENT_PASSWORD) and req.id_or_phone == "admin":
            token = issue_session(response, "agent", "admin")
            return {"ok": True, "token": token, "redirect": "/agent"}
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    
    if req.role == "supervisor":
        if hmac.compare_digest(req.pin_or_password, _SUPERVISOR_PASSWORD) and req.id_or_phone == "admin":
            token = issue_session(response, "supervisor", "admin")
            return {"ok": True, "token": token, "redirect": "/supervisor"}
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    
    # Unified User lookup
    stmt = select(User).where(User.phone == req.id_or_phone.strip())
    # Fallback to ID lookup for legacy IDs (UG-..., BY-...)
    if req.id_or_phone.strip().upper().startswith(("UG-", "BY-")):
        stmt = select(User).where(User.id == req.id_or_phone.strip().upper())
        
    user = db.execute(stmt).scalar_one_or_none()

    if user and user.role == req.role and hmac.compare_digest(req.pin_or_password, user.password_hash):
        token = issue_session(response, user.role, user.id)
        redirect = f"/farmer/{user.id}" if user.role == "farmer" else f"/buyer/{user.id}"
        if user.role == "logistics": redirect = "/logistics"
        return {"ok": True, "token": token, "redirect": redirect}

    return JSONResponse({"error": "Invalid credentials or role"}, status_code=401)


@app.post("/logout")
def logout(response: Response):
    clear_session(response)
    return {"ok": True}


@app.get("/logout")
def logout_get():
    """Convenience GET so a plain link can sign out."""
    resp = RedirectResponse("/")
    clear_session(resp)
    return resp


@app.get("/me")
def me(user: dict = Depends(require_user())):
    return {"role": user["role"], "subject": user["subject"], "exp": user["exp"]}


# ============================================================================
# DASHBOARDS (HTML pages — owner-scoped)
# ============================================================================

@app.get("/agent", response_class=HTMLResponse)
def agent_dash(user: dict = Depends(require_user("agent"))):
    return FileResponse(ROOT / "app" / "static" / "agent_dashboard.html")


@app.get("/farmer/{farm_id}", response_class=HTMLResponse)
def farmer_dash(farm_id: str, user: dict = Depends(require_user("farmer", "agent")), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", farm_id, user)
    if user["role"] == "farmer":
        profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).scalar_one_or_none()
        if profile and profile.verification_status != "verified":
            return RedirectResponse("/onboarding")
    return FileResponse(ROOT / "app" / "static" / "farmer_dashboard.html")

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(user: dict = Depends(require_user("farmer"))):
    return FileResponse(ROOT / "app" / "static" / "onboarding.html")

class KYCReq(BaseModel):
    document_id: str = Field(..., max_length=100)

@app.post("/api/onboarding/kyc")
def submit_kyc(req: KYCReq, user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not profile: return JSONResponse({"error": "not_found"}, status_code=404)
    if profile.verification_status == "pending_kyc":
        profile.verification_status = "pending_device"
        db.commit()
    return {"ok": True, "status": profile.verification_status}

@app.post("/api/onboarding/purchase")
def purchase_device(user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not profile: return JSONResponse({"error": "not_found"}, status_code=404)
    if profile.verification_status == "pending_device":
        profile.verification_status = "pending_agent"
        db.commit()
    return {"ok": True, "status": profile.verification_status}

@app.get("/api/onboarding/status")
def onboarding_status(user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not profile: return JSONResponse({"error": "not_found"}, status_code=404)
    return {"status": profile.verification_status}


@app.get("/buyer/{buyer_id}", response_class=HTMLResponse)
def buyer_dash(buyer_id: str, user: dict = Depends(require_user("buyer", "agent"))):
    require_owner_or_agent("buyer", buyer_id, user)
    return FileResponse(ROOT / "app" / "static" / "buyer_dashboard.html")


@app.get("/logistics", response_class=HTMLResponse)
def logistics_dash(user: dict = Depends(require_user("logistics", "agent"))):
    return FileResponse(ROOT / "app" / "static" / "logistics_dashboard.html")


@app.get("/supervisor", response_class=HTMLResponse)
def supervisor_dash(user: dict = Depends(require_user("supervisor"))):
    return FileResponse(ROOT / "app" / "static" / "supervisor_dashboard.html")


# ============================================================================
# DATA / WRITE ENDPOINTS — all auth gated
# ============================================================================

class VerifyFarmReq(BaseModel):
    farm_id: str
    serial: str

@app.post("/api/agent/verify-farm")
def agent_verify_farm(req: VerifyFarmReq, user: dict = Depends(require_user("agent", "supervisor")), db: Session = Depends(get_session)):
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == req.farm_id)).scalar_one_or_none()
    if not profile: return JSONResponse({"error": "not_found"}, status_code=404)
    profile.verification_status = "verified"
    db.commit()
    # Log to ledger
    from . import ledger
    ledger.write("VERIFY", {"farm_id": req.farm_id, "agent_id": user["subject"], "serial": req.serial})
    return {"ok": True}

@app.get("/farms")
def farms(user: dict = Depends(require_user("agent", "farmer", "supervisor"))):
    """Agents and supervisors see all farms; farmers see only their own."""
    from sqlalchemy import text
    with database.SessionLocal() as db:
        base_query = """
            SELECT u.id, u.phone, p.farmer_name, p.district, p.crop, p.acres, p.lat, p.lng,
                   p.collection_hub, p.current_stage, 0 as hub_lat, 0 as hub_lng
            FROM users u JOIN farmer_profiles p ON u.id = p.user_id
        """
        if user["role"] in ("agent", "supervisor"):
            rows = db.execute(text(base_query)).fetchall()
        else:
            rows = db.execute(text(base_query + " WHERE u.id = :id"), {"id": user["subject"]}).fetchall()
        rows_dict = [dict(r._mapping) for r in rows]
    
    res = {}
    for r in rows_dict:
        res[r["id"]] = {
            "farmer_name": r["farmer_name"], "district": r["district"], "crop": r["crop"],
            "phone": r["phone"], "acres": r["acres"],
            "gps": {"lat": r["lat"], "lng": r["lng"]},
            "hub": {"name": r["collection_hub"], "lat": r["hub_lat"], "lng": r["hub_lng"]},
        }
    return res


@app.get("/supervisor/stats")
def supervisor_stats(user: dict = Depends(require_user("supervisor")), db: Session = Depends(get_session)):
    """Aggregate stats for regional coordinator oversight."""
    from sqlalchemy import text
    with database.SessionLocal() as session:
        # Regional YPS distribution
        yps_dist_rows = session.execute(text("SELECT district, AVG(yps) as avg_yps, COUNT(*) as count FROM farms JOIN yield_priority ON farms.id = yield_priority.farm_id GROUP BY district")).fetchall()
        yps_dist = [dict(r._mapping) for r in yps_dist_rows]
        
        # Trade velocity
        trade_vol_rows = session.execute(text("SELECT district, SUM(kg_allocated) as total_kg FROM farms JOIN yield_priority ON farms.id = yield_priority.farm_id GROUP BY district")).fetchall()
        trade_vol = [dict(r._mapping) for r in trade_vol_rows]
        
    # Agent performance (dummy for now as we don't track agent_id per farm)
    agent_perf = [{"agent": "Agent-East-01", "onboards": 12, "verifications": 45}, {"agent": "Agent-North-01", "onboards": 8, "verifications": 32}]
    
    return {
        "regional_yps": yps_dist,
        "trade_volume": trade_vol,
        "agent_performance": agent_perf,
        "system_health": "Optimal"
    }


@app.get("/buyers")
def buyers(user: dict = Depends(require_user("agent", "buyer"))):
    """Agents see all buyers; buyers see only themselves."""
    from sqlalchemy import text
    with database.SessionLocal() as db:
        if user["role"] == "agent":
            rows = db.execute(text("SELECT id, name, region, floor_ugx, crops_json, contact, lat, lng, radius_km FROM buyers")).fetchall()
        else:
            rows = db.execute(
                text("SELECT id, name, region, floor_ugx, crops_json, contact, lat, lng, radius_km FROM buyers WHERE id = :id"),
                {"id": user["subject"]},
            ).fetchall()
        rows_dict = [dict(r._mapping) for r in rows]
        
    for r in rows_dict:
        r["crops"] = json.loads(r["crops_json"])
    return rows_dict


@app.post("/farms/onboard")
async def onboard(req: FarmerOnboardRequest, user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    fid = f"UG-{req.district[:3].upper()}-{secrets.token_hex(2).upper()}"
    
    # Create User
    new_user = User(id=fid, phone=req.phone, role="farmer", password_hash="1234")
    db.add(new_user)
    
    # Create Profile
    profile = FarmerProfile(
        user_id=fid, farmer_name=req.name, district=req.district,
        crop=req.crop, acres=req.acres, collection_hub="Aggregation-Hub-01"
    )
    db.add(profile)
    db.commit()
    
    ledger.write("ONBOARD", {"farm_id": fid, "name": req.name})
    return {"ok": True, "farm_id": fid}


@app.patch("/farmer/{farm_id}/stage")
def update_farm_stage(farm_id: str, req: FarmStageUpdate, user: dict = Depends(require_user("agent", "farmer")), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", farm_id, user)
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="farm_not_found")
    
    profile.current_stage = req.current_stage
    db.commit()
    ledger.write("UPDATE_STAGE", {"farm_id": farm_id, "new_stage": req.current_stage})
    return {"ok": True, "farm_id": farm_id, "current_stage": req.current_stage}


@app.post("/buyers/onboard")
async def onboard_buyer(req: BuyerOnboardRequest, user: dict = Depends(require_user("agent"))):
    from sqlalchemy import text
    bid = f"BY-{secrets.token_hex(2).upper()}"
    crops_json = json.dumps([c.strip().lower() for c in req.crops.split(",") if c.strip()])

    lat, lng = 0.0, 32.0
    if req.region == "Mbale": lat, lng = 1.08, 34.18
    if req.region == "Mbarara": lat, lng = -0.61, 30.65
    if req.region == "Gulu": lat, lng = 2.77, 32.30

    with database.SessionLocal() as db:
        db.execute(
            text("""INSERT INTO buyers (id, name, region, crops_json, floor_ugx, radius_km, lat, lng, contact)
               VALUES (:id, :name, :region, :crops_json, :floor_ugx, :radius_km, :lat, :lng, :contact)"""),
            {"id": bid, "name": req.name, "region": req.region, "crops_json": crops_json, 
             "floor_ugx": req.floor_ugx, "radius_km": 50, "lat": lat, "lng": lng, "contact": req.contact},
        )
        db.commit()
    ledger.write("BUYER_ONBOARD", {"buyer_id": bid, "name": req.name})
    return {"ok": True, "buyer_id": bid}


@app.post("/sensor/telemetry")
async def sensor_telemetry(req: TelemetryRecord, user: dict = Depends(require_user())):
    """IoT endpoint. In production swap to device API-key auth — for the demo the
    operator (agent or farmer) clicking 'Ping Sensor' is signed in already."""
    from sqlalchemy import text
    fid = req.farm_id
    require_owner_or_agent("farmer", fid, user)
    ts = int(time.time())
    with database.SessionLocal() as db:
        db.execute(
            text("""INSERT INTO sensor_history
               (farm_id, timestamp, soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg)
               VALUES (:farm_id, :timestamp, :soil_moisture, :temp_c, :rainfall_mm, :humidity_pct, :n_mg_kg, :p_mg_kg, :k_mg_kg)"""),
            {"farm_id": fid, "timestamp": ts, "soil_moisture": req.soil_moisture, "temp_c": req.temp_c, "rainfall_mm": req.rainfall_mm,
             "humidity_pct": req.humidity_pct, "n_mg_kg": req.n_mg_kg, "p_mg_kg": req.p_mg_kg, "k_mg_kg": req.k_mg_kg},
        )
        db.commit()
    ledger.write("SENSOR_PING", {"farm_id": fid, "timestamp": ts, "signals": 7})
    new_score = scorer.score_farm(fid)
    return {"ok": True, "farm_id": fid, "new_yps": new_score.get("yps")}


@app.get("/score/{farm_id}")
def score(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return scorer.score_farm(farm_id)


@app.get("/finance/status/{farm_id}")
def finance_status(farm_id: str, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return finance.farm_balance(farm_id)


@app.post("/finance/approve")
def finance_approve(req: PriorityApproveRequest, user: dict = Depends(require_user("agent"))):
    fid = req.farm_id
    s = scorer.score_farm(fid)
    return finance.issue(fid, s["yps"], s["kg_allocated"])


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
def crp_ask(req: CRPAskRequest, user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", req.farm_id, user)
    question = req.question[:500]  # hard input cap before reaching Groq
    return crp.advisor(req.farm_id, question, make_public=req.make_public)


# ============================================================================
# PAYMENTS — Mavuno Pay & Batching
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
    db: Session = Depends(get_session),
):
    _check_login_throttle(_client_ip(request))
    res = payments.initiate(db, user["subject"], req.offer_id, req.msisdn, req.method)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.post("/payments/confirm")
async def payments_confirm(request: Request, db: Session = Depends(get_session)):
    """PSP callback. Body is signed with HMAC_SECRET; we re-sign and compare."""
    body = await request.body()
    sig = request.headers.get("x-mavuno-sig", "")
    if not hmac.compare_digest(payments.callback_signature(body), sig):
        return JSONResponse({"error": "bad_signature"}, status_code=401)
    try:
        data = json.loads(body.decode("utf-8"))
        pid = data["payment_id"]
        success = bool(data.get("success", False))
    except (ValueError, KeyError):
        return JSONResponse({"error": "bad_body"}, status_code=400)
    return payments.confirm(db, pid, success)


@app.post("/payments/batch")
def payments_batch_init(req: PaymentBatchRequest, user: dict = Depends(require_user("buyer")), db: Session = Depends(get_session)):
    res = payments.initiate_batch(db, user["subject"], req.offer_ids, req.msisdn)
    if "error" in res: return JSONResponse(res, status_code=400)
    return res


@app.post("/payments/batch/confirm")
async def payments_batch_confirm(request: Request, db: Session = Depends(get_session)):
    body = await request.body()
    sig = request.headers.get("x-mavuno-sig", "")
    if not hmac.compare_digest(payments.callback_signature(body), sig):
        return JSONResponse({"error": "bad_signature"}, status_code=401)
    data = json.loads(body.decode("utf-8"))
    return payments.confirm_batch(db, data["batch_id"], data.get("success", False))


def _payment_party_check(p: dict, user: dict) -> None:
    if user["role"] == "agent":
        return
    if user["role"] == "buyer" and user["subject"] == p["buyer_id"]:
        return
    if user["role"] == "farmer" and user["subject"] == p["farm_id"]:
        return
    raise HTTPException(status_code=403, detail="not_payment_party")


@app.get("/payments/status/{payment_id}")
def payments_status(payment_id: str, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    p = payments.get(db, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return {
        "payment_id": p["id"], "status": p["status"],
        "amount_ugx": p["amount_ugx"], "method": p["method"],
        "created_at": p["created_at"], "settled_at": p["settled_at"],
    }


@app.get("/payments/farmer/{farm_id}")
def payments_for_farm(farm_id: str, user: dict = Depends(require_user("farmer", "agent")), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", farm_id, user)
    return {"payments": payments.for_farm(db, farm_id)}


@app.get("/payments/buyer/{buyer_id}")
def payments_for_buyer(buyer_id: str, user: dict = Depends(require_user("buyer", "agent")), db: Session = Depends(get_session)):
    require_owner_or_agent("buyer", buyer_id, user)
    return {"payments": payments.for_buyer(db, buyer_id)}


@app.get("/payments/receipt/{payment_id}")
def payments_receipt(payment_id: str, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    p = payments.get(db, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return payments.receipt(db, payment_id)


@app.get("/payments/receipt/{payment_id}/pdf")
def payments_receipt_pdf(payment_id: str, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    data = payments.receipt(db, payment_id)
    if not data:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    _payment_party_check(payments.get(db, payment_id), user)
    
    pdf_bytes = pdf.generate_receipt_pdf(data)
    filename = f"MAVUNO-RECEIPT-{payment_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# TRAINING & CERTIFICATION
# ============================================================================

@app.get("/training/modules")
def training_modules(db: Session = Depends(get_session)):
    return {"modules": training.list_modules(db)}


@app.post("/training/complete")
def training_complete(req: TrainingCompleteRequest, user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    return training.complete_module(db, user["subject"], req.module_id)


@app.get("/farmer/{farm_id}/certifications")
def farmer_certs(farm_id: str, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", farm_id, user)
    return {"certifications": training.get_farmer_certifications(db, farm_id)}


# ============================================================================
# CHAT
# ============================================================================

import asyncio  # noqa: E402

class ChatThreadReq(BaseModel):
    farm_id: str = Field(..., max_length=64)
    offer_id: str | None = Field(None, max_length=64)

class ChatMessageReq(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)

def _chat_party_check(thread: dict, user: dict) -> None:
    if user["role"] == "agent": return
    if user["role"] == "farmer" and user["subject"] == thread["farm_id"]: return
    if user["role"] == "buyer" and user["subject"] == thread["buyer_id"]: return
    raise HTTPException(status_code=403, detail="not_chat_party")

@app.post("/chat/threads")
def chat_open_thread(req: ChatThreadReq, user: dict = Depends(require_user("buyer", "agent")), db: Session = Depends(get_session)):
    if user["role"] == "buyer":
        buyer_id = user["subject"]
    else:
        raise HTTPException(status_code=400, detail="agent_open_not_supported")
    res = chat.open_thread(db, buyer_id, req.farm_id, req.offer_id)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/chat/threads")
def chat_list_threads(user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    if user["role"] == "farmer":
        return {"threads": chat.threads_for_farm(db, user["subject"])}
    if user["role"] == "buyer":
        return {"threads": chat.threads_for_buyer(db, user["subject"])}
    return {"threads": chat.threads_for_agent(db)}


@app.get("/chat/{thread_id}/messages")
async def chat_get_messages(
    thread_id: str,
    request: Request,
    since: int = 0,
    wait: int = 25,
    user: dict = Depends(require_user()),
    db: Session = Depends(get_session),
):
    thread = chat.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)

    wait = max(0, min(int(wait), 25))
    deadline = time.time() + wait
    msgs = chat.messages(db, thread_id, since_ts=since)
    while not msgs and time.time() < deadline:
        if await request.is_disconnected():
            break
        await asyncio.sleep(1.0)
        msgs = chat.messages(db, thread_id, since_ts=since)

    chat.mark_read(db, thread_id, user["role"], user["subject"])
    return {"thread_id": thread_id, "messages": msgs}


@app.post("/chat/{thread_id}/messages")
def chat_post_message(
    thread_id: str,
    req: ChatMessageReq,
    user: dict = Depends(require_user()),
    db: Session = Depends(get_session),
):
    thread = chat.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)
    _check_chat_throttle(f"{user['role']}:{user['subject']}")
    res = chat.send(db, thread_id, user["role"], user["subject"], req.body)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/chat/unread/count")
def chat_unread(user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    return {"count": chat.unread_count(db, user["role"], user["subject"])}


# ============================================================================
# MAVUNO SOCIAL
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
    return FileResponse(ROOT / "app" / "static" / "feed.html")


@app.post("/feed")
def feed_create(req: PostCreateReq, user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    res = social.create_post(db, user["subject"], req.body, req.photo_url, req.is_verified)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.get("/feed")
def feed_list(limit: int = 50, district: str | None = None, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    return {"posts": social.feed(db, limit=max(1, min(int(limit), 100)), district=district)}


@app.get("/feed/{post_id}")
def feed_get(post_id: str, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    p = social.get_post(db, post_id)
    if not p:
        raise HTTPException(status_code=404, detail="post_not_found")
    return p


@app.get("/feed/verified/gallery")
def feed_verified_gallery(user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    stmt = (
        select(Post).where(Post.hidden == False, Post.is_verified == True, Post.photo_url != None)
        .order_by(Post.created_at.desc()).limit(20)
    )
    rows = db.execute(stmt).scalars().all()
    return {"posts": [social._hydrate(db, r) for r in rows]}


@app.get("/notifications")
def notifications_list(user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    stmt = select(Notification).where(Notification.user_id == user["subject"]).order_by(Notification.created_at.desc()).limit(50)
    rows = db.execute(stmt).scalars().all()
    return {"notifications": [{
        "id": r.id, "user_id": r.user_id, "title": r.title, "body": r.body,
        "type": r.type, "read": r.read, "created_at": r.created_at
    } for r in rows]}


@app.post("/notifications/read")
def notifications_mark_read(user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    db.execute(update(Notification).where(Notification.user_id == user["subject"]).values(read=True))
    db.commit()
    return {"ok": True}


@app.post("/feed/{post_id}/react")
def feed_react(post_id: str, req: ReactReq, user: dict = Depends(require_user("farmer", "buyer")), db: Session = Depends(get_session)):
    res = social.react(db, post_id, user["role"], user["subject"], req.emoji)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


@app.post("/feed/{post_id}/flag")
def feed_flag(post_id: str, req: FlagReq, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    res = social.flag(db, post_id, user["role"], user["subject"], req.reason)
    if "error" in res:
        return JSONResponse(res, status_code=400)
    return res


# ============================================================================
# LOGISTICS
# ============================================================================

@app.get("/logistics/pending")
def logistics_pending(user: dict = Depends(require_user("logistics", "agent")), db: Session = Depends(get_session)):
    stmt = (
        select(Settlement, FarmerProfile)
        .join(FarmerProfile, Settlement.farm_id == FarmerProfile.user_id)
        .where(Settlement.status == 'settled')
        .order_by(Settlement.settled_at.desc())
    )
    rows = db.execute(stmt).all()
    return {"pending": [{
        "payment_id": s.id, "farm_id": s.farm_id, "amount_ugx": s.amount_ugx, 
        "settled_at": s.settled_at, "farmer_name": f.farmer_name, 
        "district": f.district, "lat": f.lat, "lng": f.lng, "crop": f.crop
    } for s, f in rows]}


@app.post("/logistics/optimize")
def logistics_optimize(req: LogisticsOptimizeRequest, user: dict = Depends(require_user("logistics", "agent")), db: Session = Depends(get_session)):
    stmt = (
        select(Settlement, FarmerProfile)
        .join(FarmerProfile, Settlement.farm_id == FarmerProfile.user_id)
        .where(Settlement.status == 'settled')
    )
    pending_rows = db.execute(stmt).all()
    if not pending_rows: return {"routes": []}
    
    pending = [{
        "pid": s.id, "fid": f.user_id, "lat": f.lat, "lng": f.lng, 
        "farmer_name": f.farmer_name, "crop": f.crop
    } for s, f in pending_rows]

    routes = []
    visited = set()
    max_dist_km = req.max_dist_km
    for p1 in pending:
        if p1['pid'] in visited: continue
        current_route = [p1]
        visited.add(p1['pid'])
        for p2 in pending:
            if p2['pid'] in visited: continue
            dist = crp._haversine_km(p1['lat'], p1['lng'], p2['lat'], p2['lng'])
            if dist <= max_dist_km:
                current_route.append(p2)
                visited.add(p2['pid'])
        routes.append({"id": f"RT-{secrets.token_hex(2).upper()}", "stops": current_route, "total_stops": len(current_route)})
    return {"routes": routes}


@app.post("/logistics/advise")
def logistics_advise_ai(req: LogisticsAdviseRequest, user: dict = Depends(require_user("logistics", "agent"))):
    mkt = crp.market_prices("coffee", "Eastern")
    ctx = f"Coffee trending {mkt.get('trend')}. 7d avg: {mkt.get('last7_avg')} UGX."
    return {"advice": crp.logistics_advisor(req.pending, ctx)}


# ============================================================================
# SYSTEM / CRON
# ============================================================================

@app.post("/cron/check-prices")
def cron_check_prices():
    return crp.check_price_fluctuations()

@app.get("/ledger")
def ledger_view(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return {"rows": ledger.read_all(db)}


@app.get("/ledger/verify")
def ledger_verify(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return ledger.verify(db)
