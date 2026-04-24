# Mavuno — Security Overview

This is a high-level overview of how Mavuno protects user data, sessions, and credentials. It is intentionally framework-level — implementation details (key material, exact route lists) live in code and environment variables only.

## 1. Sessions
- **Mechanism:** HMAC-SHA256-signed cookies. The cookie carries `role | subject | expiry`; nothing else.
- **Flags:** `HttpOnly`, `SameSite=Lax`, `Secure` whenever the request is HTTPS.
- **Lifetime:** 24 hours from sign-in. After expiry the next API call returns 401 and the dashboard redirects to sign-in.
- **Stateless:** No per-request database lookup; the signature alone proves authenticity. Rotating the HMAC secret invalidates every outstanding session.
- **Revocation surface:** restart the server with a new `HMAC_SECRET` to log everyone out instantly.

## 2. Authorisation
Every route falls into one of three buckets:

| Bucket | Examples |
|---|---|
| **Public** | landing page, terms, USSD simulator, market price lookup, health check |
| **Signed-in only** | sensor telemetry, ECT issue/redeem, ledger views, CRP marketplace, AI agronomist |
| **Owner-scoped** | farmer dashboard data, buyer marketplace data — agents see all; everyone else sees only their own subject |

Owner scoping is enforced by a single dependency that compares the URL subject to the cookie subject; the agent role bypasses the comparison.

## 3. Sign-in protection
- **Throttling:** small burst of attempts per IP, then a short cool-off. In-memory only; sufficient for a single-region prototype, replace with Redis on horizontal scale.
- **Timing-safe comparison:** `hmac.compare_digest` for both passwords and signatures.
- **No credential leakage:** placeholders in the sign-in form do not reveal default values; failed sign-ins return a generic error.

## 4. Secrets
All secrets are loaded from environment variables at process start. The repository ships only `.env.example` with empty values; `.env` is git-ignored.

| Variable | Purpose |
|---|---|
| `HMAC_SECRET` | Signs ECT tokens, sessions, and the ledger hash chain. |
| `AGENT_PASSWORD` | Agent sign-in. Override the default in production. |
| `GROQ_API_KEY` | Optional. Server-side only. Never reaches the browser. |
| `AT_API_KEY`, `AT_USERNAME` | Africa's Talking USSD credentials. |

## 5. AI agronomist (LLM egress)
- The Groq key is read server-side only; no client code references it.
- Each user question is **PII-redacted** before egress: phone numbers, farm IDs, and other long numeric IDs are stripped.
- The question is **length-capped** before being sent.
- The prompt context is intentionally narrow: crop, district, YPS score, and credit-health bucket — nothing personally identifying.
- If the upstream call fails or no key is configured, a deterministic on-device rule bank answers from the same context. No silent failures.

## 6. Ledger integrity
Every state change writes one row to a SHA-256 hash-chained append-only ledger. `/ledger/verify` recomputes the chain end-to-end; tampering shows up as a named bad row. The chain is signed by the same `HMAC_SECRET` so that a compromised database without the key cannot be silently rewritten.

## 7. Data minimisation
- Soil readings and GPS are written to the ledger as hashes, not raw values.
- The session cookie contains no name, email, phone, or token — only role + subject + expiry.
- Farmer-level data is never sold or shared without explicit consent (PDPO 2019).

## 8. Known limitations (and how to lift them)
- **In-memory throttling.** Best-effort across a single instance; move to Redis or Vercel KV-equivalent for multi-region.
- **SQLite on Vercel is ephemeral.** Use a managed Postgres (Neon, Supabase) for persistence at scale; the schema is portable.
- **No 2FA on the agent role yet.** Default password rotation + IP allow-listing are the current mitigations.
- **No dedicated audit log of sign-in attempts.** Application logs capture failures; centralise to a SIEM in production.

## 9. Reporting a vulnerability
Email `okechbrian@gmail.com` with subject `Mavuno security`. Please do not open public GitHub issues for security reports.

## 10. Payment integrity — Mavuno Pay
Mavuno Pay links buyers to farmers with a two-phase state machine (`pending → settled | failed`). The threat model assumes a malicious client and an untrusted network between the PSP and the server.

### 10.1 Server-side amount calculation
The `/payments/initiate` endpoint **never accepts an amount from the client**. It re-derives the amount from the referenced offer:

```
amount_ugx = offer.kg × offer.floor_ugx
```

A tampered client can only change which offer it is paying, not how much it pays for it.

### 10.2 Dedupe
An offer cannot be double-paid. Before inserting a new payment row the server checks for any existing row with `status IN ('pending','settled')` for the same `offer_id` and refuses with `payment_already_in_progress`. This prevents race-condition overpayment and stops one attacker locking up a farmer's offer on behalf of another buyer.

### 10.3 HMAC-signed receipts
Every payment row carries a signature over the canonical payload:

```
payload = "{payment_id}|{offer_id}|{amount}|{status}"
sig     = HMAC-SHA256(HMAC_SECRET, payload)
```

The `/payments/receipt/{id}` endpoint returns the payload and signature alongside the parsed fields. Any holder of the shared operator key (typically the SACCO) can recompute the HMAC offline and confirm that the amount was not altered after settlement — even in an environment without internet or database access.

### 10.4 PSP callback authentication
The mocked PSP posts back to `/payments/confirm` with an `X-Mavuno-Sig` header containing `HMAC-SHA256(HMAC_SECRET, raw_body)`. The server recomputes the signature and uses `hmac.compare_digest` — a constant-time comparison — so an attacker cannot forge a "settled" callback nor learn the signing key through timing. The confirm endpoint is also idempotent: a duplicate callback on an already-settled payment returns `{no_op: true}` without further side-effects.

### 10.5 PSP swap path for production
The mocked PSP lives in a single async function — `app/payments.py::_psp_initiate`. To go live with Flutterwave or MTN MoMo, replace that function body with the provider's HTTP call. Everything else — the DB writes, the ledger events (`PAYMENT_INITIATED`, `PAYMENT_SETTLED`, `OFFER_ACCEPTED`), the HMAC receipt format, the buyer dashboard polling — is unchanged. Key the provider to `PUBLIC_BASE_URL/payments/confirm` and expose `HMAC_SECRET` so the provider's outbound webhook can sign the body the same way the mock does today.

### 10.6 Rate limiting
`/payments/initiate` reuses the per-IP throttle bucket that protects sign-in (`_check_login_throttle` in `app/main.py`). This is an in-memory best-effort limit; move to Redis or an equivalent distributed bucket when scaling past a single instance.
