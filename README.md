# Mavuno

> *Where soil becomes credit.*

Soilbacked energy credit for smallholder farms a prototype showing how soilsensor data can replace collateral as the signal that underwrites irrigation financing.



 **Live prototype:** https://loopinstructionaldirectiveclocks.trycloudflare.com 
 **Public source:** https://github.com/okechbrian/mavuno
 **Short concept note →** [`docs/conceptnote.md`](docs/conceptnote.md)
 **Written summary →** [`docs/writtensummary.md`](docs/writtensummary.md)
 **User manual (farmer / pump operator / partner) →** [`docs/usermanual.md`](docs/usermanual.md)

## What's inside

 **YPS (Yield Probability Score)** — a gradientboosted classifier turns 7 soil features into a 0–1000 credit signal
 **ECT (Energy Credit Token)** — HMACsigned, GPSlocked, 72hour, noncashable kWh voucher redeemable at one specific solar pump
 **USSD** — menudriven interface matching Africa's Talking callback shape; runs on any feature phone
 **Ledger** — appendonly SHA256 hash chain; every issue / redeem / reject / expire is auditable
 **Dashboard** — live operations view with Uganda map + perfarm cards + streaming ledger + dark mode
 **Phone simulator** — Nokiastyle browser phone that mirrors the USSD state machine


## Documentation

 [`docs/conceptnote.md`](docs/conceptnote.md) — 1page concept note (Future Makers 2026 submission)
 [`docs/writtensummary.md`](docs/writtensummary.md) — longform written summary (Future Makers 2026 submission)
 [`docs/pitchdeck.md`](docs/pitchdeck.md) — 9slide, 5minute pitch script with speaker notes and 8 Q&A cards
 [`docs/usermanual.md`](docs/usermanual.md) — farmer, pump operator, and partner guides
 [`docs/submissionemail.md`](docs/submissionemail.md) — committeefacing email draft

## Stack

Python 3.12 · FastAPI · scikitlearn · pandas · pydantic · joblib · uvicorn[standard]
