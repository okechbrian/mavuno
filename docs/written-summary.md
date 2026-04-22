# Mavuno — Written Summary

**Future Makers Hackathon 2026 — National Science Week 2026**
**Ministry of Science, Technology & Innovation (MoSTI), Uganda**

Challenge: *Powering Uganda to a $500B Economy.*



## 1. Executive summary

Mavuno ("harvest" in Swahili) is a soilbacked energycredit system for Ugandan smallholders, delivered over USSD on 2G. It turns **soilsensor data into a working irrigation pump, a live market price, and an AI agronomist** — on any feature phone, without a smartphone, bank account, or internet connection at the farm.

The thesis is that Uganda's path to a $500B economy runs through smallholder productivity (~70% of employment, ~24% of GDP), and that smallholder productivity is currently blocked by four simultaneous walls: no collateral, no reliable grid, no weather signal, and no market signal. Mavuno collapses all four into one USSD call and one audit ledger, built on rails Uganda already owns — the **Parish Development Model (PDM)**, **UEDCL's Electricity Access Scaleup Project (EASP)**, and mobile money.

A working prototype is live today. It has a trained ML model (90.5% test accuracy), a working USSD state machine (Africa's Talking callback compatible), a hashchained audit ledger (verified intact on every call to /ledger/verify), and a browserhosted dashboard + Nokiastyle phone simulator for onstage demos.

## 2. Problem context — Uganda, 2024–2026

 **Unbanked smallholders.** An estimated 7 in 10 Ugandan smallholders have no formal banking relationship. Without collateral or salary, SACCOs and commercial banks cannot price the risk of lending for inputs or irrigation.
 **Rural electrification gap.** Only ~19% of rural Uganda has reliable grid access. REA was merged into UEDCL in 2024; the current ruralelectrification vehicle is the **UEDCL Electricity Access Scaleup Project (EASP)**, backed by World Bank ~US$638M (2023). EASP is rolling out solar pump nodes faster than demand can monetise them.
 **Yield volatility.** Rainfall variability wipes out ~20% of yields yearonyear; insurance penetration among smallholders is near zero.
 **Marketsignal blindness.** Regional farmgate prices move daily but reach the farmer weekly, if at all. Farmers sell low even when prices are high.
 **Flagship programs are already in motion.** The **Parish Development Model (PDM)** disburses UGX 100M per parish per year via SACCOs. It needs creditrisk signal and productiveuse enforcement to scale without diversion — which is exactly what Mavuno supplies.

## 3. Why prior attempts died — and how Mavuno is immune

Uganda has been here before. Two landmark programs failed publicly:

 **Oxfam Novib × ALIN — *Internet Now!* (2012).** 100 WiFienabled ICT kiosks across Northern Uganda, with crop prices, agronomy content, and market links. Killed by power cuts, tech stack mismatch (desktop PCs in a 2Gphone market), stale content, and the absence of a business model.
 **Grameen Foundation — *Community Knowledge Worker* (Uganda 2009–2014).** 1,200 trained agents, ~62,000 farmers reached, US$4.7M launch investment. By 2014 the network had collapsed to ~300 agents — classic donordependency + agentchurn failure.

The diagnosis is identical across both: no revenue attribution, no agents that could sustain themselves, no tech stack that survived rural conditions. Mavuno's architecture is designed specifically to eliminate each failure mode:

| Old failure mode | Mavuno design answer |
|||
| Kiosk power cuts | No kiosk. The farmer's own feature phone. |
| WiFi coverage gaps | USSD over 2G. Works where there is no internet. |
| Agent payroll ($4.7M) | No agents. AI advisor over USSD (Groq Llama 3.3, ~$0 per query at freetier scale, deterministic rulebased fallback when API is down). |
| Content staleness | Live feeds. Prices refresh daily; agronomy advice is conditioned on each farm's live soil reading. |
| No business model | Fee per ECT redemption + match fee + data licensing. Every interaction attributes revenue to the platform. |
| Dropout under API outage | 2second hard timeout → deterministic prewritten fallback keyed to question + crop. Farmer is never met with silence. |

## 4. Solution architecture

### 4.1 YPS — Yield Probability Score

A 0–1000 score that acts as the credit signal, replacing collateral and credit history. It is produced by a gradientboosted classifier trained on 7 soil/weather features:

 7day soilmoisture average
 7day rainfall sum
 7day temperature variance
 7day humidity average
 Deviation from cropspecific soilmoisture target
 Deviation from cropspecific rainfall target
 Crop type

The YPS maps to three lending tiers:

 **Full** (YPS ≥ 700) → up to 60 kWh ECT per cycle, UGX 200,000 credit ceiling.
 **Partial** (400–699) → up to 25 kWh ECT per cycle.
 **Denied** (< 400) → no ECT issued; farmer receives agronomy advice instead. The system **refuses to lend into a failing season.**

### 4.2 ECT — Energy Credit Token

 **HMACsigned** by the issuer with a rotating secret.
 **GPSlocked** to a 5 km radius around the farm.
 **72hour expiry** from time of issue.
 **Noncashable** — redeemable only at the specific solar pump node assigned to the farm.
 **Offlineverifiable** by the pump operator via a 20line Python script on a Raspberry Pi; ledger sync on reconnect.

Diversion rate is zero by construction — the token cannot be spent on anything except pump kWh.

### 4.3 Hashchained audit ledger

Every state transition — issue, redeem, reject, expire, offer, match, advise — is appended as a JSON line hashed into a SHA256 chain. /ledger/verify rehashes the full chain and reports tamper. MoSTI, UEDCL, and the SACCO audit the same source of truth in real time.

### 4.4 USSD interface

Six menu items on any feature phone:


[Soil sensor] → [YPS model] → [USSD *165*ACP#]
                                    ├─ 1. YPS score
                                    ├─ 2. Energy credit → [EASP solar pump]
                                    ├─ 3. Balance
                                    ├─ 4. Market price  ─── live regional feed
                                    ├─ 5. Sell produce  ─── automatch 3 buyers
                                    └─ 6. Ask Mavuno    ─── AI agronomist
                                                              ↓
                                             [SHA256 hashchained ledger]


The /ussd/at endpoint speaks Africa's Talking's standard callback shape out of the box, so production deployment is a DNS change, not a rebuild.

### 4.5 CRP — Community Resource Platform

Menu items 4–6 are the "CRP" layer — the market and advisory bundle that makes Mavuno more than a credit product. Farmgate prices, buyer matching, and an AI agronomist all live inside the same USSD session, so the farmer who dials for a pump credit also leaves with the day's price and an answer to "coffee berry borer, what do I do?"

## 5. Technical stack & validation

 **Backend:** Python 3.12 · FastAPI · uvicorn (Fluid Compute ready; vercel.json and api/index.py already wired).
 **ML:** scikitlearn GradientBoostingClassifier · pandas · joblib. Training set: syntheticbutrealistic 500row dataset modelled on USAID Uganda soilmoisture profiles for coffee, maize, and beans.
 **Frontend:** static HTML + vanilla JS — one 994line operations dashboard with Leafletbased Uganda map, perfarm cards, streaming ledger, and dark mode; one 370line Nokiastyle phone simulator that mirrors the USSD state machine pixel for pixel.
 **Ledger:** appendonly JSONL file, SHA256 hash chain, /ledger/verify endpoint.
 **Security:** HMACsigned ECTs with a rotating secret (HMAC_SECRET env var); PDPOcompliant storage posture.

### Model evaluation

From app/data/train_metrics.json on a 105sample heldout test set:

| Metric | Value |
|||
| Accuracy | **0.9048** |
| Macroavg F1 | 0.898 |
| Weightedavg F1 | 0.906 |
| Class 0 (denied) precision / recall | 1.00 / 0.89 |
| Class 1 (partial) precision / recall | 0.87 / 0.94 |
| Class 2 (full) precision / recall | 0.85 / 0.85 |

Of note for a creditissuing model: class0 precision is 1.00 — no false approvals in the heldout set. We would rather deny ten good farms than approve one bad one.

## 6. Competitive landscape

Uganda has agritech. What Uganda does not have is **soilgated, noncashable, marketplacebundled credit over USSD**. The closest comparable products:

 **Apollo Agriculture (Kenya)** — satellite + ML credit scoring for inputs (seed, fertilizer). Mavuno differs: we finance **energy**, not inputs, and we issue a **noncashable** instrument.
 **Emata (Uganda)** — cash credit against dairy/coffee cooperative payrolls. Mavuno differs: no cooperative required; we serve the unorganised smallholder directly, and the instrument cannot be diverted.
 **MKOPA, Sun King, ENGIEFenix** — solar PAYG. These are asset finance — a solar home system. Mavuno is **seasonal productiveuse credit** that runs on top of existing pump infrastructure. We complement, not compete.
 **FarmDrive (regional)** — alternativedata credit scoring. Same critique as Apollo: scoring without a diversionproof instrument leaves cash to be repurposed.

Our singlesentence differentiator: *"The only credit product that is gated by live soil data **and** bundles market price + AI advisor in the same USSD call, and whose loan instrument is noncashable by design."*

## 7. Business model

 **Transaction fee** — 2–3% on every ECT redemption at the pump, paid by the SACCO out of its interest spread.
 **Match fee** — ~1% on buyermatch completions through menu item 5.
 **Data licensing** — at scale, aggregated YPS timeseries become a droughtrisk signal that agricultural insurers and export buyers will pay for.
 **Zero fee to the farmer.** The farmer's incentive is the pump credit, the price, and the advice — never a line item.

## 8. Pilot plan

| Phase | Scope | Success metric |
||||
| **Pilot** (90 days) | 50 farms · Mbale coffee belt · 3–5 EASP pump nodes · 1 SACCO underwriter | ≥ 80% ontime pump utilisation; < 5% loanequivalent default rate (gated by YPS tier). |
| **Year1 expansion** | 5,000 farms · 3 districts · ~UGX 1.2B ECT volume | Replication of pilot metrics at 100× scale; insurer partnership signed. |
| **Year3** | National footprint via PDM integration | YPS becomes a nationally recognised prequalification signal; datalicensing revenue pays for the platform. |

## 9. Data protection posture

 **PDPO 2019 compliant** — the farmer owns their personal data; Mavuno stores it locally on the operator device.
 Only **hashes** of farmlevel state are written to the shared audit ledger; raw soil values never leave the farm's data perimeter.
 Optin, revocable at any time via USSD menu 7 (Exit) followed by an SMS optout keyword.
 Usecase filing against the Personal Data Protection Office model is prepared as part of pilot onboarding.

## 10. Roadmap & asks

 **MoSTI** — endorsement letter, plus **Parish Development Model (PDM)** dataaccess permission for the pilot cohort.
 **UEDCL** — access to 3–5 **EASP** solar pump nodes for the pilot, and a committed pumpoperator training slot.
 **SACCO partner** — one pilot SACCO to underwrite the ECT float and run collections on the interestspread side.
 **Africa's Talking** — production USSD shortcode and callback URL (the /ussd/at endpoint is already conformant).
 **No new hardware.** Python, FastAPI, SHA256, USSD on 2G. Built on rails that already exist.

## 11. Team

   1. Brian Okech   — Developer — okechbrian@gmail.com — full stack
   2. Bazira Brian   — Researcher/UI — bazbrian@gmail.com
   3. Waneroba Barry — Financial Analyst — bwaneroba@gmail.com

## 12. Appendix A — Endpoints

| Method | Path | Purpose |
||||
| GET | /health | Liveness check |
| GET | /farms | All registered farmer profiles |
| GET | /score/{farm_id} | Current YPS + tier |
| POST | /ect/issue | Issue a token for a farm |
| POST | /ect/redeem | Redeem kWh at a pump (HMAC + GPS + expiry checked) |
| GET | /ect/balance/{farm_id} | Active tokens + remaining kWh |
| GET | /ledger | Recent ledger entries |
| GET | /ledger/verify | Rehash the full chain and report tamper |
| POST | /ussd/local | USSD simulator (JSON in/out) |
| POST | /ussd/at | Africa's Talking callback (formencoded) |
| POST | /crp/offers, GET /crp/offers, POST /crp/match/{offer_id} | Marketplace |
| GET | /crp/prices | Regional farmgate price lookup |
| POST | /crp/ask | AI agronomist |
| POST | /demo/cycle | Sensor → YPS → issue → partial redeem, one call (for stage demos) |

## 13. Appendix B — Live state

As of submission:

 /health → {"ok": true, "service": "mavuno"}
 /ledger/verify → {"ok": true, "length": <growing>} — chain intact on every call.
 /score/UGMBL0001 → Akello (Mbale, coffee) YPS **862**, tier **full**, 60 kWh allocated, UGX 200,000 credit ceiling.
 /score/UGGUL0002 → Okello (Gulu, maize) — drought conditions, tier **denied**. The system refuses to lend into a failing season.
 /score/UGMBR0003 → Namazzi (Mbarara, beans) — middling discipline, tier **partial**, 25 kWh allocated.
 Dashboard + phone simulator verified via public URL.

## 14. Links

 **Live prototype:** https://loopinstructionaldirectiveclocks.trycloudflare.com
 **Public source:** https://github.com/okechbrian/mavuno
 **Pitch script (5:00, 9 slides, 8 Q&A cards):** docs/pitchdeck.md in the repo
 **User manual:** docs/usermanual.md in the repo
 **Applicant contact:** okechbrian@gmail.com · subject FUTURE MAKERS HACKATHON 2026
