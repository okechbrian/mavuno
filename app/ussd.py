"""USSD session state machine.

Matches Africa's Talking request shape:
  POST /ussd/at  (form-encoded)
  sessionId, serviceCode, phoneNumber, text
Response: plain text starting with 'CON ' (continue) or 'END ' (terminate).

Local browser simulator posts to /ussd/local with JSON {phone, text}.

Menu (post-CRP integration):
  1. YPS score
  2. Energy credit
  3. Balance
  4. Market price
  5. Sell produce   (two prompts: kg, floor UGX/kg)
  6. Ask Mavuno     (one prompt: question text)
  7. Exit
"""
from __future__ import annotations

import json

from . import crp, ect, scorer
from .config import DATA_DIR

_DISTRICT_REGION = {
    "Mbale": "Eastern", "Gulu": "Northern", "Mbarara": "Western",
    "Kampala": "Central", "Jinja": "Eastern", "Lira": "Northern",
    "Fort Portal": "Western",
}


def _farms() -> dict:
    return json.loads((DATA_DIR / "farms.json").read_text(encoding="utf-8"))


def _farm_by_phone(phone: str) -> dict | None:
    for f in _farms().values():
        if f["phone"] == phone:
            return f
    return None


def _fmt_ugx(n: int) -> str:
    return f"UGX {n:,}"


def _region(farm: dict) -> str:
    return _DISTRICT_REGION.get(farm.get("district", ""), "Central")


def _cap(s: str, n: int = 160) -> str:
    """Hard-cap USSD screen length for AT compatibility."""
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def route(phone: str, text: str) -> str:
    """Return a full USSD response string including the 'CON '/'END ' prefix."""
    farm = _farm_by_phone(phone)
    parts = [p for p in text.split("*") if p != ""] if text else []

    if farm is None:
        return "END Number not registered.\nDial *165*ACP# after registration."

    name_short = farm["farmer_name"].split()[0]
    fid = farm["farm_id"]

    # Root menu
    if len(parts) == 0:
        return _cap(
            f"CON Mavuno\n"
            f"Welcome {name_short} ({farm['crop']})\n"
            f"1. YPS score\n"
            f"2. Energy credit\n"
            f"3. Balance\n"
            f"4. Market price\n"
            f"5. Sell produce\n"
            f"6. Ask Mavuno\n"
            f"7. Exit"
        )

    root = parts[0]

    # 1. Check YPS
    if root == "1":
        s = scorer.score_farm(fid)
        if "error" in s:
            return f"END Error: {s['error']}"
        return _cap(
            f"END Your YPS: {s['yps']} / 1000\n"
            f"Tier: {s['tier_label'].upper()}\n"
            f"Credit ceiling: {_fmt_ugx(s['credit_ceiling_ugx'])}\n"
            f"kWh eligible: {s['kwh_allocated']}"
        )

    # 2. Request ECT
    if root == "2":
        if len(parts) == 1:
            return "CON Request Energy Credit\n1. Confirm & issue\n2. Cancel"
        if parts[1] == "1":
            s = scorer.score_farm(fid)
            if "error" in s:
                return f"END Error: {s['error']}"
            token = ect.issue(fid, s["yps"], s["kwh_allocated"])
            if "error" in token:
                return f"END Unable to issue: {token['error']}"
            return _cap(
                f"END Token issued!\n"
                f"ID: {token['token_id']}\n"
                f"kWh: {token['kwh_allocated']}\n"
                f"Pump: {token['pump_node']}\n"
                f"Expires: 72h\n"
                f"GPS-locked 5km"
            )
        return "END Cancelled."

    # 3. Balance
    if root == "3":
        bal = ect.farm_balance(fid)
        if not bal["tokens"]:
            return "END No active Energy Credits.\nDial *165# menu 2 to request one."
        lines = [f"END Active: {bal['active_tokens']} token(s), {bal['kwh_remaining']} kWh"]
        for t in bal["tokens"][:2]:
            lines.append(f"{t['token_id']}: {t['kwh_remaining']}kWh")
        return _cap("\n".join(lines))

    # 4. Market price (auto uses farm's crop + region)
    if root == "4":
        region = _region(farm)
        p = crp.market_prices(farm["crop"], region)
        if "error" in p:
            return f"END Price unknown for {farm['crop']}"
        arrow = {"up": "\u2191", "down": "\u2193", "flat": "="}[p["trend"]]
        return _cap(
            f"END {farm['crop'].capitalize()} {region}\n"
            f"Today: UGX {p['today']['ugx']:,}/{p['unit']}\n"
            f"7d avg: UGX {p['last7_avg']:,} {arrow}\n"
            f"Range: {p['last7_min']:,}-{p['last7_max']:,}"
        )

    # 5. Sell produce (two prompts: kg, floor UGX/kg)
    if root == "5":
        if len(parts) == 1:
            return "CON Sell produce\nEnter kg:"
        if len(parts) == 2:
            try:
                int(parts[1])
            except ValueError:
                return "END Invalid kg."
            return f"CON {parts[1]} kg {farm['crop']}\nFloor UGX/kg:"
        if len(parts) >= 3:
            try:
                kg = int(parts[1])
                floor = int(parts[2])
            except ValueError:
                return "END Invalid number."
            result = crp.list_offer(fid, farm["crop"], kg, floor)
            if "error" in result:
                return f"END Error: {result['error']}"
            m = crp.match_buyers(result["offer_id"])
            if not m.get("matches"):
                return _cap(
                    f"END Offer posted: {result['offer_id']}\n"
                    f"{kg}kg @ {_fmt_ugx(floor)}\n"
                    "No buyers match yet.\nMavuno will SMS when matched."
                )
            header = f"END Offer {result['offer_id']}\n{kg}kg @ {floor:,}/kg"
            rows = [f"{b['name'][:14]} {b['price_offered']:,}"
                    for b in m["matches"][:3]]
            return _cap(header + "\n" + "\n".join(rows))

    # 6. Ask Mavuno (AI advisor)
    if root == "6":
        if len(parts) == 1:
            return "CON Ask Mavuno\nType question (e.g. pest on coffee):"
        question = "*".join(parts[1:])  # in case user typed * in their text
        ans = crp.advisor(fid, question)
        if "error" in ans:
            return f"END Error: {ans['error']}"
        tag = "" if ans["source"] == "groq" else " (offline)"
        return _cap(f"END Mavuno{tag}:\n{ans['answer']}")

    # 7. Exit
    if root == "7":
        return "END Webale. Grow strong."

    return "END Invalid option."
