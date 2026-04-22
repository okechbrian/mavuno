# Future Makers Hackathon 2026 — Submission email draft

> Copy the block below into Gmail (or your mail client) and send.
> All four ad-required artefacts are either attached or linked.
> Attachments are markdown — they render correctly in any browser and on GitHub. If the committee requests PDF, open each link, Ctrl-P → "Save as PDF" (1 min manual step).

---

**To:** `info@sti.go.ug`
**Cc:** *(your team lead if applicable; leave blank otherwise)*
**Subject:** `FUTURE MAKERS HACKATHON 2026`
**Attach before sending:**

- `docs/concept-note.md` — short concept note (requirement #2)
- `docs/written-summary.md` — written summary (requirement #4)
- `docs/pitch-deck.md` — speaking script for the on-stage pitch (requirement #3, for reviewer reference ahead of the 28 Apr demo slot)

---

## Email body

Dear Future Makers Hackathon 2026 review committee,

We are submitting **Mavuno** — *"Where soil becomes credit"* — a soil-backed energy-credit system for Ugandan smallholders, delivered over USSD on 2G so it works on any feature phone.

Mavuno turns a farm's 7-feature soil reading into a 0–1000 Yield Probability Score, then issues an HMAC-signed, GPS-locked, 72-hour **Energy Credit Token** that is redeemable only at a specific UEDCL EASP solar pump — diversion rate zero by construction. The same USSD session bundles live market prices, buyer matching, and an AI agronomist (Groq Llama 3.3 with a deterministic rule-based fallback). Every state change is appended to a SHA-256 hash-chained audit ledger that MoSTI, UEDCL, and the underwriting SACCO can verify in real time.

We believe this directly addresses the *"Powering Uganda to a $500B Economy"* challenge because it compounds three unlocks — finance access, energy access, and market access — onto rails Uganda already owns (PDM, UEDCL EASP, mobile money), without requiring a smartphone, internet at the farm, or any new hardware category.

**Live prototype (running now):**
https://loop-instructional-directive-clocks.trycloudflare.com

- `/` → operations dashboard with three seeded farms (Akello / Mbale / coffee, Okello / Gulu / maize, Namazzi / Mbarara / beans).
- `/phone` → Nokia-style USSD simulator mirroring the real Africa's Talking callback shape.
- `/demo/cycle` → one-call sensor → YPS → ECT issue → partial redeem, useful for a ~30-second smoke test.
- `/ledger/verify` → re-hashes the full audit chain.

**Public source:** https://github.com/okechbrian/mavuno

**Submission requirements checklist:**

| Requirement | Where to find it |
|---|---|
| Prototype or MVP | Live URL above · repo above |
| Short concept note | `docs/concept-note.md` (attached; also in repo) |
| Demo pitch | `docs/pitch-deck.md` — 9-slide, 5:00 spoken script + 8 Q&A cards for the on-stage pitch 28 Apr – 3 May (attached for review; live pitch on the day) |
| Written summary | `docs/written-summary.md` (attached; also in repo) |

**Team (2–5 members as required):**

{{TEAM_ROSTER}}

**Stack:** Python 3.12 · FastAPI · scikit-learn (90.5% test accuracy on a held-out YPS set) · uvicorn · USSD (Africa's Talking compatible) · SHA-256 audit ledger · static HTML dashboard.

**Our ask for the pilot:** 50 farms, 3–5 EASP pump nodes, 90 days, one SACCO partner. No new hardware. If YPS predicts yield, the loans repay themselves. If not, no cash was ever lent. Either way, Uganda learns whether soil can be collateral.

We are available for clarifying questions at `okechbrian@gmail.com` and are ready for the demo slot between 28 April and 3 May 2026.

Thank you for considering Mavuno.

Webale nnyo.

— The Mavuno team
{{TEAM_ROSTER}}
