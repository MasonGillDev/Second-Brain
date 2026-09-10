---
title: Troubleshoot — seller's hardware submission seems stuck
audience: support, supply-ops
slug: troubleshoot-sell-submission-stuck
surface: troubleshooting
---

# Troubleshoot — seller's hardware submission seems stuck

## Symptom

A seller says: *"I posted on /hardware-sales but haven't heard anything"* or *"My submission isn't moving."*

## Common causes

1. **Submission lands as `NEW` and is waiting for ops** — by design. Ops needs to open it and click **Begin Review →** on **[Submissions](/v3/intake/submissions)** to start the flow. If nobody on ops has touched the queue, it stays `NEW`.
2. **The 24–48 hour initial-valuation SLA has been missed** — the **[Hardware buyback (customer flow)](/hardware-buyback)** marketing page commits to *"initial valuations within 24-48 hours of receiving your equipment list."* If a queue is overloaded, the seller is right to chase.
3. **Seller never signed in / claimed** — same pattern as the need flow. They submitted anonymously, got bounced to sign-in, but didn't complete it. The submission is on file but unbound.
4. **Submission is in a later state and the seller doesn't realise** — `REVIEW` / `OFFER_OUT` / `OFFER_ACCEPTED` are all valid mid-flow states; the seller may be waiting on something *they* need to do (accept the offer, ship the gear).
5. **Auction path confusion** — the seller picked **Put a lot to bid** on **[Auctions (customer flow)](/auctions/new)** instead of the buyback intake; auctions have a different timeline.

## Where to verify (admin side)

- **Open [Submissions](/v3/intake/submissions)** and search for the seller's manifest. Confirm the state and the **Last Action** date.
- **Check `NEW` filter** — if the submission is in `NEW`, nobody has begun review. Click **Begin Review →** to move it forward.
- **Check the seller's binding** — open the row. If the submitter's account is `—` (unbound), they never completed the claim flow. See **[Sell hardware (customer flow)](/hardware-sales)** for the claim-link failure modes.
- **Cross-reference with [Auctions Admin](/v3/intake/auctions)** — if the seller's name appears there instead, they took the auction path, not buyback.
- **Compare against the 24-48 hour SLA** — the submission's **Captured** timestamp on the drawer vs current time. If it's past the SLA, prioritize it.

## Resolution steps

- **If `NEW` and stale:** click **Begin Review →** to bring it into ops's active queue. State moves to `REVIEW`.
- **If unbound:** ask the seller to sign in and revisit the claim link. If the link expired (30 days), ops manually binds via **[CRM Accounts](/v3/crm/accounts)** → **Link customer user**.
- **If mid-flow but the seller is waiting:** look at the current state on **[Submissions](/v3/intake/submissions)** and tell the seller what's expected of them next:
  - `OFFER_OUT` — they need to accept the offer in their portal
  - `OFFER_ACCEPTED` — they need to ship the hardware to SLYD
  - `RECEIVED` — SLYD has it; inspection is next
  - `INSPECTED` — terminal; payout follows per the chosen path on **[Escrow](/v3/settlement/escrow)** Seller Payouts ledger
- **If they took the auction path by mistake:** ops can `Reject` the draft on **[Auctions Admin](/v3/intake/auctions)** and route them to **[Sell hardware](/hardware-sales)** instead. The seller needs to re-submit through the buyback intake.
- **If a payout is owed but they haven't received it:** check the **Seller payouts ledger** on **[Escrow](/v3/settlement/escrow)** — is the row there? What's the status? Is the wire reference set? The bank executes; the ledger records.

## Related docs

- **[Submissions](/v3/intake/submissions)** — the admin queue for the sell intake
- **[Sell hardware (customer flow)](/hardware-sales)** — the seller-side walkthrough including claim-link failure modes
- **[Escrow](/v3/settlement/escrow)** — Seller Payouts ledger for the payout side
- **[Hardware buyback (customer flow)](/hardware-buyback)** — the marketing page with the 24-48 hour SLA
- **[Auctions Admin](/v3/intake/auctions)** — the auction path (alternative to buyback)
