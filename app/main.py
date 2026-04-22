"""FastAPI app — binds USSD, YPS, ECT, ledger, and static UI together."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import crp, ect, ledger, scorer, ussd
from .config import DATA_DIR, STATIC_DIR

app = FastAPI(
    title="Mavuno",
    description="Soil-backed energy credit for smallholder farms.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "mavuno"}


# ---- Farms & scoring -----------------------------------------------------

@app.get("/farms")
def farms() -> dict:
    return json.loads((DATA_DIR / "farms.json").read_text(encoding="utf-8"))


@app.get("/score/{farm_id}")
def score(farm_id: str) -> dict:
    return scorer.score_farm(farm_id)


# ---- ECT -----------------------------------------------------------------

class IssueReq(BaseModel):
    farm_id: str


@app.post("/ect/issue")
def ect_issue(req: IssueReq) -> dict:
    s = scorer.score_farm(req.farm_id)
    if "error" in s:
        return s
    return ect.issue(req.farm_id, s["yps"], s["kwh_allocated"])


class RedeemReq(BaseModel):
    token_id: str
    lat: float
    lng: float
    kwh: int


@app.post("/ect/redeem")
def ect_redeem(req: RedeemReq) -> dict:
    return ect.redeem(req.token_id, req.lat, req.lng, req.kwh)


@app.get("/ect/balance/{farm_id}")
def ect_balance(farm_id: str) -> dict:
    return ect.farm_balance(farm_id)


@app.get("/ect/{token_id}")
def ect_get(token_id: str) -> dict:
    t = ect.get(token_id)
    return t or {"error": "not_found"}


# ---- Ledger --------------------------------------------------------------

@app.get("/ledger")
def ledger_view(limit: int = 25) -> dict:
    rows = ledger.read_all()[-limit:]
    return {"length": len(ledger.read_all()), "rows": rows}


@app.get("/ledger/verify")
def ledger_verify() -> dict:
    return ledger.verify()


# ---- USSD ---------------------------------------------------------------

class LocalUssdReq(BaseModel):
    phone: str
    text: str = ""


@app.post("/ussd/local")
def ussd_local(req: LocalUssdReq) -> dict:
    resp = ussd.route(req.phone, req.text)
    prefix, _, body = resp.partition(" ")
    return {
        "kind": prefix,            # CON or END
        "body": body,
        "raw": resp,
        "length": len(body),
    }


@app.post("/ussd/at", response_class=PlainTextResponse)
async def ussd_at(
    sessionId: str = Form(""),
    serviceCode: str = Form(""),
    phoneNumber: str = Form(""),
    text: str = Form(""),
) -> str:
    return ussd.route(phoneNumber, text)


# ---- CRP (Community Resource Platform) ----------------------------------
# Folds market-linkage + AI advisory into the same USSD session: menu items
# 4 (prices), 5 (sell), 6 (ask). Designed immune to the failure modes of
# Oxfam Novib's Internet Now! kiosks (2012) and Grameen CKW Uganda (2009-14).

@app.get("/crp/prices")
def crp_prices(crop: str, region: str = "Eastern") -> dict:
    return crp.market_prices(crop, region)


class OfferReq(BaseModel):
    farm_id: str
    crop: str
    kg: int
    floor_ugx: int


@app.post("/crp/offers")
def crp_offer_create(req: OfferReq) -> dict:
    return crp.list_offer(req.farm_id, req.crop, req.kg, req.floor_ugx)


@app.get("/crp/offers")
def crp_offers_list(limit: int = 10) -> dict:
    return crp.list_open_offers(limit=limit)


@app.post("/crp/match/{offer_id}")
def crp_match(offer_id: str) -> dict:
    return crp.match_buyers(offer_id)


class AskReq(BaseModel):
    farm_id: str
    question: str


@app.post("/crp/ask")
def crp_ask(req: AskReq) -> dict:
    return crp.advisor(req.farm_id, req.question)


# ---- Demo-only: run the full Akello cycle in one call -------------------

class CycleReq(BaseModel):
    farm_id: str


@app.post("/demo/cycle")
def demo_cycle(req: CycleReq) -> dict:
    """sensor -> YPS -> ECT issue -> partial redeem at pump."""
    import json as _json
    farms_data = _json.loads((DATA_DIR / "farms.json").read_text(encoding="utf-8"))
    if req.farm_id not in farms_data:
        return {"error": "unknown_farm"}
    s = scorer.score_farm(req.farm_id)
    if "error" in s:
        return s
    t = ect.issue(req.farm_id, s["yps"], s["kwh_allocated"])
    if "error" in t:
        return {"score": s, "ect": t}
    pump = farms_data[req.farm_id]["pump"]
    r = ect.redeem(t["token_id"], pump["lat"], pump["lng"], min(10, t["kwh_allocated"]))
    return {"score": s, "ect": t, "redeem": r}


# ---- Static pages -------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/phone", response_class=HTMLResponse)
def phone() -> FileResponse:
    return FileResponse(STATIC_DIR / "phone.html")
