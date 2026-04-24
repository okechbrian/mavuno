# Roadmap — Chat + Farmer/Buyer Social Layer

Status: **implemented (Tier 1 + Tier 2 text-only)** as of 2026-04-24. Image uploads (§3.4) remain deferred to a post-hackathon Vercel Blob integration. This document is kept as a design record — the live code is in `app/chat.py`, `app/social.py`, the dashboards, and `app/static/feed.html`.

This document captures the design for an in-app chat feature and an optional lightweight social feed ("Mavuno Social"). Both are built to snap onto the existing Mavuno architecture — same auth, same SQLite schema style, same HMAC ledger, same `jget`/`jpost` helpers in the dashboards.

---

## 1. Why

Today the buyer marketplace + Mavuno Pay close a clean commerce loop: browse → match → pay → receipt. What it does not yet support is the **conversation before the deal** — questions like *"is this Robusta or Arabica?"*, *"can you bag it in 50 kg sacks?"*, *"when was it harvested?"* Judges and real users will both push on this gap. Wiring chat to the offer model turns it into a deal-closing tool, not a standalone messaging tab.

A farmer ↔ buyer social feed is a separate, heavier ambition — farmers posting crop updates, buyers reacting. It is a strong demo moment but strictly optional; Tier 1 chat is the minimum viable win.

## 2. Tier 1 — Direct chat tied to offers (target: half a day)

### 2.1 New module `app/chat.py`
Mirrors the shape of `app/payments.py`.

- `open_thread(buyer_id, farm_id, offer_id=None) -> dict` — get-or-create. Unique on `(farm_id, buyer_id, offer_id)`.
- `send(thread_id, sender_role, sender_id, body) -> dict` — validates body length, PII-redacts, inserts, writes `CHAT_MSG` to ledger.
- `messages(thread_id, since_ts=0) -> list[dict]` — long-poll cursor read; server holds the request up to 25 s waiting for new rows, then flushes.
- `threads_for_farm(farm_id)` / `threads_for_buyer(buyer_id)` — inbox lists, newest `last_msg_at` first.
- `unread_count(role, subject_id)` — count of messages newer than the subject's last-read cursor across all their threads.

### 2.2 New tables in `app/database.py`
```sql
CREATE TABLE IF NOT EXISTS chat_threads (
  id TEXT PRIMARY KEY,                -- TH-XXXX
  farm_id TEXT NOT NULL,
  buyer_id TEXT NOT NULL,
  offer_id TEXT,                      -- nullable: chat may pre-date an offer
  created_at INTEGER NOT NULL,
  last_msg_at INTEGER NOT NULL,
  UNIQUE(farm_id, buyer_id, offer_id),
  FOREIGN KEY (farm_id)  REFERENCES farms  (id),
  FOREIGN KEY (buyer_id) REFERENCES buyers (id),
  FOREIGN KEY (offer_id) REFERENCES offers (id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,                -- MSG-XXXX
  thread_id TEXT NOT NULL,
  sender_role TEXT NOT NULL,          -- 'farmer' | 'buyer' | 'agent'
  sender_id TEXT NOT NULL,
  body TEXT NOT NULL,                 -- max 500 chars, PII-redacted on write
  created_at INTEGER NOT NULL,
  FOREIGN KEY (thread_id) REFERENCES chat_threads(id)
);

CREATE INDEX IF NOT EXISTS idx_chat_msgs_thread ON chat_messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_threads_farm  ON chat_threads(farm_id,  last_msg_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_threads_buyer ON chat_threads(buyer_id, last_msg_at DESC);
```

### 2.3 Routes in `app/main.py` (5 new)
| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/chat/threads` | buyer | Body `{farm_id, offer_id?}`. Idempotent open-or-fetch. |
| `GET`  | `/chat/threads` | buyer / farmer | Owner-scoped inbox. |
| `GET`  | `/chat/{thread_id}/messages?since=ts` | party-check | Long-poll; holds up to 25 s. |
| `POST` | `/chat/{thread_id}/messages` | party-check | Body `{body}` ≤ 500 chars; rate-limited 1 msg / 2 s per sender. |
| `GET`  | `/chat/unread/count` | any signed-in | Small badge feed for the topbar. |

Authorisation helper: reuse `session.require_user` + a new `_chat_party_check(thread, user)` analogous to `_payment_party_check` in `app/main.py`.

### 2.4 Transport — long-poll, not WebSockets
Vercel Fluid Compute reuses function instances across requests and the default timeout is 300 s, so a 25 s hold is cheap and safe. Real WebSockets on serverless are fragile (idle-disconnect, no shared state between instances) — we can upgrade later if traffic demands it. Client pseudocode:

```js
let cursor = 0;
async function pump() {
  while (alive) {
    const r = await fetch(`/chat/${thread}/messages?since=${cursor}`);
    const { messages } = await r.json();
    for (const m of messages) { render(m); cursor = m.created_at; }
  }
}
```

### 2.5 Frontend — ~150 LOC each side, no new dependencies
- **`app/static/buyer_dashboard.html`**: a `💬 Chat` button on each offer card, placed beside the existing `Pay UGX …` and `View details` buttons. Clicking opens a slide-in panel with a thread list (left) + active conversation pane (right). Reuses `jget`/`jpost` and the existing toast helper.
- **`app/static/farmer_dashboard.html`**: a new `.radar-card` titled **Buyer messages** under the `My active listings` table; unread badge (red dot + count) on the topbar.
- **CSS**: reuses the form-control color cascade already added, so dark-mode text is readable out of the box. Message bubbles: farmer = left / `var(--accent)`, buyer = right / `var(--gold)`.

### 2.6 Hardening — non-negotiable before demo
- **PII redaction on write** — reuse `crp._redact_pii()` so phone numbers, farm IDs and other long numeric IDs can't leak outside the sealed Mavuno Pay flow.
- **Length cap** — `body: str = Field(..., min_length=1, max_length=500)` on the Pydantic model.
- **Rate limit** — 1 msg / 2 s per `sender_id` using an in-memory bucket that mirrors `_check_login_throttle` in `app/main.py:57`.
- **Party check** — only the buyer, the farmer, or an agent may read or write a given thread. Agents can audit any thread.
- **Ledger events** — `CHAT_OPEN` and `CHAT_MSG` (payload includes `thread_id`, `sender_role`, `sender_id`, `msg_id`, never the body).
- **No moderation** — acceptable for a 90-second demo; note in `docs/SECURITY.md` §11 as a known gap.

### 2.7 Verification
Extend `scripts/verify_payments_e2e.py` (or add `scripts/verify_chat_e2e.py`):
1. buyer opens thread → receives `thread_id`
2. buyer sends `"is this Robusta?"` → 200, body redaction asserted (phone-number test case)
3. farmer logs in, polls `/chat/threads`, sees the thread with unread count 1
4. farmer replies → long-poll on buyer side wakes up with the reply
5. second duplicate send within 2 s returns 429
6. ledger contains `CHAT_OPEN` + two `CHAT_MSG` events with no body leakage

---

## 3. Tier 2 — Mavuno Social (optional stretch, target: another half day)

### 3.1 What
A lightweight public feed where farmers post crop updates and buyers react. Think *Instagram for smallholders* — the demo narrative moment judges remember.

### 3.2 Tables
```sql
CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,                -- P-XXXX
  farm_id TEXT NOT NULL,
  body TEXT NOT NULL,                 -- 1–300 chars
  photo_url TEXT,                     -- nullable; Vercel Blob URL in prod
  created_at INTEGER NOT NULL,
  FOREIGN KEY (farm_id) REFERENCES farms(id)
);
CREATE TABLE IF NOT EXISTS reactions (
  post_id TEXT NOT NULL,
  reactor_role TEXT NOT NULL,
  reactor_id TEXT NOT NULL,
  emoji TEXT NOT NULL,                -- 🌱 🔥 ❤️ 👏
  created_at INTEGER NOT NULL,
  PRIMARY KEY (post_id, reactor_role, reactor_id, emoji)
);
```

### 3.3 Routes
- `POST /feed` — farmer creates a post; body PII-redacted; ≤ 300 chars.
- `GET /feed?limit=50` — reverse-chrono feed across all farms; any signed-in user.
- `POST /feed/{post_id}/react` — buyer or farmer adds a reaction.
- `GET /feed/{post_id}` — single-post detail with reaction counts grouped by emoji.

### 3.4 Image hosting
Photos are optional. If present, upload to **Vercel Blob** (private bucket) and store the returned URL. Do not allow raw image bytes through the FastAPI process — pre-sign from the frontend.

### 3.5 Frontend
New route `/feed` (static HTML, same design language). Farmers see a "Post an update" form at the top; everyone sees the feed below with reaction counts and a single-tap reaction picker.

### 3.6 Moderation
- Flag button on every post → writes `POST_FLAGGED` to the ledger and hides from the public feed until an agent reviews in the cockpit.
- Banned-word list in a JSON config, loaded at startup; server rejects on write.

---

## 4. Why this beats "just add chat"

Pinning chat to **offers** turns it into a deal-closing tool, not just messaging. The demo narrative becomes: *buyer browses marketplace → asks "Robusta or Arabica?" → farmer replies → buyer pays in-app → receipt lands*. That is a complete commerce loop, not a feature collage.

Tier 2 social is the viral layer on top — farmers building a public reputation that converts to buyer trust. It is aspirational for the demo; valuable for adoption.

## 5. Risks / notes

- **SQLite ephemerality on Vercel** — same caveat as offers and payments. Cold starts wipe chat history. Defer to the Neon/Postgres migration.
- **Long-poll holds a function instance** — at < 10 concurrent users (demo scale) this is fine. Revisit at scale; Vercel Fluid Compute will share the instance across concurrent requests but CPU-active time is still billed.
- **No moderation on Tier 2** — do not ship to real users without at least the flag-and-hide flow in §3.6.
- **PII redaction is best-effort regex** — it catches the obvious phone / ID patterns but not free-form "call me at zero seven...". Product fix: a "Share contact" button that uses the Mavuno Pay msisdn field instead of pasting numbers in chat.

## 6. Suggested order if greenlit

1. Tier 1 backend — `app/chat.py` + tables + 5 routes. **2 h.**
2. Tier 1 frontend — both dashboards. **3 h.**
3. TestClient verification (§2.7). **30 min.**
4. Docs — update `README.md` feature table, add §11 Chat to `docs/SECURITY.md`, extend `docs/user-manual.md` with farmer + buyer chat flows. **30 min.**
5. Tier 2 only if Tiers 1–4 land before end of day 2026-04-26. **~5 h incl. moderation.**

Ship path: three focused commits on `main` (`feat(chat): …` · `feat(ui): chat panels` · `docs: chat + social`), then a single `git push origin main`. No deploy — user owns that step, same as the Mavuno Pay rollout.
