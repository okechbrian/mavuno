# Mavuno

> *Where soil becomes credit.*

Soil-backed energy credit for smallholder farms — a prototype showing how soil-sensor data can replace collateral as the signal that underwrites irrigation financing.

---

## Future Makers Hackathon 2026 — submission index

Submitted to MoSTI Uganda's Future Makers Hackathon 2026 ("Powering Uganda to a $500B Economy"). Application deadline: **2026-04-22**. Demo window: **2026-04-28 → 2026-05-03**.

- **Live prototype:** https://loop-instructional-directive-clocks.trycloudflare.com (ephemeral Cloudflare quick tunnel → laptop `:8000`; promoted to a named tunnel before the demo window)
- **Public source:** https://github.com/okechbrian/mavuno
- **Short concept note →** [`docs/concept-note.md`](docs/concept-note.md)
- **Written summary →** [`docs/written-summary.md`](docs/written-summary.md)
- **Demo pitch (9-slide, 5:00 script, 8 Q&A cards) →** [`docs/pitch-deck.md`](docs/pitch-deck.md)
- **User manual (farmer / pump operator / partner) →** [`docs/user-manual.md`](docs/user-manual.md)
- **Submission email draft →** [`docs/submission-email.md`](docs/submission-email.md)

---

## What's inside

- **YPS (Yield Probability Score)** — a gradient-boosted classifier turns 7 soil features into a 0–1000 credit signal
- **ECT (Energy Credit Token)** — HMAC-signed, GPS-locked, 72-hour, non-cashable kWh voucher redeemable at one specific solar pump
- **USSD** — menu-driven interface matching Africa's Talking callback shape; runs on any feature phone
- **Ledger** — append-only SHA-256 hash chain; every issue / redeem / reject / expire is auditable
- **Dashboard** — live operations view with Uganda map + per-farm cards + streaming ledger + dark mode
- **Phone simulator** — Nokia-style browser phone that mirrors the USSD state machine

## Run locally

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python ml\generate_data.py
.venv\Scripts\python ml\train.py
.venv\Scripts\uvicorn app.main:app --port 8000 --reload
```

Open:
- `http://localhost:8000/` — operations dashboard
- `http://localhost:8000/phone` — USSD simulator

## Deploy to Vercel

1. Install the Vercel CLI (one-time):
   ```
   npm i -g vercel
   ```

2. From the project root, make sure seed data + model are generated:
   ```
   .venv\Scripts\python ml\generate_data.py
   .venv\Scripts\python ml\train.py
   ```

3. Deploy:
   ```
   vercel deploy
   ```
   Accept the defaults. First run creates the project.

4. **Set `HMAC_SECRET`** in the Vercel dashboard (Settings → Environment Variables), then redeploy to production:
   ```
   vercel env add HMAC_SECRET production
   vercel deploy --prod
   ```
   Without this, tokens signed on one invocation may not verify on another.

5. Open the returned `https://mavuno-xxxxx.vercel.app/` URL.

**Serverless notes:**
- Ledger and token state live in `/tmp/mavuno_data` on Vercel and reset on cold start. Fine for a demo — each session is a fresh chain. For a pilot, swap `app/ledger.py` and `app/ect.py` to a durable store (SQLite/WAL, Redis, or Vercel Blob).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/farms` | All registered farmer profiles |
| GET | `/score/{farm_id}` | Current YPS + tier |
| POST | `/ect/issue` | Issue a token for a farm |
| POST | `/ect/redeem` | Redeem kWh at a pump (HMAC + GPS + expiry checked) |
| GET | `/ect/balance/{farm_id}` | Active tokens + remaining kWh |
| GET | `/ledger` | Recent ledger entries |
| GET | `/ledger/verify` | Re-hash the full chain and report tamper |
| POST | `/ussd/local` | USSD simulator (JSON in/out) |
| POST | `/ussd/at` | Africa's Talking callback (form-encoded) |
| POST | `/demo/cycle` | Sensor → YPS → issue → partial redeem, one call |

## Documentation

- [`docs/concept-note.md`](docs/concept-note.md) — 1-page concept note (Future Makers 2026 submission)
- [`docs/written-summary.md`](docs/written-summary.md) — long-form written summary (Future Makers 2026 submission)
- [`docs/pitch-deck.md`](docs/pitch-deck.md) — 9-slide, 5-minute pitch script with speaker notes and 8 Q&A cards
- [`docs/user-manual.md`](docs/user-manual.md) — farmer, pump operator, and partner guides
- [`docs/submission-email.md`](docs/submission-email.md) — committee-facing email draft

## Stack

Python 3.12 · FastAPI · scikit-learn · pandas · pydantic · joblib · uvicorn[standard]
