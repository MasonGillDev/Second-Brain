# Demand ↔ CapacityListing matching pass (bookings rank against live/forward capacity)

**Project:** SLYD core + admin
**Date:** 2026-07-14
**Author:** d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

### Update (same day): "Link" action added
Ops can now bind a booking to the viewed listing directly from the capacity table:
- **`BookingLinkService`** (`admin/src/Admin.Application/Features/Matching/`, + `IBookingLinkService`, `BookingLinkResult`, DI registration) — sets `Demand.CapacityListingId`. Guards: authenticated admin, Compute demand, Open/ReVerify state, not already linked (same listing → "already linked", different listing → conflict error), listing Approved. Writes an append-only `AuditEvent` (`demand.capacity-linked`, before `{capacityListingId: null}` → after with listing ref/site) via `IAuditEventWriter`, following the `ProposalDraftService` pattern. Deliberately does NOT touch demand state or `CommittedRatio` — linking is a routing decision; deal formation still goes through Assemble.
- **`MatchEngine.razor`** — capacity-mode rows get a **Link** button (hidden on `BookedOnThisListing` rows); success re-scores the listing so the row re-renders with its BOOKED HERE chip; guard failures surface in a new dismissible error banner (mirrors Pipeline.razor's). `_linkingDemandId` disables all Link buttons while a write is in flight.
- Because the link is a `Demand` update through `SlydDbContext`, the `EntityChangedHandler` interceptor enqueues a targeted match refresh automatically — the demand's precomputed candidates rebuild and its DemandToCapacity pass is skipped now that it's linked.
- Admin tests: 142/142 pass; solution builds 0 errors.

This completes the forward-lot story: **book (BKG-, no capacity) → rank on match-engine → link when the lot comes online as capacity → Assemble.**

---

The matching engine only scored Demand↔Lot; `CapacityListing` never participated. Added a new **capacity pass** so booking demands (Compute, `CapacityListingId == null` — e.g. the new forward-lot BKG- bookings) match against **Approved capacity listings, live or forward**, surfaced on the admin **/v3/deal-flow/match-engine** page.

**Product calls (Mason):**
- **No hard exclusions** for this pass beyond closed demands / zero qty / same-party — "show all bookings, just ranked best to worst." Model mismatch and low quantity fit score low instead of being dropped (deliberately looser than the lot pass's §3.3 filters).
- Weights reuse `MatchingConstants` verbatim; **GpuGrade skipped** (capacity has no grade — spec precedent §4.3 where assembly pairs swap dimension sets). Max attainable total: 90.

### Core (`SLYD.Matching`)
- Six new scorers (`Scoring/Scorers/Capacity*.cs`), all `IDimensionScorer<CapacityListing, Demand>`, same persisted dimension keys as the lot pass ("GpuModel", "Region", …):
  - `CapacityModelScorer` — strict GPU equality +30 / else 0, no exclusion
  - `CapacityQuantityScorer` — fit vs **available** GPUs via `BookingDemandService.AvailableOf` (uncommitted, epsilon-floored)
  - `CapacityRegionScorer` — Site lat/lon → Site ISO/Region centroid fallback; same mile bands
  - `CapacityUrgencyScorer` — ready = live now or `OnlineAt <= NeedByDate`; same urgency bands
  - `CapacityDeliveryWindowScorer` — live or online-by-need-by = +10; ≤14d late = +6; else 0; forward with no need-by = +6
  - `CapacityPriceScorer` — 0 pts, explanation compares `RatePerGpuHour` vs ceiling
- `IMatchScoringService`/`MatchScoringService`: `ScoreCapacityAgainstDemands`, `ScoreDemandAgainstCapacity`, `ScoreCapacityPair`, private `IsCapacityExcluded` (Approved-only, closed demands, qty ≤ 0, same-party). Ctor takes the six new scorers — **every test factory constructing `MatchScoringService` directly needed updating** (4 in core tests, 2 in admin tests, 1 in platform tests).
- `MatchRefreshJob.RefreshDemandCandidatesAsync`: for Compute demands with null `CapacityListingId`, also writes `MatchCandidate` rows with `MatchKind = "DemandToCapacity"`, `CounterpartyType = "CapacityListing"` (top 20; existing wipe-per-demand covers cleanup). Demands linked to a listing are skipped — they know their capacity.
- DI: six scorer singletons registered in `AddSlydMatching`.

### Admin
- Models: `CapacityPickerItem`, `CapacityEngineView`, and `DemandCandidateView.BookedOnThisListing`.
- `IMatchingEngineFeatures`/`MatchingEngineFeatures`: `GetMatchableCapacityAsync` (Approved, live+forward) and `GetCapacityEngineViewAsync` — loads Compute demands (unlinked **plus** those booked on this very listing, flagged `BookedOnThisListing`), scores with `int.MaxValue` (full visibility like the lot view).
- `MatchEngine.razor`: second picker section "Or choose capacity · live & forward" (typeahead + demo quick-picks), capacity summary card, one candidate table "Bookings · compute demand" reusing `RenderCandidateTable` (now parameterized `allowPropose` — capacity rows get **no Propose button**; proposal drafts are lot-based, capacity deals form through Assemble). New "BOOKED HERE" chip when the demand is already linked to the viewed listing. Lot and capacity selection are mutually exclusive.

**Tests:** core 311 pass, admin match tests 40 pass, platform match tests 16 pass. All three solutions build 0 errors.

## Notes (non-blocking enhancements, feature is complete)
- `EntityChangedHandler` doesn't invalidate on CapacityListing changes — new/edited listings enter precomputed candidates on the 15-min `RefreshAll` sweep; the match-engine page scores live so it's always current.
- No dedicated unit tests for the six capacity scorers or `BookingLinkService` (all existing suites pass; scorers mirror the tested lot-scorer shapes).
- The demand-book drawer (`DemandBookFeatures`) reads only `CounterpartyType == "Lot"` — capacity candidates could surface there too someday.
- No "unlink" action — a mislinked booking needs a manual fix. Enhancement, not a blocker.
- Spec (`SLYD_Matching_Engine_Architecture.md`) could gain a capacity-pass addendum section.
