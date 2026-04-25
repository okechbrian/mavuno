# Mavuno - Prototype v2

**Live Prototype:** [https://mavuno-prototype.vercel.app](https://mavuno-prototype.vercel.app)

This is the interactive prototype for the **Mavuno**. It demonstrates how soil data, when linked to an immutable SQLite ledger and cryptographically secured tokens, can power Uganda to a $500B economy by unlocking smallholder agricultural finance.

## Getting Started

Because standard Python installations can have conflicting dependency packages, we have provided a foolproof startup script.

1. Open your terminal.
2. Navigate into the prototype directory:
   ```bash
   cd mavuno-prototype
   ```
3. Make the startup script executable (if it isn't already):
   ```bash
   chmod +x start.sh
   ```
4. Run the server:
   ```bash
   ./start.sh
   ```

The server will automatically start on **Port 8001** (to avoid conflicts with any other running apps).
Open your browser and visit: **http://localhost:8001**

## Features Overview

### 1. Multi-User Login Portal
The root address (`http://localhost:8001`) features a secure, multi-role landing page where:
- **Agents** sign in with the agent password configured server-side (see `.env.example`).
- **Farmers** sign in with their Farm ID (or phone number) and PIN to access their personalized dashboard, YPS score, and the AI agronomist.
- **Buyers** sign in with their Buyer ID (or phone number) and PIN to view a live, filtered marketplace of crops matching their pre-verified floor prices.

All sessions use HMAC-signed, HttpOnly cookies (24h TTL). Dashboard, sensor, ECT, ledger, and CRP routes require an authenticated session; resource routes are owner-scoped (a farmer can only see their own farm; agents see all). Per-IP login throttling is applied on the sign-in endpoint. Default credentials are not displayed in the UI.

### 2. The Agent Cockpit (Decision Support System)
The main dashboard serves as an operations center for SACCOs and Co-ops. It features:
- **Biometric Analytics:** Live Nitrogen, Phosphorus, and Potassium (NPK) sparklines.
- **Credit Health Gauges:** Visual indicators of a farmer's credit-worthiness based on their Yield Probability Score (YPS).
- **Macro-Analytics:** The left sidebar displays real-time Credit Velocity, System Risk, and Ledger Verification status.

### 2. Buyer Network & CRP Marketplace
The system operates a live Community Resource Platform (CRP) marketplace connecting smallholders with pre-verified institutional off-takers.
- **The Buyer Network List:** Visible in the left sidebar, showing registered SACCOs and regional cooperatives.
- **How to Onboard:** Click the **"+ Onboard Buyer"** button in the sidebar. Enter the institution's name, their operating region, floor price, and the crops they purchase. Once registered, they are instantly available to be matched with farmers on the USSD interface via the CRP engine.
- **Full marketplace browse with smart-sort:** The buyer dashboard now shows **every open offer**, not just exact matches. Filter chips (`All` · `My region` · `My crops` · `Within budget`) toggle the view and are reflected in the URL for shareable links. Each offer card carries a match badge — `★ MATCH` (all three conditions satisfied), `~ partial` (two of three), or unbadged — and sorts highest-score-first, then newest-first.

### 2b. Mavuno Pay — direct buyer → farmer settlement
A complete payment state machine wired into the marketplace:
- **`POST /payments/initiate`** — a buyer clicks **Pay UGX …** on an offer; the server computes the amount as `offer.kg × offer.floor_ugx` (the client-supplied amount is never trusted), creates a `pending` payment row, writes a `PAYMENT_INITIATED` ledger event, and triggers a mocked PSP.
- **`POST /payments/confirm`** — callback endpoint. The body's HMAC signature (`X-Mavuno-Sig` header) is verified against `HMAC_SECRET` using `hmac.compare_digest` before the state transitions to `settled` or `failed`. On success the matching offer closes and `OFFER_ACCEPTED` lands in the ledger.
- **`GET /payments/receipt/{id}`** — JSON receipt with payload format `payment_id|offer_id|amount|status` and a HMAC-SHA256 signature over it. A holder can verify the receipt offline using the operator's shared key.
- **Dashboards:** the buyer dashboard polls `GET /payments/status/{id}` every 1.5 s until settled/failed and shows a toast; the farmer dashboard's **Payments Received** feed renders `GET /payments/farmer/{id}`.
- **PSP swap path:** `app/payments.py::_psp_initiate` is the one function to replace for production — wire it to Flutterwave or MTN MoMo and the rest of the flow (DB writes, ledger, receipts) is unchanged.

### 2d. Mavuno Chat — offer-scoped buyer ↔ farmer messaging
A long-poll chat layer that pins conversations to specific offers, so judges (and real users) can see the *"is this Robusta? what bag size? when harvested?"* exchange that closes a deal:
- **`POST /chat/threads`** — buyer-initiated, idempotent on `(farm_id, buyer_id, offer_id)`. Writes `CHAT_OPEN` to the ledger.
- **`POST /chat/{thread_id}/messages`** — body capped at 500 chars, **PII-redacted on write** (phone numbers and farm IDs replaced with `[redacted]`), rate-limited 1 msg / 2 s per `sender_id`. Writes `CHAT_MSG` to the ledger — **payload never carries the body**, only structural identifiers.
- **`GET /chat/{thread_id}/messages?since=ts&wait=25`** — long-poll read. Holds up to 25 s waiting for new rows; breaks early on client disconnect. Auto-advances the reader's cursor so unread counts settle without a separate call.
- **`GET /chat/threads`** — owner-scoped inbox; `GET /chat/unread/count` powers the topbar badge.
- **Surfaces:** buyer dashboard has both a per-offer 💬 button on the offer card *and* a topbar Messages chip; the farmer dashboard has a "Buyer Messages" inbox card and the same topbar chip. Drawer is pure CSS slide-in, no new deps.

### 2e. Mavuno Social — public farmer feed (text-only for demo)
A lightweight reputation surface where farmers post crop updates and buyers react:
- **`POST /feed`** (farmer-only) — body 1–300 chars, PII-redacted, banned-word checked against `app/data/banned_words.json`. Writes `POST_CREATED`.
- **`GET /feed?limit=50`** — reverse-chrono, excludes hidden posts; hydrated with farmer name, district, crop, and grouped reaction counts.
- **`POST /feed/{id}/react`** — emoji allowlist (🌱 🔥 ❤️ 👏); composite-PK upsert means clicking the same emoji twice is a no-op.
- **`POST /feed/{id}/flag`** — any signed-in user can flag; first flag flips `posts.hidden = 1` and writes `POST_FLAGGED`. Auto-moderation only — production needs a human review queue (documented in `docs/SECURITY.md` §11.5).
- **Page:** `/feed-page` serves a standalone feed UI with role-aware composer; topbar links from every dashboard.
- **Photos deferred:** `posts.photo_url` is reserved for a follow-up Vercel Blob integration.

### 2c. Farmer self-listing
Farmers now post offers directly from their dashboard (previously USSD-only):
- **Inline form** (`List Produce for Sale` card): crop dropdown (prefilled from the farm's registered crop, plus a common-crop allowlist), quantity in kg (1 – 50 000), floor price in UGX/kg (100 – 10 000 000). Submits to **`POST /crp/offers`** (farmer-role, owner-scoped).
- **My active listings** table below the form reads `GET /crp/offers?farm_id={id}&include_closed=true` and shows the joined `payment_status` as a pill (`open` / `pending` / `settled` / `failed`).

### 3. Multi-Language USSD Simulator & CRP Advisor
Visit **http://localhost:8001/phone** to simulate the farmer's experience on a 2G feature phone.
- The simulator is fully functional in both **English and Luganda**.
- Farmers can check market prices, sell produce (which auto-matches against the Buyer Network), and ask the CRP AI Agronomist for specific advice based on their live soil readings.

### 4. Dirt-to-Ledger IoT Telemetry (The 7 Crucial Signals)
Mavuno is not just software; it is an IoT-integrated protocol. Real physical hardware in the field captures 7 distinct environmental and agronomic signals:
1. **Soil Moisture (%)**
2. **Soil Temperature (°C)**
3. **Nitrogen (mg/kg)**
4. **Phosphorus (mg/kg)**
5. **Potassium (mg/kg)**
6. **Ambient Humidity (%)**
7. **Rainfall (mm)**

**How to deploy this practically and affordably?**
Please read the [Hardware & Practical Deployment Strategy](docs/HARDWARE_DEPLOYMENT.md) document to see how we use **Sentinel Nodes** to drop the hardware cost to **~$4.00 per farmer**, and how we use shared solar hubs to distribute water without putting farmers in asset debt.


### 5. Cryptographic Security & Offline Verification
Tokens are signed using HMAC-SHA256. To demonstrate that remote solar pumps can verify these tokens *without* an internet connection, run the offline verification script:
```bash
python3 offline_pump_demo.py
```
This script proves that the system remains resilient to rural infrastructure failures.

### 6. AI Agronomist (Groq)
The `Ask Mavuno` feature uses Groq's `llama-3.3-70b-versatile` for one- or two-line, context-aware advice. The API key is read from `GROQ_API_KEY` server-side; it never reaches the browser. All farmer questions are PII-redacted (phone numbers, farm IDs, and other long numeric IDs are stripped) and length-capped before egress. If the key is absent or the upstream call fails, a deterministic on-device rule bank answers — the farmer always gets a reply.

**UI fix (2026-04-24):** the agronomist textarea in dark mode was rendering black-on-black because browsers do not inherit `color` onto form controls by default. The farmer dashboard now applies an explicit `color: var(--ink); -webkit-text-fill-color: var(--ink); caret-color: var(--ink);` cascade to every input, textarea, and select.

### 7. Mobile-First UI
Every dashboard (Agent, Farmer, Buyer) collapses into a single column at ≤768px with a slide-in nav drawer, a backdrop overlay, and 44px touch targets. The login screen reorders for thumb reach. The USSD simulator at `/phone` renders cleanly on a feature-phone-sized viewport.

## Environment Variables
See `.env.example`. Never commit a real `.env` file. The `.gitignore` excludes `.env`, `.env.local`, `.env.*.local`, the SQLite database, and the virtual environment by default.

| Variable | Purpose |
|---|---|
| `HMAC_SECRET` | Signs ECT tokens, sessions, payment receipts, and the ledger hash chain. Rotate to invalidate all sessions. |
| `AGENT_PASSWORD` | Override the default agent sign-in password. Set this in production. |
| `GROQ_API_KEY` | Optional. Enables LLM-backed agronomy advice. Falls back to rule bank when absent. |
| `PUBLIC_BASE_URL` | Used for cookie `Secure` flag detection, absolute links, and the mocked PSP callback URL. |
| `AT_USERNAME` / `AT_API_KEY` | Africa's Talking USSD credentials (production only). |

## HTTP API surface (selected)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/crp/offers` | Farmer (or agent) posts a new offer. Body: `{farm_id, crop, kg, floor_ugx}`. |
| `GET` | `/crp/offers` | Buyer/agent sees all open offers. With `?farm_id=…&include_closed=true` a farmer sees their own history. Each row carries a joined `payment_status`. |
| `POST` | `/payments/initiate` | Buyer starts a payment. Body: `{offer_id, msisdn, method}`. Amount is derived server-side. |
| `POST` | `/payments/confirm` | PSP callback. Body HMAC'd in `X-Mavuno-Sig`. |
| `GET`  | `/payments/status/{id}` | Polled by the buyer dashboard for live status. |
| `GET`  | `/payments/farmer/{id}` | Feed for the farmer dashboard. |
| `GET`  | `/payments/buyer/{id}` | Feed for the buyer dashboard. |
| `GET`  | `/payments/receipt/{id}` | Offline-verifiable, HMAC-signed JSON receipt. |
| `POST` | `/chat/threads` | Buyer opens (or fetches) a thread on `(farm_id, offer_id?)`. Idempotent. |
| `GET`  | `/chat/threads` | Owner-scoped inbox: farmer sees their threads, buyer sees theirs, agent sees all. |
| `GET`  | `/chat/{id}/messages?since=ts&wait=25` | Long-poll read. Auto-marks the reader's cursor. |
| `POST` | `/chat/{id}/messages` | Body PII-redacted on write. Rate-limited 1/2 s per `sender_id`. |
| `GET`  | `/chat/unread/count` | Topbar badge feed. |
| `GET`  | `/feed-page` | Public farmer feed UI (any signed-in user). |
| `POST` | `/feed` | Farmer creates a post. PII-redacted, banned-word filtered. |
| `GET`  | `/feed?limit=50` | Reverse-chrono feed; excludes hidden posts. |
| `GET`  | `/feed/{id}` | Single post with grouped reaction counts. |
| `POST` | `/feed/{id}/react` | Emoji allowlist (🌱 🔥 ❤️ 👏); idempotent on (post, user, emoji). |
| `POST` | `/feed/{id}/flag` | Auto-hides the post; writes `POST_FLAGGED` to the ledger. |
