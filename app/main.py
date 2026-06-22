"""FastAPI app for Mavuno — agent cockpit, farmer/buyer dashboards, USSD demo.

Auth model
----------
- Public:   /, /login, /logout, /terms, /phone, /static/*, /health,
            /crp/prices (public market data), /ussd/gateway (Real USSD), /ussd/local (Sim)
- Auth'd:   every dashboard route + every data/write endpoint
- Owner-scoped: /farmer/{id}, /buyer/{id} and their data routes
"""
from __future__ import annotations
import json
import time
import secrets
import hmac
import asyncio
from collections import deque
from typing import Deque, Optional, List

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status, Form, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, update, text
from sqlalchemy.orm import Session

from . import crp, finance, ledger, scorer, ussd, database, payments, chat, social, pdf, training, store, logistics, notifications, hardware
from .config import HMAC_SECRET, ROOT, PUBLIC_BASE_URL
from .database import engine, get_session, SessionLocal
from .models import User, FarmerProfile, BuyerProfile, SoilTelemetry, YieldPriority, MarketOffer, Settlement, Notification, Post, Conversation, Message
from .gateways import send_sms, initiate_fw_payment, verify_fw_transaction
from .session import (
    COOKIE_NAME, clear_session, current_user, issue_session,
    require_owner_or_agent, require_user, get_current_user,
)
from .schemas import (
    FarmerOnboardRequest, BuyerOnboardRequest, TelemetryRecord, ErrorResponse,
    PriorityApproveRequest, CRPAskRequest, PaymentBatchRequest, TrainingCompleteRequest,
    LogisticsOptimizeRequest, LogisticsAdviseRequest, FarmStageUpdate,
    ChatThreadReq, ChatMessageReq
)

# Idempotent startup
database.init_db()
with SessionLocal() as db:
    training.seed_training_data(db)
    database.seed_from_json(db)

app = FastAPI(title="Mavuno")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail), "path": request.url.path})

app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

# --- Demo credentials ---
import os as _os
_AGENT_PASSWORD = _os.getenv("AGENT_PASSWORD", "mavuno2026")
_SUPERVISOR_PASSWORD = _os.getenv("SUPERVISOR_PASSWORD", "governance2026")

# --- Throttling ---
_login_attempts: dict[str, Deque[float]] = {}
def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")

def _check_login_throttle(ip: str):
    now = time.time()
    bucket = _login_attempts.setdefault(ip, deque())
    while bucket and now - bucket[0] > 60: bucket.popleft()
    if len(bucket) >= 8: raise HTTPException(status_code=429, detail="too_many_attempts")
    bucket.append(now)

_chat_last_send: dict[str, float] = {}
def _check_chat_throttle(sender_key: str):
    now = time.time()
    if now - _chat_last_send.get(sender_key, 0.0) < 2.0: raise HTTPException(status_code=429, detail="too_many_messages")
    _chat_last_send[sender_key] = now

# ============================================================================
# PUBLIC & GATEWAY ROUTES
# ============================================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": database.get_engine_name(),
        "timestamp": int(time.time())
    }

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    user = current_user(request)
    if user:
        if user["role"] == "agent": return RedirectResponse("/agent")
        if user["role"] == "supervisor": return RedirectResponse("/supervisor")
        if user["role"] == "farmer": return RedirectResponse(f"/farmer/{user['subject']}")
        if user["role"] == "buyer": return RedirectResponse(f"/buyer/{user['subject']}")
        if user["role"] == "logistics": return RedirectResponse("/logistics")
    return FileResponse(ROOT / "app" / "static" / "index.html")

@app.post("/ussd/gateway")
async def ussd_gateway(sessionId: str = Form(...), serviceCode: str = Form(...), phoneNumber: str = Form(...), text: str = Form("")):
    """Production USSD gateway for AfricasTalking."""
    resp = ussd.route(phoneNumber, text)
    return Response(content=resp, media_type="text/plain")

@app.post("/ussd/local")
def ussd_local(req: dict):
    """USSD simulator endpoint."""
    resp = ussd.route(req.get("phone"), req.get("text", ""))
    kind, _, body = resp.partition(" ")
    return {"kind": kind, "body": body}

@app.post("/payments/fw-webhook")
async def fw_webhook(request: Request, db: Session = Depends(get_session)):
    """Webhook for Flutterwave payment notifications."""
    from .gateways import FW_SECRET_KEY
    sig = request.headers.get("verif-hash")
    if FW_SECRET_KEY and sig != FW_SECRET_KEY: return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    if data.get("status") == "successful":
        tx_id, tx_ref = data.get("data", {}).get("id"), data.get("data", {}).get("tx_ref")
        v = await verify_fw_transaction(tx_id)
        if v.get("status") == "success": payments.confirm(db, tx_ref, True)
    return {"status": "received"}

# ============================================================================
# AUTH & DASHBOARDS
# ============================================================================

class LoginReq(BaseModel):
    role: str
    id_or_phone: str
    pin_or_password: str

@app.post("/login")
def login(req: LoginReq, request: Request, response: Response, db: Session = Depends(get_session)):
    _check_login_throttle(_client_ip(request))
    if req.role == "agent" and hmac.compare_digest(req.pin_or_password, _AGENT_PASSWORD) and req.id_or_phone == "admin":
        return {"ok": True, "token": issue_session(response, "agent", "admin"), "redirect": "/agent"}
    if req.role == "supervisor" and hmac.compare_digest(req.pin_or_password, _SUPERVISOR_PASSWORD) and req.id_or_phone == "admin":
        return {"ok": True, "token": issue_session(response, "supervisor", "admin"), "redirect": "/supervisor"}
    
    stmt = select(User).where((User.phone == req.id_or_phone) | (User.id == req.id_or_phone.upper()))
    user = db.execute(stmt).scalar_one_or_none()
    if user and user.role == req.role and hmac.compare_digest(req.pin_or_password, user.password_hash):
        token = issue_session(response, user.role, user.id)
        red = f"/farmer/{user.id}" if user.role == "farmer" else (f"/buyer/{user.id}" if user.role == "buyer" else "/logistics")
        return {"ok": True, "token": token, "redirect": red}
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)

@app.get("/logout")
def logout_get():
    response = RedirectResponse("/")
    clear_session(response)
    return response

@app.get("/agent", response_class=HTMLResponse)
def agent_dash(user: dict = Depends(require_user("agent"))): return FileResponse(ROOT / "app" / "static" / "agent_dashboard.html")

@app.get("/supervisor", response_class=HTMLResponse)
def supervisor_dash(user: dict = Depends(require_user("supervisor"))):
    return FileResponse(ROOT / "app" / "static" / "supervisor_dashboard.html")

@app.get("/logistics", response_class=HTMLResponse)
def logistics_dash(user: dict = Depends(require_user("logistics", "agent"))):
    return FileResponse(ROOT / "app" / "static" / "logistics_dashboard.html")

@app.get("/farmer/{farm_id}", response_class=HTMLResponse)
def farmer_dash(farm_id: str, user: dict = Depends(require_user("farmer", "agent")), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", farm_id, user)
    profile = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).scalar_one_or_none()
    if profile and profile.verification_status != "verified": return RedirectResponse("/onboarding")
    return FileResponse(ROOT / "app" / "static" / "farmer_dashboard.html")

@app.get("/buyer/{buyer_id}", response_class=HTMLResponse)
def buyer_dash(buyer_id: str, user: dict = Depends(require_user("buyer", "agent"))):
    require_owner_or_agent("buyer", buyer_id, user)
    return FileResponse(ROOT / "app" / "static" / "buyer_dashboard.html")

@app.get("/store", response_class=HTMLResponse)
def store_page(user: dict = Depends(require_user())):
    return FileResponse(ROOT / "app" / "static" / "store.html")

# ============================================================================
# CORE DATA ENDPOINTS
# ============================================================================

class PaymentInitiateReq(BaseModel):
    offer_id: str
    msisdn: str
    method: str = "mavuno-pay"

@app.post("/payments/initiate")
def payments_initiate(req: PaymentInitiateReq, request: Request, user: dict = Depends(require_user("buyer")), db: Session = Depends(get_session)):
    _check_login_throttle(_client_ip(request))
    res = payments.initiate(db, user["subject"], req.offer_id, req.msisdn, req.method)
    if "error" in res: return JSONResponse(res, status_code=400)
    return res

def _payment_party_check(p: dict, user: dict) -> None:
    if user["role"] == "agent": return
    if user["role"] == "buyer" and user["subject"] == p["buyer_id"]: return
    if user["role"] == "farmer" and user["subject"] == p["farm_id"]: return
    raise HTTPException(status_code=403, detail="not_payment_party")

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
def payments_batch_init(req: PaymentBatchRequest, db: Session = Depends(get_session), user: dict = Depends(require_user("buyer"))):
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

@app.get("/payments/status/{payment_id}")
def payments_status(payment_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    p = payments.get(db, payment_id)
    if not p: raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return p

@app.get("/payments/farmer/{farm_id}")
def payments_for_farm(farm_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user("farmer", "agent"))):
    require_owner_or_agent("farmer", farm_id, user)
    return {"payments": payments.for_farm(db, farm_id)}

@app.get("/payments/buyer/{buyer_id}")
def payments_for_buyer(buyer_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user("buyer", "agent"))):
    require_owner_or_agent("buyer", buyer_id, user)
    return {"payments": payments.for_buyer(db, buyer_id)}

@app.get("/payments/receipt/{payment_id}")
def payments_receipt(payment_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    p = payments.get(db, payment_id)
    if not p: raise HTTPException(status_code=404, detail="payment_not_found")
    _payment_party_check(p, user)
    return payments.receipt(db, payment_id)

@app.get("/payments/receipt/{payment_id}/pdf")
def payments_receipt_pdf(payment_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    data = payments.receipt(db, payment_id)
    if not data: raise HTTPException(status_code=404, detail="receipt_not_found")
    _payment_party_check(payments.get(db, payment_id), user)
    pdf_bytes = pdf.generate_receipt_pdf(data)
    filename = f"MAVUNO-RECEIPT-{payment_id}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})

class OfferReq(BaseModel):
    farm_id: str
    crop: str
    kg: int
    floor_ugx: int

@app.post("/crp/offers")
def crp_offer_create(req: OfferReq, user: dict = Depends(require_user("farmer", "agent")), db: Session = Depends(get_session)):
    require_owner_or_agent("farmer", req.farm_id, user)
    return crp.list_offer(db, req.farm_id, req.crop.lower(), req.kg, req.floor_ugx)

@app.get("/crp/offers")
def crp_offers_list(limit: int = 50, farm_id: Optional[str] = None, include_closed: bool = False, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    if user["role"] == "farmer" and (not farm_id or farm_id != user["subject"]): raise HTTPException(status_code=403)
    return crp.list_open_offers(db, limit=limit, farm_id=farm_id, include_closed=include_closed)

@app.post("/sensor/telemetry")
async def sensor_telemetry(req: TelemetryRecord, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    require_owner_or_agent("farmer", req.farm_id, user)
    ts = int(time.time())
    new_t = SoilTelemetry(farm_id=req.farm_id, timestamp=ts, soil_moisture=req.soil_moisture, temp_c=req.temp_c, rainfall_mm=req.rainfall_mm, humidity_pct=req.humidity_pct, n_mg_kg=req.n_mg_kg, p_mg_kg=req.p_mg_kg, k_mg_kg=req.k_mg_kg)
    db.add(new_t)
    db.commit()
    ledger.write("SENSOR_PING", {"farm_id": req.farm_id, "timestamp": ts})
    return {"ok": True, "new_yps": scorer.score_farm(db, req.farm_id).get("yps")}

# --- Store API ---
@app.get("/api/store/products")
def store_products(): return store.list_products()

class StorePurchaseReq(BaseModel):
    product_id: str
    phone: str

@app.post("/api/store/purchase")
def store_purchase(req: StorePurchaseReq, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    return store.purchase(db, user["subject"], req.product_id, req.phone)

# ============================================================================
# TRAINING & ACADEMY
# ============================================================================

@app.get("/training/modules")
def list_training_modules(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    return {"modules": training.list_modules(db)}

@app.post("/training/complete")
def complete_training_module(req: TrainingCompleteRequest, db: Session = Depends(get_session), user: dict = Depends(require_user("farmer"))):
    return training.complete_module(db, user["subject"], req.module_id)

@app.get("/farmer/{farm_id}/certifications")
def get_certifications(farm_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    require_owner_or_agent("farmer", farm_id, user)
    return {"certifications": training.get_farmer_certifications(db, farm_id)}

@app.post("/crp/ask")
def crp_ask(req: CRPAskRequest, user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    """AI Agronomist advisor endpoint. Supports public knowledge sharing."""
    # If the user is a farmer, we use their own farm context.
    # If agent/buyer, we might need a specific farm_id in the request.
    farm_id = req.farm_id if user["role"] in ["agent", "buyer", "supervisor"] else user["subject"]
    return crp.advisor(farm_id, req.question, req.make_public)

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(user: dict = Depends(require_user("farmer"))):
    return FileResponse(ROOT / "app" / "static" / "onboarding.html")

@app.get("/api/onboarding/status")
def onboarding_status(user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    return {"status": f.verification_status}

class KYCReq(BaseModel):
    document_id: str

async def _process_webp(file: UploadFile, prefix: str, user_id: str) -> str:
    """Helper to process and save WebP images."""
    try:
        from PIL import Image
        import io
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        img.thumbnail((800, 800))
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=60, method=6)
        
        upload_dir = ROOT / "app" / "static" / "uploads" / prefix
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        fname = f"{prefix}_{user_id}_{int(time.time())}.webp"
        fpath = upload_dir / fname
        fpath.write_bytes(out.getvalue())
        return f"/static/uploads/{prefix}/{fname}"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Processing failed: {str(e)}")

@app.post("/api/onboarding/kyc")
async def onboarding_kyc(
    document_id: str = Form(...), 
    file: UploadFile = File(...),
    user: dict = Depends(require_user("farmer")), 
    db: Session = Depends(get_session)
):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    
    # Process the ID photo
    photo_url = await _process_webp(file, "kyc", user["subject"])
    
    f.verification_status = "pending_device"
    db.commit()
    ledger.write("KYC_SUBMITTED", {"farm_id": user["subject"], "nin": document_id, "id_photo": photo_url})
    
    # Notify Agent
    notifications.notify(
        db, "admin", "KYC Submitted",
        f"Farmer {f.farmer_name} has submitted KYC documents for review.",
        n_type="kyc_submitted"
    )
    
    return {"ok": True, "status": "pending_device", "photo_url": photo_url}

@app.post("/api/onboarding/purchase")
def onboarding_purchase(user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    f.verification_status = "pending_agent"
    db.commit()
    ledger.write("HARDWARE_ORDERED", {"farm_id": user["subject"]})
    
    # Notify Field Agent
    notifications.notify(
        db, "admin", "Hardware Ordered",
        f"Farmer {f.farmer_name} has paid for hardware. Field inspection required.",
        n_type="hardware_ordered"
    )
    
    # SMS Fallback (mocked)
    send_sms("+256770000000", f"Alert: Farm {f.farmer_name} ({f.district}) needs hardware installation.")
    return {"ok": True, "status": "pending_agent"}

@app.get("/me")
def get_me(user: dict = Depends(require_user())):
    return {"id": user["subject"], "role": user["role"]}

@app.get("/farms")
def list_farms(db: Session = Depends(get_session)):
    stmt = select(FarmerProfile)
    rows = db.execute(stmt).scalars().all()
    return {f.user_id: {
        "id": f.user_id,
        "farmer_name": f.farmer_name,
        "district": f.district,
        "crop": f.crop,
        "yps": scorer.score_farm(db, f.user_id).get("yps", 0) if f.verification_status == "verified" else 0
    } for f in rows}

@app.get("/buyers")
def list_buyers_alias(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    """Alias for /api/buyers to support dashboard legacy calls."""
    rows = db.execute(select(BuyerProfile)).scalars().all()
    return [{"id": b.user_id, "name": b.name, "region": b.region, "crops": json.loads(b.crops_json), "floor_ugx": b.floor_ugx} for b in rows]

@app.get("/crp/prices")
def get_crp_prices(crop: str, region: str):
    return crp.market_prices(crop, region)

@app.get("/score/{farm_id}")
def get_farm_score(farm_id: str, db: Session = Depends(get_session)):
    return scorer.score_farm(db, farm_id)

@app.get("/finance/status/{farm_id}")
def get_finance_status(farm_id: str, db: Session = Depends(get_session)):
    # Aggregated finance view for farmer dashboard
    settled = db.execute(select(Settlement).where(Settlement.farm_id == farm_id, Settlement.status == "settled")).scalars().all()
    pending = db.execute(select(Settlement).where(Settlement.farm_id == farm_id, Settlement.status == "pending")).scalars().all()
    return {
        "balance_ugx": sum(s.amount_ugx for s in settled),
        "pending_ugx": sum(s.amount_ugx for s in pending),
        "recent_payments": [dict(id=s.id, amount=s.amount_ugx, status=s.status, date=s.created_at) for s in settled[-5:]]
    }

@app.get("/supervisor/stats")
def supervisor_stats(user: dict = Depends(require_user("supervisor")), db: Session = Depends(get_session)):
    # Regional YPS breakdown
    regional_yps = []
    districts = db.execute(text("SELECT DISTINCT district FROM farmer_profiles")).scalars().all()
    for d in districts:
        scores = [scorer.score_farm(db, f.user_id).get("yps", 0) 
                  for f in db.execute(select(FarmerProfile).where(FarmerProfile.district == d)).scalars().all()]
        if scores:
            regional_yps.append({"district": d, "avg_yps": int(sum(scores)/len(scores))})
    
    # Mocked monthly trade volume for the chart
    trade_volume = [
        {"month": "Jan", "total_kg": 4500},
        {"month": "Feb", "total_kg": 5200},
        {"month": "Mar", "total_kg": 6100},
        {"month": "Apr", "total_kg": 7800}
    ]
    return {"regional_yps": regional_yps, "trade_volume": trade_volume}

class SignupReq(BaseModel):
    role: str
    phone: str
    name: str
    pin_or_password: str
    district_or_region: str
    crop_or_floor: str

@app.post("/api/signup")
def signup(req: SignupReq, response: Response, db: Session = Depends(get_session)):
    user_id = ("UG-FARM-" if req.role == "farmer" else "BY-") + secrets.token_hex(3).upper()
    user = User(id=user_id, phone=req.phone, role=req.role, password_hash=req.pin_or_password)
    db.add(user)
    db.flush()
    
    if req.role == "farmer":
        profile = FarmerProfile(user_id=user_id, farmer_name=req.name, district=req.district_or_region, crop=req.crop_or_floor, acres=1.0)
        db.add(profile)
    else:
        profile = BuyerProfile(user_id=user_id, name=req.name, region=req.district_or_region, crops_json="[]", floor_ugx=int(req.crop_or_floor), lat=0.0, lng=0.0)
        db.add(profile)
    
    db.commit()
    issue_session(response, req.role, user_id)
    return {"ok": True, "id": user_id, "redirect": f"/farmer/{user_id}" if req.role == "farmer" else f"/buyer/{user_id}"}

# ============================================================================
# AGENT OPS
# ============================================================================

@app.get("/api/agent/overview")
def agent_overview(db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    """Unified operational state for the Agent Command Center."""
    # 1. Fetch Farmers & Compute Aggregates
    farmers = db.execute(select(FarmerProfile)).scalars().all()
    
    farmer_list = []
    triage_kyc = []
    triage_inspection = []
    triage_alerts = []
    total_yps = 0
    total_kg_allocated = 0
    
    for f in farmers:
        # Get latest telemetry
        latest_t = db.execute(
            select(SoilTelemetry)
            .where(SoilTelemetry.farm_id == f.user_id)
            .order_by(SoilTelemetry.timestamp.desc())
        ).first()
        
        # Get live score & prediction
        score = scorer.score_farm(db, f.user_id)
        yps = score.get("yps", 0)
        total_yps += yps
        
        # Get active priority
        priority = db.execute(
            select(YieldPriority)
            .where(YieldPriority.farm_id == f.user_id, YieldPriority.status == "active")
        ).scalar_one_or_none()
        
        if priority: total_kg_allocated += priority.kg_allocated
            
        f_data = {
            "id": f.user_id, "name": f.farmer_name, "district": f.district,
            "crop": f.crop, "yps": yps, "status": f.verification_status,
            "predicted_yield_kg": score.get("predicted_yield_kg"),
            "predicted_harvest_days": score.get("predicted_harvest_days"),
            "telemetry": {
                "moisture": latest_t[0].soil_moisture if latest_t else 0,
                "n": latest_t[0].n_mg_kg if latest_t else 0,
                "temp": latest_t[0].temp_c if latest_t else 0,
            } if latest_t else None
        }
        farmer_list.append(f_data)
        
        # Triage Logic
        if f.verification_status == "pending_kyc":
            triage_kyc.append(f_data)
        elif f.verification_status == "pending_agent":
            triage_inspection.append(f_data)
            
        if latest_t and (latest_t[0].soil_moisture < 20 or yps < 300):
            triage_alerts.append({"id": f.user_id, "name": f.farmer_name, "issue": "Low Moisture" if latest_t[0].soil_moisture < 20 else "Low YPS"})

    # 2. Logistics (Hub Aggregation)
    hub_stmt = select(MarketOffer.kg).where(MarketOffer.status == "matched")
    matched_kg = db.execute(hub_stmt).scalars().all()
    
    # 3. Moderation (Flagged Posts)
    flagged = db.execute(select(Post).where(Post.hidden == True).limit(10)).scalars().all()

    # 4. Notifications
    unread_n = db.execute(select(Notification).where(Notification.user_id == user["subject"], Notification.read == False)).scalars().all()

    return {
        "farmers": farmer_list,
        "triage": {"kyc": triage_kyc, "inspection": triage_inspection, "alerts": triage_alerts},
        "logistics": {"expected_kg": sum(matched_kg)},
        "moderation": [{"id": p.id, "body": p.body[:50] + "..."} for p in flagged],
        "macro": {
            "system_risk": round(100 - (total_yps / (len(farmers) or 1)), 1),
            "credit_velocity": total_kg_allocated,
            "ledger_verified": ledger.verify(db).get("ok", False),
            "unread_notifications": len(unread_n)
        }
    }

@app.post("/api/agent/verify/{farm_id}")
def api_agent_verify(farm_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    f.verification_status = "verified"
    db.commit()
    ledger.write("FARM_VERIFIED", {"farm_id": farm_id, "agent": user["subject"]})
    
    # Notify Farmer
    notifications.notify(
        db, farm_id, "Account Verified", 
        "Your Mavuno account is now verified! You can now list harvests and apply for credit.",
        n_type="kyc_verified", sms_fallback=True
    )
    return {"ok": True}

@app.post("/api/agent/social/moderate/{post_id}")
def api_agent_moderate(post_id: str, action: str = Form(...), db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    p = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if not p: raise HTTPException(404, "post_not_found")
    if action == "unflag": p.hidden = False
    elif action == "delete": db.delete(p)
    db.commit()
    ledger.write("POST_MODERATED", {"post_id": post_id, "action": action, "agent": user["subject"]})
    return {"ok": True}

@app.post("/api/agent/priorities/issue")
def api_agent_priority_issue(req: PriorityApproveRequest, db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    # Check if already has active priority
    existing = db.execute(select(YieldPriority).where(YieldPriority.farm_id == req.farm_id, YieldPriority.status == "active")).first()
    if existing: return JSONResponse({"error": "already_has_active_priority"}, status_code=400)
    
    score = scorer.score_farm(db, req.farm_id)
    if "error" in score: return JSONResponse(score, status_code=400)
    
    pid = "YP-" + secrets.token_hex(4).upper()
    now = int(time.time())
    expires = now + (72 * 3600)
    
    new_p = YieldPriority(
        id=pid, farm_id=req.farm_id, yps=score["yps"], 
        kg_allocated=score["kg_allocated"], kg_remaining=score["kg_allocated"],
        expires_at=expires, signature="SIG-" + secrets.token_hex(16)
    )
    db.add(new_p)
    db.commit()
    ledger.write("PRIORITY_ISSUED", {"priority_id": pid, "farm_id": req.farm_id, "yps": score["yps"]})
    
    # Notify Farmer
    notifications.notify(
        db, req.farm_id, "Trade Priority Issued",
        f"Congratulations! You've been issued a Trade Priority for {score['kg_allocated']}kg of {score.get('crop', 'produce')}.",
        n_type="priority_issued", sms_fallback=True
    )
    return {"ok": True, "priority_id": pid}

# ============================================================================
# CHAT
# ============================================================================

def _chat_party_check(thread: dict, user: dict) -> None:
    if user["role"] == "agent": return
    if user["role"] == "buyer" and user["subject"] == thread["buyer_id"]: return
    if user["role"] == "farmer" and user["subject"] == thread["farm_id"]: return
    raise HTTPException(status_code=403, detail="not_chat_party")

@app.post("/chat/threads")
def chat_open_thread(req: ChatThreadReq, db: Session = Depends(get_session), user: dict = Depends(require_user("buyer", "agent"))):
    if user["role"] == "buyer": buyer_id = user["subject"]
    else: raise HTTPException(status_code=400, detail="agent_open_not_supported")
    res = chat.open_thread(db, buyer_id, req.farm_id, req.offer_id)
    if "error" in res: return JSONResponse(res, status_code=400)
    return res

@app.get("/chat/threads")
def chat_list_threads(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    if user["role"] == "farmer": return {"threads": chat.threads_for_farm(db, user["subject"])}
    if user["role"] == "buyer": return {"threads": chat.threads_for_buyer(db, user["subject"])}
    return {"threads": chat.threads_for_agent(db)}

@app.get("/chat/{thread_id}/messages")
async def chat_get_messages(thread_id: str, request: Request, since: int = 0, wait: int = 25, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    thread = chat.get_thread(db, thread_id)
    if not thread: raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)
    wait = max(0, min(int(wait), 25))
    deadline = time.time() + wait
    msgs = chat.messages(db, thread_id, since_ts=since)
    while not msgs and time.time() < deadline:
        if await request.is_disconnected(): break
        await asyncio.sleep(1.0)
        msgs = chat.messages(db, thread_id, since_ts=since)
    chat.mark_read(db, thread_id, user["role"], user["subject"])
    return {"thread_id": thread_id, "messages": msgs}

@app.post("/chat/{thread_id}/messages")
def chat_post_message(thread_id: str, req: ChatMessageReq, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    thread = chat.get_thread(db, thread_id)
    if not thread: raise HTTPException(status_code=404, detail="thread_not_found")
    _chat_party_check(thread, user)
    _check_chat_throttle(f"{user['role']}:{user['subject']}")
    res = chat.send(db, thread_id, user["role"], user["subject"], req.body)
    if "error" in res: return JSONResponse(res, status_code=400)
    return res

@app.get("/chat/unread/count")
def chat_unread(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    return {"count": chat.unread_count(db, user["role"], user["subject"])}

# ============================================================================
# MAVUNO SOCIAL
# ============================================================================

class SocialPostReq(BaseModel):
    body: str
    photo_url: Optional[str] = None
    is_verified: bool = False
    metadata: Optional[dict] = None

@app.get("/feed/verified/gallery", response_class=HTMLResponse)
def get_verified_gallery_page(user: dict = Depends(require_user())):
    """Serves the visually-rich Verified Harvest Gallery."""
    return FileResponse(ROOT / "app" / "static" / "gallery.html")

@app.get("/api/feed")
def get_feed(limit: int = 50, district: Optional[str] = None, db: Session = Depends(get_session)):
    return social.feed(db, limit=limit, district=district)

@app.get("/api/feed/verified")
def get_verified_feed(limit: int = 50, db: Session = Depends(get_session)):
    """Returns only posts marked as verified (Verified Harvests)."""
    from .models import Post
    from sqlalchemy import select
    stmt = select(Post).where(Post.is_verified == True, Post.hidden == False).order_by(Post.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [social._hydrate(db, r) for r in rows]

@app.post("/api/feed")
def create_feed_post(req: SocialPostReq, user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    return social.create_post(db, user["subject"], req.body, req.photo_url, req.is_verified, req.metadata)

@app.post("/api/feed/{post_id}/react")
def react_to_post(post_id: str, emoji: str = Form(...), user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    return social.react(db, post_id, user["role"], user["subject"], emoji)

@app.post("/api/feed/{post_id}/flag")
def flag_post(post_id: str, reason: Optional[str] = Form(None), user: dict = Depends(require_user()), db: Session = Depends(get_session)):
    return social.flag(db, post_id, user["role"], user["subject"], reason)

class SocialBidReq(BaseModel):
    offer_id: Optional[str] = None

@app.post("/api/social/bid/{post_id}")
def social_bid(post_id: str, req: SocialBidReq, user: dict = Depends(require_user("buyer")), db: Session = Depends(get_session)):
    """Allows a buyer to initiate a bid/chat from a social post."""
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if not post: raise HTTPException(404, "post_not_found")
    
    # Open a chat thread tied to this post (or an existing offer)
    thread = chat.open_thread(db, post.farm_id, user["subject"], req.offer_id)
    
    # Auto-send an opening message
    msg_body = f"Hello! I saw your post: '{post.body[:50]}...'. I'm interested in bidding on your harvest."
    chat.send(db, thread["id"], "buyer", user["subject"], msg_body)
    
    ledger.write("SOCIAL_BID_INITIATED", {"post_id": post_id, "buyer_id": user["subject"], "thread_id": thread["id"]})
    
    # Notify Farmer
    notifications.notify(
        db, post.farm_id, "New Social Bid",
        f"A buyer is interested in your recent harvest post! Check your messages to respond.",
        n_type="social_bid", sms_fallback=True
    )
    return {"ok": True, "thread_id": thread["id"]}

@app.get("/api/buyers")
def get_buyers_list(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    """Returns the list of all registered buyers."""
    from .models import BuyerProfile
    rows = db.execute(select(BuyerProfile)).scalars().all()
    return [{"id": b.user_id, "name": b.name, "region": b.region, "crops": json.loads(b.crops_json), "floor_ugx": b.floor_ugx} for b in rows]

@app.get("/buyers")
def get_buyers_redirect(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    """Alias for /api/buyers to support dashboard legacy calls."""
    return get_buyers_list(db, user)

@app.post("/api/feed/upload")
async def upload_harvest_photo(file: UploadFile = File(...), user: dict = Depends(require_user("farmer"))):
    """Handles low-bandwidth WebP image uploads using the shared helper."""
    photo_url = await _process_webp(file, "harvest", user["subject"])
    return {"photo_url": photo_url}

@app.get("/feed-page", response_class=HTMLResponse)
def feed_page(user: dict = Depends(require_user())):
    return FileResponse(ROOT / "app" / "static" / "feed.html")

@app.get("/feed/{post_id}")
def feed_get(post_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user())):
    from .models import Post
    p = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if not p: raise HTTPException(status_code=404, detail="post_not_found")
    return social._hydrate(db, p)

@app.get("/notifications")
def notifications_list(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    from .models import Notification
    rows = db.execute(select(Notification).where(Notification.user_id == user["subject"]).order_by(Notification.created_at.desc()).limit(50)).scalars().all()
    return {"notifications": [
        {"id": n.id, "title": n.title, "body": n.body, "type": n.type, "read": n.read, "created_at": n.created_at}
        for n in rows
    ]}

@app.post("/notifications/read")
def notifications_mark_read(db: Session = Depends(get_session), user: dict = Depends(require_user())):
    from .models import Notification
    db.execute(update(Notification).where(Notification.user_id == user["subject"]).values(read=True))
    db.commit()
    return {"ok": True}

# ============================================================================
# LOGISTICS
# ============================================================================

@app.get("/logistics/pending")
def logistics_pending(db: Session = Depends(get_session), user: dict = Depends(require_user("logistics", "agent"))):
    # Returns settled payments with farm info for collection
    stmt = select(
        Settlement.id, Settlement.farm_id, Settlement.amount_ugx, Settlement.settled_at,
        FarmerProfile.farmer_name, FarmerProfile.district, FarmerProfile.crop
    ).join(FarmerProfile, Settlement.farm_id == FarmerProfile.user_id).where(Settlement.status == 'settled').order_by(Settlement.settled_at.desc())
    
    rows = db.execute(stmt).all()
    return {"pending": [dict(r._mapping) for r in rows]}

@app.post("/logistics/optimize")
def logistics_optimize(req: LogisticsOptimizeRequest, db: Session = Depends(get_session), user: dict = Depends(require_user("logistics", "agent"))):
    """Real geospatial supply clustering for collection routes."""
    return {"routes": logistics.cluster_collection_routes(db)}

@app.post("/logistics/advise")
def logistics_advise_ai(req: LogisticsAdviseRequest, user: dict = Depends(require_user("logistics", "agent"))):
    # Context-aware logistics advice
    mkt = crp.market_prices("coffee", "Eastern")
    ctx = f"Coffee trending {mkt.get('trend')}. 7d avg: {mkt.get('last7_avg')} UGX."
    return {"advice": crp.logistics_advisor(req.pending, ctx)}

# ============================================================================
# SYSTEM / LEDGER
# ============================================================================

@app.get("/ledger")
def ledger_view(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return {"rows": ledger.read_all(db)}

@app.get("/ledger/verify")
def ledger_verify(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return ledger.verify(db)

# ============================================================================
# HARDWARE & SENSORS
# ============================================================================

class HeartbeatReq(BaseModel):
    farm_id: str
    device_id: str
    firmware: str
    battery: float
    rssi: int

@app.post("/hardware/heartbeat")
def hardware_heartbeat(req: HeartbeatReq, db: Session = Depends(get_session)):
    """Sensor-originating heartbeat to track device health."""
    # Note: In production, this would be authenticated via device-specific HMAC keys
    return hardware.log_heartbeat(db, req.farm_id, req.device_id, req.firmware, req.battery, req.rssi)

@app.get("/api/agent/hardware/status")
def agent_hardware_status(db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    """Returns the latest health status for all Sentinel Nodes."""
    return {"devices": hardware.list_system_health(db)}

@app.get("/terms", response_class=HTMLResponse)
def terms(): return FileResponse(ROOT / "app" / "static" / "terms.html")

@app.get("/phone", response_class=HTMLResponse)
def phone_page(): return FileResponse(ROOT / "app" / "static" / "phone.html")
