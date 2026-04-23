# Mavuno — Concept Note

**Future Makers Hackathon 2026 · National Science Week 2026**
**Challenge:** Powering Uganda to a $500B Economy.

> *Where soil becomes credit. And the same phone call becomes a market, an advisor, and a pump.*

---

## 1. The problem

Ugandan smallholders hit four walls at once:

- **No collateral, no credit.** ~7 in 10 are unbanked; without land title or salary, SACCOs cannot lend.
- **No grid, no irrigation.** Only ~19% of rural Uganda has reliable electricity, so pumps sit idle even when water is nearby.
- **No weather signal, no insurance.** Rainfall variability destroys ~20% of yields year-on-year.
- **No market signal, no pricing power.** Farmers sell at the farmgate low-price because the nearest price board is a twelve-hour bus away.

Cash micro-loans do not solve any of this — cash gets diverted. A different financial instrument, carried over a different information channel, is needed.

## 2. The solution — Mavuno

Mavuno turns **soil data** into a **non-cashable energy credit**, delivered over **USSD on a feature phone**. One dial-string, six menu items, zero smartphones.

| # | Menu item | What it does |
|---|---|---|
| 1 | YPS score | Returns the farm's Yield Probability Score (0–1000) from 7 soil features, using a gradient-boosted classifier (90.5% test accuracy). |
| 2 | Energy credit | Issues an **Energy Credit Token (ECT)** — HMAC-signed, GPS-locked to 5 km of the farm, 72-hour expiry, redeemable **only** at a specific solar pump. |
| 3 | Balance | Active tokens, remaining kWh. |
| 4 | Market price | Live regional farmgate price for the farmer's crop from the Community Resource Platform (CRP). |
| 5 | Sell produce | Posts an offer to the CRP Marketplace; auto-matches up to 3 buyers within 24 hours. |
| 6 | Ask Mavuno | CRP AI agronomist (Groq Llama 3.3, with a deterministic rule-based fallback when offline). Answers conditioned on live soil data, returned in USSD-safe 140-char chunks. |

Every state change — issue / redeem / reject / expire / offer / match / advise — is appended to a **SHA-256 hash-chained audit ledger**. MoSTI, UEDCL, and the SACCO audit the same source of truth in real time.

## 3. What is new

- **The YPS signal.** Instead of "do you have land title?" we ask "does your soil say you'll grow a crop?" Seven features, one gradient-boosted model, 90%+ accuracy on held-out test data.
- **The ECT instrument.** A cash loan gets diverted. An ECT cannot. It is not money; it buys irrigation kWh, within 5 km, within 72 hours, at one specific pump. Diversion rate is **zero by construction.**
- **Information channel.** Credit, market prices, and an AI agronomist all live inside the same USSD session — no app install, no WiFi, no agent network. The USSD is now **multi-language (English and Luganda)** for maximum rural accessibility.
- **Agent Decision Support.** The v2 prototype features an interactive **Agent Cockpit** for SACCOs. It provides real-time **NPK (Nitrogen, Phosphorus, Potassium) biometric trends**, Credit Velocity tracking, and one-click farmer onboarding, turning data into actionable field operations.
- **Immunity by design.** We studied why agri-tech keeps dying in East Africa: Oxfam Novib's *Internet Now!* (2012, 100 Northern Uganda kiosks) lost to power cuts and content staleness; Grameen's *Community Knowledge Worker* program (Uganda 2009–14, 1,200→300 agent collapse) lost to agent churn and donor dependency. Mavuno eliminates every one of those failure modes.

## 4. Why this wins the $500B challenge

Uganda's Vision 2040 / $500B economy depends on unlocking smallholder productivity — ~70% of employment, ~24% of GDP. Mavuno compounds three unlocks on one rail:

1. **Finance access** — turns soil into collateral; SACCOs can price risk they previously could not touch.
2. **Energy access** — routes every approved token through a **UEDCL EASP** solar pump node, putting unused pump capacity to work.
3. **Market access** — farmers price in real time, sell to pre-verified buyers, log every transaction to a PDM-compatible ledger.

All three use rails that **already exist** — Parish Development Model (PDM, UGX 100M/parish/year), UEDCL EASP (World Bank ~$638M, 2023), mobile money. We are not building new infrastructure; we are making the existing infrastructure addressable from a feature phone.

## 5. Impact & scale

- **Pilot:** 50 farms · Mbale coffee belt · 90 days · 3–5 EASP pump nodes · 1 partner SACCO.
- **Year-1 target:** 5,000 farms across 3 districts, ~UGX 1.2B in ECT volume, sub-5% loan-equivalent default rate (gated by YPS).
- **Practical Hardware:** Mavuno uses a **Sentinel Node** deployment strategy. One 7-in-1 IoT sensor node is placed in the center of a 1km Parish block, providing data for 10-15 farmers simultaneously. This reduces hardware CAPEX to just **~$4.00 per farmer**.
- **Scale ceiling:** The backend is hardened with an **ACID-compliant SQLite database** to handle concurrent USSD sessions at national scale. The YPS model is stateless per farm, allowing thousands of farmers to be served from a single compute instance.
- **Data dividend:** the YPS time-series becomes a drought-risk signal that insurers and export buyers will pay for — licensable at national scale.

## 6. Business model

- 2–3% transaction fee on ECT redemption at the pump — paid by the SACCO out of its interest spread.
- ~1% success fee on buyer-match completions via the CRP marketplace.
- At scale: data licensing of aggregated YPS signals to insurers and export buyers.
- **Zero fee to the farmer.**

## 7. Compliance

- **PDPO 2019** aligned — farm data stored locally; only hashes written to the shared ledger; farmer owns and can revoke the keys.
- **Minister Musenero's "productive capital" framing** — the ECT is productive capital by construction (it cannot buy anything non-productive).

## 8. Status today

- **Prototype v2 live:** Featuring an interactive Agent Cockpit, durable SQLite storage, and multi-user login (Farmer, Buyer, Agent).
- **Source (public):** https://github.com/okechbrian/mavuno
- **Stack:** Python 3.12 · FastAPI · scikit-learn · uvicorn · SQLite · USSD (Africa's Talking callback shape) · SHA-256 ledger.
- **Ledger state:** chain verified intact — `/ledger/verify` returns `{"ok": true}`.
- **Hardware Integration:** API-ready for GSM-enabled 7-in-1 soil sensor telemetry.

## 9. Team

{{TEAM_ROSTER}}

## 10. The ask

50 farms. 3 pumps. 90 days. MoSTI endorsement, UEDCL EASP pump access, one SACCO underwriter. If YPS predicts yield, the loans repay themselves. If not, no cash was ever lent. Either way, Uganda learns whether soil can be collateral.

## 11. Contact

- **Email:** okechbrian@gmail.com
- **Subject-line reference:** FUTURE MAKERS HACKATHON 2026
- **Repo:** https://github.com/okechbrian/mavuno
- **Live demo:** https://mavuno-prototype.vercel.app
