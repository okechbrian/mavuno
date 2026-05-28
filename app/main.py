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
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import crp, finance, ledger, scorer, ussd, database, payments, chat, social, pdf, training, store
from .config import HMAC_SECRET, ROOT, PUBLIC_BASE_URL
from .database import engine, get_session, SessionLocal
from .models import User, FarmerProfile, BuyerProfile, SoilTelemetry, YieldPriority, MarketOffer, Settlement, Notification, Post
from .gateways import send_sms, initiate_fw_payment, verify_fw_transaction
from .session import (
    COOKIE_NAME, clear_session, current_user, issue_session,
    require_owner_or_agent, require_user, get_current_user,
)
from .schemas import (
    FarmerOnboardRequest, BuyerOnboardRequest, TelemetryRecord, ErrorResponse,
    PriorityApproveRequest, CRPAskRequest, PaymentBatchRequest, TrainingCompleteRequest,
    LogisticsOptimizeRequest, LogisticsAdviseRequest, FarmStageUpdate
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
def health(): return {"ok": True}

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

@app.post("/api/onboarding/kyc")
def onboarding_kyc(req: KYCReq, user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    f.verification_status = "pending_device"
    db.commit()
    ledger.write("KYC_SUBMITTED", {"farm_id": user["subject"], "nin": req.document_id})
    return {"ok": True, "status": "pending_device"}

@app.post("/api/onboarding/purchase")
def onboarding_purchase(user: dict = Depends(require_user("farmer")), db: Session = Depends(get_session)):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user["subject"])).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    f.verification_status = "pending_agent"
    db.commit()
    ledger.write("HARDWARE_ORDERED", {"farm_id": user["subject"]})
    return {"ok": True, "status": "pending_agent"}

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
        
        # Get active priority
        priority = db.execute(
            select(YieldPriority)
            .where(YieldPriority.farm_id == f.user_id, YieldPriority.status == "active")
        ).scalar_one_or_none()
        
        yps = priority.yps if priority else 0
        total_yps += yps
        if priority: total_kg_allocated += priority.kg_allocated
            
        f_data = {
            "id": f.user_id, "name": f.farmer_name, "district": f.district,
            "crop": f.crop, "yps": yps, "status": f.verification_status,
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
        if latest_t and (latest_t[0].soil_moisture < 20 or yps < 300):
            triage_alerts.append({"id": f.user_id, "name": f.farmer_name, "issue": "Low Moisture" if latest_t[0].soil_moisture < 20 else "Low YPS"})

    # 2. Logistics (Hub Aggregation)
    hub_stmt = select(MarketOffer.kg).where(MarketOffer.status == "matched")
    matched_kg = db.execute(hub_stmt).scalars().all()
    
    # 3. Moderation (Flagged Posts)
    flagged = db.execute(select(Post).where(Post.hidden == True).limit(10)).scalars().all()

    return {
        "farmers": farmer_list,
        "triage": {"kyc": triage_kyc, "alerts": triage_alerts},
        "logistics": {"expected_kg": sum(matched_kg)},
        "moderation": [{"id": p.id, "body": p.body[:50] + "..."} for p in flagged],
        "macro": {
            "system_risk": round(100 - (total_yps / (len(farmers) or 1)), 1),
            "credit_velocity": total_kg_allocated,
            "ledger_verified": ledger.verify(db).get("ok", False)
        }
    }

@app.post("/api/agent/verify/{farm_id}")
def api_agent_verify(farm_id: str, db: Session = Depends(get_session), user: dict = Depends(require_user("agent"))):
    f = db.execute(select(FarmerProfile).where(FarmerProfile.user_id == farm_id)).scalar_one_or_none()
    if not f: raise HTTPException(404, "farm_not_found")
    f.verification_status = "verified"
    db.commit()
    ledger.write("FARM_VERIFIED", {"farm_id": farm_id, "agent": user["subject"]})
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
    
    score = scorer.score_farm(req.farm_id)
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
    return {"ok": True, "priority_id": pid}

# ============================================================================
# SOCIAL FEED
# ============================================================================

class SocialPostReq(BaseModel):
    body: str
    photo_url: Optional[str] = None
    is_verified: bool = False
    metadata: Optional[dict] = None

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
    return {"ok": True, "thread_id": thread["id"]}

@app.post("/api/feed/upload")
async def upload_harvest_photo(file: UploadFile = File(...), user: dict = Depends(require_user("farmer"))):
    """Handles low-bandwidth WebP image uploads."""
    try:
        from PIL import Image
        import io
        
        # 1. Read and validate
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 2. Resize and Compress to WebP (Target ~100kb)
        img.thumbnail((800, 800))
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=60, method=6)
        
        # 3. Save to static/uploads
        upload_dir = ROOT / "app" / "static" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        fname = f"harvest_{user['subject']}_{int(time.time())}.webp"
        fpath = upload_dir / fname
        fpath.write_bytes(out.getvalue())
        
        return {"photo_url": f"/static/uploads/{fname}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

# ============================================================================
# SYSTEM / LEDGER
# ============================================================================

@app.get("/ledger")
def ledger_view(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return {"rows": ledger.read_all(db)}

@app.get("/ledger/verify")
def ledger_verify(user: dict = Depends(require_user("agent")), db: Session = Depends(get_session)):
    return ledger.verify(db)

@app.get("/me")
def me_endpoint(user: dict = Depends(require_user())):
    return {"role": user["role"], "subject": user["subject"], "exp": user["exp"]}

@app.get("/terms", response_class=HTMLResponse)
def terms(): return FileResponse(ROOT / "app" / "static" / "terms.html")

@app.get("/phone", response_class=HTMLResponse)
def phone_page(): return FileResponse(ROOT / "app" / "static" / "phone.html")
