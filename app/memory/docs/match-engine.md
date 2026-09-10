---
title: Match Engine
route: /v3/deal-flow/match-engine
audience: deal-ops, supply-ops, revenue-ops
slug: match-engine
surface: admin
---

# Match Engine

Match Engine is the **lot-driven matching console**. Pick an inventory lot and the page ranks every open demand against it — scored, banded, and explainable. Use it when ops has supply on hand and needs to find the buyer to pair it with. Open at **V3 Deal Flow → Match Engine** (`/v3/deal-flow/match-engine`).

The companion view is **[Matching · 3-sided](/v3/deal-flow/matching)** — same scoring infrastructure, but starting from a **site** instead of a **lot**. Lot definitions and lifecycle live on **[Inventory Lots](/v3/supply/inventory)**; demand definitions live on **[Demand Book](/v3/crm/demand)**. This page only describes the matching console.

## Page layout

- **Header** — page title + a dynamic subhead that reads:
  - *"Loading inventory…"* while lots load
  - *"N lots ready · choose one to rank demand by score"* before a lot is selected
  - *"Scoring demand against <Model> supply…"* while a lot is being scored
  - *"N demand candidates · top 20 by score"* once results are loaded
- **Choose a lot** section — typeahead search box (plus a quick-pick chip row in demo with ≤25 lots)
- **Lot details** card (after selection) — summary of the picked lot's headline fields
- **Hardware-buy demand** table + **Compute-contract demand** table (split-grid)
- **Propose modal** — opens when ops clicks **Propose** on a candidate row
- **Success banner** at the top after a successful Propose

## Choose a lot

The picker is a typeahead — it filters results as you type. It matches on:

- **DisplayId** (the lot's chip ID, e.g. `LOT-…`)
- **GPU model**
- **ISO** code

Placeholder text: *"Search by display id, GPU model, or ISO…"*

For demos with fewer than 25 lots in the queue, a **quick-pick row** of clickable chips also appears so ops doesn't have to type. Each chip shows `<DisplayId> · <GPU model> · <Quantity> · <ISO>`. The row auto-hides once the catalog scales past the threshold.

Only lots in **LISTED** state appear in the picker. Pre-LISTED states (`CLAIMED` / `SOURCED` / `GRADED`) and post-LISTED states (`RESERVED` / `ALLOCATED` / `DEPLOYED`) are excluded — Propose can only create a deal from a published, unbound lot, and showing other states would just produce guaranteed-fail clicks. See **[Inventory Lots](/v3/supply/inventory)** for the full lifecycle; only lots that have reached **LISTED** but have not yet been reserved against a deal are eligible here.

## Lot details card

After a lot is picked, the page shows a summary grid:

- **Lot** — DisplayId
- **Model** — GPU model
- **Quantity** — count
- **Grade** — A / B / C / New
- **ISO** — region code
- **State** — current lot state pill (from the lifecycle on **[Inventory Lots](/v3/supply/inventory)**)
- **Origin firm** — first 8 chars of the origin firm ID (when present)
- **Cost basis** — internal cost basis in dollars
- **Price** — current sale price

## Candidate tables — Hardware-buy and Compute-contract demand

Two side-by-side tables (split-grid). Each shows the **top 20** demand candidates for the selected lot, ranked by score.

The same demand types defined on **[Demand Book](/v3/crm/demand)** drive the split — **Hardware-buy demand** comes from demands of type Hardware; **Compute-contract demand** from demands of type Compute.

Both tables share the same columns:

- **#** — rank
- **Score** — banded score pill (colour-coded — hot / warm / cold). The score is a composite from the scoring engine.
- **Demand** — DisplayId + buyer name (or *"Unnamed buyer"* if the demand has no account binding)
- **Wants** — `<Quantity> × <GPU model>` on top, `by <YYYY-MM-DD>` need-by below
- **Urgency** — pill (Standard / Elevated / Critical) — definitions on **[Demand Book](/v3/crm/demand)**
- **Top dimensions** — up to **3** dimension chips, ordered by absolute point magnitude. Each chip shows the dimension name and the points contributed (with sign), colour-coded by direction. Hover shows the full explanation.
- A **Propose** button on the right

Empty state per table: *"No demand candidates found for this lot."*

## Expand a row for the full breakdown

Clicking any column of a row (except the **Propose** button) expands the row to show the **full dimension breakdown**:

- A nested table with three columns: **Dimension · Points · Explanation**
- Every dimension the scoring engine considered, in order — both positive (matches, fit) and negative (penalties, distance). Each row colour-codes its points cell by direction.

Click the row again to collapse.

This is the closest thing to a "why this score" explanation the page exposes — use it when a candidate's score doesn't match ops's intuition.

## Propose a match

The terminal action — create a new deal that pairs this lot with the chosen demand.

1. On the candidate row, click **Propose** (paper-plane icon).
2. The **Propose modal** opens, pre-loaded with the lot's details and the candidate demand's details.
3. Fill in **Price per unit** (defaults to the lot's listed price) and optional **Notes**.
4. Click **Send proposal**.
5. On success, the modal closes and a green banner reads: *"Deal SLY-YYYY-NNNN created — lot reserved, demand attached."*

The Propose action commits three changes in one step:

- A new **Deal** is created in the **CONFIGURING** stage on **[Deal Pipeline](/v3/deal-flow/pipeline)**, with the buyer derived from the chosen demand and a region/value seeded from the demand and the proposed price × lot quantity.
- The lot advances from **LISTED** to **RESERVED** and is bound to the new deal.
- The demand transitions from **OPEN** to **MATCHED** and is attached to the deal.

Each step is written to the **[Audit Log](/v3/platform/audit)** as `deal.created`, `lot.reserved` (via provenance), and the demand attach. The deal is immediately visible on **[Deal Pipeline](/v3/deal-flow/pipeline)** — refresh that page to see it.

If you change your mind, see **Release** on **[Inventory Lots](/v3/supply/inventory)** — releasing the reserved lot detaches the demand and deletes the empty deal in one click.

## What ops *cannot* do here

- Edit the lot (everything on the lot details card is read-only; mutations live on **[Inventory Lots](/v3/supply/inventory)**)
- Edit the demand (mutations live elsewhere; **[Demand Book](/v3/crm/demand)** itself is read-only in v1)
- Re-rank candidates — the score is set server-side at lot select; the page is a read
- Pick more than one lot at a time (single-lot view by design)
- Trigger Propose against multiple demands at once (one at a time)
- Pass an arbitrary score threshold filter (no score-cutoff control)

## Things to know

- **Top 20 only.** The candidate tables are capped at the top 20 candidates per side by score. If a likely match isn't there, refine the lot first (price, grade, ISO) and reload.
- **Score band ≠ stage.** A high score doesn't mean the demand will close — it means the lot fits well. Stage / state are independent.
- **Cancellation is built in.** Selecting a different lot while a score is in flight cancels the in-flight load and starts a fresh one. The subhead updates in real time as you switch.
- **Quick-pick is demo-only.** The clickable chip row only appears with ≤25 lots in the pool. In production, the typeahead is the only affordance.
- **Demand type drives table placement.** Hardware-buy demands always go in the left table; Compute-contract demands always go in the right. A demand can't appear in both.
- **The dimension chips are a preview.** The row shows only the top 3 by magnitude. Click to expand for the complete breakdown.
- **Proposing creates a real deal.** The new deal lands in **[Deal Pipeline](/v3/deal-flow/pipeline)** under **CONFIGURING** immediately. The lot is reserved against it and the demand is attached, all in one step. There is no separate "promote draft" action — Propose **is** the create-deal action.
- **Undo path.** A propose can be unwound from **[Inventory Lots](/v3/supply/inventory)** by opening the reserved lot and clicking **Release**. That detaches the demand and deletes the deal if it has no other lots/parties/escrow/documents.
- **Origin firm shows abbreviated ID.** The Lot details card shows only the first 8 chars of the origin firm ID — to see the firm name, open the lot on **[Inventory Lots](/v3/supply/inventory)**.
- **Related surface — [Matching · 3-sided](/v3/deal-flow/matching).** Match Engine pairs **lot ↔ demand** (two-sided). The 3-sided page pairs **site + operator + offtake-buyer** (three-sided). Same scoring infrastructure, different entry point.
