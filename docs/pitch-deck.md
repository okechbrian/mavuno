# Mavuno — Pitch Deck

> *Where soil becomes credit. And the same phone call becomes a market, an advisor, and a pump.*
>
> 9 slides · 5:00 · target audience: MoSTI, UEDCL, SACCO leadership

Paste each slide's body into Google Slides. The speaker notes are what **you say out loud**.



## Slide 1 — TITLE  [0:00–0:15]

**On screen:**
> **Mavuno**
> *Where soil becomes credit.*
>
> Soilbacked energy credit · AI agronomy · farmer marketplace
> One USSD call. Any feature phone.

**Say:**
"Good [morning]. I'm Brian Okech. Meet Mavuno — Swahili for *harvest*. In five minutes I'll show you how one USSD call turns a coffee farmer's soil data into a working irrigation pump, a live market price, and an AI agronomist — without her ever owning a smartphone."



## Slide 2 — THREE WALLS  [0:15–0:50]

**On screen:**
 **7 in 10** Ugandan smallholders are unbanked — no collateral = no credit
 Only **~19%** of rural Uganda has reliable grid electricity
 Rainfall variability wipes out ~20% of yields year on year — and farmers sell at the wrong price because they don't know today's market

**Say:**
"Four walls, really. No collateral means no credit. No grid means no irrigation. No weather signal means no insurance. And because the nearest marketprice noticeboard is a twelvehour bus away, farmers sell low even when prices are high. Cash loans don't fix any of this — cash gets diverted. We need a different instrument *and* a different information channel."



## Slide 3 — THE CREDIT UNLOCK  [0:50–1:25]

**On screen:**
> **YPS — Yield Probability Score**
> Soil sensors + ML → 0to1000 credit signal
> (not collateral, not credit history)
>
> 7 features · gradientboosted classifier · 90% test accuracy

**Say:**
"Mavuno's first unlock is the Yield Probability Score. Instead of *'do you have land title?'* we ask *'does your soil say you'll grow a crop?'* Seven features, a gradientboosted classifier, 90% accuracy. The farmer becomes her own credit bureau."



## Slide 4 — THE INSTRUMENT  [1:25–2:00]

**On screen:**
> **ECT — Energy Credit Token**
>  HMACsigned by issuer
>  GPSlocked to 5 km around the farm
>  72hour expiry
>  Never cashable — redeemable only at solar pump
>
> Every issue / redeem / reject / expire / offer / match / advise → SHA256 hashchained audit ledger

**Say:**
"A cash loan gets diverted. An Energy Credit Token can't. It's not money — it buys irrigation kilowatthours. Within 5 km, within 72 hours, at one specific pump. Every state change is hashed into an appendonly ledger. MoSTI, UEDCL, and the SACCO audit the same source of truth in real time."



## Slide 5 — WHY MOST AGTECH DIES  [2:00–2:40]

**On screen (two columns):**

> **What the field has tried**
>  *Internet Now!* (Oxfam Novib × ALIN, 2012) — 100 WiFi kiosks across Northern Uganda
>  *Community Knowledge Workers* (Grameen, 2009–2014) — 1,200 agents, 62,000 farmers, $4.7M launch
>
> **What killed them**
>  Kiosks: power cuts · wrong tech (WiFi, PCs) · content stales · no revenue
>  CKWs: agent churn · donor dependency · collapsed to 300 agents by 2014
>  Both: no business model, extensionservices friction

**Say:**
"Uganda has been here before. In 2012 Oxfam Novib and ALIN built a hundred internet kiosks across the north — realtime crop prices, agronomy lessons — and the power went out. In 2009 Grameen trained twelve hundred Community Knowledge Workers, three in every parish, to carry smartphones from house to house. By 2014 the program had collapsed to three hundred. The diagnosis is the same every time: agents quit, kiosks break, donors leave, content stales, and nobody could answer 'who pays for this next month?' If Mavuno doesn't learn from those grave markers, it'll join them."



## Slide 6 — MAVUNOCRP: IMMUNE BY DESIGN  [2:40–3:15]

**On screen (sidebyside):**

> **The old failure** → **The Mavuno answer**
> Kiosk power cuts → **No kiosk.** The farmer's own feature phone.
> WiFi in the bush → **USSD on 2G.** Works where there is no internet.
> Agent churn ($4.7M payroll) → **No agents.** Groqhosted Llama 3.3 answers over USSD.
> Content stales → **Live feeds.** Prices refresh daily; advice is conditioned on live soil data.
> No business model → **kWh fee + SACCO margin + match fee.** Every redemption attributes revenue.
> Groq API down → **Rulebased fallback** returns a safe answer inside 2 s.

**Say:**
"MavunoCRP is the same idea Internet Now had — link farmers to markets, prices, and advice — but built immune to each of those failure modes. The kiosk is replaced by the farmer's own phone. The Community Knowledge Worker is replaced by an AI agronomist that costs cents per query and never quits. The content library is replaced by live feeds. And every interaction carries a fee that attributes revenue to the platform. No kiosk, no agents, no donor treadmill."



## Slide 7 — HOW IT FLOWS  [3:15–3:45]

**On screen:**
```
[Soil sensor] → [YPS model] → [USSD *165*ACP#]
                                    ├─ 1. YPS score
                                    ├─ 2. Energy credit  → [EASP solar pump]
                                    ├─ 3. Balance
                                    ├─ 4. Market price   ─── live regional feed
                                    ├─ 5. Sell produce   ─── automatch 3 buyers
                                    └─ 6. Ask Mavuno     ─── AI agronomist
                                                              ↓
                                              [SHA256 hashchained ledger]
```

**Say:**
"One phone call. Six menu items. Credit, price, marketplace, advisor — all on a Nokia 105, which is what sixty percent of our target farmers actually own. Every state change lands in the same hash chain. Six functions, one ledger, zero smartphones."



## Slide 8 — LIVE WALKTHROUGH  [3:45–4:40]

**On screen:** live dashboard + phone simulator

**Say (while navigating):**
"Three farmers. Akello in Mbale — coffee, strong soil — **YPS 862, full tier, 60 kWh approved**. Okello in Gulu — maize, drought — **YPS 200, denied**. The system refuses to lend into a failing season. Namazzi in Mbarara — beans, middling discipline — **partial, 25 kWh**.
[Click 'Run full cycle'] Three cycles, three ledger entries. [Click 'Verify ledger'] Chain intact.
[Scroll to Market pulse] Today's coffee farmgate in Eastern region — 8,100 shillings. Akello just saw the same number on her phone.
[Scroll to Ask Mavuno; type 'coffee berry borer'] Groqhosted Llama 3.3 answers conditioned on her live soil reading — in 140 characters, USSDsafe.
[Switch to USSD simulator] Akello dials, selects 2 — ECT issued, 72h, pumplocked. Done."



## Slide 9 — THE ASK  [4:40–5:00]

**On screen:**
> **Pilot: 50 farms · Mbale coffee belt · 90 days**
>
> Partners:
>  **MoSTI** — endorsement + PDM data access
>  **UEDCL** — 3–5 EASP pump nodes for pilot
>  **1 SACCO** — underwriting + collections rail
>
> No new hardware. Python, FastAPI, SHA256, USSD on 2G.
> Built on rails that already exist — PDM, EASP, mobile money.

**Say:**
"Give us 50 farms, 3 pumps, 90 days. If YPS predicts yield, the loans repay themselves. If not, no cash was ever lent. Either way, Uganda learns whether soil can be collateral — and whether the farmer's phone can replace the thousandkiosk model that came before. Webale."



# Q&A — 8 cards

### 1. "How do you make money?"
Three lines: (a) transaction fee on every ECT redemption at the pump (2–3%), paid by the SACCO out of its interest spread; (b) success fee on buyermatch completions (~1%); (c) at scale, data licensing — YPS is a droughtrisk signal insurers will pay for. Zero fee to the farmer.

### 2. "What about data privacy? PDPO 2019 compliance?"
Farm data is stored locally and hashes to the ledger — not raw values. Farmer owns the keys. Optin, revocable. Usecase framing is registered against the Personal Data Protection Office model.

### 3. "Apollo Agriculture, Emata, MKOPA already do this."
Apollo lends inputs; Mavuno finances energy. Emata lends cash against cooperatives; Mavuno issues a noncashable instrument. MKOPA is asset finance, not seasonal credit. We complement, not overlap — and we're the only one gated by soil data *and* that bundles the market + advisor in the same USSD call.

### 4. "What if the pump has no internet?"
The ECT is HMACsigned and selfcontained. The pump operator verifies offline with a shared key and a 20line Python script on a Raspberry Pi. Sync to ledger when the connection returns.

### 5. "How do you avoid the CKW churn trap that hit Grameen?"
We don't employ agents. The agronomy advisor is Groqhosted Llama 3.3 over USSD — no payroll, no dropouts, always on. A rulebased fallback answers when the API is down, so the farmer never gets silence. Perquery cost is fractions of a cent.

### 6. "What if Groq is down when you demo?"
The advisor layer has a 2second hard timeout. On miss it returns a deterministic, prewritten answer keyed to the question ('pest', 'water', 'price', crop). The farmer sees *"Mavuno (offline): Check with extension officer."* — still answered, still logged.

### 7. "How does this scale past 50 farms?"
The software is stateless per farm — one Fluid Compute instance handles thousands. The bottleneck is sensor hardware, and PDM extensionservices budget lines already cover basic soil kits.

### 8. "Why not just disburse via mobile money?"
Cash gets diverted. Mavuno's diversion rate is **zero by construction** — an ECT cannot be spent on anything but a pump. Mobile money is a rail; the ECT is what runs on it.



# Speaker checklist

 [ ] Laptop charged; HDMI adapter tested
 [ ] `uvicorn app.main:app port 8000` running before stage
 [ ] `ledger.jsonl` + `tokens.jsonl` deleted for clean start
 [ ] Browser tabs preopened: `/` and `/phone`
 [ ] Seed a "coffee offer" on Akello before stage so Open offers isn't empty
 [ ] `.env` has `GROQ_API_KEY` (otherwise advisor runs offline fallback — still works)
 [ ] Backup video on USB
 [ ] Timer visible — 5:00 hard stop
 [ ] Water nearby
