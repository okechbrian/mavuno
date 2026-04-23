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
