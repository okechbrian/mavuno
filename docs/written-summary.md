# Mavuno â€” Written Summary

**Mavuno â€” National Science Week 2026**
**Ministry of Science, Technology & Innovation (MoSTI), Uganda**

Challenge: *Powering Uganda to a $500B Economy.*

---

## 1. Executive summary

Mavuno ("harvest" in Swahili) is a soil-backed energy-credit system for Ugandan smallholders, delivered over USSD on 2G. Designed specifically for the **Mavuno Challenge**, it turns **soil-sensor data into a working irrigation pump, a live market price, and an AI agronomist** â€” on any feature phone, without a smartphone, bank account, or internet connection at the farm.

The thesis is that Uganda's path to a **$500B economy** runs directly through smallholder productivity (~70% of employment, ~24% of GDP). Currently, this productivity is blocked by four simultaneous walls: no collateral, no reliable grid, no weather signal, and no market signal. Mavuno collapses all four into one USSD call and one audit ledger, built on rails Uganda already owns â€” the **Parish Development Model (PDM)**, **UEDCL's Electricity Access Scale-up Project (EASP)**, and mobile money.

To ensure **practicality and scale**, the v2 prototype features:
1. **Durable SQLite Backend:** An ACID-compliant relational database for concurrent national-scale operations.
2. **Sentinel Node Hardware:** A modular IoT strategy using one 7-in-1 sensor cluster per micro-zone to drop CAPEX to ~$4.00 per farmer.
3. **Agent Decision Support Cockpit:** A professional interface for SACCO agents featuring live NPK biometric trends and regional risk analytics.
4. **Community Resource Platform (CRP):** A bundled marketplace and AI advisory service that turns precision soil data into cash for the farmer.

A working prototype is live today. It features a trained ML model, a multi-language USSD state machine (English/Luganda), an immutable hash-chained audit ledger, and an interactive cockpit for real-world field operations.

## 2. Problem context â€” Uganda, 2024â€“2026

- **Unbanked smallholders.** An estimated 7 in 10 Ugandan smallholders have no formal banking relationship. Without collateral or salary, SACCOs and commercial banks cannot price the risk of lending for inputs or irrigation.
- **Rural electrification gap.** Only ~19% of rural Uganda has reliable grid access. REA was merged into UEDCL in 2024; the current rural-electrification vehicle is the **UEDCL Electricity Access Scale-up Project (EASP)**, backed by World Bank ~US$638M (2023). EASP is rolling out solar pump nodes faster than demand can monetise them.
- **Yield volatility.** Rainfall variability wipes out ~20% of yields year-on-year; insurance penetration among smallholders is near zero.
- **Market-signal blindness.** Regional farmgate prices move daily but reach the farmer weekly, if at all. Farmers sell low even when prices are high.
- **Flagship programs are already in motion.** The **Parish Development Model (PDM)** disburses UGX 100M per parish per year via SACCOs. It needs credit-risk signal and productive-use enforcement to scale without diversion â€” which is exactly what Mavuno supplies.

## 3. Why prior attempts died â€” and how Mavuno is immune

Uganda has been here before. Two landmark programs failed publicly:

- **Oxfam Novib Ã— ALIN â€” *Internet Now!* (2012).** 100 WiFi-enabled ICT kiosks across Northern Uganda, with crop prices, agronomy content, and market links. Killed by power cuts, tech stack mismatch (desktop PCs in a 2G-phone market), stale content, and the absence of a business model.
- **Grameen Foundation â€” *Community Knowledge Worker* (Uganda 2009â€“2014).** 1,200 trained agents, ~62,000 farmers reached, US$4.7M launch investment. By 2014 the network had collapsed to ~300 agents â€” classic donor-dependency + agent-churn failure.

The diagnosis is identical across both: no revenue attribution, no agents that could sustain themselves, no tech stack that survived rural conditions. Mavuno's architecture is designed specifically to eliminate each failure mode:

| Old failure mode | Mavuno design answer |
|---|---|
| Kiosk power cuts | No kiosk. The farmer's own feature phone. |
| WiFi coverage gaps | USSD over 2G. Works where there is no internet. |
| Agent payroll ($4.7M) | No agents. AI advisor over USSD (Groq Llama 3.3, ~$0 per query at free-tier scale, deterministic rule-based fallback when API is down). |
| Content staleness | Live feeds. Prices refresh daily; agronomy advice is conditioned on each farm's live soil reading. |
| No business model | Fee per Trade Priority redemption + match fee + data licensing. Every interaction attributes revenue to the platform. |
| Dropout under API outage | 2-second hard timeout â†’ deterministic pre-written fallback keyed to question + crop. Farmer is never met with silence. |

## 4. Solution architecture

### 4.1 YPS â€” Yield Probability Score

A 0â€“1000 score that acts as the credit signal, replacing collateral and credit history. It is produced by a gradient-boosted classifier trained on 7 soil/weather features:

- 7-day soil-moisture average
- 7-day rainfall sum
- 7-day temperature variance
- 7-day humidity average
- Deviation from crop-specific soil-moisture target
- Deviation from crop-specific rainfall target
- Crop type

The YPS maps to three lending tiers:

- **Full** (YPS â‰¥ 700) â†’ up to 60 KG Trade Priority per cycle, UGX 200,000 credit ceiling.
- **Partial** (400â€“699) â†’ up to 25 KG Trade Priority per cycle.
- **Denied** (< 400) â†’ no Trade Priority issued; farmer receives agronomy advice instead. The system **refuses to lend into a failing season.**

### 4.2 Trade Priority â€” Yield Priority

- **HMAC-signed** by the issuer with a rotating secret.
- **GPS-locked** to a 5 km radius around the farm.
- **72-hour expiry** from time of issue.
- **Non-cashable** â€” redeemable only at the specific solar pump node assigned to the farm.
- **Offline-verifiable** by the pump operator via a 20-line Python script on a Raspberry Pi; ledger sync on reconnect.

Diversion rate is zero by construction â€” the token cannot be spent on anything except pump KG.

### 4.3 Hash-chained audit ledger

Every state transition â€” issue, redeem, reject, expire, offer, match, advise â€” is appended as a JSON line hashed into a SHA-256 chain. `/ledger/verify` re-hashes the full chain and reports tamper. MoSTI, UEDCL, and the SACCO audit the same source of truth in real time.

### 4.4 USSD interface & CRP
Six menu items on any feature phone. Menu items 4â€“6 form the **Community Resource Platform (CRP)**, a bundled marketplace and advisory service:

```
[Soil sensor] â†’ [YPS model] â†’ [USSD *165*ACP#]
                                    â”œâ”€ 1. YPS score
                                    â”œâ”€ 2. Energy credit â†’ [EASP solar pump]
                                    â”œâ”€ 3. Balance
                                    â”œâ”€ 4. Market price  â”€â”€â”€ CRP live feed
                                    â”œâ”€ 5. Sell produce  â”€â”€â”€ CRP auto-match
                                    â””â”€ 6. Ask Mavuno    â”€â”€â”€ CRP AI agronomist
                                                              â†“
                                             [SHA-256 hash-chained ledger]
```

The `/ussd/at` endpoint speaks Africa's Talking's standard callback shape out of the box, so production deployment is a DNS change, not a rebuild.

### 4.5 CRP â€” Community Resource Platform

Menu items 4â€“6 are the "CRP" layer â€” the market and advisory bundle that makes Mavuno more than a credit product. Farmgate prices, buyer matching, and an AI agronomist all live inside the same USSD session, so the farmer who dials for a pump credit also leaves with the day's price and an answer to "coffee berry borer, what do I do?"

## 5. Technical stack & validation

- **Backend:** Python 3.12 Â· FastAPI Â· uvicorn (Fluid Compute ready; `vercel.json` and `api/index.py` already wired).
- **ML:** scikit-learn GradientBoostingClassifier Â· pandas Â· joblib. Training set: synthetic-but-realistic 500-row dataset modelled on USAID Uganda soil-moisture profiles for coffee, maize, and beans.
- **Frontend:** static HTML + vanilla JS â€” one 994-line operations dashboard with Leaflet-based Uganda map, per-farm cards, streaming ledger, and dark mode; one 370-line Nokia-style phone simulator that mirrors the USSD state machine pixel for pixel.
- **Ledger:** append-only JSONL file, SHA-256 hash chain, `/ledger/verify` endpoint.
- **Security:** HMAC-signed ECTs with a rotating secret (`HMAC_SECRET` env var); PDPO-compliant storage posture.

### Model evaluation

From `app/data/train_metrics.json` on a 105-sample held-out test set:

| Metric | Value |
|---|---|
| Accuracy | **0.9048** |
| Macro-avg F1 | 0.898 |
| Weighted-avg F1 | 0.906 |
| Class 0 (denied) precision / recall | 1.00 / 0.89 |
| Class 1 (partial) precision / recall | 0.87 / 0.94 |
| Class 2 (full) precision / recall | 0.85 / 0.85 |

Of note for a credit-issuing model: class-0 precision is 1.00 â€” no false approvals in the held-out set. We would rather deny ten good farms than approve one bad one.

## 6. Competitive landscape

Uganda has agri-tech. What Uganda does not have is **soil-gated, non-cashable, marketplace-bundled credit over USSD**. The closest comparable products:

- **Apollo Agriculture (Kenya)** â€” satellite + ML credit scoring for inputs (seed, fertilizer). Mavuno differs: we finance **energy**, not inputs, and we issue a **non-cashable** instrument.
- **Emata (Uganda)** â€” cash credit against dairy/coffee cooperative payrolls. Mavuno differs: no cooperative required; we serve the unorganised smallholder directly, and the instrument cannot be diverted.
- **M-KOPA, Sun King, ENGIE-Fenix** â€” solar PAYG. These are asset finance â€” a solar home system. Mavuno is **seasonal productive-use credit** that runs on top of existing pump infrastructure. We complement, not compete.
- **FarmDrive (regional)** â€” alternative-data credit scoring. Same critique as Apollo: scoring without a diversion-proof instrument leaves cash to be repurposed.

Our single-sentence differentiator: *"The only credit product that is gated by live soil data **and** bundles market price + AI advisor in the same USSD call, and whose loan instrument is non-cashable by design."*

## 7. Business model

- **Transaction fee** â€” 2â€“3% on every Trade Priority redemption at the pump, paid by the SACCO out of its interest spread.
- **Match fee** â€” ~1% on buyer-match completions through menu item 5.
- **Data licensing** â€” at scale, aggregated YPS time-series become a drought-risk signal that agricultural insurers and export buyers will pay for.
- **Zero fee to the farmer.** The farmer's incentive is the pump credit, the price, and the advice â€” never a line item.

## 8. Pilot plan

| Phase | Scope | Success metric |
|---|---|---|
| **Pilot** (90 days) | 50 farms Â· Mbale coffee belt Â· 3â€“5 EASP pump nodes Â· 1 SACCO underwriter | â‰¥ 80% on-time pump utilisation; < 5% loan-equivalent default rate (gated by YPS tier). |
| **Year-1 expansion** | 5,000 farms Â· 3 districts Â· ~UGX 1.2B Trade Priority volume | Replication of pilot metrics at 100Ã— scale; insurer partnership signed. |
| **Year-3** | National footprint via PDM integration | YPS becomes a nationally recognised pre-qualification signal; data-licensing revenue pays for the platform. |

## 9. Data protection posture

- **PDPO 2019 compliant** â€” the farmer owns their personal data; Mavuno stores it locally on the operator device.
- Only **hashes** of farm-level state are written to the shared audit ledger; raw soil values never leave the farm's data perimeter.
- Opt-in, revocable at any time via USSD menu 7 (Exit) followed by an SMS opt-out keyword.
- Use-case filing against the Personal Data Protection Office model is prepared as part of pilot onboarding.

## 10. Roadmap & asks

- **MoSTI** â€” endorsement letter, plus **Parish Development Model (PDM)** data-access permission for the pilot cohort.
- **UEDCL** â€” access to 3â€“5 **EASP** solar pump nodes for the pilot, and a committed pump-operator training slot.
- **SACCO partner** â€” one pilot SACCO to underwrite the Trade Priority float and run collections on the interest-spread side.
- **Africa's Talking** â€” production USSD short-code and callback URL (the `/ussd/at` endpoint is already conformant).
- **No new hardware.** Python, FastAPI, SHA-256, USSD on 2G. Built on rails that already exist.

## 11. Team

{{TEAM_ROSTER}}

## 12. Appendix A â€” Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/farms` | All registered farmer profiles |
| GET | `/score/{farm_id}` | Current YPS + tier |
| POST | `/finance/approve` | Issue a token for a farm |
| POST | `/priority/redeem` | Redeem KG at a hub (HMAC + GPS + expiry checked) |
| GET | `/finance/status/{farm_id}` | Active tokens + remaining KG |
| GET | `/ledger` | Recent ledger entries |
| GET | `/ledger/verify` | Re-hash the full chain and report tamper |
| POST | `/ussd/local` | USSD simulator (JSON in/out) |
| POST | `/ussd/at` | Africa's Talking callback (form-encoded) |
| POST | `/crp/offers`, GET `/crp/offers`, POST `/crp/match/{offer_id}` | Marketplace |
| GET | `/crp/prices` | Regional farmgate price lookup |
| POST | `/crp/ask` | AI agronomist |
| POST | `/demo/cycle` | Sensor â†’ YPS â†’ issue â†’ partial redeem, one call (for stage demos) |

## 13. Appendix B â€” Live state

As of submission:

- `/health` â†’ `{"ok": true, "service": "mavuno"}`
- `/ledger/verify` â†’ `{"ok": true, "length": <growing>}` â€” chain intact on every call.
- `/score/UG-MBL-0001` â†’ Akello (Mbale, coffee) YPS **862**, tier **full**, 60 KG allocated, UGX 200,000 credit ceiling.
- `/score/UG-GUL-0002` â†’ Okello (Gulu, maize) â€” drought conditions, tier **denied**. The system refuses to lend into a failing season.
- `/score/UG-MBR-0003` â†’ Namazzi (Mbarara, beans) â€” middling discipline, tier **partial**, 25 KG allocated.
- Dashboard + phone simulator verified via public URL.

## 14. Links

- **Live prototype:** https://mavuno-prototype.vercel.app
- **Public source:** https://github.com/okechbrian/mavuno
- **Pitch script (5:00, 9 slides, 8 Q&A cards):** `docs/pitch-deck.md` in the repo
- **User manual:** `docs/user-manual.md` in the repo
- **Applicant contact:** okechbrian@gmail.com Â· subject `Mavuno`

`


