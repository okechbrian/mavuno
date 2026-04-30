# Mavuno Yield — Concept Note

**Mavuno Yield · National Science Week 2026**
**Challenge:** Powering Uganda to a $500B Economy.

> *Where soil data becomes trusted trade. And the same phone call becomes a market, an advisor, and a verified score.*

---

## 1. The problem

Ugandan smallholders hit four walls at once:

- **No collateral, no credit.** ~7 in 10 are unbanked; without land title or salary, SACCOs cannot lend.
- **No data, no trust.** Buyers cannot verify if a farmer's yield will be reliable, leading to low farmgate prices.
- **No weather signal, no insurance.** Rainfall variability destroys ~20% of yields year-on-year.
- **No market signal, no pricing power.** Farmers sell at the farmgate low-price because the nearest price board is a twelve-hour bus away.

Traditional micro-loans do not solve the trust gap. A verified intelligence layer, carried over a standard information channel, is needed to unlock agricultural trade.

## 2. The solution — Mavuno Yield

Mavuno Yield turns **soil data** into a **trusted trade priority**, delivered over **USSD on a feature phone**. One dial-string, six menu items, zero smartphones.

| # | Menu item | What it does |
|---|---|---|
| 1 | YPS score | Returns the farm's Yield Probability Score (0–1000) from 7 soil signals. |
| 2 | Trade Priority | Issues an **Yield Priority (Trade Priority)** — HMAC-signed, verified for CRP marketplace listing. |
| 3 | Balance | Verified KG remaining for marketplace trade. |
| 4 | Market price | Live regional farmgate price for the farmer's crop from the Community Resource Platform (CRP). |
| 5 | Sell produce | Posts an offer to the CRP Marketplace; auto-matches verified institutional buyers. |
| 6 | Ask Mavuno | CRP AI agronomist (Groq Llama 3.3). Answers conditioned on live soil data, returned in USSD-safe 140-char chunks. |

Every state change — YPS update / trade listing / match / settlement — is appended to a **SHA-256 hash-chained audit ledger**. Supervisors and SACCOs audit the same source of truth in real time.

## 3. What is new

- **The YPS engine.** Instead of "do you have land title?" we ask "does your soil say you'll grow a crop?" Seven signals, calibrated for Ugandan soil, providing a trust layer for trade.
- **CRP Access.** A Yield Priority isn't just a number; it's priority access to premium buyers. Diversion of value is eliminated as transactions are tied to verified harvest potential.
- **Decentralized Oversight.** v2 features a **Governance Dashboard** for SACCOs and regional coordinators. It provides regional YPS trends, trade velocity tracking, and agent performance monitoring.
- **USSD-First Intelligence.** Credit health, market prices, and an AI agronomist all live inside the same USSD session — no app install, no WiFi. Multi-language support (English/Luganda) ensures rural reach.
- **Immunity by design.** Mavuno eliminates common failure modes in East African agri-tech by using existing infrastructure (USSD, mobile money, SACCO networks) rather than building redundant systems.

## 4. Why this wins the $500B challenge

Uganda's Vision 2040 / $500B economy depends on unlocking smallholder productivity. Mavuno Yield compounds three unlocks on one rail:

1. **Finance access** — turns soil into collateral; SACCOs can price trade risk using YPS.
2. **Trade verification** — verified soil signals prove production capacity to institutional buyers.
3. **Market matching** — farmers price in real time and sell to pre-verified buyers on the CRP.

We are making existing agricultural infrastructure addressable and trusted from any feature phone.

## 5. Impact & scale

- **Pilot:** 50 farms · Mbale coffee belt · 90 days · 1 partner SACCO.
- **Year-1 target:** 5,000 farms across 3 districts, ~UGX 1.2B in verified trade volume.
- **Scale ceiling:** The backend uses an ACID-compliant protocol to handle concurrent USSD sessions at national scale. The YPS model is stateless per farm, allowing thousands of users to be served from a single compute instance.
- **Data dividend:** Aggregated YPS trends become a national drought-risk and productivity signal for government and insurers.

## 6. Business model

- ~1% success fee on buyer-match completions via the CRP marketplace.
- Data licensing of aggregated regional soil intelligence to insurers and large-scale buyers.
- **Zero fee to the farmer.**

## 7. Compliance

- **PDPO 2019** aligned — farm data remains private; only cryptographic hashes are written to the ledger.
- **Productive Capital** — YPS ensures that trade and financing are tied strictly to agricultural output.

## 8. Status today

- **Mavuno Yield Live:** Featuring Agent, Buyer, Farmer, and Supervisor dashboards with durable SQLAlchemy storage.
- **Source (public):** https://github.com/okechbrian/mavuno
- **Stack:** Python 3.12 · FastAPI · scikit-learn · uvicorn · SQLite · SHA-256 ledger.
- **Security:** HMAC-signed sessions, role-based access, server-side LLM coordination.

## 9. Contact

- **Email:** okechbrian@gmail.com
- **Subject:** Mavuno Yield
- **Repo:** https://github.com/okechbrian/mavuno
- **Live demo:** https://mavuno-prototype.vercel.app
