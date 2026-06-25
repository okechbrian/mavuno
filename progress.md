# Mavuno — Project Progress Report

**Generated:** 22 June 2026  
**Repository:** `C:\Users\y\agrochain-pulse` (branch `main`)  
**Live:** http://localhost:8001

---

## Ecosystem Overview

The Mavuno project spans 4 directories:

| Project | Stack | Status | Description |
|---------|-------|--------|-------------|
| `agrochain-pulse/` | FastAPI + SQLAlchemy + SQLite | **Active (~95%)** | Full-featured backend with auth, payments, chat, social, training, logistics, hardware store, notifications |
| `mavuno/` | FastAPI + SQLAlchemy + SQLite | **Redesign branch (~93%)** | Fork of agrochain-pulse on `redesign/farmer-dashboard` branch with UI modernization |
| `mavuno-prototype/` | FastAPI + raw SQLite | **Archived (~92%)** | Early proof-of-concept, deployed at mavuno-prototype.vercel.app |
| `mavuno-app/` | Kotlin + Jetpack Compose | **In progress (~78%)** | Multi-module Android app (farmer/agent/buyer) with Hilt, Room, Retrofit |

---

## agrochain-pulse — Feature Completion

### Backend API (50+ endpoints)

| Feature | Status | Notes |
|---------|--------|-------|
| Auth (HMAC cookie sessions, multi-role) | Done | Agent, farmer, buyer, logistics, supervisor roles |
| Farmer/Buyer onboarding | Done | Signup, KYC, hardware purchase flows |
| YPS Scoring Engine | Done | ML model (GradientBoosting, ~90% accuracy) |
| Energy Credit / Trade Priority | Done | HMAC-signed, 72h expiry, issue/redeem |
| Marketplace (CRP) | Done | Offers, matching, market prices |
| Mavuno Pay | Done | Initiate, confirm, batch, PDF receipts, HMAC verification |
| Chat (offer-scoped) | Done | Long-poll, PII redaction, rate limited |
| Social Feed | Done | Posts, reactions, flagging, verified harvests |
| AI Agronomist | Done | Groq + Gemini with rule-bank fallback |
| Training & Certification | Done | 4 modules, verifiable on-ledger |
| Logistics Route Optimization | Done | KMeans clustering (falls back flat list without sklearn) |
| Hardware Store | Done | Catalog, purchase flow, Sentinel Node audit |
| USSD Simulator | Done | Bilingual (EN/LG), 7 menu items |
| Immutable Ledger | Done | SHA-256 hash chain, verify endpoint |
| Notifications | Done | In-app + SMS fallback |
| Supervisor Dashboard | Done | Regional YPS, trade volume |

### Frontend Dashboards (14 HTML pages)

| Page | Status | Notes |
|------|--------|-------|
| Landing / Login | Done | Light/dark theme, role selection |
| Agent Command Center | Done | **Last worked on** — hover-rail sidebar, user dropdown, triage queue, biometric grid, credit mgmt, logistics, hardware audit |
| Farmer Dashboard | Done | YPS display, NPK trends, market prices, AI advisor |
| Buyer Dashboard | Done | Live offers, market trends |
| Logistics Dashboard | Done | Collection routes |
| Supervisor Dashboard | Done | Regional stats |
| USSD Phone Simulator | Done | Interactive Nokia-style |
| Hardware Store | Done | Product catalog |
| Onboarding Flow | Done | KYC + purchase steps |
| Social Feed | Done | Verified gallery, moderation |
| Terms of Service | Done | — |

### Mobile App (mavuno-app/)

| Layer | Status | Notes |
|-------|--------|-------|
| Architecture | 90% | Multi-module Clean Architecture + MVVM |
| Navigation | 85% | 3 APKs with full nav graphs |
| UI Screens | 85% | 13 Compose screens |
| Data Layer | 80% | Room DB + Retrofit; some repos mocked |
| Offline/Sync | 70% | WorkManager setup; some sync simulated |
| Hardware Integration | 50% | BLE framework exists, data is simulated |

**Known issues:**
- `FarmerEntity.toDomain()` positional args mismatch — won't compile
- `MarketplaceViewModel` references `offer.farmerName` — field doesn't exist
- `placeBid()` returns empty `flow { }`
- Buyer profile data entirely mocked
- "List Produce" and "Comments" are TODO stubs
- JVM OOM on <8GB RAM during Gradle build

---

## Recently Completed Work (22 June)

### Sidebar & User Menu (agent_dashboard.html)
- Converted sidebar from toggle collapse → **hover-rail** pattern
- Sidebar fixed position, narrow rail by default, expands on hover
- Removed old sidebar toggle button and `localStorage` persistence logic
- Added user avatar dropdown with notification badge
- Dropdown items: Notifications, Settings, Sign out

### Backend Integration (main.py)
- `triage_inspection` bucket for farmers needing field inspection
- `unread_notifications` count in agent overview API
- Notification calls on KYC submission and hardware purchase

### Fixes Applied
- `logistics.py`: scikit-learn import made lazy (not in requirements.txt)
- `gateways.py`: africastalking import made optional
- Installed missing deps: `python-multipart`, `africastalking`

---

## Q2 Acceleration Plan (from Gemini CLI — Not Executed)

The discontinued Gemini CLI left these items planned but unstarted:

| Phase | Task | Status |
|-------|------|--------|
| 1 | PostgreSQL/Neon database migration | **Not started** — still on SQLite |
| 2 | Vercel Blob image uploads for social feed | **Not started** — photo upload endpoint missing |
| 3 | React Native bridge foundation | **Not started** — no RN project created |

---

## How to Run

```bash
cd C:\Users\y\agrochain-pulse
pip install -r requirements.txt
python run.py
# Server starts at http://localhost:8001
# First startup takes ~69s (DB schema + seed data)
# Subsequent restarts are faster
```

### Demo Credentials
- **Agent:** ID `admin`, password `mavuno2026`
- **Farmer/Buyer:** PIN `1234`
- **Supervisor:** ID `admin`, password `governance2026`
