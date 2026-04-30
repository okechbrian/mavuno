# Mavuno â€” User Manual

> *Where soil becomes credit.*

This manual covers four audiences:
1. **Farmer** â€” the person dialling `*165*ACP#` on a feature phone, or signed into the farmer dashboard in the browser
2. **Buyer** â€” a pre-verified SACCO / aggregator browsing the marketplace and paying farmers directly
3. **Collection hub operator** â€” the EASP kiosk or co-operative that redeems tokens
4. **Partner** â€” MoSTI / UEDCL / SACCO staff who use the dashboard to audit the system

---

## 1. For the farmer

### 1.1 What Mavuno does for you

Mavuno reads your soil data and decides how much **Yield Priority** you can borrow. Yield Priority is not money — it is a voucher that only runs your collection sequence. If the soil says your crop will grow, Mavuno approves credit. If the soil says the season will fail, Mavuno protects you from taking on debt you can't repay.

### 1.2 Dialling Mavuno

Dial `*165*ACP#` from your registered SIM. The menu appears:

```
Mavuno
Welcome [Name] ([crop])
1. YPS score
2. Trade Priority
3. Balance
4. Market price
5. Sell produce
6. Ask Mavuno
7. Exit
```


Every menu item is one digit + **send**. Menus 1â€“3 are the credit loop. Menus 4â€“6 are the community resource layer: live prices, buyer matching, and an AI agronomist.

### 1.3 Checking your YPS score (menu 1)

Press **1** then **send**. The reply shows:

- Your YPS score (0 to 1000)
- Your tier (full / partial / denied)
- The credit ceiling in Ugandan shillings
- The number of KG you are eligible for

| Tier | YPS range | KG | Credit ceiling |
|---|---|---|---|
| Full | 700 â€“ 1000 | 60 KG | UGX 200,000 |
| Partial | 400 â€“ 699 | 25 KG | UGX 75,000 |
| Denied | below 400 | 0 | â€” |

### 1.4 Requesting a Trade Priority (menu 2)

1. Press **2** â€” *Trade Priority*.
2. Press **1** to confirm.
3. The reply shows your token ID, the KG allocated, your collection hub, and the 72-hour expiry.

**Important:**
- The token is locked to the collection hub within **5 km of your farm**. It will not work at other hubs.
- The token expires after **72 hours**. Use it or lose it.
- The token is **not money**. It cannot be withdrawn or transferred.

### 1.5 Checking your balance (menu 3)

Press **3**. The reply lists your active tokens and remaining KG.

### 1.6 What if I'm denied?

A "denied" result means your recent soil readings suggest the crop will struggle this season. This is not a punishment. Mavuno is protecting you from taking a loan you may not be able to repay. Options:

- Improve soil moisture (mulching, drip irrigation) and re-check in 7 days â€” the score refreshes on a rolling 7-day window.
- Speak to your PDM extension officer.
- Ask the SACCO about a smaller group-liability loan outside Mavuno.

### 1.7 Today's market price (menu 4)

Press **4**. The reply shows, for your crop and region:

- Today's farmgate price per kilogram (UGX/kg)
- The 7-day average with a trend arrow (â†‘ rising Â· â†“ falling Â· = flat)
- The 7-day price range (low â€“ high)

No inputs needed â€” Mavuno picks the crop from your registered profile and the region from your district.

### 1.8 Posting an offer to sell produce (menu 5)

1. Press **5**.
2. Enter the weight in kilograms, then **send**.
3. Enter your floor price in UGX per kilogram, then **send**.
4. Mavuno auto-matches up to three pre-verified buyers and replies with names and their offered prices. If no buyer matches immediately, you'll receive an SMS when one does.

Your offer goes into the shared ledger; you can always ask the SACCO to verify that the buyer you sell to was a Mavuno-matched offer.

### 1.9 Asking Mavuno for advice (menu 6)

1. Press **6**.
2. Type a short question â€” e.g. *"coffee berry borer what do I do"*, *"how much produce intake for maize"*, *"best time to plant beans"* â€” then **send**.
3. Mavuno replies in one or two SMS-length lines, conditioned on your live soil reading.

If the AI service is temporarily unavailable, the reply is tagged *(offline)* and comes from a rule-based fallback â€” you still get an answer, never silence.

### 1.10 Exiting (menu 7)

Press **7**. The reply is *Webale. Grow strong.* and the session ends. No charge is made for ending a call.

### 1.11 Listing produce from the farmer dashboard (browser)

You can also post offers without dialling the USSD code. Sign in at `/` as a farmer and look for the **List Produce for Sale** card:

1. Pick the crop from the dropdown (your registered crop is pre-selected; common alternatives follow).
2. Type the quantity in kilograms (1 â€“ 50 000).
3. Type the floor price in UGX per kilogram (100 â€“ 10 000 000).
4. Press **Post listing**.

A toast confirms the new offer ID (format `OF-XXXXXX`). The **My active listings** table directly below refreshes. Each row shows a status pill:

| Pill | Meaning |
|---|---|
| `open` | No buyer has paid yet â€” still visible to buyers. |
| `pending` | A buyer tapped **Pay UGX â€¦**; the payment is in flight. |
| `settled` | Payment confirmed â€” the offer is closed. |
| `failed` | The PSP rejected the payment; the offer re-opens for other buyers. |

### 1.12 Payments received

The **Payments Received** card shows your last five buyer settlements: amount, method (`mtn` / `airtel` / `mavuno-pay`), a status pill, and a **receipt** link for settled rows. The receipt is a JSON blob signed with HMAC-SHA256; any SACCO holding the shared operator key can recompute the signature and confirm the amount was not tampered with.

---

## 2. For the buyer

### 2.1 Finding produce on the marketplace

Sign in at `/` as a buyer. The marketplace lists **every open offer** from every farmer, not just exact region/crop/price matches. Above the list:

- **Filter chips** â€” `All` Â· `My region` Â· `My crops` Â· `Within budget`. Tap a chip to narrow the view. The chip state is reflected in the URL so you can bookmark or share it.
- **Match badges** on each card â€”
  - `â˜… MATCH` â€” region, crop, and price all line up with your buyer profile.
  - `~ partial` â€” two of the three match.
  - No badge â€” a browse-only card.

Results are smart-sorted: strongest matches first, then newest.

### 2.2 Paying a farmer (Mavuno Pay)

On a match card press **Pay UGX {amount}**. An inline panel asks for:

- **Msisdn** â€” your mobile-money number. Pre-filled from your buyer profile; editable.
- **Method** â€” `mtn` Â· `airtel` Â· `mavuno-pay`.

Press **Send payment**. The dashboard shows a `pending` toast and polls status every 1.5 seconds. Within a few seconds the toast flips to `settled` (or `failed`, in which case the offer reopens). A receipt link appears â€” the same HMAC-signed JSON receipt the farmer sees.

You never enter the amount â€” Mavuno computes it server-side as `kg Ã— floor_ugx`, so a tampered client can't underpay. The same offer cannot be double-paid; if another buyer has a pending or settled payment the server refuses new initiations with `payment_already_in_progress`.

### 2.3 What happens on the farmer's side

As soon as your payment settles:
1. The offer's status flips from `open` â†’ `accepted`.
2. The farmer's **Payments Received** feed shows `+UGX {amount}` with a `settled` pill and a receipt link.
3. The ledger records `PAYMENT_INITIATED` â†’ `PAYMENT_SETTLED` â†’ `OFFER_ACCEPTED` in order.

---

## 3. For the collection hub operator

### 3.1 Redeeming a token

When a farmer arrives with a valid token:

1. Scan or enter the **token ID** (format `Trade Priority-XXXXXXXXXXXX`).
2. The collection hub terminal POSTs to `/priority/redeem` with `{token_id, lat, lng, kg}`.
3. Three checks run automatically:
   - **Signature** â€” HMAC must match the issuer's key
   - **GPS** â€” your collection hub must be within 5 km of the farm's GPS
   - **Expiry** â€” the token must not be more than 72h old
4. If all three pass, the collection hub releases the requested KG and the ledger records the event.

### 3.2 Offline mode

If your kiosk has no internet:
- The token carries its own HMAC signature â€” you can verify it offline using the shared operator key (ask your SACCO for the key).
- Record each redemption locally (CSV or paper).
- Sync to the ledger next time you have connectivity. The Mavuno API accepts backdated redeem events up to 24 hours after the fact.

### 3.3 Common error codes

| Error | Meaning | What to do |
|---|---|---|
| `token_not_found` | ID mismatch or typo | Re-enter the ID |
| `invalid_signature` | Token was tampered with or forged | **Do not redeem.** Flag for review |
| `expired` | Past 72-hour window | Farmer must request a new token |
| `already_redeemed` | KG balance is zero | Farmer must request a new token |
| `out_of_range` | Collection hub is >5 km from farm | Direct farmer to the correct collection hub |
| `insufficient_balance` | Farmer asked for more KG than remains | Reduce request |

---

## 4. For the partner dashboard

### 4.1 Opening the dashboard

Browse to `https://<your-mavuno-url>/`.

You see:
- **Left column** â€” Uganda map with operational-zone markers. Click a marker to jump to that farm.
- **Right column** â€” one card per registered farmer: name, district, crop, YPS, tier, KG allocation, credit ceiling in UGX, collection hub, and current Trade Priority balance.
- **Bottom panel** â€” live audit ledger, refreshing every 2 seconds.

### 4.2 Controls

| Control | What it does |
|---|---|
| **Run full cycle** (left toolbar) | Runs sensor â†’ YPS â†’ Trade Priority issue â†’ partial redeem for all farms in one click â€” useful for demos and regression checks |
| **Refresh** | Re-pulls all farm scores and balances |
| **Verify ledger** | Recomputes the full SHA-256 hash chain and reports any tamper |
| **Run cycle** (per-farm) | Single-farm end-to-end cycle |
| **Issue Trade Priority** (per-farm) | Issue a token without redemption |
| **Theme toggle** (moon icon, top-right) | Switches between light and dark mode; persists |

### 4.3 Understanding the ledger

Every state change in Mavuno writes to an append-only ledger. Each row shows:
- **Timestamp** â€” when the event happened (browser local time)
- **Event type** â€”
  - `ISSUE` â€” a new Trade Priority was issued (green)
  - `REDEEM` â€” a farmer redeemed KG at a collection hub (gold)
  - `REJECT` â€” a redemption was blocked (out of range, bad signature) (red)
  - `EXPIRE` â€” a token passed its 72-hour TTL (grey)
- **Payload** â€” the JSON body of the event
- **Hash** â€” first 10 characters of the SHA-256 hash tying this row to the previous row

A tampered ledger shows up as a red toast when you click **Verify ledger**, naming the first bad line.

### 4.4 USSD Simulator (development only)

Browse to `/phone`. This is a browser-based Nokia-style phone for testing the USSD flow without an Africa's Talking account:
1. Click a farmer SIM on the right.
2. Press **CALL**.
3. Tap menu digits â€” they auto-send after 0.8 seconds, or press `#` to send immediately.
4. Press **END** to hang up.

Every USSD action hits the same state machine as the real AT callback. The dashboard ledger reflects it live.

---

## 5. Keyboard shortcuts

| Location | Keys | Action |
|---|---|---|
| `/phone` | `0`â€“`9` | Tap digit |
| `/phone` | `*` | Clear pending input |
| `/phone` | `#` | Send pending input |
| `/phone` | `Enter` | CALL |
| `/phone` | `Esc` | END |

---

## 6. Security & Terms of Service

### 6.1 Sign-in & sessions
Sign-in is role-based (Farmer, Buyer, Agent). On success the server sets an HMAC-signed, HttpOnly, SameSite=Lax cookie that expires after 24 hours; the cookie is also flagged `Secure` whenever the site is served over HTTPS. The cookie carries no PII â€” only the role, the subject ID, and an expiry â€” so a stolen cookie cannot be replayed beyond its window and the server can re-derive trust on every request without a database lookup.

Failed sign-in attempts are throttled per IP (a small burst, then a short cool-off). The sign-in form does not display default credentials; field placeholders no longer hint at PIN values.

### 6.2 Authorisation model
- **Public:** the landing page, the Terms page, the USSD simulator at `/phone`, and the static market-price feed.
- **Signed-in only:** every dashboard route, sensor telemetry, Trade Priority issue/redeem, ledger views, the buyer marketplace, and the AI agronomist.
- **Owner-scoped:** Farmers can only see their own farm; Buyers only their own marketplace view. Agents see everything.

If a session expires while a dashboard is open, the next API call returns 401 and the page redirects back to sign-in automatically â€” there is no broken state.

### 6.3 Terms and Conditions
All users implicitly accept the **Terms & Conditions** by signing in (the link sits below the sign-in button). The full text lives at `/terms`.

### 6.4 Mobile-friendly dashboards
The Agent, Farmer, and Buyer dashboards collapse into a single-column layout at â‰¤768px with a slide-in nav drawer, a tap-anywhere backdrop, and 44px touch targets. The USSD simulator at `/phone` is feature-phone-sized by default. No horizontal scrolling on any supported viewport.

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

## 7. Mavuno Chat â€” talking to a counterparty before the deal

Chat is offer-aware. Every conversation is pinned to a specific listing so questions like *"is this Robusta?"*, *"50 kg sacks ok?"*, or *"when was it harvested?"* stay with the deal they belong to.

### 7.1 Buyer flow
There are two entry points to the same drawer:

- **From an offer card** â€” every offer in the marketplace shows a `ðŸ’¬ Chat` button next to `Pay UGX â€¦`. Clicking opens (or reopens) a thread tied to that specific offer with that specific farmer.
- **From the topbar** â€” the `ðŸ’¬ Messages` chip at the top right opens an inbox view of every thread you've ever opened, sorted by most-recent message. The red dot on the chip is your unread count; it refreshes every 15 s.

Inside a thread, type and press **Enter** to send (Shift+Enter for a new line). Messages are capped at 500 characters. The composer auto-redacts phone numbers and farm IDs you paste in â€” **don't** paste contact info into chat; use the Mavuno Pay msisdn field on the offer card instead, which moves the contact through a sealed channel.

A small rate limit (1 message every 2 seconds) prevents accidental double-fires from a slow connection. If you hit it you'll see a toast â€” wait a moment and try again.

### 7.2 Farmer flow
Open the farmer dashboard. The topbar gains a `ðŸ’¬ Messages` chip with the same unread badge. Inside, you see a list of every buyer who has reached out, newest message first. Tap a row to open the conversation.

Replies use the same composer. The same 500-character cap and auto-redaction apply on your side.

### 7.3 What the audit log records
Every chat event writes one row to the Mavuno ledger: thread ID, sender role, sender ID, message ID, timestamps. **The body of the message is never written to the ledger.** That means an auditor with the operator key can prove *when and between whom* a conversation happened, without storing the text in a tamper-evident log.

### 7.4 Known limits in this build
- **Cold-start eviction.** Until the Neon/Postgres migration ships, the SQLite database wipes on a Vercel cold start. Threads and messages clear with it. Treat anything older than ~24 hours as gone.
- **Best-effort PII redaction.** The regex catches obvious phone-number patterns but not free-form workarounds ("call me at zero sevenâ€¦"). The product fix is the Mavuno Pay msisdn channel, which is sealed end-to-end.
- **No end-to-end encryption.** Bodies are stored server-side in plaintext after redaction. Fine for a market negotiation; insufficient for medical or legal content.

---

## 8. Mavuno Social â€” public farmer feed

A lightweight reputation surface where farmers post crop updates and buyers browse.

### 8.1 Get there
Every dashboard now has a `ðŸŒ¾ Mavuno Social` link in the topbar. Or visit `/feed-page` directly.

### 8.2 Farmer flow
The composer at the top of the page is visible only to farmers. Type up to 300 characters â€” *"Harvest done, 200 kg Robusta ready for pickup"*, *"Beans graded A; floor price holding at 2 200 UGX/kg"* â€” and click **Post**. The post appears immediately at the top of everyone's feed.

Avoid: contact info (it auto-redacts to `[redacted]` anyway), profanity (the post is rejected with a banned-word error before it lands).

### 8.3 Buyer flow
The feed is reverse-chronological across all farmers. Each post shows the farmer's name, their district, the registered crop, the body, a time-since stamp, and four reaction emojis: ðŸŒ± ðŸ”¥ â¤ï¸ ðŸ‘. Click any emoji to react â€” the count bumps live. Clicking again is a no-op (one reaction per buyer per emoji per post).

### 8.4 Flagging
Every post has a ðŸš© button. Clicking it asks for confirmation, then immediately hides the post from the feed for everyone and writes `POST_FLAGGED` to the ledger. There is **no human moderator** in this build â€” the first flag is the whole defence. A cockpit review queue is in the post-hackathon roadmap.

### 8.5 Known limits
- **Text-only.** The `photo_url` field is reserved in the schema, but Tier 2 ships text-only for the demo window. Image uploads are deferred to the Vercel Blob integration.
- **Same SQLite cold-start caveat as chat.** Posts wipe on cold start until the Postgres migration.

---

## 9. Support

- **Collection hub operator questions** â†’ SACCO operations line
- **Dashboard / API questions** â†’ MoSTI technical liaison
- **Farmer account / SIM registration** â†’ PDM parish officer

