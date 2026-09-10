# Provider Server Pricing — Card vs Deploy Modal Discrepancy ($1.50 vs $12.00)

**Project:** SLYD Platform (Platform.WebUI)
**Date:** 2026-07-14
**Author:** 6155554b-60a3-4d4e-ab5d-0d421e340c8e

## What Was Done

### Symptom
On production, a Tier 1 compute marketplace card ("1x NVIDIA H100 PCIe", Oldenburg) showed
**$1.50/hour**, but clicking **Deploy Server** opened the deploy modal showing an estimated
**$12.00/hr**. Same server, two different prices.

### Root Cause
`ProviderServerPricing` is an **append-only price history**. `ProviderServerRepository.SetProviderServerPricing`
only ever `AddAsync`es a new row — it never updates the existing one — so each server accumulates
multiple pricing rows over time (e.g. an old $12.00 row and a newer $1.50 row after a price drop).

The two surfaces selected **different rows** from that history:

- **Card (correct):** `MarketplaceListingMapper.MapServerToListing` (core, line 24) uses
  `ProviderServerPricing.OrderByDescending(p => p.CreatedAt).FirstOrDefault()` → the **newest** price = $1.50.
- **Deploy modal (buggy):** `RentComputeModal.EstimatedCost` used
  `selectedServer.ProviderServerPricing.First()` with **no ordering**. EF's `.Include(x => x.ProviderServerPricing)`
  in `ProviderServerRepository.GetProviderServer` has no `OrderBy`, so `.First()` returned an arbitrary
  (in practice oldest/physical-first) row = the stale $12.00.

Confirmed the modal value was exactly $12.00: the modal's "Minimum required balance (10 min)" showed
$2.00, and `MinimumRequiredBalance = EstimatedCost / 6` → 12.00 / 6 = 2.00. Also $12.00 ≠ the modal's
hardcoded `2.50m` fallback, so it was a genuine DB row.

Note: the exact production server (H100, 128 GB, those prices) is **not present in any local DB**
(active DB per `launchSettings.json` is `SLYD2`, whose `ProviderServerPricing` only holds 0.01/0.1/1
and has no H100 / 128 GB server). The bug was diagnosed from the code + the append-only-history
mechanism, not by reproducing the exact rows locally.

### Fix
Changed each price-read site to select the newest row by `CreatedAt`, matching the mapper's existing
convention. Chose read-site fixes (pure in-memory LINQ) over a repository `Include`-ordering fix because
the App Marketplace's `SelectedServer` comes from `ServerMatchingService`, not the repository, so a
repo-only fix would not cover every load path. Read-site ordering is guaranteed correct regardless of
how the server entity was loaded. (EF Core 10 is in use, so ordered includes are available if a
systemic fix is preferred later.)

Pattern applied everywhere: `.ProviderServerPricing.First()` → `.ProviderServerPricing.OrderByDescending(p => p.CreatedAt).First()`

5 deploy/billing-critical sites fixed (all in `platform/src/Platform.WebUI`):

1. `ComputeMarketplaceElements/RentComputeModal.razor:710` — compute deploy `EstimatedCost` (**the reported bug**)
2. `ComputeMarketplaceElements/RentComputeModal.razor:1036` — compute existing-instances wallet check
3. `AppMarketplaceElements/AppDeploymentModal.razor:553` — App Marketplace deploy `EstimatedCost` (**same bug, copy of the compute one**)
4. `AppMarketplaceElements/AppDeploymentModal.razor:721` — App Marketplace existing-instances wallet check
5. `ComputeMarketplaceElements/CapacityDeploymentModal.razor:730` — existing-instances wallet check (shared calc)

WebUI builds clean (0 errors). Not committed — repo rule is to ask before committing/pushing, and
network operations (push/PR) are human-only per platform CLAUDE.md.

---

## Update 2026-08-03 — display/sort sweep completed via a shared helper

**Author:** fdc3226f-77ce-4366-9023-007ba5ad0235
**Directory:** /Users/masongill/Slyd-Platform/admin (edits in `core/` and `platform/`)

The remaining display/sort sites were swept. The count was **20**, not ~15 — the earlier estimate
undercounted. All line numbers in the original list were still exact three weeks on.

### Chose a helper over repeating the one-liner

The expression was heading for ~26 copies (20 unswept + 5 already fixed + the mapper). Added
`core/src/SLYD.Domain/Models/Provider/ProviderServerPricingExtensions.cs`, in the same namespace as
`ProviderServer` (`SLYD.Domain.Models.ProviderModels`):

```csharp
public static ProviderServerPricing? LatestPricing(this ProviderServer? server) =>
    server?.ProviderServerPricing?.MaxBy(p => p.CreatedAt);

public static decimal? LatestPricePerHour(this ProviderServer? server) =>
    server.LatestPricing()?.PricePerHour;
```

`MaxBy` over `OrderByDescending().First()`: same result (both return the first-encountered max on
ties), O(n) instead of O(n log n), and it reads as the intent. Accepts a null server because most
call sites were already null-tolerant. Works off the loaded collection, so it is correct regardless
of load path.

5 unit tests in `core/tests/SLYD.Core.Tests/Domain/Provider/ProviderServerPricingExtensionsTests.cs`
pin the contract — notably that the answer does not change when the collection is ordered
newest-first vs oldest-first. This is the first regression coverage this behaviour has had.

### Two corrections to the original analysis

**1. The systemic-alternative caveat was wrong.** The note said a repository `Include` fix "does not
cover `ServerMatchingService`-loaded servers." It would have: `ServerMatchingService:37` →
`ProviderServerFeatures.GetAllProviderServers():51` → `ProviderServerRepository
.GetAvailableProvisionedServersAsync():349`, which carries the pricing include at line 365. All 7
includes in that repository cover the load paths that actually populate pricing. The repo fix was
still declined, but for the better reason: it makes correctness invisible at the point of use — a
reader at `.First()` cannot see a distant `Include` making it safe — and silently stops protecting
anything loaded outside those 7 methods.

**2. Neither "possibly billing-relevant" site charges money.** Traced both:
`CustomerInstanceFeatures.cs:1242` populates `PastRentalServer.HourlyRate`, consumed only by
`DashboardPastRentalsPanel.razor:125`; `InstanceDetails.razor:1622` sets `hourlyRate`, rendered only
at lines 201–213. All 20 sites were display/sort.

### InstanceDetails had a deeper bug than ordering

`InstanceRental` carries `PricePerHour` — the rate is **snapshotted at rental creation**
(`CustomerInstanceFeatures.cs:239-255`), and a later provider price change does not move it. So the
instance details page was showing the server's *current advertised* price on a *running* instance —
a number the customer may not be paying. Applying the mechanical fix alone would only have changed
which wrong row it read.

Rewrote it to read `InstanceRental.PricePerHour` for the running rental, falling back to the
server's current price when there is no rental or the rental predates locked pricing (the column is
nullable). **The locked rate is already resource-share-adjusted** for custom instances
(`CustomerInstanceFeatures.cs:247`), so the `ResourceShareRatio` multiply is deliberately *not*
re-applied on that path — doing so would have squared the ratio.

Did not use `IInstanceRentalRepository.GetRentalAsync(instanceId)`: it is itself an unordered
`.FirstOrDefault()` over an instance's rentals (`InstanceRentalRepository.cs:73-80`) — the same
class of bug — and an instance can be rented more than once. Queried `DbContext.InstanceRentals`
directly (already injected on the page) ordered by `StartDateTime` descending. **That repository
method is still unfixed** and is billing-adjacent; see To Do.

### Deliberately not touched

- `ProviderView/RentalHistory.razor:1126` — the only site on the list that feeds gross revenue,
  commission, and net revenue. Its primary path uses the actual billing record; this rate is the
  fallback when none exists. Held back on the explicit instruction not to touch billing-related code.
  Still shows a stale rate in that fallback.
- `AppMarketplaceElements/ServerCardBak.razor:97` — dead backup, as originally noted.
- The 5 already-fixed deploy/wallet sites — correct already, and billing-critical.
- The 5 remaining correct-but-verbose `OrderByDescending(...).FirstOrDefault()` sites
  (`CustomerInstanceFeatures.cs:240,636`, `MarketplaceListingMapper.cs:24`, `MarketplaceService.cs:190`,
  `ProviderRevenueController.cs:501`) — not converted to the helper, to keep the diff to actual fixes.

### Verification

Core: builds clean, **587 tests pass**. Platform.WebUI: full rebuild clean (0 errors).
Platform.WebUI.Tests has **6 pre-existing failures** (`AccountResolverTests`, `MarketplaceIntakeTests`,
`AuthPipelineTests`) — confirmed pre-existing by stashing the sweep and re-running to an identical
6-failure baseline, then restoring. They relate to the reverted anonymous-intake rate-limiting work,
not to pricing.

Not committed. Both repos carry unrelated uncommitted work on `feat/crm-accounts-quote-builder`;
these changes are separable from it.

## To Do Next

- **`ProviderView/RentalHistory.razor:1126`** — decide whether the revenue-fallback rate should be
  swept. It is the last live unordered read.
- **`InstanceRentalRepository.GetRentalAsync():73-80`** — unordered `.FirstOrDefault()` over an
  instance's rentals. Returns an arbitrary rental for any instance rented more than once. Not
  touched here because it is billing-adjacent and used by other callers; worth auditing those
  callers before changing it.
- Optional: convert the 5 correct-but-verbose sites to `LatestPricing()` so the raw expression stops
  being available to copy-paste.
