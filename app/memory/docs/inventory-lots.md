---
title: Inventory Lots
route: /v3/supply/inventory
audience: supply-ops, deal-ops
slug: inventory-lots
surface: admin
---

# Inventory Lots

The Inventory Lots page is the operational heart of the supply→deploy chain. Every hardware unit on the SLYD platform is a **lot** that moves through seven states from **CLAIMED** to **DEPLOYED**, carrying an end-to-end provenance trail. This is where SLYD supply ops verify inbound inventory, grade and price it, list it to the marketplace, reserve it for a buyer, and allocate it to a specific deal before deployment. Open it at **V3 Supply → Inventory Lots** (`/v3/supply/inventory`).

## The seven-state lifecycle — read this first

A lot moves forward through these states in order. You can't skip a step. There is exactly **one reverse transition** in the lifecycle — **Release**, which sends a **RESERVED** lot back to **LISTED** and unwinds the deal it was reserved against (see [Release a reserved lot](#release-a-reserved-lot) below).

1. **CLAIMED** — Broker / inbound inventory enters here. **Unverified.** Not yet ops-confirmed.
2. **SOURCED** — Ops has confirmed exclusive availability. Ops-verified but not yet graded or priced.
3. **GRADED** — Condition grade (A / B / C, or New) confirmed.
4. **LISTED** — Published to the public marketplace and visible to the **[Match Engine](/v3/deal-flow/match-engine)** picker. **This is the only state from which a Propose can create a deal.**
5. **RESERVED** — A buyer has reserved capacity. Ops must now bind it to a specific deal. *Reversible via **Release** → LISTED.*
6. **ALLOCATED** — Bound to a deal in the pipeline.
7. **DEPLOYED** — Live in the buyer's hands; the lot has completed the chain.

The most important boundary on the page is the banner at the top: **"Claimed ≠ matchable."** A CLAIMED lot is a claim, not a confirmed asset — and the same is true for SOURCED and GRADED: until the lot is **LISTED**, it doesn't appear in the **[Match Engine](/v3/deal-flow/match-engine)** picker or on the public marketplace. The banner highlights the most common gate (CLAIMED), but the operative rule for visibility is `state == LISTED`. This prevents matching against unverified, ungraded, or unpriced inventory.

## Page layout

- **Header** — page title and the **+ New Lot** button (top right)
- **State Machine strip** — visual reference of all seven states; the dot lights up for each state that the currently-selected lot has reached
- **Claimed ≠ matchable banner** — yellow warning bar explaining that unverified CLAIMED lots are not yet ops-confirmed. (The full visibility rule is stricter: only `LISTED` lots appear in **[Match Engine](/v3/deal-flow/match-engine)** or on the public marketplace.)
- **Filter bar** — state pills (All + one per state), then category pills (All categories + one per asset category), then a `N LOTS · N UNITS` counter
- **Lot table** (left) — the working list
- **Lot drawer** (right) — detail, pricing controls, subscription terms, provenance trail, and the **advance** button for the selected lot

Clicking a row in the table opens the drawer on the right.

## Create a new lot

Use this when a broker or supplier sends in claimed inventory that doesn't already live in the system.

1. Click **+ New Lot** in the page header.
2. Fill the inline form:
   - **GPU Model** — e.g. `B200`
   - **Quantity** — number of units, must be at least 1
   - **Grade** — pick from the dropdown (`New`, `A`, `B`, `C`)
   - **ISO** — the grid ISO code, e.g. `ERCOT` (optional)
   - **Rate $/GPU·hr** — sale rate (optional; leave blank for RFQ)
   - **Cost basis $/GPU·hr** — what SLYD is paying (optional)
3. Click **Create claimed lot**. The lot is assigned a DisplayId and lands as **CLAIMED**.

A success banner confirms creation. The drawer opens on the new lot so you can review it. **New lots are always CLAIMED — there is no way to create a lot directly into any other state.**

## Advance a lot through the lifecycle

Every lot has one forward action at a time. The button label changes based on the current state.

| Current state | Button label | What it does |
|---|---|---|
| **CLAIMED** | **Confirm & Source →** | Confirms exclusive availability (ops-verified). The lot is not yet visible to Match Engine or the marketplace — that happens at LISTED. |
| **SOURCED** | **Mark Graded →** | Locks in the condition grade |
| **GRADED** | **Publish to Inventory →** | Lists the lot publicly to the marketplace |
| **LISTED** | **Reserve →** | A buyer has reserved capacity |
| **RESERVED** | **Allocate to Deal →** | Binds the lot to a specific deal (requires a deal pick) |
| **ALLOCATED** | **Mark Deployed →** | Marks the lot as live in the buyer's hands |
| **DEPLOYED** | — | Terminal state, no further action |

To advance:

1. Click the lot in the table to open the drawer.
2. At the bottom of the drawer, click the forward button (e.g. **Confirm & Source →**).
3. A success banner confirms the new state and notes that the transition was logged to the provenance trail and the Audit Log.

The Provenance Trail section in the drawer updates immediately, adding a new entry with the timestamp, the advancing admin's name, and the resulting state.

### Special case: RESERVED → ALLOCATED requires a deal

When the lot is in RESERVED, an extra **Allocate to deal** picker appears above the action button. The button is **disabled** until you pick a deal from the dropdown. Each option shows the deal's DisplayId, Region, and dollar value. After binding, the deal's DisplayId appears in the **Bound To** column of the lot table and in the drawer's **Bound To Deal** field.

#### Automatic broker attribution at RESERVED → ALLOCATED

If the lot you're allocating was stamped with a broker (created via Accept on a broker submission — see [Brokers](/v3/platform/brokers)), allocation also triggers automatic commission attribution:

1. The system looks for an open Demand from the same buyer with a matching category + model. If one exists, it attaches to the deal as the demand side. **Oldest matching open Demand wins** when there's more than one candidate.
2. The **same-broker-both-sides** rule is upheld: if the auto-detected Demand's broker is the same as any supply-side broker on this deal, the demand attach is silently skipped. The broker can never be attributed on both sides of one deal — the conflicting demand stays in the pool for a different deal.
3. **One Pipeline LedgerEntry per attributed broker** is created automatically. Zero brokers → no entries; one broker → one entry; two distinct brokers (one per side) → two entries. The new LGE rows appear immediately in the Commission Ledger on [Brokers](/v3/platform/brokers).
4. Each broker's originating submission flips from **CONVERTED → DEAL** on their portal kanban.

You never need to hand-create a ledger entry for a broker-attributed deal — this path handles it. The manual **+ New entry** flow on [Brokers](/v3/platform/brokers) is for SLYD-direct deals or after-the-fact attributions.

## Release a reserved lot

Use this when a deal that reserved a lot fell through, or when ops realises the lot was matched to the wrong demand. **Release** sends a **RESERVED** lot back to **LISTED** and unwinds the deal it was reserved against — in one click.

1. Open the **RESERVED** lot in the drawer.
2. Below the **Allocate to Deal →** action area, click **Release**. The button switches to **Confirm — release lot**.
3. Click **Confirm — release lot** to commit.
4. A success banner reads `<DisplayId> released — back to LISTED. Any bound deal/demand was unwound.`

What Release does, in one atomic step:

- The lot returns to **LISTED** and is unbound from its deal. Provenance gets a new entry (visible in the drawer's Provenance Trail) noting the release.
- Every demand currently **MATCHED** to that deal goes back to **OPEN** and detaches from the deal.
- The deal itself is **deleted** if and only if it has no remaining lots, no remaining demands, no parties, no escrow accounts, no documents, and no deployment. (A deal that's been worked on past **CONFIGURING** stays — only the lot/demand unbind happens. Ops then sees a "deal without a lot" on **[Deal Pipeline](/v3/deal-flow/pipeline)** and decides what to do with it.)

Each step is written to the **[Audit Log](/v3/platform/audit)**: `lot.released`, then per-demand `demand.detached`, then `deal.deleted` if applicable.

### When Release deletes the deal vs not

| Deal looks like… | Result of Release |
|---|---|
| Configuring deal created by **Propose** on **[Match Engine](/v3/deal-flow/match-engine)** (one lot, one demand, no party attribution yet) | Lot → LISTED, demand → OPEN, deal **deleted** |
| Configuring deal created by **Assemble** on **[Matching · 3-sided](/v3/deal-flow/matching)** with a reserved supply lot since attached | Lot → LISTED, that lot's matching demand → OPEN. Deal **stays** because the offtake demand and operator/offtake-buyer party bindings still exist |
| Deal with broker LedgerEntries, escrow, signed documents, or a deployment | Lot → LISTED, matching demand → OPEN. Deal **stays** intact — these signals mean the deal has substance ops should not lose |

If the deal **stays** but its lots all drop, it'll appear on **[Deal Pipeline](/v3/deal-flow/pipeline)** as a lot-less deal — escalate the cleanup decision from there.

## Edit pricing on an existing lot

Manual pricing edits the **record**, not the rulebook — the values you enter here override the engine/intake-set defaults for this specific lot only.

1. Open the lot in the drawer.
2. In the **Pricing** section, edit any of:
   - **Sale rate $/GPU·hr** (or **Sale price $/unit** for non-GPU categories)
   - **New-OEM equivalent $** — what a new comparable would cost
   - **Cost basis $** — internal-only, marked with the **INT** chip
3. The **Save pricing →** button is disabled until at least one field differs from the current value. When dirty, a `was: …` note appears showing the prior values.
4. Click **Save pricing →**. A success banner confirms the change was logged to the Audit Log.

Pricing edits are audited as `lot.price-changed` and the previous values are preserved in the log.

## Set forward-subscription terms

Forward-subscription terms control how a LISTED lot fills up on the marketplace — **the marketplace renders these terms verbatim** (e.g. "closes at 95% or Jul 1"). Set them once the lot is listed and you have a clear capacity target.

1. Open the lot in the drawer.
2. In the **Forward subscription** section, fill any of:
   - **Deposit target $** — total deposit value to consider the lot "full"
   - **Closes at %** — close once subscriptions reach this fraction of target (0–100)
   - **Close date** — close on this calendar date regardless of fill
3. Click **Save terms**. A success banner confirms the marketplace will render the new terms verbatim.

Leave any field blank to clear that close condition.

## Correct the ownership tenure

Ownership tenure describes who owns the asset right now. It is admin-correctable from the drawer.

1. Open the lot in the drawer.
2. In the **Ownership** field (marked **INT**), pick from the dropdown:
   - **OWNED** — the lot is on SLYD's balance sheet (upfront buyout or pay-on-inspect)
   - **CONSIGNED** — SLYD holds and sells for the seller; title passes seller → buyer at resale
   - **BROKERED** — SLYD never holds the asset; matching + clearing fee only
3. The change applies immediately and is logged to the Audit Log.

Use this only to correct a misclassification — changing tenure does not move the asset, it just relabels who owns it.

## Filters and columns

**State filter pills** — `All`, then one pill per state (`Claimed`, `Sourced`, `Graded`, `Listed`, `Reserved`, `Allocated`, `Deployed`). Single-select.

**Category filter pills** — `All categories`, then one pill per asset category (`Gpu`, `Server`, `Cpu`, `Networking`, `Power`, `Cooling`, `Memory`, `Storage`, `Other`). Single-select.

**Counter** — to the right of the filters: `N LOTS · N UNITS`. UNITS is the sum of quantities across the visible lots.

**Table columns** — Lot ID · Category · Hardware · Origin (**INT**) · Grade · Qty · $/GPU·hr · State · Bound To.

- The **Origin** column shows the broker firm tagged with `SRC` for broker-sourced lots, or `direct` if SLYD sourced it directly.
- The **Bound To** column shows the bound deal's DisplayId when the lot is RESERVED / ALLOCATED / DEPLOYED, otherwise `—`.
- The `$/GPU·hr` column shows `RFQ` when no rate is set.

## Lot drawer details

When you click a row, the right drawer shows:

- **Header** — `<GPU Model> × <Quantity>`, the DisplayId, and the current state pill
- **Detail grid** — Category, Ownership (editable), Intake batch (first 8 chars of the batch ID), Origin, Public Tier, Grade, ISO, Cost Basis (**INT**), Rate
- **Spec attributes** — extra attribute key/value pairs if the lot has a SpecJson payload (e.g. `cpuModel`, `gpuCount`, `portCount` — varies by category)
- **Bound To Deal** — only shows when the lot is bound to a deal
- **Provenance Trail** — every state transition with timestamp, actor, and note; remaining unreached states show as `Pending`
- **Pricing** card — sale price, New-OEM equivalent, cost basis (see above)
- **Forward subscription** card — deposit target / close % / close date (see above)
- **Allocate to deal** picker — only shows when state is RESERVED
- **Advance button** — only shows when there's a next state
- **Release** button — only shows when state is RESERVED; two-click confirmation; sends the lot back to LISTED and unwinds the bound deal (see [Release a reserved lot](#release-a-reserved-lot))

## INT chips — what they mean

Fields tagged with a small **INT** chip (Ownership, Origin, Cost Basis, the cost-basis pricing input) are **internal-only**. They are not shown to buyers on the public marketplace. Pricing fields marked **INT-editable** mean that the value is admin-editable but its purpose is internal (cost-basis is for SLYD's margin tracking, not for buyers).

## Things to know

- **Pre-LISTED lots are invisible to matching.** The **[Match Engine](/v3/deal-flow/match-engine)** picker and the public marketplace only show lots in `LISTED` state. CLAIMED, SOURCED, and GRADED lots are all hidden from those surfaces — the lot must be advanced all the way to LISTED before it can be proposed or bought. This is by design: a lot needs to be ops-verified, graded, and published before it's eligible to clear.
- **The lifecycle is forward-only with one exception.** All advances are one-directional except **Release** on a RESERVED lot, which sends it back to LISTED. Earlier states (CLAIMED, SOURCED, GRADED) and later states (ALLOCATED, DEPLOYED) cannot be reversed from the page — if an advance there was made in error, escalate.
- **Every transition is provenance-logged and audited.** Each advance writes a hash-chained Audit Log entry plus a provenance item visible in the drawer. The trail is permanent.
- **Allocate requires a deal.** When advancing from RESERVED, the **Allocate to Deal →** button stays disabled until a deal is picked from the dropdown. Open deals are loaded the moment a RESERVED lot is selected.
- **Subscription terms are rendered verbatim.** The marketplace shows the close condition exactly as you save it — phrase it the way a buyer should read it.
- **Pricing is a record-level override, not a rule change.** Editing pricing here changes only this lot; the Pricing Engine config is unaffected. To change the system-wide default, see [Pricing Engine](/v3/pricing/engine).
- **Broker attribution rides the lot itself, not the Origin column.** Lots created via Accept on a broker submission carry the broker's id directly. When the lot is later allocated to a deal, that broker id is what triggers the automatic Pipeline LedgerEntry (see "Automatic broker attribution" above). The **Origin** column is a separate concept — it shows the supplier firm and is informational only.
- **Same broker can never be on both sides of one deal.** If you're allocating a broker-stamped lot to a deal where a matching open Demand exists from the same buyer AND that demand has the same broker, the demand auto-attach is silently skipped. The lot still allocates and the supply-side broker still earns commission; the conflicting demand stays in the pool.
- **DEPLOYED is terminal.** Once a lot is DEPLOYED, it has no further action button and stays in the trail forever.
