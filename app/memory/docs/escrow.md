---
title: Escrow
route: /v3/settlement/escrow
audience: finance, deal-ops, support
slug: escrow
surface: admin
---

# Escrow

Escrow is the **forward-escrow settlement back office** — the ledger for every deposit a buyer puts down to hold forward capacity, and every payout SLYD owes a seller. Capacity is **held only via deposit**, never via a soft hold. The whole rule of the marketplace is in the subhead: *deposits convert to prepaid usage credit when the operator meets the delivery window, refund in full when the window is missed*.

Open at **V3 Settlement → Escrow** (`/v3/settlement/escrow`).

This is one of the highest-stakes pages on the admin — every action moves real money.

## Page layout

- **Header** — page title + subhead
- **KPI strip** — four cards: Total Held · At-Risk · Converted LTM · Refunded
- **Terms banner** — yellow callout summarising the held → converted / refunded / at-risk rule
- **Filter bar** — state pills + counter on the right
- **Left panel** — escrow accounts table
- **Right panel** — drawer with detail, terms, and the action buttons
- **Seller payouts ledger** — separate table below the split-grid for the seller-money-out side of settlement
- **Banners** at the top — success / error feedback

Clicking a row opens the drawer. Click a seller-payout row to expand its detail inline.

## The six escrow states

The state machine that runs every account:

- **HELD** — deposit is in escrow; capacity is held; window hasn't fired yet (the normal state)
- **AT-RISK** — window is near AND deployment is behind — ops attention required
- **LATE** — window is missed; ops needs to decide
- **PARTIAL** — partial delivery; ops needs to settle
- **CONVERTED** — terminal happy path; deposit released as prepaid usage credit
- **REFUNDED** — terminal; full deposit returned via the deposit's rail

Filter pills appear in that order. Single-select.

## KPI strip

- **Total Held** — sum of all deposits in `HELD · AT-RISK · LATE · PARTIAL` states. Sub-line: *"deposits in HELD · AT-RISK · LATE · PARTIAL."*
- **At-Risk** — count in `AT-RISK`. Sub-line: *"window near + deployment behind — ops attention."*
- **Converted · LTM** — count converted in the last twelve months. Sub-line: *"released as prepaid usage credit."*
- **Refunded** — count of refunds. Sub-line: *"window missed — returned via deposit rail."*

## Filter the list

- **State pills** — `All` + one pill per state with count. Single-select.
- **Counter** on the right: `N ACCOUNTS · $N HELD` for the current filter.

## Table columns (escrow accounts)

- **ID** — escrow DisplayId
- **Depositor** — depositor account name
- **Listing / Deal** — chips: the source listing's DisplayId (accent) + the deal DisplayId (if bound), or `—`
- **Deposit** — dollar amount
- **Fee** — fee included in the escrow
- **Contract** — contract value secured
- **Qty** — quantity in `GPU·hr/mo`
- **Term** — term in months
- **Window** — countdown text (`in N days`, `now`, `N days past`), colour-coded by state
- **Rail** — payment rail pill (the rail the deposit came in on; refunds go back via the same rail)
- **State** — state pill

## Inspect an escrow account

Click any row. The drawer shows:

- **Header** — depositor name + DisplayId · contact name (if set) · state pill
- **Deposit amount** (large) + sub-line `DEPOSIT · $N CONTRACT · $N FEE`
- **Detail grid** — Listing (accent) · Deal · Quantity · Term · Window · Rail · Opened date · Last Action (date + admin who last acted)
- **Terms callout** — *"Prepaid services with refund triggers. Converts to prepaid usage credit if the operator meets the delivery window. Full refund via the `<rail>` rail if the window is missed. Forward rate locked at signing."*
- **Action buttons** (state-dependent — see below)

## Actions — every state change is on the chain

Mutating actions are gated by the current state. The page uses the **two-click confirm** pattern: first click arms the action ("Confirm convert?"), second click commits.

### When state is HELD / AT-RISK / LATE / PARTIAL — the settling states

Primary actions:

- **Convert to Credit** — moves to `CONVERTED`. Deposit is released as prepaid usage credit on the buyer's wallet. Two-click confirm ("Confirm convert?").
- **Execute Refund** — moves to `REFUNDED`. Deposit returns via the rail. Two-click confirm ("Confirm refund?").

If the current state is exactly `HELD`, secondary action buttons appear:

- **Mark At-Risk** — flag for ops attention (the window is near and the deployment is behind)
- **Mark Late** — window missed; not yet converted or refunded
- **Mark Partial** — partial delivery; ops needs to settle

A note below the actions reads: *"State changes write to the Audit Log and settle via the deposit's rail."*

### When state is CONVERTED or REFUNDED — terminal states

Instead of action buttons, a green resolved note:

- For `CONVERTED`: *"Resolved — deposit released as prepaid usage credit."*
- For `REFUNDED`: *"Resolved — deposit returned in full via the `<rail>` rail."*

## Seller payouts ledger (below the split-grid)

The **buyer side** is escrow; the **seller side** is payouts. They live in one Settlement view. Payouts are recorded; the bank executes; the audit chain remembers.

Columns:

- **Payout** — DisplayId (accent)
- **Submission** — originating submission DisplayId (links conceptually to **[Submissions](/v3/intake/submissions)**)
- **Path** — payout path (see below)
- **Scheduled** — scheduled amount
- **Paid** — amount paid to date
- **Status** — payout status pill
- **Wire** — wire reference, or `—`

The page itself does not **create** payouts — that happens in the **[Submissions](/v3/intake/submissions)** drawer when ops records settlement. This ledger is the read.

### The three payout paths (ADR 0007)

The Path column shows which seller payout option was chosen:

- **Pay on inspect (50/50)** — 50% on inspection clear, 50% on delivery
- **Consignment (pay on resale)** — seller is paid only after SLYD resells
- **Buy-out (upfront)** — full payment upfront

These mirror the seller-side options defined on the **GPU Buyback** tab of **[Pricing Engine](/v3/pricing/engine)**.

### Per-payout detail

Clicking a payout row expands an inline detail panel:

- Seller name + email
- Path label
- Scheduled, Paid, Outstanding amounts
- Created timestamp
- Wire reference
- An optional **Note**
- Action buttons:
  - **Open submission queue →** — link back to **[Submissions](/v3/intake/submissions)**
  - **Open in ERP →** — deep-link to the ERP customer-payment record (only renders when `Erp:PayoutUrlTemplate` is configured; otherwise a dim note says ERP link not configured)

## What ops *cannot* do here

- Create an escrow account from scratch (deposits flow in from the marketplace; escrows are written by the deposit-acceptance flow)
- Skip the two-click confirm on Convert / Refund
- Force a state change that the state machine doesn't allow (e.g. Refund → Held)
- Edit the deposit amount, fee, contract, term, or rail after creation
- Edit a payout's scheduled amount or path (those come from the submission record)
- Mark a payout paid from this page — payouts are settled out-of-band by the bank; ops records the wire reference back on **[Submissions](/v3/intake/submissions)**

## Things to know

- **Capacity is held only via deposit.** There is no soft hold anywhere in the system. If a buyer says "I'm interested but not depositing yet," nothing is reserved for them.
- **Two-click confirm on every Convert / Refund.** Same pattern as **[Brokers](/v3/platform/brokers)** commission transitions and **[Deal Pipeline](/v3/deal-flow/pipeline)** stage advances. The first click arms (button text becomes *"Confirm convert?"* or *"Confirm refund?"*); the second commits.
- **Forward rate is locked at signing.** Whatever the published Pricing Engine config said at the moment the buyer escrowed, that's the rate on this escrow forever. Later Pricing Engine changes don't drift live escrows.
- **The rail is the refund channel.** A refund returns via the same payment rail the deposit came in on. The rail isn't editable post-creation.
- **Window is computed live.** The countdown changes colour-coded by state — green when on track, yellow as the window nears, red when past.
- **AT-RISK is a soft state, not a money move.** Marking AT-RISK flags ops attention but doesn't transfer money. The actual money move happens with Convert or Refund.
- **PARTIAL is a settlement preparation state.** Mark Partial when the operator delivered only some of the capacity. The final settle (Convert / Refund / split) still uses the same two action buttons.
- **Buyer side and seller side share this page.** Escrow accounts (buyer money in) at the top; seller payouts (seller money out) below. Same Settlement.
- **Payouts are created elsewhere.** The drawer on **[Submissions](/v3/intake/submissions)** is where ops records a settlement that creates a payout row here.
- **ERP deep-link is config-gated.** The **Open in ERP →** button only renders when `Erp:PayoutUrlTemplate` is configured. If you see *"ERP link not configured"*, that's an environment / config issue, not a per-payout problem.
- **Every state change writes to the Audit Log.** Convert, Refund, Mark At-Risk / Late / Partial all write hash-chained entries to **[Platform Audit](/v3/platform/audit)**.
- **Customer-side experience.** Buyers see their own escrows reflected in **[Deal Room](/deals/{DealId})** → Finance tab → Escrow accounts table (with state, deposit, contract, term, window). Buyers also see escrow on **[Consumer wallet](/consumer/wallet)** when prepaid usage credit is released.
