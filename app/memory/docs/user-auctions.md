---
title: Auctions (customer flow)
route: /auctions
audience: support, deal-ops, partnership-ops
slug: user-auctions
surface: user
---

# Auctions — customer flow

End-to-end walkthrough of what a signed-in customer sees on the SLYD auction surfaces. Three pages:

- **`/auctions`** — the auction list, filtered to the auctions this account can bid on
- **`/auctions/{AuctionId}`** — the **Auction room**, which renders one of two views (bidder or seller) depending on whether the signed-in account owns the auction
- **`/auctions/new`** — **Put a lot to bid**, the self-serve drafting form

The admin counterpart is **[Auctions Admin](/v3/intake/auctions)**, which owns the canonical state-machine definitions (PendingReview → Open → Awarded → Settled / Passed / Cancelled), the fee snapshot, auto-publish, and the commit–reveal receipt as ops sees it.

The big idea is the same on both sides: **sealed-bid first-price**. *"No bids are displayed — to anyone. The market prices the lot; the audit chain proves it was fair."*

## Sign-in and verification — the KYC gate

Every auction page is sign-in-gated. Beyond that, **bidding and selling require a verified account** — the KYC step lives in **[Settings](/settings)**.

If the customer isn't verified, they see a yellow banner at the top of the `/auctions` page (and on the bid panel inside the room):

- If their docs are still in review: *"Your verification documents are in review — bidding unlocks once ops approves."*
- Otherwise: *"Bidding and selling require a verified account."*

Both versions include a **Complete verification →** button linking to `/settings`. Until they're verified, the bid panel won't accept bids and they cannot draft a new auction.

If they sign in but have no account binding at all (no SLYD account linked to their Auth0 sub), the page shows: *"No account is linked to this login yet."* This is the same not-bound state surfaced on **[Broker portal](/broker)** and **[Deal Room](/deals/{DealId})** — the fix is admin-side on **[CRM Accounts](/v3/crm/accounts)** → **Link customer user**.

## `/auctions` — the list page

What the bidder sees:

- **Page header** — *Auctions · "Sealed-bid component lots. No bids are displayed — to anyone. The market prices the lot; the audit chain proves it was fair."*
- A **Put a lot to bid** button (gavel icon) at the top right linking to `/auctions/new`
- A verification banner if not verified
- A grid of **auction cards**

Each card shows:

- DisplayId chip
- State pill — `BIDDING OPEN`, `YOU WON`, `CONCLUDED`, or the raw state (`PENDING REVIEW`, `PASSED`, `CANCELLED`, etc.)
- The manifest summary (the seller's lot title)
- `N line(s) · N units` — how many manifest lines, total units across them
- Close timing — `Closes in 47m` / `Closes in 6h 12m` / `Closes Jun 30, 17:00 UTC` (live updates with the clock; says `Closing…` once past the moment)
- If this bidder has placed a bid: a **Your bid · $N** chip in the footer

Cards link to `/auctions/{AuctionId}` (the Auction room).

Empty state: *"No open auctions right now."*

## `/auctions/{AuctionId}` — the Auction room (bidder view)

When a bidder opens an auction they don't own, they see:

### Header

- Manifest summary + the line: *"<DisplayId> · sealed first-price · edit your bid until the hard close. No valuations shown — the market prices this lot."*
- State pill on the right

### Lines table

The manifest itself — every line the seller listed:

- **#** — line number
- **Category** (· Subcategory)
- **Model**
- **Qty**
- **Grade** (with **age** in months if set, e.g. `A · 12mo`)
- **Spec** — raw spec JSON if the seller attached any

### Bid panel (right side)

State-dependent:

**When `Open` and the bidder is verified:**
- **Hard close · <date> UTC — no extensions** banner
- **Your sealed bid** — current bid amount, or *"none yet"*; if placed, shows the commit timestamp
- A number input labelled **Place your bid $** (first bid) or **Raise / change to $** (subsequent edit)
- A **Seal my bid →** / **Update sealed bid →** button
- A note: *"Whole dollars. Your bid is sealed — nobody (including SLYD ops) sees it before close; only a hash commitment goes on the audit chain. SLYD may bid in this auction under the same blindness — verifiable after close."*

**When `Open` but unverified:**
- The verify banner replaces the bid form

**After close — bidder won:**
- A green **YOU WON THIS LOT** card showing the winning price
- Body text: *"SLYD ops will confirm wire instructions against your deal record — payment is by bank wire (recorded on the platform, executed by your bank). Goods ship seller → you on settlement."*
- A **See your deal →** link to `/deals`

**After close — bidder lost or auction passed:**
- A neutral **AUCTION CONCLUDED** card
- Body: *"This lot was passed (reserve not met)"* or *"awarded to another bidder. The clearing price is not disclosed."*

### Sealed-bid receipt (bidder side)

If the bidder has placed any bid version, a **Your sealed-bid receipt** card appears with a **Verify my bid →** button. Clicking it loads the bidder-side verification — every bid version this bidder placed, with a check whether each commitment recomputes.

The full **commit–reveal receipt** with bidder identities is only ever shown post-close to the **seller** and to **ops** (on the **[Auctions Admin](/v3/intake/auctions)** page).

## `/auctions/{AuctionId}` — the Auction room (seller view)

When the signed-in account **owns** the auction, the same URL renders the seller's view instead:

### Header

- Manifest summary + the line: *"<DisplayId> · your auction · sealed bids — you see the count, never the amounts, until close."*
- State pill

### Seller stat grid

- **Sealed bids** — the bid count (no amounts)
- **Hard close** — close timestamp
- **Your reserve** — the seller's own reserve, or `none` if they didn't set one (this is the **only** place the reserve is ever visible pre-close, and only to the seller)
- After close: **Winning price**, **Winner** (name), and **Net to you (after `5%` fee)** — the seller's net payout

If the auction `Passed`:
- A terminal note: *"Passed at close — the top bid did not meet your reserve (how close is never disclosed). You can relist any time."*

### Integrity receipt (seller side)

Post-close (Awarded / Settled / Passed), the seller can click **Verify this auction →** to load the seller-side receipt:

- A **ALL COMMITMENTS VERIFY ✓** or **COMMITMENT MISMATCH ✗** pill
- A subhead: *"Every bid was committed to the audit chain as a SHA-256 hash BEFORE close. All N sealed bid(s) recompute correctly — nobody altered, inserted, or peeked. Losing bids stay sealed; you only ever see the winning one."*
- The winning bid line: *"Winning bid `$N` by `<Winner>` · commitment `<hash prefix>` ✓"*

Losing bid amounts are **never disclosed to the seller** — only the winner. This is the seller-side mirror of the cockpit blindness on **[Auctions Admin](/v3/intake/auctions)**.

## `/auctions/new` — Put a lot to bid

The self-serve seller drafting form.

### Verify-gated

If the seller isn't verified, the form is replaced by a verify banner with a **Complete verification →** link to `/settings`.

### The form

Three blocks:

**1 · The lot**
- **Title** — free text, placeholder *"Q2 datacenter decommission — CPU/RAM/NVMe"*

**2 · Lines** — repeating manifest block
- **Category** dropdown (every asset category)
- **Subtype** dropdown — populated from the chosen category (or *"Any subtype"*)
- **Model** input — placeholder *"Model · e.g. EPYC 9654"*
- **Quantity** input
- **Grade** — `New` / `A` / `B` / `C`
- **Age (months)** input
- **+ Add line** button
- Lines appear in a table below with a **✕** button to remove

**3 · Terms**
- **Hard close (UTC)** — datetime input. Note below it: *"No extensions — bidding ends at this exact moment. Bidders may edit their sealed bid until then."*
- **Reserve $** (optional, confidential) — number input. Note: *"Sealed like the bids — even SLYD ops can't see it until close. If the top bid misses it, the auction passes; nobody learns how close."*
- **Fee note** — *"SLYD's fee: 5% of the winning price, deducted from your payout. You'll see the bid count while bidding runs — never amounts or bidders — and the winning price + winner only at close."*

### Submit

A **Submit for review → (N line(s))** button. Disabled until at least one line is on the manifest.

After submit, the form is replaced by a big success banner: *"<DisplayId> submitted for review. You'll see it on your auctions list; bidding opens on approval."* and a **Done →** button back to `/auctions`.

The auction lands as `PendingReview` on the admin **[Auctions Admin](/v3/intake/auctions)** page. After the seller has 3 settled, dispute-free auctions, future drafts may auto-publish without review (see **[Auctions Admin](/v3/intake/auctions)** for the auto-publish detail).

## Things to know

- **Sealed first-price, no extensions, no soft close.** The clock is the close. Bidders can edit their sealed bid as many times as they want, but at the hard close, whichever bid each bidder last committed is the bid that counts.
- **Bidder sees only their own bid.** Pre-close: the bidder's own bid amount + commit timestamp, never anyone else's. Post-close: their own bid + the winning price *only if they won*; losers see *"awarded to another bidder. The clearing price is not disclosed."*
- **Seller sees count + reserve.** Pre-close: bid count + their own reserve, never amounts or bidder identities. Post-close: winning price, winner name, and the integrity receipt (which still hides losing bid amounts).
- **Cockpit on the admin side is blind too.** Ops sees no more than the seller does pre-close. See **[Auctions Admin](/v3/intake/auctions)**.
- **No engine valuation, anywhere.** SLYD never publishes a price estimate for an auction lot — to bidders, sellers, or ops. The market prices the lot.
- **Verification is the bidding gate.** Customers who can't bid almost always have the wrong account compliance status. Send them to `/settings`. If their status is `DocsSubmitted`, they're in review — wait for ops to approve.
- **Reserve is forever sealed pre-close — including from the seller's own ops contact.** When a seller calls and says "I told ops my reserve, why can't they see it," that's the answer: the system genuinely doesn't surface it to ops until close.
- **Auto-publish is earned.** After 3 settled, dispute-free auctions the seller's next drafts may bypass `PendingReview` (see **[Auctions Admin](/v3/intake/auctions)** for the auto-publish counter). For sellers below 3, every draft needs ops review.
- **Fee is snapshotted at publish.** 5% (or whatever the published rate is) is locked when ops publishes the auction. Later Pricing Engine changes don't drift live auctions.
- **Wire instructions follow the deal record.** Winners pay by bank wire — *"recorded on the platform, executed by your bank."* The deal record on **[Deal Room](/deals/{DealId})** is the source of truth for instructions and confirmation.
- **Goods ship seller → buyer on settlement.** Not before. The auction itself doesn't move stock; the post-settle deal does.
