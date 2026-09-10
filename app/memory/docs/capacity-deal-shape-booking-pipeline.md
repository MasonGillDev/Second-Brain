# Capacity Deal Shape + Booking→Deal Pipeline (Operator ↔ Offtake)

**Project:** SLYD Platform (core + platform + admin)
**Date:** 2026-07-14
**Author:** b13a711e-6622-434c-9082-fba21a5678db

## What Was Done

Built the full trail from a marketplace **Book** action to a closable deal. Previously a booking minted a `BKG-` Compute demand + ops email and dead-ended — no deal could be formed because capacity listings had no owner party, the demand didn't record which listing it targeted, and the deal machine had no Operator↔Offtake shape.

```
LOT DEAL ◄─ SourceDealId ─ CapacityListing ─ OwnerAccountId ─► operator
(hardware)                  │ CommittedRatio
                            ▲ CapacityListingId (per offtake buyer)
                    CAPACITY DEALS { Type=Capacity, Kind: Live|Forward,
                                     Operator ↔ Offtake buyer }
```

### Core (`Slyd-Platform/core`, committed through 9e51a8a/495fd52 + uncommitted follow-ups)
- `Deal`: `DealType Type` {Unknown=0, Hardware, ThreeSided, Capacity}, `CapacityDealKind? CapacityKind` {Unknown=0, Live, Forward} (stamped at formation from `OnlineAt <= now`, not derived later), `Guid? CapacityListingId` + nav, `int GpuCount` (denormalized booked qty — powers gate + bump without loading the demand). Enums int-persisted, append-only.
- `CapacityListing`: `OwnerAccountId` (the operator party) + `SourceDealId` (trail back to the lot deal).
- `Demand`: `CapacityListingId` + `TermMonths` stamped at booking.
- EF: all new FKs explicit `.WithMany()` + SetNull + indexed. **Critical catch:** the two Deal↔CapacityListing reference navs pair into a bogus unique 1:1 by convention — needed `HasIndex(e => e.CapacityListingId).IsUnique(false)` or only one capacity deal per listing would ever be allowed. Migration `20260710150646_AddCapacityDealShape` (8 additive columns) applied to local SLYD2.
- `BookingDemandService`: guard `gpuCount <= AvailableOf(listing)` where `AvailableOf = floor(GpuCount × (1 − clamp(CommittedRatio,0,1)) + 1e-9)` — the epsilon guards IEEE 754 (100 × 0.10 = 9.999… must be 10).
- `EscrowMath.HoursPerMonth = 720m` (24×30 — matches the four existing razor computations; do NOT introduce 730).
- `AuctionService.CreateWinnerDealAsync` stamps `DealType.Hardware`; DemoSeedJob stamps types + listing owners.

### Platform (`Slyd-Platform/platform`, uncommitted)
- `GatedMarketplaceService.BookListingAsync` plumbs `termMonths`; rows carry `AvailableGpus`; booking capped at available with an honest error.
- `DeploySurfaceService` stamps `OwnerAccountId` at listing creation; my-listings query is owner-id UNION legacy activity-marker ids, deduped.

### Admin (`Slyd-Platform/admin`, uncommitted)
- **`CapacityDealDraftService.FormAsync`** (new): validates demand Open + listing-linked (legacy BKG demands without a link get a "legacy booking" note, no NRE) + buyer present + listing owner set ("set it in Supply → Capacity first") + formation-time availability. Creates `Deal{Type=Capacity, Kind, Operator←listing owner, Offtake←demand buyer, GpuCount←WantQuantity, PromisedDeliveryDate=OnlineAt if Forward}`, attaches demand, audits, notifies both parties best-effort after save.
- **Stage gates** (`DealPipelineFeatures.RequirementsFor`): Capacity branch — Financing needs operator+offtake+value>0; Live needs signed doc + no at-risk escrow + `GpuCount <= AvailableOf(listing)`; missing listing renders as an unmet gate.
- **Escrowed→Live bump**: `CommittedRatio = min(1.0, ratio + (double)GpuCount / listing.GpuCount)` in the same SaveChanges as the stage flip. The Live bump is now the system of record for CommittedRatio; `UpdateCommittedAsync` demoted to a correction tool (UI hint added).
- Demand Book drawer: "Booked capacity" block + inline "Form capacity deal" (Value pre-filled with `EscrowMath.ContractValue(gpuCount × 720, term, rate)` estimate, ops-editable). SupplyOps: owner picker, "From lot deal" dropdown, owner backfill. Pipeline: shape badges (CAPACITY·LIVE/FWD, 3-SIDED, HARDWARE), listing chip, sourced-capacity section on lot deals, Booked-GPUs edit.

### Locked user decisions
One deal per offtake buyer (listing is the batch) · booking capped at **available** not total · over-commit blocked at the Live gate, not clamped · both parties notified at formation · v1 ops surface = Demand Book drawer only · Value = editable estimate.

### Accepted risks (documented, not built)
No optimistic-concurrency tokens (linear one-way stages, demo scale); no CommittedRatio unwind after Live (manual correction via SupplyOps is the runbook).

Test state: core 519 + matching 311 + platform 49 + admin 136, all green.

## To Do Next
- **Commits pending user sign-off** (repo rule: always ask): core capacity-deal-shape work on top of 130de84; platform (booking wiring + marketplace) and admin (capacity deal feature + user's pre-existing WIP).
- Production ship order: migrate DB out-of-band → tag/publish core NuGet → bump `SLYD.*` PackageReferences in platform + admin → deploy.
- When testing live: restart both apps (stale-binary lesson), set owners on CAP-2026-0001/0002 via SupplyOps; legacy BKG demands show "legacy booking".
- Deferred idea: three-tier capacity matching (live > forward capacity > forward lots) — user chose manual ops for v1, "then iterate".
