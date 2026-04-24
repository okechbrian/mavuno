# Mavuno — User Manual

> *Where soil becomes credit.*

This manual covers four audiences:
1. **Farmer** — the person dialling `*165*ACP#` on a feature phone, or signed into the farmer dashboard in the browser
2. **Buyer** — a pre-verified SACCO / aggregator browsing the marketplace and paying farmers directly
3. **Pump operator** — the EASP kiosk or co-operative that redeems tokens
4. **Partner** — MoSTI / UEDCL / SACCO staff who use the dashboard to audit the system

---

## 1. For the farmer

### 1.1 What Mavuno does for you

Mavuno reads your soil data and decides how much **energy credit** you can borrow. Energy credit is not money — it is a voucher that only runs your irrigation pump. If the soil says your crop will grow, Mavuno approves credit. If the soil says the season will fail, Mavuno protects you from taking on debt you can't repay.

### 1.2 Dialling Mavuno

Dial `*165*ACP#` from your registered SIM. The menu appears:

```
Mavuno
Welcome [Name] ([crop])
1. YPS score
2. Energy credit
3. Balance
4. Market price
5. Sell produce
6. Ask Mavuno
7. Exit
```

Every menu item is one digit + **send**. Menus 1–3 are the credit loop. Menus 4–6 are the community resource layer: live prices, buyer matching, and an AI agronomist.

### 1.3 Checking your YPS score (menu 1)

Press **1** then **send**. The reply shows:

- Your YPS score (0 to 1000)
- Your tier (full / partial / denied)
- The credit ceiling in Ugandan shillings
- The number of kWh you are eligible for

| Tier | YPS range | kWh | Credit ceiling |
|---|---|---|---|
| Full | 700 – 1000 | 60 kWh | UGX 200,000 |
| Partial | 400 – 699 | 25 kWh | UGX 75,000 |
| Denied | below 400 | 0 | — |

### 1.4 Requesting an Energy Credit Token (menu 2)

1. Press **2** — *Energy credit*.
2. Press **1** to confirm.
3. The reply shows your token ID, the kWh allocated, your pump, and the 72-hour expiry.

**Important:**
- The token is locked to the pump within **5 km of your farm**. It will not work at other pumps.
- The token expires after **72 hours**. Use it or lose it.
- The token is **not money**. It cannot be withdrawn or transferred.

### 1.5 Checking your balance (menu 3)

Press **3**. The reply lists your active tokens and remaining kWh.

### 1.6 What if I'm denied?

A "denied" result means your recent soil readings suggest the crop will struggle this season. This is not a punishment. Mavuno is protecting you from taking a loan you may not be able to repay. Options:

- Improve soil moisture (mulching, drip irrigation) and re-check in 7 days — the score refreshes on a rolling 7-day window.
- Speak to your PDM extension officer.
- Ask the SACCO about a smaller group-liability loan outside Mavuno.

### 1.7 Today's market price (menu 4)

Press **4**. The reply shows, for your crop and region:

- Today's farmgate price per kilogram (UGX/kg)
- The 7-day average with a trend arrow (↑ rising · ↓ falling · = flat)
- The 7-day price range (low – high)

No inputs needed — Mavuno picks the crop from your registered profile and the region from your district.

### 1.8 Posting an offer to sell produce (menu 5)

1. Press **5**.
2. Enter the weight in kilograms, then **send**.
3. Enter your floor price in UGX per kilogram, then **send**.
4. Mavuno auto-matches up to three pre-verified buyers and replies with names and their offered prices. If no buyer matches immediately, you'll receive an SMS when one does.

Your offer goes into the shared ledger; you can always ask the SACCO to verify that the buyer you sell to was a Mavuno-matched offer.

### 1.9 Asking Mavuno for advice (menu 6)

1. Press **6**.
2. Type a short question — e.g. *"coffee berry borer what do I do"*, *"how much water for maize"*, *"best time to plant beans"* — then **send**.
3. Mavuno replies in one or two SMS-length lines, conditioned on your live soil reading.

If the AI service is temporarily unavailable, the reply is tagged *(offline)* and comes from a rule-based fallback — you still get an answer, never silence.

### 1.10 Exiting (menu 7)

Press **7**. The reply is *Webale. Grow strong.* and the session ends. No charge is made for ending a call.

### 1.11 Listing produce from the farmer dashboard (browser)

You can also post offers without dialling the USSD code. Sign in at `/` as a farmer and look for the **List Produce for Sale** card:

1. Pick the crop from the dropdown (your registered crop is pre-selected; common alternatives follow).
2. Type the quantity in kilograms (1 – 50 000).
3. Type the floor price in UGX per kilogram (100 – 10 000 000).
4. Press **Post listing**.

A toast confirms the new offer ID (format `OF-XXXXXX`). The **My active listings** table directly below refreshes. Each row shows a status pill:

| Pill | Meaning |
|---|---|
| `open` | No buyer has paid yet — still visible to buyers. |
| `pending` | A buyer tapped **Pay UGX …**; the payment is in flight. |
| `settled` | Payment confirmed — the offer is closed. |
| `failed` | The PSP rejected the payment; the offer re-opens for other buyers. |

### 1.12 Payments received

The **Payments Received** card shows your last five buyer settlements: amount, method (`mtn` / `airtel` / `mavuno-pay`), a status pill, and a **receipt** link for settled rows. The receipt is a JSON blob signed with HMAC-SHA256; any SACCO holding the shared operator key can recompute the signature and confirm the amount was not tampered with.

---

## 2. For the buyer

### 2.1 Finding produce on the marketplace

Sign in at `/` as a buyer. The marketplace lists **every open offer** from every farmer, not just exact region/crop/price matches. Above the list:

- **Filter chips** — `All` · `My region` · `My crops` · `Within budget`. Tap a chip to narrow the view. The chip state is reflected in the URL so you can bookmark or share it.
- **Match badges** on each card —
  - `★ MATCH` — region, crop, and price all line up with your buyer profile.
  - `~ partial` — two of the three match.
  - No badge — a browse-only card.

Results are smart-sorted: strongest matches first, then newest.

### 2.2 Paying a farmer (Mavuno Pay)

On a match card press **Pay UGX {amount}**. An inline panel asks for:

- **Msisdn** — your mobile-money number. Pre-filled from your buyer profile; editable.
- **Method** — `mtn` · `airtel` · `mavuno-pay`.

Press **Send payment**. The dashboard shows a `pending` toast and polls status every 1.5 seconds. Within a few seconds the toast flips to `settled` (or `failed`, in which case the offer reopens). A receipt link appears — the same HMAC-signed JSON receipt the farmer sees.

You never enter the amount — Mavuno computes it server-side as `kg × floor_ugx`, so a tampered client can't underpay. The same offer cannot be double-paid; if another buyer has a pending or settled payment the server refuses new initiations with `payment_already_in_progress`.

### 2.3 What happens on the farmer's side

As soon as your payment settles:
1. The offer's status flips from `open` → `accepted`.
2. The farmer's **Payments Received** feed shows `+UGX {amount}` with a `settled` pill and a receipt link.
3. The ledger records `PAYMENT_INITIATED` → `PAYMENT_SETTLED` → `OFFER_ACCEPTED` in order.

---

## 3. For the pump operator

### 3.1 Redeeming a token

When a farmer arrives with a valid token:

1. Scan or enter the **token ID** (format `ECT-XXXXXXXXXXXX`).
2. The pump terminal POSTs to `/ect/redeem` with `{token_id, lat, lng, kwh}`.
3. Three checks run automatically:
   - **Signature** — HMAC must match the issuer's key
   - **GPS** — your pump must be within 5 km of the farm's GPS
   - **Expiry** — the token must not be more than 72h old
4. If all three pass, the pump releases the requested kWh and the ledger records the event.

### 3.2 Offline mode

If your kiosk has no internet:
- The token carries its own HMAC signature — you can verify it offline using the shared operator key (ask your SACCO for the key).
- Record each redemption locally (CSV or paper).
- Sync to the ledger next time you have connectivity. The Mavuno API accepts backdated redeem events up to 24 hours after the fact.

### 3.3 Common error codes

| Error | Meaning | What to do |
|---|---|---|
| `token_not_found` | ID mismatch or typo | Re-enter the ID |
| `invalid_signature` | Token was tampered with or forged | **Do not redeem.** Flag for review |
| `expired` | Past 72-hour window | Farmer must request a new token |
| `already_redeemed` | kWh balance is zero | Farmer must request a new token |
| `out_of_range` | Pump is >5 km from farm | Direct farmer to the correct pump |
| `insufficient_balance` | Farmer asked for more kWh than remains | Reduce request |

---

## 4. For the partner dashboard

### 4.1 Opening the dashboard

Browse to `https://<your-mavuno-url>/`.

You see:
- **Left column** — Uganda map with operational-zone markers. Click a marker to jump to that farm.
- **Right column** — one card per registered farmer: name, district, crop, YPS, tier, kWh allocation, credit ceiling in UGX, pump, and current ECT balance.
- **Bottom panel** — live audit ledger, refreshing every 2 seconds.

### 4.2 Controls

| Control | What it does |
|---|---|
| **Run full cycle** (left toolbar) | Runs sensor → YPS → ECT issue → partial redeem for all farms in one click — useful for demos and regression checks |
| **Refresh** | Re-pulls all farm scores and balances |
| **Verify ledger** | Recomputes the full SHA-256 hash chain and reports any tamper |
| **Run cycle** (per-farm) | Single-farm end-to-end cycle |
| **Issue ECT** (per-farm) | Issue a token without redemption |
| **Theme toggle** (moon icon, top-right) | Switches between light and dark mode; persists |

### 4.3 Understanding the ledger

Every state change in Mavuno writes to an append-only ledger. Each row shows:
- **Timestamp** — when the event happened (browser local time)
- **Event type** —
  - `ISSUE` — a new ECT was issued (green)
  - `REDEEM` — a farmer redeemed kWh at a pump (gold)
  - `REJECT` — a redemption was blocked (out of range, bad signature) (red)
  - `EXPIRE` — a token passed its 72-hour TTL (grey)
- **Payload** — the JSON body of the event
- **Hash** — first 10 characters of the SHA-256 hash tying this row to the previous row

A tampered ledger shows up as a red toast when you click **Verify ledger**, naming the first bad line.

### 4.4 USSD Simulator (development only)

Browse to `/phone`. This is a browser-based Nokia-style phone for testing the USSD flow without an Africa's Talking account:
1. Click a farmer SIM on the right.
2. Press **CALL**.
3. Tap menu digits — they auto-send after 0.8 seconds, or press `#` to send immediately.
4. Press **END** to hang up.

Every USSD action hits the same state machine as the real AT callback. The dashboard ledger reflects it live.

---

## 5. Keyboard shortcuts

| Location | Keys | Action |
|---|---|---|
| `/phone` | `0`–`9` | Tap digit |
| `/phone` | `*` | Clear pending input |
| `/phone` | `#` | Send pending input |
| `/phone` | `Enter` | CALL |
| `/phone` | `Esc` | END |

---

## 6. Security & Terms of Service

### 6.1 Sign-in & sessions
Sign-in is role-based (Farmer, Buyer, Agent). On success the server sets an HMAC-signed, HttpOnly, SameSite=Lax cookie that expires after 24 hours; the cookie is also flagged `Secure` whenever the site is served over HTTPS. The cookie carries no PII — only the role, the subject ID, and an expiry — so a stolen cookie cannot be replayed beyond its window and the server can re-derive trust on every request without a database lookup.

Failed sign-in attempts are throttled per IP (a small burst, then a short cool-off). The sign-in form does not display default credentials; field placeholders no longer hint at PIN values.

### 6.2 Authorisation model
- **Public:** the landing page, the Terms page, the USSD simulator at `/phone`, and the static market-price feed.
- **Signed-in only:** every dashboard route, sensor telemetry, ECT issue/redeem, ledger views, the buyer marketplace, and the AI agronomist.
- **Owner-scoped:** Farmers can only see their own farm; Buyers only their own marketplace view. Agents see everything.

If a session expires while a dashboard is open, the next API call returns 401 and the page redirects back to sign-in automatically — there is no broken state.

### 6.3 Terms and Conditions
All users implicitly accept the **Terms & Conditions** by signing in (the link sits below the sign-in button). The full text lives at `/terms`.

### 6.4 Mobile-friendly dashboards
The Agent, Farmer, and Buyer dashboards collapse into a single-column layout at ≤768px with a slide-in nav drawer, a tap-anywhere backdrop, and 44px touch targets. The USSD simulator at `/phone` is feature-phone-sized by default. No horizontal scrolling on any supported viewport.

### 6.5 AI agronomist privacy
"Ask Mavuno" is powered by an LLM when `GROQ_API_KEY` is configured server-side. The key is never sent to the browser. Before each question leaves the server, phone numbers, farm IDs, and other long numeric IDs are stripped from the question; the prompt is also length-capped. If the LLM is unreachable or no key is set, a deterministic rule bank answers from the same `(crop, district, YPS, health)` context.

### 6.6 Data privacy
Mavuno complies with Uganda's Personal Data Protection Act 2019:
- Farmer soil readings and GPS are stored as hashed entries in the audit ledger, not raw values
- Each farmer opts in and can revoke consent at any time
- The HMAC signing key lives in environment variables, never in source code
- No farmer-level data is sold or shared with third parties without explicit consent

Questions: write to the Mavuno operations team via your SACCO contact.

---

## 7. Support

- **Pump operator questions** → SACCO operations line
- **Dashboard / API questions** → MoSTI technical liaison
- **Farmer account / SIM registration** → PDM parish officer
