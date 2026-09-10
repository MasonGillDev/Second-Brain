# SiteSubmission → Site Conversion (Phase 0)

**Project:** SLYD Platform (admin)
**Date:** 2026-08-20
**Author:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Built the deferred `SiteSubmission` → `Site` conversion. This is Phase 0 of a
larger plan to add public capacity intake (`CapacitySubmission`), and it went
first because of a finding that reordered everything:

**No production code creates a `Site`.** The only `new Site` constructions in
the whole solution were `DemoSeedJob` (demo data) and a transient, never-persisted
one in `PublicV3IntakeController.PowerOpportunityPreview`. `ISiteIntakeFeatures`
exposes only `ListAsync` / `GetAsync` / `UpdateAvailableKwAsync` — no create. So
every real site in the database was seeded or hand-inserted, and conversion is
now the only production path that makes one.

That made it a hard prerequisite: the planned `CapacitySubmission` conversion
must resolve-or-create a `Site` (a capacity listing with no `Site` scores 0 on
region forever — see `CapacityRegionScorer`'s own doc comment), and no code
existed that could.

### Why conversion is a DD form, not a button

The public form captures twelve stated fields; `Site` needs several the form
never asks for. Ops must supply: `Name` (non-nullable, no form field),
`Latitude`/`Longitude` (required for distance scoring), `Kw` nameplate (the
submission states only *available* kW — a different number), `VoltageClass`,
and `RequiredCapabilities`. `SiteType` is guessed from the free-text `Source`
and confirmed by ops.

Eight stated fields have **no home on `Site` at all**: `CostPerMwh`,
`TermMonths`, `Structure`, `Water`, `Fiber`, `Commercial`, `MoveInWindow`,
`Notes`. They stay on the submission permanently as the provenance record,
linked by `ConvertedSiteId`. This is the stated-vs-verified stance
`BrokerOpsFeatures` already takes with `Lot.BrokerEstimateUsd` ("ops-set Price
/ CostBasis remain authoritative; this preserves the broker's original claim as
a separate fact"). There's a test asserting those eight survive.

### Key decisions

- **`ConvertAsync` lives on `ISiteSubmissionBookFeatures`**, not on the Sites
  Registry, matching `BrokerOpsFeatures` where `MarkConverted` is called. The
  audit event is submission-scoped (`site-submission.converted`).
- **0,0 coordinates are rejected outright.** It's the default-struct value and
  a plausible-looking one; a site silently placed in the Gulf of Guinea would
  score wrong distances against every demand forever rather than failing loudly.
  Also range-checked (-90..90, -180..180).
- **`AvailableKw > Kw` is rejected** — available can't exceed nameplate.
- **Ownership carries over from the claim.** An unclaimed submission converts to
  an unowned `Site`; ops sets the owner later, same as the capacity-listing
  owner backfill. Not a blocker, since most intake is unclaimed.
- **`SiteSourceTypeMap` is a suggestion, never an authority.** Unrecognised
  sources land on `SiteType.Unknown` rather than guessing — an ops user picking
  the right type is cheap, a silently mistyped site is not.
- `MarkConverted` already existed on the entity (guarded to Submitted/InReview)
  and was dead code. It's now called.

### Files

- `Admin.Application/Models/DealOS/SiteSubmissionBookModels.cs` —
  `SiteConversionRequest`, `SiteConversionResult`
- `Admin.Application/Interfaces/Features/DealOS/ISiteSubmissionBookFeatures.cs` —
  `ConvertAsync`; removed the "conversion is deferred" note
- `Admin.Application/Features/DealOS/SiteSubmissionBookFeatures.cs` —
  implementation, `SITE-{year}-{nnnn}` display id off a counter query
- `Admin.Application/Features/DealOS/SiteSourceTypeMap.cs` — new
- `Admin/Components/Pages/V3/Intake/SiteSubmissionsIntake.razor` (+ `.css`) —
  convert panel, prefilled; Converted status now links to `/v3/sites`
- `tests/Admin.Tests/Features/V3/Intake/SiteSubmissionConversionTests.cs` — new,
  24 tests

No migration and no core change — `SiteSubmission` and `Site` both already had
every column needed. Ships independently of the core-release/version-bump path.

### Verification

Admin suite: 377 passed, 0 failed.

## To Do Next

Not committed or pushed.

Remaining phases of the capacity-intake plan, in order:

1. **`CapacitySubmission` data structures** — entity mirroring `SiteSubmission`
   (stated block + claim-token block + `ConvertedCapacityListingId` + audit),
   `CapacitySubmissionStatus` state machine, EF config with the filtered unique
   `ClaimToken` index, migration, `ICapacitySubmissionRepository`.
   **Blocked on Mason confirming the STATED field list** — proposed eleven
   (GpuModel, GpuCount, PowerKw, Region, Availability, OnlineAt,
   AskRatePerGpuHour, TermMonths, CommittedRatio, Hosting, Notes), with
   `NetworkFabric` a plausible twelfth.
2. **Public endpoint** `api/marketplace/capacity/submit` in
   `PublicV3IntakeController`, with a parallel `FormSubmission` under a new
   `FormTypes.CapacityIntake` carrying a `capacitySubmissionRef` field.
3. **Website form** + `/capacity/claim/{token}` mirroring `SiteClaim.razor`.
4. **Admin queue + conversion** — reuses this phase's Site creation; mints the
   `CapacityListing` as `PendingReview`, NOT Approved (unlike
   `CreateListingAsync`, where ops-creation is self-approval). That's what gives
   "reviewed but not public" with no new `CapacityListingState`.
5. **Spam cleanup** — `IntakeCleanupFeatures` keys off `<entity>Ref` fields on
   `FormSubmission`; add `capacitySubmissionRef`, a `CapacitySubmissionIds` set,
   the `RemoveRange`, and those ids to `AlertTargetIds`.
6. Tests.

Then the separate **Need Compute** work (agreed to follow this):
- `/need` gets a HARDWARE/COMPUTE toggle; the `own`/`rent`/`open` consumption
  selector is **dropped entirely** (Mason's call), which requires rewriting the
  FAQ, structured data, and "three consumption paths" section on `Need.razor`.
- `PublicV3IntakeController.SubmitNeed` hardcodes `Type = DemandType.Hardware`
  — thread the mode through `NeedSubmitRequest`. **Live bug:** every "Rent
  capacity" submission to date is a Hardware demand, and `MatchRefreshJob` only
  ranks `DemandType.Compute` against capacity listings, so they structurally
  cannot match.
- `GatedMarketplace.razor:99` "Request hardware" is tab-independent
  (`OpenPostNeed` sets `_needHardware = false`, never reads `_tab`), and
  `MarketplaceIntakeService.cs:222` hardcodes Hardware. Make both follow the tab.

Also unshipped from earlier today: the CapacityListing archive/restore work
(core + admin + platform) — see [capacity-listing-archive-state.md](capacity-listing-archive-state.md).

Optional gap noted but not built: `SitesRegistry` still has no standalone
"New Site" action. After this change, conversion is the only way to create one —
fine if every site originates from intake, a gap if ops needs to add one directly.
