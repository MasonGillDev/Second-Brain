---
title: Brokers
route: /v3/platform/brokers
audience: partnership-ops, finance, deal-ops
slug: brokers
surface: admin
---

# Brokers

The Brokers page is where ops manages the broker roster (onboard, approve, pause, suspend, terminate), triages broker-submitted deals through the conversion pipeline, and runs the commission ledger from accrual through payout. Open it at **V3 Platform → Brokers** (`/v3/platform/brokers`).

## Page layout

- **KPI strip** — Active Brokers, Accrued Commission (pending payout), Paid LTM Commission, Open Submissions
- **Broker Roster** — full broker list with per-row status action buttons (Approve / Pause / Suspend / Reinstate / Terminate)
- **Broker Submissions** — incoming submissions filterable by state, with per-row Screen / Accept / Decline actions
- **Commission Ledger** — every commission entry across Pipeline / Earned / Paid / Reversed

Clicking a roster row does not open a drawer — every action is inline.

## Create a broker

1. In the **Broker Roster** panel header, click **+ Add broker**.
2. Fill the inline form:
   - **Link to Account** — dropdown of V3 Accounts typed as Broker that aren't already linked to a non-terminated roster row. Select one to bind this broker to a real platform login. Leaving it as **— unlinked (firm-name fallback) —** keeps the legacy firm-name string match path.
   - **Contact name** — e.g. "Jane Operator".
   - **Firm** — auto-fills from the selected Account. If left unlinked, **Firm must match the V3 Account name exactly** so the broker portal can bind the login through the firm-name fallback.
   - **Tier** — pick from the tier dropdown.
3. Click **Add broker**.

The success banner reads `"Broker BKR-… added in PENDINGREVIEW — Click Approve on the roster row to activate."` Every newly added broker lands in **PENDINGREVIEW** — the broker cannot submit until you Approve them from the roster.

## Approve, pause, suspend, reinstate, terminate

Every roster row has an **Actions** column that exposes only the transitions valid from the broker's current status. Every button uses the two-click confirmation pattern (first click arms, second click commits).

| Current status | Available actions |
|---|---|
| **PENDINGREVIEW** | **Approve** (→ Active), **Terminate** |
| **ACTIVE** | **Pause**, **Suspend**, **Terminate** |
| **PAUSED** | **Reinstate** (→ Active), **Terminate** |
| **SUSPENDED** | **Reinstate** (→ Active), **Terminate** |
| **TERMINATED** | (no actions — terminal) |

What each transition means in the broker's portal:
- **Approve / Reinstate** → broker sees the full portal and can submit deals.
- **Pause** → broker sees a "Broker access paused" notice; submissions blocked.
- **Suspend** → broker sees a "Broker access suspended" notice; submissions blocked.
- **Terminate** → broker disappears from the broker portal entirely (filtered out at resolution).

Each transition writes to the audit log with a kind that reflects the action: `broker.approved`, `broker.paused`, `broker.suspended`, `broker.reinstated`, `broker.terminated`. Illegal transitions are blocked (you can't move anything back from **TERMINATED**, and **PENDINGREVIEW** can only go to **ACTIVE** or **TERMINATED**).

## Triage a broker submission

The **Broker Submissions** panel shows everything the broker has submitted. Each row carries a structured **Summary** chip (e.g. `H100 × 64 · ERCOT` for a demand, `2 line(s) · 48 total units · CAISO` for a supply manifest) plus the broker's free-text notes if any.

The full submission lifecycle is **REVIEW → SCREENED → CONVERTED → DEAL → SETTLED** with **DECLINED** as a terminal exit from any non-terminal state. (Legacy submissions from before Phase 1 also have a **MATCHED** state — see the legacy section below.)

On any submission in **REVIEW** or **SCREENED**, three actions are available:

### Screen (optional DD gate)

1. On a **REVIEW**-state row, click **Screen**, then **Confirm screen?**.
2. The submission transitions to **SCREENED**. Use this when you've started DD on the broker's submission but aren't ready to commit the conversion yet.

Screen is optional — you can Accept a submission directly from **REVIEW** without screening first.

### Accept (commit the conversion)

1. Click **Accept**, then **Confirm accept?**.
2. The submission transitions to **CONVERTED**.
3. The **Outcome** column shows a `→ LOT-2026-NNNN` chip (for supply manifests, this is the first lot created — the rest share the same IntakeBatchId) or `→ DEM-2026-NNNN` chip (for demand).

What Accept actually creates:
- **Supply manifest** → one **Lot** per line in the broker's manifest, all sharing an IntakeBatchId so they show up together in Inventory. Each lot is created in **Sourced** state and stamped with the broker's id so commission attribution can find it later.
- **Demand** → one **Demand** row stamped with the broker's id, projecting the structured fields the broker submitted (model, quantity, grade, region, price ceiling, need-by).

The **Accept** button is **disabled** on rows with no structured data (legacy free-text submissions from before the structured-intake form shipped). The tooltip says: *"Legacy free-text submission — no structured data to convert. Decline it instead."*

### Decline

1. Click **Decline**, then **Confirm decline?**.
2. The submission transitions to **DECLINED**. The broker sees the row drop off their kanban; the audit log captures the decline.

## What happens after Accept — automatic commission attribution

When the converted Lot is later allocated to a Deal (via **Reserved → Allocated** on the [Inventory Lots](/v3/supply/inventory) page), the system automatically:

1. Tries to auto-detect a matching open Demand from the same buyer (same category + model). If one is found, that Demand attaches to the Deal too.
2. **Same-broker-both-sides guard** — if the auto-detected Demand's broker is the same as any supply-side broker on the deal, the demand attach is silently skipped. The broker is never on both sides of one deal; the guard logs a notice ("Skipping demand auto-attach: would conflict with supply broker"), and the conflicting demand stays in the pool for a different deal.
3. **One Pipeline LedgerEntry per attributed broker** is created automatically. Zero brokers → no entries; one broker → one entry; two brokers (one per side) → two entries. The new LGE rows show up immediately in the **Commission Ledger** panel.
4. The originating broker submission flips from **CONVERTED → DEAL** so the broker's portal kanban shows the deal-stage state pill.

The basis (hardware vs compute) is decided by whether the deal carries any lots: deals with lots are **hardware** (settle once at delivery); deals without lots are **compute** (settle on contract term).

You do **not** need to hand-create a ledger entry for any broker-attributed deal — the auto-attribution path handles it. The **+ New entry** button below is for SLYD-direct deals where ops needs to manually attribute a broker after the fact.

## Create a commission ledger entry manually

For deals where the broker wasn't on the originating lot or demand (rare; usually a hand-attribution after a deal already closed), use the **+ New entry** flow.

1. In the **Commission Ledger** panel header, click **+ New entry**.
2. Fill the form:
   - **Broker** — pick from the roster dropdown (terminated brokers don't appear).
   - **Deal** — pick from the deals dropdown (each option shows DisplayId, Region, compacted value).
3. The preview shows the commission rate %, deal value, and estimated commission $.
4. Click **Create pipeline entry**.

The entry lands as **PIPELINE**. The preview math (1% standard, 0.6% above $25M) matches what the server computes from the published [Pricing Engine](/v3/pricing/engine) config.

## Move a ledger entry through its lifecycle

All transitions use two-click confirmation.

### Pipeline → Earned

1. On a Pipeline row, click **Mark earned**, then **Confirm earned?**.
2. The entry transitions to **EARNED**, and the commission is added to the broker's **Accrued** total on the roster.

### Earned → Paid

1. On an Earned row, click **Mark paid**, then **Confirm paid?**.
2. The amount moves from Accrued to **Paid LTM** for that broker.

### Reverse any entry (claw back)

1. On any entry that isn't already **REVERSED**, click **Reverse**, then **Confirm reverse?**.
2. The entry transitions to **REVERSED**. Commission is clawed back and broker accruals unwound. The entry stays in the ledger forever for audit — entries are never deleted.

## Filters and columns

**Broker Submissions** — filter pills: All / Review / Screened / Matched / Converted / Declined.
Columns: ID, Broker, Kind, **Summary** (structured chip + broker notes), Value, State, **Outcome** (→ LOT-/DEM- chip when converted), Actions.

**Commission Ledger** — filter pills: All / Pipeline / Earned / Paid / Reversed.
Columns: ID, Broker, Deal, Deal Value, Rate (%), Commission, Basis, State, On (date), Actions.
The **Basis** column shows the settlement basis: hardware basis settles one-time at delivery; compute basis settles on the contract term.

**Broker Roster** — no filters. Columns: ID, Broker (name + firm), Tier (pill), Status (pill), Subs · 30d, Open Deals, Accrued, Paid LTM, Actions.

## Things to know

- **Every new broker starts in PENDINGREVIEW.** No exceptions — even brokers you create from a known-good account. Click **Approve** on the roster row to activate them. Brokers cannot submit deals until they're Active.
- **Status drives the broker portal.** A paused or suspended broker still sees a portal, just a single notice card explaining their status and pointing them to partnerships@slyd.com. A terminated broker disappears entirely.
- **Account link beats firm-name match.** When ops links a broker to a V3 Account via the dropdown, the broker portal resolves the login through the FK — much more robust than the legacy firm-name string match. The fallback exists for legacy roster rows; new ones should always be linked.
- **Accept creates real Lots / Demands.** Once a broker submission is Accepted, the matching engine sees the resulting Lot or Demand and scores it alongside SLYD-direct supply/demand. You cannot un-accept a submission — if the conversion was wrong, Decline future submissions and handle the orphan Lot/Demand on its own page.
- **Open Deals is derived live, not hand-maintained.** The counter reflects deals where the broker is on either the supply (lot) or demand side AND the deal hasn't been delivered yet (no delivery date set).
- **Submissions · 30d is recomputed nightly** as a true rolling 30-day window. New submissions bump it immediately; the nightly recompute trims off submissions that fell out of the window.
- **Same-broker-both-sides is forbidden at deal formation.** A broker may be supply on one deal and demand on another, but never both sides of the same deal. If you see a Lot allocation that didn't pull in a demand even though one exists for the same buyer + model, check the broker — the system silently skipped the attach to uphold the invariant.
- **Entries are never deleted.** Use **Reverse** to undo a Pipeline or Earned entry — the REVERSED state remains in perpetuity.
- **Legacy free-text submissions.** Submissions from before the structured-intake form was added have only free-text Description and no structured fields. **Accept** is disabled on these (tooltip explains why); the only valid action is **Decline**. They still show **Mark matched** if you need the legacy state for any reason. New brokers can't create these — the platform-side drawer is structured-only.
- **Broker-side view of the same data.** Brokers see their own roster row, submissions kanban, and commission ledger in the [Broker portal (broker flow)](/broker). They self-submit deals from there into your **Broker Submissions** panel as **REVIEW**.
