# Mavuno â€” Submission email

This is a mirror of the Gmail draft that will be sent to the Mavuno review committee. The Gmail draft lives in the applicant's Drafts folder; the only edit required before sending is to fill the `TEAM` block with 2â€“5 named members.

---

**To:** `info@sti.go.ug`
**Subject:** `Mavuno` (exact match to the ad)

---

## Email body

Dear Members of the Mavuno Review Committee,

I am writing to submit Mavuno â€” a soil-backed energy-credit system for Ugandan smallholders, delivered over USSD on 2G so that it works on any feature phone â€” to the Mavuno.

Mavuno turns a farm's seven-feature soil reading into a 0â€“1,000 Yield Probability Score, then issues an HMAC-signed, GPS-locked, 72-hour Yield Priority (Trade Priority) that is redeemable only at a specific UEDCL EASP solar pump node â€” with a diversion rate of zero by construction. The same USSD session bundles live market prices, buyer matching, and an AI agronomist (Groq Llama 3.3 with a deterministic rule-based fallback when offline). Every state change is appended to a SHA-256 hash-chained audit ledger that the Ministry, UEDCL, and an underwriting SACCO can each verify in real time.

Mavuno speaks directly to the *"Powering Uganda to a $500B Economy"* challenge because it compounds three unlocks â€” finance access, energy access, and market access â€” onto rails that Uganda already owns: the Parish Development Model (PDM), UEDCL's Electricity Access Scale-up Project (EASP), and mobile money. No new hardware category is required.

```
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LIVE PROTOTYPE
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

   https://mavuno-prototype.vercel.app
   /               Operations dashboard (three seeded farms â€” Mbale, Gulu, Mbarara)
   /phone          Nokia-style USSD simulator, mirrors the Africa's Talking callback
   /demo/cycle     Full sensor â†’ YPS â†’ Trade Priority issue â†’ partial redeem, in one call
   /ledger/verify  Re-hashes the full SHA-256 audit chain

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PUBLIC SOURCE
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

   https://github.com/okechbrian/mavuno

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SUBMISSION REQUIREMENTS â€” ARTEFACT INDEX
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

   1. Prototype or MVP
      Live URL and public repository above.

   2. Short concept note
      https://github.com/okechbrian/mavuno/blob/main/docs/concept-note.md

   3. Demo pitch
      Nine-slide, five-minute script with eight Q&A cards:
      https://github.com/okechbrian/mavuno/blob/main/docs/pitch-deck.md
      The on-stage delivery will take place between 28 April and 3 May 2026.

   4. Written summary
      https://github.com/okechbrian/mavuno/blob/main/docs/written-summary.md

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TEAM  (2â€“5 members, per hackathon rules)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

   >>> [TEAM ROSTER â€” PLEASE FILL BEFORE SENDING] <<<

   1. ______________________ â€” Role â€” email â€” one-line bio
   2. ______________________ â€” Role â€” email â€” one-line bio
   3. ______________________ â€” Role â€” email â€” one-line bio

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
STACK
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

Python 3.12 Â· FastAPI Â· scikit-learn (90.5% test accuracy on a held-out Yield Probability Score set) Â· uvicorn Â· USSD (Africa's Talking compatible) Â· SHA-256 audit ledger Â· static HTML operations dashboard + Nokia-style phone simulator.

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PILOT ASK
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

50 farms Â· 3â€“5 EASP pump nodes Â· 90 days Â· one underwriting SACCO Â· Mbale coffee belt. No new hardware. If the Yield Probability Score predicts yield, the loans repay themselves; if it does not, no cash has ever been lent. Either outcome produces national-scale learning for the Ministry.

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
```

I am available for clarifying questions at `okechbrian@gmail.com`, and am ready for any demo slot between 28 April and 3 May 2026.

Thank you for considering Mavuno.

Yours sincerely,

**Brian Okech**
On behalf of the Mavuno team
`okechbrian@gmail.com`

---

## Send checklist

- [ ] Team roster filled â€” three or more named members, each with role, email, and a one-line bio.
- [ ] Live prototype URL responds (`curl -s https://mavuno-prototype.vercel.app/health` â†’ `{"ok": true}`).
- [ ] Repository is public and all five `docs/` files render anonymously on GitHub.
- [ ] Subject line matches the ad exactly: `Mavuno`.
- [ ] QR-code application form (on the poster) scanned in parallel â€” if the form asks for fields beyond what is in this email, copy-paste from the repo docs.
- [ ] Copy saved to the applicant's *Sent* folder as the definitive submission record.

## Post-send

- Keep the Cloudflare tunnel process alive until the on-stage demo window (28 April â†’ 3 May 2026). If the laptop must sleep before then, promote the quick tunnel to a named Cloudflare Tunnel on a stable subdomain and update this document + the Gmail sent copy with the new URL via a short follow-up reply.

