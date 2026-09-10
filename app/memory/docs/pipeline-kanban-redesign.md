# Pipeline Page Kanban Redesign (per deal type)

**Project:** SLYD Platform — Admin
**Date:** 2026-08-13
**Author:** db573a0e-2c34-4a76-b41a-0676c6af891e
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Redesigned `/v3/deal-flow/pipeline` from a stage-filtered table into a kanban per deal
type, modeled on Mason's mockup (Hardware Sales / Power Sites / Offtake tabs with stage
columns and rich cards) but using only data we actually store.

**Deal-type facts established first (Mason's question):**
- `DealType` enum (core `SLYD.Domain/Models/DealOS/Deal.cs:175`): `Hardware`,
  `ThreeSided`, `Capacity` (+ `CapacityDealKind` Live/Forward flavor), `Unknown` for
  legacy rows (shape inferred from party FKs). BOM/quote-builder deals are Hardware
  deals carrying `Lines` — not a separate enum value.
- **Stages are shared across all types** — one hard-coded linear machine
  (Configuring → Financing → Escrowed → Live) enforced on the `Deal` entity (private
  setter, throwing transition methods). Different stage *names/sequences* per type
  would be a core-repo domain change (per-type stage machine + migration + every
  `DealStage` consumer). BUT per-type *advance requirements* already exist:
  `RequirementsFor` in `DealPipelineFeatures.cs:748` branches on Capacity / BOM /
  ThreeSided-vs-Hardware. So the kanban renders the same 4 columns on every board,
  with per-type gate checklists in the drawer.

**UI (Pipeline.razor / .css):**
- Type tabs (HARDWARE / 3-SIDED / CAPACITY) with counts; active tab is a solid pill.
  Unknown-type rows are bucketed by the same FK inference the stage machine uses
  (site+operator+offtake → 3-sided, else hardware) so legacy deals don't vanish.
  On load, lands on the first board that has deals.
- Right-side aggregates: Pipeline total, board total, LATE count (red).
- 4 stage columns per board, header = stage name + count + value with stage accent.
- Cards: party chain title (per shape: Hardware = buyer; Capacity = operator→offtake;
  3-sided = buyer→operator→offtake), DisplayId link + site, value + MW, chips (GPU
  summary, FORWARD/LIVE kind, region, DUE date / LATE / DELIVERED), dashed footer with
  child counts (lots/escrow/docs) and age in days (from CreatedAt — we do NOT store
  stage-entry time, so "days in stage" from the mockup was deliberately not faked).
- Mockup's weighted-% and next-step fields were skipped — we store neither
  (no probability field, no task/next-step entity on deals).
- Deal drawer (edit / documents / gated stage advance) kept untouched; no drag-and-drop
  since transitions are linear and gate-checked server-side.

**Backend (minimal):**
- `DealPipelineRow` gained optional `GpuSummary` (e.g. "H200 ×256", "MIXED ×384").
- `ListDealsAsync`: lot count query extended to aggregate model+quantity per deal;
  added `Include(CapacityListing)` so capacity cards show listing model × booked
  `GpuCount`. UI now always loads unfiltered (stage grouping is client-side).

**Verification:** `dotnet build` clean (0 errors); all 74 `~DealFlow` tests pass.
Not yet visually checked in the running app.

## To Do Next

- Visual pass in the running app (dark/light, narrow widths — kanban collapses to
  2 columns under 1200px next to the 440px drawer).
- If Mason wants true "days in stage": needs a stage-entered-at timestamp (derivable
  from the hash-chained AuditEvents or a new column) — not currently stored.
- If weighted pipeline is wanted: needs a probability/weight field on Deal (core change).
- Per-type stage *names* (cosmetic column relabeling) is cheap if desired; per-type
  stage *machines* is a medium core-repo change.
