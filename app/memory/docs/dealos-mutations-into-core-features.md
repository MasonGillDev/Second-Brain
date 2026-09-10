# DealOS mutations moved into core Application features (CapacityListing + LotDeposit)

**Project:** SLYD Platform
**Date:** 2026-07-16
**Author:** 8b33f0d9-476b-468b-a373-ed8e56d7f106
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Context: audited the platform for surfaces that write DealOS domain entities directly against `SlydDbContext` instead of going through core. Two mutation flows were the worst offenders and got fixed this session (clean-architecture, "properly build the feature"):

1. `DeploySurfaceService.ListSpareCapacityAsync` — built a `CapacityListing` + ownership `Activity` inline, including the operator/Verified gates, field validation, and the `CAP-` id sequence.
2. `GatedMarketplaceService.PlaceDepositAsync` — built a `LotDeposit` + `Activity` inline, including the lot-state gate and the subscription-close gate.

### The established pattern (important)
Core already had two sibling services for exactly this class of operation — `IBookingDemandService` and `IReserveDemandService` in `core/src/SLYD.Infrastructure/Features/DealOS/`. Convention: the service **operates on a caller-owned `SlydDbContext`**, stages the domain mutation (`db.X.Add(...)`) with all business rules + id sequencing, and returns the staged entity. It does **NOT** call `SaveChanges` — the platform caller owns the transaction so the core insert commits atomically with the surface's own `Activity` marker + ops notification. I followed this pattern rather than making self-contained services, because it's the codebase idiom and preserves transactional atomicity.

### New core files
- `SLYD.Domain/Services/ForwardSubscriptionMath.cs` — moved the forward-lot subscription math (`CommittedUsd/FractionOf/SparkFractionsOf/IsClosed`) out of the platform (`GatedMarketplaceService`) into Domain, made `public`. It's pure `Lot` business logic and the same `IsClosed` condition now gates both the board read AND the deposit write, so it needed one authoritative home. Platform `GatedMarketplaceService` + `PublicMarketplaceLotController` now `using SLYD.Domain.Services;`.
- `SLYD.Infrastructure/Features/DealOS/ICapacityListingService.cs` + `CapacityListingService.cs` — `AddSpareCapacityListingAsync(db, ownerAccountId, gpuModel, powerKw, gpuCount, onlineAt, ratePerGpuHour, at, ct)`. Owns operator gate (Type==Operator OR Operator deal role), Verified gate, field validation, `CAP-{year}-{seq:D4}` (change-tracker-aware), builds the `PendingReview` listing with `OwnerAccountId`. Returns `AddCapacityListingResult(Listing?, OwnerAccountName?, Error?)` — Error carries the exact user-facing message.
- `SLYD.Infrastructure/Features/DealOS/ILotDepositService.cs` + `LotDepositService.cs` — `AddDepositAsync(db, lotId, accountId?, amountUsd, contact..., at, allowSpotListed, ct)`. Owns amount gate, lot-state gate (`allowSpotListed` widens to include `Listed` spot for the gated path; the anonymous public path passes false), subscription-close gate, `DEP-yyyyMMdd-XXXX` id. Supports both authenticated (accountId) and anonymous (contact-only) callers so the public controller can adopt it too. Returns `AddLotDepositResult(Deposit?, Lot?, AccountName?, Error?)`.

### Wiring / refactors
- Registered both services in `core/src/SLYD.Infrastructure/DependencyInjection.cs` inside `AddDatabase(...)` (next to the demand services; `AddInfrastructure` → `AddDatabase`, called by both WebUI + HangFire).
- `DeploySurfaceService`: injected `ICapacityListingService`; `ListSpareCapacityAsync` now resolves the account, calls core, throws `InvalidOperationException(result.Error)` on failure (preserving the exception contract the Razor form catches), then stages the `[LISTING]` ownership Activity marker + `SaveChanges` + ops notify. `IsDealRoleOperatorAsync` stays (still used by `GetAsync`).
- `GatedMarketplaceService`: injected `ILotDepositService`; `PlaceDepositAsync` calls core (`allowSpotListed: true`), returns `GatedDepositResult.Fail(result.Error)` on failure, then stages the `[DEPOSIT]` Activity + `SaveChanges` + ops notify + wire instructions. Deleted the internal `ForwardSubscriptionMath` (now in Domain).

### Tests
- Updated the two test call-sites for the new ctors: `DeployListingGateTests.NewService()` (adds `new CapacityListingService(...)`), `HardwareSourceMarketplaceTests.NewMarketplaceService()` (adds `new LotDepositService(...)`).
- New `CapacityListingServiceTests` (input validation theory, non-operator, unverified operator, buyer-with-operator-deal-role, happy path CAP-/OwnerAccountId/PendingReview, sequence increments).
- New `LotDepositServiceTests` (zero amount, missing lot, spot-not-allowed vs allowed, closed-by-date, unknown account, happy path DEP-/staged/Pledged, anonymous no-account). Note: `Lot.State` has no setter — seed helper walks the machine `MarkSourced→MarkGraded→Publish(→Listed)→Reserve(→Reserved)` with an AdminUser. Contact fields are preserved verbatim (only blank→null), not trimmed.
- Full suites green: **platform 81/81, core 537/537.**

## To Do Next
- `PublicMarketplaceLotController.PlaceDeposit` still builds a `LotDeposit` inline — it's the second deposit caller. `ILotDepositService.AddDepositAsync` was deliberately designed to support it (nullable accountId + contact, `allowSpotListed: false`). Route it through the service to kill the last rule-drift risk on deposits.
- Remaining audit offenders not touched this session (see the broader audit): HIGH — `ProviderRevenueController` (→ `IProviderFinancialsFeatures`/`IUnifiedBillingService`), `LxdServerStatsJob`, `ServerLocationMap.razor.cs` (DbContext in a Razor component); `AuctionSellerService` should route through the existing `IAuctionService`. Plus DealOS feature gaps for compliance status + intake (`ComplianceService`, `MarketplaceIntakeService`).
