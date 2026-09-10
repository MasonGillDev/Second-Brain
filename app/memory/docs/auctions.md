---
title: Auctions Admin
route: /v3/intake/auctions
audience: deal-ops, supply-ops, partnership-ops
slug: auctions
surface: admin
---

# Auctions Admin

The Auctions Admin console is the ops cockpit for SLYD's sealed-bid first-price auctions (ADR 0008). The big idea: **even ops sees nothing it shouldn't**. Pre-close, the console shows bid **count** only — never amounts, never bidders, and the reserve is sealed from this surface too. That's not a UI choice; it's enforced by the auction service. Post-close, everything opens — including a cryptographic **commit–reveal receipt** that proves nobody (including SLYD, which may bid in its own auctions) altered, inserted, or peeked.

Open at **V3 Intake → Auctions** (`/v3/intake/auctions`).

The customer-facing surfaces are **[Auctions (bidder flow)](/auctions)**, **[Auction room (bidder/seller flow)](/auctions/{AuctionId})**, and **[Put a lot to bid (seller flow)](/auctions/new)** — covered in the user-facing companion doc.

## Page layout

- **Header** — page title + a subhead emphasizing the blind-cockpit principle ("ops sees count only — the reserve is sealed from this console too")
- **Filter bar** — state pills
- **Auctions table** — one row per auction, fully self-contained (no drawer)
- **Inline receipt row** — expands under a row when ops opens the commit–reveal receipt

## The six auction states

The state machine is linear (except for `Cancelled`, which can come from any non-terminal state):

1. **PendingReview** — seller has drafted; ops needs to **Publish** or **Reject**
2. **Open** — bidding is live; bids are sealed
3. **Awarded** — bidding closed, a winner exists, awaiting settlement confirmation
4. **Settled** — terminal happy path; counts toward the seller's auto-publish record
5. **Passed** — terminal; the top bid did not meet the seller's reserve (how close is never disclosed)
6. **Cancelled** — terminal; ops killed it or rejected the draft

Filter pills in the bar (in this order): All · PendingReview · Open · Awarded · Settled · Passed · Cancelled. Single-select.

## Table columns

- **Auction** — DisplayId (accent mono)
- **Lot** — manifest summary (the human-readable lot description the seller typed)
- **Seller** — seller's account DisplayId
- **Hard close** — close timestamp (`MMM dd, HH:mm`)
- **Sealed bids** — bid **count** only (never amounts; that's the cockpit-blindness principle)
- **Reserve** — `sealed` while `Open` or `PendingReview` (even ops can't see it), a dollar amount once the auction has closed, or `—` if the seller set no reserve
- **Winning** — winning price after close, or `—`
- **State** — state pill
- **Actions** — state-aware action buttons (see below)

## Actions by state

Action buttons appear on each row depending on the current state.

### PendingReview

- **Publish →** — moves the auction to `Open`. Bidding goes live; the fee snapshot is locked at the published rate (ADR 0008 — auction fee is snapshotted at publish, not re-pulled at settle). The success banner reads: `<DisplayId> → OPEN — bidding is live; the fee snapshot is <N>%.`
- **Reject** — moves to `Cancelled`. Same as **Kill** below, just earlier in the lifecycle. Success banner: `<DisplayId> → CANCELLED — logged for the record.`

### Open

- **Kill** — moves to `Cancelled`. Use only when something is wrong (compliance flag, fraudulent draft missed at review, etc.). Bids are discarded.

### Awarded

- **Mark settled** — confirms the seller-side settlement happened and moves to `Settled`. Settling counts toward the seller's **auto-publish** record — after 3 settled, dispute-free auctions, future drafts by that seller may auto-publish without ops review. Success banner: `<DisplayId> → SETTLED — counts toward the seller's auto-publish record.`
- **Receipt** — opens the commit–reveal receipt inline (see below)

### Settled / Passed

- **Receipt** — opens the commit–reveal receipt inline

## The commit–reveal receipt

Click **Receipt** on any post-close auction. An inline row expands below the table row showing the cryptographic verification of every bid that was placed.

The receipt header shows the auction's DisplayId and one of:
- **ALL COMMITMENTS VERIFY ✓** (green) — every committed bid hash matches its revealed contents
- **COMMITMENT MISMATCH ✗** (red) — at least one bid's commitment doesn't recompute, which would be a serious integrity flag (investigate immediately)

A subhead explains the contract: *"Every bid version below was committed to the audit chain BEFORE close as SHA-256(auction·bidder·amount·nonce). Recompute any of them — the chain proves nobody (including SLYD, who may bid) altered, inserted, or peeked."*

The receipt table shows every bid placed across the auction's lifetime (including superseded edits):

- **Bidder** — bidder DisplayId
- **Amount** — bid in dollars
- **Placed** — timestamp to the second
- **Commitment** — first 16 chars of the SHA-256 commitment hash
- **Check** — ✓ if the commitment recomputes, ✗ otherwise
- A trailing column flagging the **WINNER** (green pill) or `superseded` (dim) for any bid version that was overwritten before close

If the auction was settled into a payout or a downstream deal, a **Settlement** line at the bottom links to the **[Escrow](/v3/settlement/escrow)** payout DisplayId and the deal's DisplayId.

Clicking **Receipt** again on the same row collapses it.

## Auto-publish — the seller earn-down

Sellers don't get auto-publish by default. The seller's auto-publish record is incremented when ops **Mark settled** a Settled auction without subsequent dispute. After **3 settled, dispute-free auctions**, the seller's next drafts can auto-publish (skipping `PendingReview` entirely and landing as `Open`). Sellers with fewer than 3 still go through ops review every time.

This is the trust-earned promotion described in ADR 0008. Ops doesn't toggle it manually — the count rolls up automatically. To revoke, a Cancellation or dispute resets the run.

## What the cockpit *cannot* see

Pre-close, the auction service does **not** return any of these to the admin page — so the page can't render them no matter what:

- **Bid amounts** — only the count
- **Bidder identities**
- **The reserve** — `sealed` until close, even for ops
- **Any engine valuation** — there is no SLYD valuation surfaced anywhere on the auction system

Post-close, amounts and the reserve become visible; bidder identities are revealed only in the commit–reveal receipt.

This blindness is what lets SLYD bid in its own auctions provably blind. The audit chain proves it.

## What ops *cannot* do here

- Place a bid (admins use a separate account if they want to bid as SLYD)
- See, edit, or override the reserve before close
- Extend the hard close (no extensions — the clock is the close)
- Edit the lot manifest after publish
- Settle an auction the seller hasn't confirmed
- Re-open a `Cancelled` or `Passed` auction (it has to be re-drafted)
- Edit the fee snapshot — it's locked at publish
- Trigger an automatic seller auto-publish (only settlements increment the count)

## Things to know

- **The cockpit is blind too.** This is the most important thing about the page: ops sees count + state + close + winner-after-close. Anything else is sealed. If a seller calls and asks "what's my high bid," ops literally can't tell them — they have to wait for close. That's by design.
- **Reserve is sealed forever pre-close.** Not even ops can see the seller's reserve while the auction is open. Don't promise visibility you can't deliver.
- **Fee is snapshotted at publish.** Auction fee (typically 5%) is locked when ops clicks **Publish**. Later changes to the published Pricing Engine config never drift live auctions. See **[Pricing Engine](/v3/pricing/engine)**.
- **`Mark settled` is what counts toward auto-publish.** A `Settled` row is the trust-earning event. `Passed` doesn't count.
- **Cancellation is for cause only.** Use `Reject` (from PendingReview) or `Kill` (from Open) only when something's actually wrong. Cancelled auctions can't be reopened — the seller has to re-draft.
- **Receipts open inline.** They don't open in a modal or new page. The receipt row expands below the auction row. Click **Receipt** again to collapse.
- **Settlement links live in the receipt.** When an auction settles into a payout or a deal, the receipt shows the **[Escrow](/v3/settlement/escrow)** payout DisplayId and the deal DisplayId — that's the audit trail from auction → cash → record.
- **Commitment mismatch is a serious flag.** A red **COMMITMENT MISMATCH ✗** badge on a receipt means at least one bid's committed hash doesn't recompute. That's tampering or corruption; escalate immediately and don't settle.
- **Customer-side surfaces.** Sellers draft auctions at **[Put a lot to bid](/auctions/new)**, bidders browse at **[Auctions](/auctions)**, and both sides meet in the **[Auction room](/auctions/{AuctionId})**. Customer-side verification (each bidder sees only their own bid; sellers see count + reserve) is mirror-image of what ops sees here.
