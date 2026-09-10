# Deal Workspace (Quote Builder) — Admin UI

**Project:** SLYD admin
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
**Directory:** /Users/masongill/Slyd-Platform/core (admin work in /Users/masongill/Slyd-Platform/admin)

## What Was Done

### Update 2026-07-22: REVERSAL — quote→lot creation stripped (session 0fe1f5b8-00f4-4b3d-81a5-492f38cfe93e)

Sales feedback via Mason: quotes are **data points on a supplier commitment**,
not reliable supply — too many variables for them to serve as lots for
matching; the quote data alone (SupplierQuote: amount, lead time, ValidUntil,
revisions) is what's wanted for analysis. The July 21 quote→lot piece was
removed before anything was committed. `Lot.SupplierAccountId` went too
(Mason's call — nothing would write it once the mint path was gone).

**Core (all previously uncommitted):**
- `Lot.cs`: removed `SupplierAccountId`/`SupplierAccount`,
  `SourceQuoteId`/`SourceQuote`, and `LotOwnershipType.QuoteBacked` (the
  enum's append-only rule didn't bind — it was never committed/published).
- `SlydDbContext.cs`: removed the two Lot FK configs; `DealLineFulfillment`
  config + DbSet kept.
- Migration `20260721145707_AddProcurementLoop` deleted and regenerated as
  `20260722172745_AddDealLineFulfillment` — DealLineFulfillments table only,
  no Lot columns. **DealLineFulfillment survives in full** (line↔real-inventory
  allocation is orthogonal to quotes-as-supply and still wanted).
- Tests: dropped the QuoteBacked pin + the two provenance-FK integration
  tests. Green: 582 unit / 57 integration.

**Admin (all previously uncommitted):**
- `DealWorkspaceFeatures`: `CreateLotFromQuoteAsync` deleted; the
  workspace-view quote→lot lookup deleted; `CommitLineFulfillmentAsync` no
  longer flips ownership (allocation just stamps `Lot.DealId`); unused
  `Truncate` helper removed. Interface + xmldocs updated.
- Models: `RfqQuoteRow.LotId`/`LotDisplayId` removed.
- `DealDetail.razor`: "Create lot" button/chip and handler removed;
  `AllocatableLots` now offers Listed inventory candidates only; hint texts
  rewritten. Physical coverage section, fulfillment rows, and the "expired"
  quote badge all kept. 187 admin tests green.

**Pending on Mason (permission-gated):** SLYD2 dev DB still has the old
migration applied. Rollback SQL was pre-generated before the migration files
were removed. Run:
1. `psql -d SLYD2 -f <scratchpad>/rollback-AddProcurementLoop.sql`
2. `ConnectionStrings__Conn="Host=localhost;Database=SLYD2;Username=masongill" dotnet ef database update --project src/SLYD.Infrastructure` (from core repo root)

Removed migration files + rollback SQL backed up at
`/private/tmp/claude-501/-Users-masongill-Slyd-Platform-core/0fe1f5b8-00f4-4b3d-81a5-492f38cfe93e/scratchpad/removed-quote-lot/`
(temp dir — gone after reboot; the git history of this doc is the durable record).

### Update 2026-07-21: Lead-time stat card
Fourth card on the workspace stat strip — the deal's current lead time =
LONGEST LeadTimeDays across SELECTED quotes ("critical path — longest
selected quote"); before any selection, falls back to longest across ALL
received quotes ("longest received — none selected yet"); "—" when no quote
states a lead time. Pure razor computation (RfqQuoteRow already carried
LeadTimeDays); no backend change. Razor gotcha: pattern variable `lead`
collided with an existing local — named `leadTime`.

### Update 2026-07-21: Procurement loop — manual deals, quote-backed lots, line fulfillment, stage parity

**Core (migration `20260721145707_AddProcurementLoop`, applied to SLYD2):**
- `Lot.SupplierAccountId` (Restrict) + `Lot.SourceQuoteId` (SetNull) — CRM/quote
  provenance; staleness derived through the quote link (ValidUntil), never
  duplicated. `LotOwnershipType.QuoteBacked = 3` (append-only): backed by a
  supplier's offer, not stock. Mason's rule encoded: quote-backed lots enter at
  **Claimed = not matchable**; Claimed → Sourced stays the ops availability
  verification, same trust gate as broker inventory.
- `DealLineFulfillment` (LineId, LotId, Quantity; unique pair, cascades both
  ways) — the single line↔lot mechanism: partial coverage, multi-lot tranches,
  and existing-inventory fulfillment in one shape. Tests: 583 unit / 59
  integration green (enum pins, quantity sums, unique rejection, cascade,
  Restrict, SetNull).

**Admin services:**
- `CreateDealAsync` (DealPipelineFeatures): manual whale-deal creation — mints
  `SLY-yyyy-NNNN` (auction-path pattern), stamps Type, value 0, writes Buyer
  `DealParty` with optional ContactId (validated to belong to the account).
  + `ListContactsForAccountAsync` picker.
- BOM-aware stage gates in `RequirementsFor`: deals with Lines gate Financing
  on "every line has a selected quote" (not raw lot attachment); Live keeps
  lot-allocation gate only for lots that exist (service-only lines don't block).
- `SelectQuoteAsync` now upserts `DealParty(Supplier, account, rfq.Contact)` —
  supplier involvement visible on account/contact workspaces; kept on deselect.
- `CreateLotFromQuoteAsync` — mints QuoteBacked/Claimed lot from any quote
  (won or lost — losing quotes become known supply "for free"), CostBasis =
  quote amount, provenance entry, one lot per quote.
- `CommitLineFulfillmentAsync` — allocation with quantity guards (never exceed
  lot quantity across lines); committing a QuoteBacked lot = purchase
  commitment → ownership flips Owned + `Lot.DealId` stamped; state untouched.
- `RemoveFulfillmentAsync` — only while Claimed/Sourced; detaches lot from
  deal when last allocation goes.

**Admin UI:**
- Pipeline: "New deal" button + form (type, buyer account → contact cascade,
  region) → navigates into the workspace.
- Workspace per line: "Physical coverage — N/M units" section with fulfillment
  rows (lot, qty, state, ownership chips, remove), Allocate form (candidates =
  quote-born lots + matching Listed inventory), per-quote "Create lot" button
  (chip once created), "expired" stale badge on quotes past ValidUntil.
- No admin tests per Mason's standing waiver; 184 existing admin tests green.

Built the deal workspace on the quote-builder schema — replaced the DealDetail
stub at `/v3/deal-flow/pipeline/{id}` with the full page.

### Admin.Application (branch feat/crm-accounts-quote-builder)

- `Models/DealOS/DealWorkspaceModels.cs` — DealWorkspaceView (header + stage +
  parties + CuratedValue), DealLineRow (with full RFQ/quote tree so lines
  expand without a second fetch), LineRfqRow, RfqQuoteRow,
  SupplierCandidateRow, Add/Update line + AddRfq + RecordQuote requests.
- `Features/DealOS/DealWorkspaceFeatures.cs` (+interface, +DI) —
  AccountWorkspaceFeatures precedent (dbFactory + admin actor + audit; deal
  Activity rows on RFQ send/decline/withdraw, quote received, selection).
  Notable behaviors:
  - AddLine auto-numbers (max+1); RemoveLine refused once any RFQ left Draft.
  - AddRfq: dup (line, supplier) friendly error; null ContactId auto-routes to
    the supplier's closest contact (RelationshipStatus desc, EngagementScore
    desc); explicit contact validated to belong to the supplier; OutreachOrder
    auto-appends.
  - MarkRfqSent stamps `RFQ-yyyyMMdd-NNNN` DisplayId on first send.
  - RecordQuote appends revision + MarkQuoted (throws unless Sent/Quoted).
  - Select/ClearQuote recompute Deal.Value = sum of selected quotes across
    lines (RecomputeDealValueAsync joins lines→quotes, override for the
    in-flight line).
  - GetSupplierCandidatesAsync: name search, Supplier-type accounts first,
    each with closest contact for the picker.

### Admin UI

- `DealDetail.razor` + scoped CSS — header (stage chip, buyer/operator links,
  buyer contact), stat strip (curated value, lines selected, RFQs out/quoted),
  BOM lines as expandable cards (click row → inline edit + RFQ management),
  add-RFQ form with live supplier search showing each account's closest
  contact, per-RFQ state actions (Send / Record quote / Declined / Withdraw),
  quote list per RFQ with Select/Clear (selected highlighted), activity feed.
- Razor gotcha hit: interpolated strings with double quotes inside @onclick
  lambdas break the Razor parser — moved to named handlers in @code.

**No tests written — Mason explicitly waived tests for this batch** (flag in
PR description per repo rules). Existing 184 admin tests still green; solution
builds clean.

## To Do Next

- Run the SLYD2 rollback + new-migration apply (two commands in the 2026-07-22 update above — permission-gated, Mason must run).
- Commit core + admin (branch feat/crm-accounts-quote-builder; ask Mason first per repo rules).
- Supplier capability tags on Account + "blast out" bulk RFQ creation (sales ask).
- Quote document upload (SupplierQuote.DealDocumentId has no UI yet).
- Manual deal creation entry point (workspace currently opens existing deals only).
