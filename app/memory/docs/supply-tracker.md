---
title: Supply Tracker
route: /v3/supply/tracker
audience: supply-ops, partnership-ops
slug: supply-tracker
surface: admin
---

# Supply Tracker

Supply Tracker is the **confidential, internal-only** supplier-firm relationship CRM. It tracks every firm SLYD sources hardware from — equipment-finance houses, ITAD shops, OEM lifecycle / asset-recovery partners, and secondary-market distributors — with stage, ownership tenure, movement score, and MW pipeline. Open it at **V3 Supply → Tracker** (`/v3/supply/tracker`).

The page is wrapped in a **CONFIDENTIAL · INTERNAL ONLY** banner. Firm identities are **never** exposed to buyer-facing surfaces. Buyers only ever see anonymized **public tiers** on lots (set via the `PublicTier` field on **[Inventory Lots](/v3/supply/inventory)**). Don't link to or screenshot this page in customer-facing communications.

## Page layout

- **Header** — page title + subhead
- **Confidential banner** — yellow warning explaining the privacy rule (firm identities never reach buyers)
- **KPI strip** — four cards: Firms · Warm · Active · MW Pipeline
- **Tier filter bar** — All Tiers + one pill per tier with count
- **Stage filter bar** (second row) — All Stages + one pill per stage; counter on the right showing `N FIRMS · N MW PIPELINE`
- **Left panel** — firms table
- **Right panel** — drawer with detail + inline edit form

Clicking a row opens the drawer.

## Tiers — the four firm classifications

The tier captures *what kind of firm* SLYD is dealing with. The four tiers:

- **Equipment Finance / Off-Lease** — leasing companies returning gear at lease end
- **ITAD / Decommissioning** — IT Asset Disposition / data-centre decommissioning
- **OEM Lifecycle / Asset Recovery** — OEM-run lifecycle / asset-recovery programs
- **Distributors / Secondary** — secondary-market distributors

Filter pills appear in that order.

## Stages

The relationship lifecycle stage with each firm — set per the V3 `TrackerFirmStage` enum (e.g. `Prospect`, `Warm`, `Active`, etc.). Pills are rendered for every defined stage; single-select.

## KPI cards

- **Firms** — total firms in the current filter
- **Warm** — count where the **Warm flag** is set (warm intro / hot relationship)
- **Active** — count where Stage = `Active`
- **MW Pipeline** — sum of MW pipeline across visible firms

## Table columns

- **Firm** — firm name (with the **INT** chip in the header to remind ops this is internal-only)
- **Tier** — tier label
- **Stage** — stage pill
- **Owner** — owning admin's name, or `—`
- **Movement** — 0–100 score with a horizontal bar (low / med / hi colour-banded)
- **Warm** — `🔥 WARM` flag if set, otherwise `—`
- **Last Touch** — relative time of last interaction (`47m ago`, `9d ago`, or full date for older), plus an inline **Touch** button to stamp it to now
- **MW** — MW pipeline number
- **Lots** — count of lots SLYD has sourced from this firm (link to **[Inventory Lots](/v3/supply/inventory)** for the lot records)

## Filter the list

Two single-select pill bars, composable:

- **Tier** — All Tiers + one pill per tier with count
- **Stage** — All Stages + one pill per stage

The counter on the right of the Stage bar shows `N FIRMS · N MW PIPELINE` for the current filter.

## Stamp a touch

The page's lightest-weight mutation — record that ops just interacted with the firm without opening the drawer.

1. On the row, click **Touch**.
2. The Last Touch column updates to *just now*.
3. Success banner: `<Firm> touched — last interaction stamped and logged to the Audit Log.`

Touches are audited. Use them every time you reach out — phone, email, in person.

## Edit a relationship

The drawer opens an **Edit Relationship** form covering the four mutable fields:

1. Click a row to open the drawer.
2. The drawer shows the firm summary + the edit form pre-loaded with current values.
3. Edit any of:
   - **Stage** — dropdown of all stages
   - **Movement Score (0–100)** — must be in range
   - **Warm intro flag** — checkbox
   - **MW Pipeline** — numeric (step 0.1)
4. Click **Save changes**.

Validation: *"Movement score must be between 0 and 100."* On success: `<Firm> updated — before/after snapshots logged to the Audit Log.`

## What ops *cannot* do here

- Add a new firm (firms are seeded out-of-band; if a firm isn't on the list, escalate)
- Delete a firm
- Edit the firm name, tier, or owner (only Stage / Movement / Warm / MW Pipeline are editable)
- See firm identities on any buyer-facing surface — they're scrubbed by design
- Click into **Sourced Lots** count for a per-lot list (the count is a rollup; cross-reference **[Inventory Lots](/v3/supply/inventory)** filtered by Origin firm)

## Things to know

- **Internal-only. Confidential.** This is the central rule. Don't reference firm names or this page in customer-facing messages, support tickets, or screenshots. Buyers see only the anonymized **PublicTier** field on lots.
- **The INT chip is a reminder.** It appears in the firm column header and on the firm name in the drawer. Treat any field flagged INT as internal-only.
- **Every mutation is audited.** Touches, Stage / Movement / Warm / MW Pipeline edits all write hash-chained Audit Log entries with before/after values on **[Platform Audit](/v3/platform/audit)**.
- **Movement is a 0–100 score.** Ops's own judgement of how "moving" the relationship is right now. The bar colour-bands at 40 and 70 (low / med / hi). Use it as a rough ranking; the absolute number is whatever ops calibrates it to.
- **Warm intros stand out.** The `🔥 WARM` flag shows in the table and the Warm KPI counts only flagged firms. Treat warm flags as "high-priority next touch."
- **Touch is the cheapest, most useful mutation.** Stamp it after every real interaction — it keeps the Last Touch column meaningful and the relationship hygiene reports honest.
- **MW Pipeline is a forecast, not a reservation.** It's ops's estimate of how much MW of supply this firm might bring in the foreseeable future. Edits to it are just ops re-forecasting; they don't reserve anything.
- **Sourced Lots count is read-only.** It rolls up from lots where Origin Firm = this firm. For the full list, open **[Inventory Lots](/v3/supply/inventory)** and filter by origin (visible in the lot drawer's Origin field).
- **Related surface — [Inventory Lots](/v3/supply/inventory).** Every lot SLYD sources from a tracked firm carries that firm in its Origin field. Inventory Lots is the per-lot record; Supply Tracker is the per-firm relationship.
- **Customer-side experience.** Buyers never see firm names. Their experience of "where this lot came from" is the anonymized **Public Tier** label on the lot — if a buyer asks "who's the supplier," the right answer is the tier, not the firm.
