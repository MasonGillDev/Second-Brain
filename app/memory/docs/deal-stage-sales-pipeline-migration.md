# Deal Stages → 6-Stage Sales Pipeline (core + admin done, platform PENDING)

**Project:** SLYD Platform — core + admin (+ platform pending)
**Date:** 2026-08-13
**Author:** db573a0e-2c34-4a76-b41a-0676c6af891e
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Replaced the deal execution stage machine (Configuring → Financing → Escrowed →
Live) with Mason's sales pipeline: **New Inquiry → Qualified → Sourcing →
Quote Sent → Negotiating → Closed**, plus **Lost** as a terminal exit from any
open stage. Decisions locked with Mason: Closed = won and post-close execution
is tracked in Deployments; every deal (including system-formed capacity
bookings) enters at New Inquiry; per-type *gates* now, rep-task system later
on top of the same gate definitions.

**Core** (`SLYD-Platform/core`, all local, UseLocalCore builds):
- `Deal.cs`: new `DealStage` enum with explicit load-bearing ints
  (NewInquiry=0 … Closed=5, Lost=6). Mark* methods replaced by `Advance(by, at)`
  (linear, throws on terminal) and `MarkLost(by, at)` (refused from Closed/Lost).
  New rows default to NewInquiry.
- Migration `20260813172427_RemapDealStageToSalesPipeline` (scaffolded empty via
  dotnet-ef, raw SQL added): 3→5 (Live→Closed), 1,2→4 (Financing/Escrowed→
  Negotiating), 0→2 (Configuring→Sourcing). **Statement order is load-bearing**
  (highest-first so rewritten rows can't be recaptured). No schema change.
- `DemoSeedJob`: Mark* chains → `AdvanceTo` helper walking `Advance`.
- Verified: core solution builds, **657 + 311 + 74 tests green**.

**Admin** (`SLYD-Platform/admin`):
- `DealStageMachine`: 6-stage Order (Lost deliberately excluded — exit, not
  step), Next, NextLabel, and new `Label()` ("New Inquiry"/"Quote Sent" pretty
  forms; callers uppercase for micro-labels).
- `DealPipelineFeatures`: AdvanceStageAsync now calls `deal.Advance`; the
  capacity CommittedRatio bump moved from Escrowed→Live to Negotiating→Closed
  (still atomic with the flip, still fires once). New `MarkLostAsync` (no
  gates; audit "deal.lost" only — the DealStageAdvancedCheck sweep provides the
  ops signal). ListDealsAsync guards Lost out of stage aggregates so Lost value
  never inflates pipeline totals. Counterparty notification copy rewritten
  (early stages generic; Closed messaging escrow-aware).
- `RequirementsFor` gate matrix (per type, entering each stage):
  - Capacity: Qualified=op+offtake; Sourcing=listing linked+value>0;
    QuoteSent=GPUs available (over-book caught before quote goes out);
    Negotiating=doc attached; Closed=signed doc+escrow healthy+availability
    re-check+escrow-HELD advisory.
  - BOM (has Lines): Qualified=buyer; Sourcing=[] (sourcing IS the work);
    QuoteSent=every line quoted+value; Negotiating=doc; Closed=lots
    allocated rule+signed+escrow rows.
  - Hardware/3-sided/Unknown-inferred: Qualified=buyer (3S: any party);
    Sourcing=[]; QuoteSent=lot attached+value (3S: site+op+offtake+value);
    Negotiating=doc; Closed=existing lots/signed/escrow rows.
  - Escrow-HELD advisory moved from the old Escrowed hop to Closed.
- UI: Pipeline kanban now 6 columns (board scrolls horizontally beside the
  drawer; min 180px columns), new stage colors/pills incl. `st-lost`, Lost
  chip in aggregates, Lost cards off the board (terminal, still reachable via
  deal detail), quiet "Mark lost" button with confirm-pulse in the drawer,
  Closed/Lost resolved notes. DealDetail stage track relabeled + Lost pill +
  copy fixes. `DealStageAdvancedCheck` sweeps the new audit kinds.
- Tests: 7 files remapped (gate boundaries moved to their new equivalents,
  seed helpers now walk `Advance` in a loop); new MarkLost coverage (terminal
  from open stage; refused on Closed). **All 255 admin tests green.**

**Semantic mapping used everywhere:** `== Live` (fully executed) → `== Closed`;
"open pipeline" `!= Live` → `!= Closed && != Lost` (ProcurementLineProjection,
InventoryLotFeatures, DashboardV3Features, EscrowFeatures); formation stage
Configuring → NewInquiry (default, no explicit sets needed).

**Migration APPLIED to the local dev DB** (`SLYD2` on localhost, Mason's
explicit connection string) and verified: 4 Configuring→Sourcing,
3 Financing + 2 Escrowed→Negotiating (5), 4 Live→Closed. All 13 rows
accounted for; `20260813172427_RemapDealStageToSalesPipeline` is the head of
`__EFMigrationsHistory`. It was the only pending migration.

**PLATFORM DONE** — see the "Platform: buyer-facing status layer" section
below.

## Platform: buyer-facing status layer (same session)

Decision (Mason asked whether buyers should see the new stages): **no.** The
new `DealStage` IS the sales funnel, so it inherits the "no CRM shows a
prospect their pipeline position" rule wholesale. "Sourcing" is the worst leak
— it tells the buyer we don't hold the supply yet, which is pricing leverage.

Built `Platform.WebUI/Services/CustomerDealStatus.cs`: a SEPARATE enum
(PreparingQuote / QuoteReady / Contracting / PreparingDelivery / Active /
Inactive) + `CustomerDealStatusMap`. Deliberately not a relabeling of the
internal enum — when ops adds a "Stalled" stage later it maps onto an existing
customer status instead of flickering into customer view.
Mapping: NewInquiry/Qualified/Sourcing → PreparingQuote (one bucket ON PURPOSE
— the customer cannot tell them apart); QuoteSent → QuoteReady; Negotiating →
Contracting; Closed → PreparingDelivery, or Active once `DeliveredAt` is set
(closing wins the deal, it doesn't hand over compute); Lost → Inactive.

**The load-bearing structural choice: the internal enum stops at the service
layer.** Platform view records (`MyDealRow`, `DealRoomView`,
`DealOsPipelineRow`, `FinanceableDealRow`) now carry `CustomerDealStatus`, not
`DealStage`. Verified by grep: ZERO `DealStage` references remain in any
`.razor` file; the only ones left are queries/decisions in Services and
Controllers. This also auto-fixed `DiligencePackService`, which builds the
lender zip entirely from `DealRoomView` — it now serializes the customer
status without a targeted change.

Two leaks found that weren't in the plan: `CommandBar` searched deals by
`d.Stage.ToString()` (typing "sourcing" would have revealed pipeline
position — now matches the customer label), and `BrokerDashboardController`
shipped raw stage strings in its JSON API.

Surface changes: Lost deals filtered out of My Deals + the Deal OS dashboard
(query-level) and given a neutral "no longer active" note in the Deal Room
instead of the journey tracker (the room stays reachable for bookmarks).
The Deal Room's existing 5-step journey (Source→Configure→Finance→Deploy→
Match) was KEPT as narrative but re-gated on customer status. New dashboard
action item at QuoteSent ("Quote ready for review") — the first moment the
deal asks anything of the customer; the old Financing signature prompt moved
to Negotiating. `FinanceableStages` (was Configuring+Financing) = all five
open pre-close stages. Broker commission status is now a commission lifecycle
(Paid = closed+delivered, Cleared = closed, Closed out = lost, Pending =
open), and Lost stays in the broker's win-rate DENOMINATOR (it's their
performance record) while dropping out of in-flight commission.

Tests: new `CustomerDealStatusTests` pins the whole mapping table, that
pre-quote stages are indistinguishable, and that no customer label echoes
internal vocabulary. **Platform green: 161 + 11 + 5 + 11 across all four test
projects.** Admin re-verified at 255 after the platform work.

## Deal Room correctness pass (same session, after Mason reviewed it)

Mason caught four things wrong with the customer-facing room. All platform-side.

**1. BOM deals looked EMPTY to their own buyer.** Platform had zero references
to `DealLineItem` — the Spec tab rendered only Lots, which don't exist on a
quote-builder deal until supply is physically allocated. So a whale deal showed
its buyer an empty room. Added `DealRoomLineItem` (LineNumber, Category,
Subcategory, Description, Quantity) + `Lines` on `DealRoomView`, rendered as a
"Line items" table above the lots table; Spec tab badge counts both.
**Deliberately NOT carried on the line: the selected supplier quote or amount
(our cost/margin), the RFQ fan-out, and any per-line sourcing/fulfilment
state** — a line reading "not yet sourced" leaks our supply position, the exact
leverage leak the status layer exists to prevent. Quantity 0 renders "—"
because lot-scoped lines keep real counts in SpecJson.

**2. The journey promised services SLYD doesn't provide.** Step 04 said SLYD
"racks the hardware at the energy site, wires power and cooling, and brings the
cluster online." Per Mason: **we deliver the hardware, that's it.** Renamed
Deploy → **Deliver**, copy now "SLYD delivers the hardware against the agreed
date. Installation and operation are handled on your side (or by your chosen
operator)."

**3. Matching read as automatic.** Step 05 said matching "begins the moment the
cluster is deployed" and auto-completed to "LIVE · IN PRODUCTION". Listing
someone's compute is THEIR decision. It now never auto-completes, shows meta
"OPT-IN", carries a new `wait-optional` tier ("OPTIONAL — YOUR CALL", muted
styling), and reads "Nothing is listed unless you ask us to."

**4. The audit tab was the worst leak in the room** — worse than the stage
pills I'd just fixed. It shipped every `SubjectType == Deal` AuditEvent
verbatim: raw kinds (`deal.sourcing`, `deal.quotesent`, `deal.lost` — defeating
the whole CustomerDealStatus layer) AND expandable before/after JSON, which
carries **deal Value edits (the entire negotiation and margin history),
`bypassedWarnings` (that ops advanced past an unmet escrow gate), and
`listingCommittedRatio` (how much of a listing OTHER buyers hold)**.
Replaced with an **allowlist**, `DealRoomService.CustomerVisibleAuditKinds`
(deal.created → "Deal opened", deal.quotesent → "Quote issued",
deal.negotiating → "Contracting started", deal.closed → "Deal closed"), filtered
in SQL. `DealRoomAuditRow` now carries only When / WhoDisplay / Label /
AfterHash — **no field capable of holding a diff**. Allowlist not blocklist, so
a new ops event kind is invisible until someone deliberately adds it. Tab
renamed Audit → History. Deleted ~5.8KB of now-dead diff-extraction code
(`ExtractDiff`/`PrettyPrint` in the service, `ReadAuditFields`/`FormatAuditValue`/
`IsIdentifierKey`/`HumanizeKey` + expansion state in the component) rather than
leave the leak mechanism lying around. `DiligencePackService` inherits all of
it (builds from the room view); its CSV header is now "Milestone".

New `DealRoomLeakTests` pins all of it: BOM visible with lots empty, line
record has no quote/supplier/price/fulfilment property, history shows only the
two milestones out of five seeded events, the audit row type cannot carry a
payload, and the allowlist excludes qualified/sourcing/updated/lost/deleted.
**Platform green: 166 + 11 + 5 + 11.**

## Pre-production cleanup pass

Fixed:
- **Customer-visible copy naming dead stages.** `Finance.razor` empty-state read
  "Deals appear here while they're still Configuring or Financing. Once
  escrowed…" — three stages that no longer exist, shown to customers. Now
  "Deals appear here until they close."
- **Historical audit rows would have blanked every existing deal's history.**
  Rows keep the kind they were written with, and the local DB alone has
  `deal.financing` ×12, `deal.escrowed` ×8, `deal.live` ×5. The allowlist only
  had modern kinds, so every pre-remap deal would show "Deal opened" and then
  nothing. Added legacy mappings: `deal.live` → "Deal closed",
  `deal.financing` → "Contracting started". `deal.escrowed` deliberately left
  out (no customer milestone; escrow state is on the Finance tab). Test pins
  both the inclusion and the exclusion.
- ~12 stale doc comments / titles across all three repos ("five-step pipeline
  (Source → Configure → Finance → Deploy → Match)", "Live stage gate",
  "go-Live", "starts at Configuring"). Re-verified green after: core
  657+311+74, admin 255, platform 166.

### DEPLOY-ORDER HAZARD — read before pushing

`ci-cd.yml` runs migrations **before** deploying new application code (line
~143, deliberate). The stage remap rewrites ints under the OLD code, so for
the window between migration and rollout, production code misreads every deal:
stage 2 renders as "Escrowed" when it now means Sourcing, and `Closed = 5`
is outside the old 0–3 enum entirely (renders as "5"; old `MarkLive` paths
throw). **Admin and Platform deploy independently and both run migrations** —
whichever goes first starts the window, and it stays open until the other
finishes. Mitigation: deploy the two back-to-back in a low-traffic window.
There is no backwards-compatible path here; the remap is inherently breaking.

### Version state at time of writing
- Core: uncommitted, **on `main`** (needs tag + publish; new version, call it
  0.2.14).
- Admin: `development`, references core **0.2.13** → bump to the new tag.
- Platform: `development`, references core **0.2.12** → **two-version jump**,
  which also pulls in the S3 document work from the prior session.
- Everything in all three repos is still uncommitted.

## To Do Next

- Ship sequence: tag/publish core, bump admin + platform package versions,
  deploy (migration runs via the efbundle in CI — the dev DB is already done).
- DealDetail page has no Mark-lost button yet (Pipeline drawer only).
- Historical audit rows keep old kinds ("deal.financing" etc.) — the ops sweep
  no longer matches them (cursor-forward only, harmless).
- Future per Mason: gates surfaced as rep tasks + manually added task-gates.
- Visual pass of the 6-column kanban AND the platform customer surfaces still
  pending — nothing has been clicked through in a running app.
- Deferred buyer-facing work (needs new domain, designed for but NOT built):
  request lifecycle states (Received → Matching → Options ready → Quoted) on
  the buyer's demand object; "what we need from you" checklist (blocked on the
  rep-task layer having an OWNER-PARTY field — `StageRequirement` has no
  ownership concept today, which is itself a reason not to expose requirements
  to customers now); rep-entered expected-completion window (never
  auto-derived — auto dates slip publicly and burn trust); richer per-party
  views on ThreeSided deals so each side sees only its own leg.
