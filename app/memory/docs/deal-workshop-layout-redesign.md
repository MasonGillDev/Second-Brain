# Deal Workshop Layout Redesign

**Project:** SLYD Platform — Admin
**Date:** 2026-08-13
**Author:** db573a0e-2c34-4a76-b41a-0676c6af891e
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Restructured the deal workspace (`/v3/deal-flow/pipeline/{id}` — `DealDetail.razor`) to match a
mockup Mason supplied. Explicit scope from him: **layout only, first pass, no new
functionality** — show what current features can supply, and where a card or field can't be
backed by real data, render it with its title and "coming soon" rather than omitting it or
faking it.

### The shape

Old page was a vertical stack: header → stat strip → stage panel → documents → matching →
BOM lines → activity. New page:

- **Hero card** — title, kicker (`Type · Stage`), meta line, a four-metric strip
  (Amount / COGS / Gross margin / Your commission), and the six-stage tracker as full-width pills.
- **Two-column body** (`1fr / 340px`, collapsing at 1200px):
  - **Main:** Deal specifics (16-cell label/value grid) → BOM lines (proper table) → Documents
    & settlement → Matching engine → Activity.
  - **Rail:** Next step → Buying committee → Suggested matches.

### What's real vs. coming soon

Real, from data already loaded by `IDealWorkspaceFeatures` / `IDealPipelineFeatures`:

| Mockup element | Backed by |
|---|---|
| Amount | `Deal.Value` |
| Your commission | `Value × 0.10` — same flat rate the Pipeline kanban cards already use |
| Stage tracker | `DealStageMachine.Order` (6 stages + Lost) |
| Deal type, power, region, site, delivery window, delivered, opened, platform deal ID | `DealWorkspaceView` / `DealDetailView` |
| GPU model, quantity | derived from allocated lots → attached demands → BOM line quantities (capacity deals prefer the stamped `GpuCount`) |
| Lead time (longest) | the existing `CurrentLeadTime()` — longest selected quote, falling back to longest received |
| BOM line item / qty / net / fulfillment | `DealLineRow` — net is the curated (selected-quote) amount; fulfillment chips are allocated lots, else the selected supplier, else "Sourcing" |
| Next step | first unmet **blocking** stage gate, else first advisory, else the advance itself |
| Buying committee | party FK slots + `DealParty` attributions, deduped |
| Suggested matches | `line.InventoryCandidates` rolled up across the BOM, deduped by lot |

"Coming soon": COGS, gross margin, origination, close date, owner, ECCN status, contract term,
account domain, list price, discount slider, per-line margin, price floors, committee role
mapping (champion / economic buyer / blocker), last-touch recency, match scores.

**Why COGS and margin can't be shown:** `RecomputeDealValueAsync` sets `deal.Value = sum of
selected supplier quotes`. Sell price and cost are the *same number* today — there is no
separate customer price on the record, so any margin figure would be fabricated. That's a data
model change, not a UI one.

### Preservation

Nothing was removed. The whole RFQ/quote/allocation workflow still lives in the expanded line —
it now opens as a `<tr class="bom-detail-row"><td colspan="7">` beneath the row instead of
inside a `.line-card`. The deal edit form moved into the Deal specifics card head; the gate
checklist and Advance button moved into the rail's Next step card (they were the old Stage
panel, which is gone — the hero pills replaced its tracker).

### Method note

The markup restructure was done with a throwaway Python script that spliced exact line ranges of
the untouched blocks (line detail, documents, matching, activity, edit form, add-line form) into
newly-written scaffolding, rather than retyping ~500 lines by hand. Backup of the original is at
`scratchpad/DealDetail.razor.bak`. Verified afterwards by diffing the set of CSS classes used
before vs. after — every disappearance was intentional, and every orphaned CSS rule was deleted.

**Verification:** `dotnet build src/Admin` → 0 errors; `Admin.Tests` → 255/255 pass.
Not yet clicked through in a running app.

## To Do Next

- Visual pass in a running app — this has only been build- and test-verified.
- The mockup's discount slider and live-margin readout need a sell-price field on `Deal`
  (or on `DealLineItem`) distinct from the curated supplier cost. That's the blocker for the
  whole COGS / gross margin / discount / floor column group.
- Committee role chips need a role field on `Contact` (or on `DealParty`) — champion,
  economic buyer, technical eval, blocker.
- Next step becomes a real task once the rep-fulfilled task layer lands (already deferred in
  [deal-stage-sales-pipeline-migration.md](deal-stage-sales-pipeline-migration.md)); the gate-derived
  headline is a stand-in.
- Match scores exist in the Match Engine but aren't loaded by the workspace query — plumbing,
  not new logic.
