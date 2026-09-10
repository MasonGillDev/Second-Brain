# Capacity Listing Archive / Restore

**Project:** SLYD Platform (core + admin + platform)
**Date:** 2026-08-20
**Author:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Ops had no way to take a capacity listing off the marketplace board. The only
lifecycle actions were Approve/Reject, and both were gated to `PendingReview` by
`CapacityListing.Transition()` — so an already-Approved listing was stuck on the
board permanently. The workaround was setting committed% to 100, which hides
demand but leaves the listing visible.

Added an `Archived` state with a reversible transition.

### Design decisions

- **`Archived = 3`, appended.** State persists as `int` (no `HasConversion` in
  `SlydDbContext`), so the enum value alone needed no migration.
- **Reachable from any state** (Approved / PendingReview / Rejected). Unlike
  Approve/Reject there is no single legal source, so `Archive()` does not reuse
  the private `Transition()` helper.
- **Reversible via a `PreArchiveState` stash.** This is the non-obvious bit: with
  archive-from-any-state, a naive `Unarchive → Approved` would let ops archive a
  PendingReview listing and restore it straight onto the board, silently bypassing
  review. Storing the source state and restoring to it closes that hole. Fallback
  is `PendingReview` (fail-closed) for rows with an empty stash.
  **This stash is the only reason a migration was needed** —
  `20260820140832_CapacityListingArchive`, one nullable int column.
- **Attached capacity deals warn but do not block** (ops call). A dead-but-
  undeleted deal shouldn't strand a listing on the board. The deal count rides on
  the audit entry and shows in the confirm step.
- **No hard delete.** Everything stays on the audit hash chain.

### Blast radius was small by construction

Every marketplace/booking read already gated on `== CapacityListingState.Approved`
(`BookingDemandService`, `MatchRefreshJob`, `MatchScoringService`,
`GatedMarketplaceService`, `MatchingEngineFeatures`, `BookingLinkService`), so a
new state is excluded from the board without touching any of them.

Two real gaps found and fixed:

1. **`CapacityDealDraftService`** had no state gate. It reaches a listing via
   `demand.CapacityListingId`, and `BookingLinkService` only checks `Approved` at
   *link* time — a listing archived afterward could still form a deal. Added the
   re-check at formation.
2. **`Deploy.razor`** (operator-facing) chipped state as
   `if Approved / else if PendingReview / else → REJECTED`, so an archived listing
   would have shown the operator "REJECTED". Added an explicit branch, a muted
   chip style, the archived tally, and extended the ops-note block to archived.

### Known non-fix

`MatchCandidate` rows computed before an archive linger until that demand's next
refresh. They're already filtered on read (`MatchingEngineFeatures` returns null
for non-Approved), so this is cosmetic staleness, not a correctness bug. Left
alone deliberately rather than adding an archive→match-invalidation hook.

### Files

**core** — `SLYD.Domain/Models/DealOS/CapacityListing.cs` (state, stash,
`Archive`/`Unarchive`), migration `20260820140832_CapacityListingArchive`,
new `tests/SLYD.Core.Tests/Domain/DealOS/CapacityListingStateMachineTests.cs`.

**admin** — `ISupplyOpsFeatures` + `SupplyOpsFeatures`
(`ArchiveListingAsync`/`UnarchiveListingAsync`, audit `listing.archived` /
`listing.unarchived`, owner notice only when the listing was actually on the
board, `archivedOnly` list flag with archived excluded from every KPI count),
`SupplyOpsModels` (`CapacityDealCount`, `PreArchiveState`, `ArchivedCount`),
`CapacityDealDraftService` gate, `CapacityListings.razor` + `.css`.

**platform** — `Deploy.razor` + `.css`.

### Verification

- core: 670 passed
- admin: 353 passed
- platform: Platform.Tests 11, Platform.WebUI.Tests 166 passed

Four pre-existing `CapacityDealDraftServiceTests` failed against the new gate —
their fixture seeded a booking against a listing left at the `PendingReview`
default, a state the real system cannot produce (the link path requires
Approved). Fixed the fixture to approve, rather than weakening the gate.

## To Do Next

- Not committed or pushed. Ship order matters: core is consumed as a NuGet
  package (`UseLocalCore=true` locally), so core PR → release → bump
  `SLYD.Infrastructure` in `admin/src/Admin/Admin.csproj` and platform's csproj →
  deploy. The migration is additive and nullable, so deploy order between admin
  and platform doesn't matter.
- Admin tests run on the EF InMemory provider, so a green suite doesn't prove
  Postgres translation. The only new server-side query is the `Deals` GroupBy for
  deal counts in `ListListingsAsync` (all state filtering happens in memory after
  `ToListAsync`). Worth a sanity check against a real database before shipping.
