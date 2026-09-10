# Match Engine: BOM Lines as a Demand Source (SHIPPED)

**Project:** SLYD admin (match engine + deal workspace)
**Date:** 2026-07-21 (designed) / 2026-07-28 (implemented)
**Author:** 0f7c0174-fc17-4d62-975d-5c097ba9dbaf
**Directory:** /Users/masongill/Slyd-Platform/core (work in ../admin)

## What Was Done

### Update 2026-08-12: BOM lines surfaced in the Demand Book (both spines, one page)

Mason came back with "I want to populate the demand book with BOM lines."
Re-litigated the 2026-07-21 decision against the current codebase and the
projection **still wins** — but the pushback was partly right and the reasoning
below is the durable part.

**Where the original doc overstated it.** The "Demand and open BOM lines point
in opposite directions" framing is weak. Mason's counter: a BOM line means SLYD
is procuring that hardware *for the buyer*, so it's derived demand for the same
physical units. Correct — and it's exactly why the projection works at all
(the line maps into a `Demand` and runs through the identical scorer). The real
argument against persisting was never direction, it was **double-counting**:
`AssemblyRefreshJob.cs:86` / `RegionalBalanceJob.cs:48` aggregate offtake
demand, `AccountWorkspaceFeatures.cs:80` counts demands by `BuyerAccountId`
(which the projection must set for same-party exclusion), and
`DealDetail.razor:315` renders "Attached demands" beside the very lines they'd
be minted from.

**Mason's counter-proposal** — make BOM lines the spine: demand→deal mints a
line and links the *existing* demand instead of leaving an inert row;
deal-built-from-scratch mints a demand per line. That 1:1 invariant genuinely
dissolves the double-counting objection. What it doesn't survive is
**cardinality**: a Demand is one ask, a BOM is a decomposition (`DealLineItem`
owns per-line `Rfqs`/`SelectedQuote`/`Fulfillments`), so one demand usually
becomes several lines. At 1:N, "what's still needed" has two answers
(`demand.WantQuantity` vs Σ line remaining) and you're maintaining a sum
invariant — same sync burden, relocated. Parked, not rejected: **if the
cardinality turns out to be genuinely 1:1 in real deals, the spine is the
cleaner model** and worth the core migration.

**The real bug that surfaced, still unfixed.** `Demand.AttachToDeal`
(core `Demand.cs:240`) flips Open→Matched at deal formation, and every matching
path excludes Matched (`MatchingEngineFeatures.cs:203`, `:416`,
`MatchController.cs:77`). So the instant a deal forms the need goes dark as
demand even though nothing has been procured. That's why the book felt empty
mid-deal. The Demand Book work below papers over the *visibility* half; the
matching half is already covered by the projection (open lines are scored), but
the inert Matched demand row itself is still dead weight on the page.

**What shipped (admin-only, zero core changes, no migration):**
- **`ProcurementLineProjection.cs`** (new, `Features/Matching/`) — extracted
  `LoadOpenProcurementLinesAsync` + `ResolveLineModel` + the `ProcurementLine`
  record verbatim out of `MatchingEngineFeatures` and made them public, plus
  `DisplayIdOf`/`UrgencyOf` helpers. One definition of "open BOM line" so the
  book and the engine can't drift. Pure move — the 9 existing
  `ProcurementMatchingTests` passing unchanged is the proof.
- **`DemandBookModels.cs`** — `DemandRowKind {Demand, BomLine}`,
  `DemandBookScope {All, Hardware, Compute, Procurement}` (replaces the
  `DemandType?` filter), and a BOM-only trailing block on `DemandListRow`
  (`Kind`, `DealId`, `DealStage`, `RequiredQuantity`, `UnscoreableReason`) as
  optional params so the demand construction site was untouched.
- **`DemandBookFeatures.ListAsync`** — merges both spines newest-first.
  `Quantity` on a BOM row is the **uncovered remainder**, `RequiredQuantity` the
  line total. Category/ISO narrow both spines so the pill counts stay
  comparable (caught in self-review: first cut counted BOM lines unfiltered).
  Hardware/Compute counts deliberately exclude BOM lines — they're all
  hardware, so folding them in would silently inflate the intake pill.
- **`DemandBook.razor`** — PROCURE badge, "Deal lines" scope pill, OPEN LINE
  + "60/200 covered" sub-line, deal-stage pill standing in for demand state
  (a line has no `DemandState`), unscoreable lines kept visible with the reason.
  BOM rows **don't** open the drawer: their Id is a `DealLineItem` Id and the
  candidates panel reads `MatchCandidate` rows that only exist for persisted
  demands, so they `NavigateTo` `/v3/deal-flow/pipeline/{dealId}?line={lineId}`
  — the lot-less form of the existing deep link, which expands the line and
  opens its allocate form (`DealDetail.razor:866` returns early with no `lot`).
- **Tests**: `DemandBookProcurementTests` (11, EF InMemory) — both spines
  listed, counts isolated, scope filters, deep-link identity, remainder vs
  required, unscoreable visibility, covered/Live exclusion, category filter
  across both spines, `GetAsync` null for a line Id, and no Demand rows
  persisted. Suite 240/240 green, solution builds clean.

Uncommitted on `development`.

### Update 2026-07-28: implemented — admin-only, zero core changes

Built exactly per the projection design (admin repo, branch
feat/crm-accounts-quote-builder, uncommitted alongside the workspace batch).
Note: implemented AFTER the 2026-07-22 quote→lot reversal — quotes are data
points again, so Listed inventory is the only matchable pool and this radar is
now the primary "supply meets open BOM line" surface.

**Feature layer** (`MatchingEngineFeatures.cs`):
- `LoadOpenProcurementLinesAsync`: DealLineItems on non-Live deals, Quantity>0,
  remaining = Quantity − Σ fulfillments > 0 → synthetic in-memory `Demand`
  (never persisted; Id = line Id as score key). Mapping: GPU model = line
  Subcategory (WantSubcategory null — GPU lots keep Subcategory null!),
  non-GPU model = SpecJson "model" key; Priority→Urgency
  (Immediate→Critical, High→Elevated); IsoCode = Deal.Region;
  BuyerAccountId = Deal.BuyerAccountId (same-party exclusion works).
  No-model lines = unscoreable, kept visible with reason.
- `GetLotEngineViewAsync` now returns `ProcurementCandidates` (ranked via the
  same `ScoreLotAgainstDemands` pass as demand lists).
- New `GetProcurementRadarAsync`: all open lines × Listed/deal-free pool via
  `ScoreDemandAgainstLots` → matchable count + best score/lot; ordered
  priority-first (Unset last) then largest gap.

**UI** (`MatchEngine.razor`): lot mode gained a "Procurement · open deal
lines" ranked table (PROCURE chip, dimension chips + expansion breakdown,
**Allocate →** navigates to the workspace); new "procurement radar" section
(third subject beside lot/capacity pickers, mutually exclusive) listing the
whole sourcing worklist with per-line matchable-supply stats.

**Deep-link** (`DealDetail.razor`): `?line={id}&lot={id}` query params —
expands the line, opens the allocate form, preselects the lot. New
`IDealWorkspaceFeatures.GetAllocationCandidateAsync(lineId, lotId)` validates
lots outside the top-5 hint slice (Listed, deal-free, category/model
compatible) and appends them to the dropdown so the hand-off can't dead-end.
Allocation itself still goes through `CommitLineFulfillmentAsync` — one write
path.

**Tests**: `ProcurementMatchingTests` (9, real MatchScoringService over EF
InMemory per MatchingEngineFeaturesTests precedent): under-covered filter,
priority/gap ordering, unscoreable visibility, pool eligibility, SpecJson
model resolution, partial coverage, no-Demand-rows-persisted. Admin suite
196/196 green; solution builds clean. Zero core changes — no tag/publish
chain needed.

### Original design (2026-07-21)

Design discussion only — decision recorded so implementation isn't skipped.

### The gap
Under-covered deal BOM lines (`DealLineItem` where sum of `DealLineFulfillment.Quantity`
< `Quantity`) are invisible to the match engine. When new supply lands (intake
conversion, broker manifest acceptance, quote-backed lot), nothing flags "this
covers line 2 of SLY-2026-0042." The workspace Allocate form is pull-only — ops
only sees candidates when they happen to open the deal. The reverse flow
(supply arrives → open lines light up) doesn't exist.

### The decision: projection, NOT Demand rows
Mason's original framing was the symmetry "quotes create lots, so BOM lines
should create Demands." Rejected minting real `Demand` rows because:
- A BOM line already IS a demand-shaped record — a shadow Demand duplicates an
  existing fact and owns a permanent sync burden (line qty edits, partial
  fulfillment, line removal must all propagate; drift = phantom demand).
- Demand's lifecycle points at deal *formation* and customer surfaces. A
  line-born demand already belongs to a deal — every consumer (deal formation,
  CustomerNotifier, customer pages) would need "except when" carve-outs.
  Demand = customer wants something FROM SLYD; open line = SLYD needs
  something FROM the market. Opposite directions.

**Chosen shape:** make under-covered BOM lines a second *demand source* the
match engine reads directly — a read-side projection of open-deal lines mapped
into the shape `MatchScoringService` scores (Category/Subcategory/SpecJson/
Quantity all exist on `DealLineItem`, mirroring `SellSubmissionLine`). Matches
render on the match-engine surface tagged as procurement ("covers
SLY-2026-0042 · line 2") and deep-link into the deal workspace's Allocate flow
instead of deal formation. Zero dual-write; "line still open" is always
computed from line + fulfillments.

This follows the week's convergence pattern (one claim path via
ClaimResolution, one line↔lot mechanism via DealLineFulfillment): a read-side
projection over the source of truth, not a shadow table.

Fallback only if projection proves too invasive: real Demand rows flagged with
a `SourceDealLineItemId`, system-attributed, auto-closed with the line, and
excluded from deal formation + notifications + customer surfaces.

## To Do Next
- **Decide the cardinality question** — do real deals decompose one demand into
  several BOM lines, or is it usually 1:1? A 1:1 answer makes Mason's
  demand↔line spine the better model (core FK + `DemandSource` value +
  migration); 1:N keeps the projection. Everything below assumes the projection.
- **Matched demands go dark mid-deal** (`Demand.cs:240` + the three exclusion
  sites). The book now shows the live BOM lines, but the originating demand
  still sits there as an inert Matched row with no coverage context. Options:
  show its deal's live coverage on the row, or collapse it into its lines.
- Commit the admin batch (procurement matching rides with the uncommitted
  workspace changes on feat/crm-accounts-quote-builder).
- Deferred fast-follow: on-Listed alert — when a lot publishes, evaluate open
  BOM lines via this projection and write Activity rows on covered deals
  (touches core `MatchAlertJob` machinery → commit→tag→publish chain).
- Consider CapacityListings as a second pool for service-ish lines (not yet).
- Still pending from the same session: cross-deal quote price-book page
  (`/v3/deal-flow/quotes` — filter by hardware, $/unit normalization,
  price-over-time chart, won/lost dimension).
