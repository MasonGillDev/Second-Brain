# Lot pricing UI: ask price, not rental rate

**Project:** SLYD Admin (Deal OS)
**Date:** 2026-08-14
**Author:** e503dc75-e0cf-4a94-b311-c18127000c13
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

### The question that started it

Mason asked why a lot has no "price we are selling it at" — was that only decided
when negotiating with the deal's buyer?

The answer turned out to be that the field *exists* and was being spent on the
wrong thing. `Lot.Price` in Core is documented literally as
`/// <summary>Sale price to the buyer.</summary>`
(`core/src/SLYD.Domain/Models/DealOS/Lot.cs:94`), but every admin surface was
projecting it out as `RatePerGpuHour` and labelling it `$/GPU·hr`. So on a lot
being sold outright (B200 × 8) the one sale-price slot held a notional hourly
rental rate, and there was nowhere to record the ask.

The rest of the system already treated it as an outright price — only the
inventory page disagreed:

- `ProposeModal.razor:112` — `_price = Lot.Price ?? 0m` pre-fills the Propose drawer
- `ProposalDraftService.cs:80` — `Value = request.Price * lot.Quantity`
- `DealDetail.razor:596,953` — renders `lot.Price` as `C0`, falling back to "unpriced"

### The basis decision (important)

`Lot.Price` is **per unit**, not a lot total. That is not stated anywhere in the
schema — it is implied by `ProposalDraftService` multiplying by `lot.Quantity`.
All new labels say `$/unit` explicitly and the UI shows the derived lot total
beside the per-unit figure, so the basis is never left to inference again. The
per-unit reading is now written down in the `SetLotPricingRequest` doc comment.

`CostBasis` was relabelled `$/unit` on the same reasoning: margin (ask − cost)
is only meaningful if both sit on the same basis, and the new-lot form's old
`Cost basis $/GPU·hr` label was certainly wrong — the domain calls it "Cost SLYD
paid for this lot". **This is an assumption, not something the schema enforces.**
If any historical rows were entered as lot totals, their margin now reads wrong.

### Changes (admin-only — no Core change, no migration)

DTO rename `RatePerGpuHour` → `PricePerUnit`:
- `Admin.Application/Models/DealOS/InventoryLotModels.cs` — `LotListRow`, `LotDetailView`, `NewLotRequest`
- `Admin.Application/Models/DealOS/SubmissionModels.cs` — `ConvertToLotRequest`
- `InventoryLotFeatures.cs`, `SubmissionFeatures.cs` — the two `Price = request.…` mappings

UI (`Components/Pages/V3/Supply/InventoryLots.razor` + `.css`):
- table column `$/GPU·hr` → `Ask $/unit`, plus a new derived **Lot total** column
- drawer tile "Rate … /GPU·hr" → "Ask … /unit · $N lot", with a tooltip saying the
  final number is negotiated on the deal
- pricing panel labels → `Ask $/unit` / `New-OEM equivalent $/unit` / `Cost basis $/unit`
- new derived row under the pricing inputs: **lot total** and **margin**
  ($/unit and %), turning red when negative — so ops sets an ask with the spread
  on screen instead of from memory
- money formats `0.00` → `N0` throughout (cents are noise at GPU prices)
- `Components/Pages/V3/Intake/Submissions.razor` — same relabel on convert-to-lot

The pricing panel previously had a `Category == Gpu ? "Sale rate $/GPU·hr" :
"Sale price $/unit"` ternary — i.e. non-GPU lots were *already* labelled as an
outright per-unit price. The rental framing was GPU-only cosmetics; it is gone.

### Why UI-only was the right call

Mason explicitly did not want a rental price. Adding a real
`RatePerGpuHour` column to Core would be the alternative (keeping both concepts),
but nothing wanted the rental number, so the cheap correct fix was to stop
mislabelling the column that already means "sale price". `CapacityListing`
already owns the genuine $/GPU·hr rental concept for capacity deals — untouched.

### Verification

`dotnet build src/Admin.sln` — 0 errors (141 pre-existing warnings, none in
touched files). `dotnet test tests/Admin.Tests` — **284/284 pass**. One named
argument fixed in `LotCatalogLinkTests.cs:90`.

Not verified in a running browser — the change is labels plus two derived
read-only values, and no test renders this page.

## To Do Next

- **Confirm the cost-basis basis.** If existing lots recorded `CostBasis` as a
  lot total rather than per unit, the new margin readout is wrong for those rows.
  Worth an eyeball over the lot table before trusting the margin figure.
- `MarketplaceListing` has `Price` / `Cogs` / `SalePrice` but **no `LotId` FK** —
  storefront pricing and the lot book are still unconnected, so a listed lot's
  public price cannot be derived from the lot.
- `DealWorkspaceFeatures.cs:727` sets `deal.Value` from the sum of selected
  *supplier* quote amounts — a cost-side number used as deal value. May be
  intentional (pass-through + fee) but it is worth a deliberate decision.
