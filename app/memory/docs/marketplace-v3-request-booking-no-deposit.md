# Marketplace-v3: Place Deposit → Request Booking (no deposit anywhere)

**Project:** SLYD Platform (platform + core)
**Date:** 2026-07-14
**Author:** d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15

## What Was Done

Removed the "Place Deposit" flow from the signed-in marketplace board (`/marketplace-v3`, `GatedMarketplace.razor`) and replaced it with deposit-free demand creation. No form on this page submits a deposit value anymore.

**Product decision (Mason):** hardware spot lots file a **reserve demand (RSV-)**; Offtake Forward lots file a **booking demand (BKG-)**. Forward lots are hardware today, but once they deploy and come online they become forward capacity — at that point ops links the new CapacityListing to the booking demand. Key enabler: `Demand.CapacityListingId` is a nullable FK, explicitly documented as "demand stays Open in the pool and keeps matching" when null, so a booking demand can be created *before* the capacity exists.

### Changes

**core repo:**
- `SLYD.Infrastructure/Features/DealOS/IBookingDemandService.cs` + `BookingDemandService.cs` — new `AddForwardLotBookingDemandAsync(db, lotId, buyerAccountId, at)`. Mirrors `AddReserveDemandAsync` but stamps `Source=Booking`, `Type=Compute`, `Category=Gpu`, seeds `WantGpuModel`/`WantQuantity`/`IsoCode` from the lot, `CapacityListingId=null`, `TermMonths=null`, reuses the `BKG-{year}-{seq:D4}` sequence. Guard: lot must be a **forward GPU lot** (`Category==Gpu && State ∈ {Reserved, Allocated}`) — the same widened state filter as the forward board feed, NOT `Listed` (that's the spot/reserve guard).

**platform repo:**
- `Services/GatedMarketplaceService.cs` — new `RequestForwardBookingAsync(lotId, note)` + `GatedForwardBookingResult` record. Mirrors `BookListingAsync`: `[BOOKING REQUEST]` Activity (so it appears in MyBookings), staged BKG demand, atomic SaveChanges, best-effort `OpsSubmissionEvent` (Kind `ForwardLotBookingRequested`). `PlaceDepositAsync` **kept** in the service (public controller mirror / MyDeals deposits list still use LotDeposits) — it's just no longer reachable from marketplace-v3.
- `Components/Pages/DealOS/GatedMarketplace.razor` —
  - Forward-lot cards: "Place Deposit" → "Request Booking" → new simple drawer (lot summary + optional ops note only), submits `RequestForwardBookingAsync`.
  - Hardware GPU spot cards: "Place Deposit" → "Request Booking" → opens the existing lot-detail drawer; its footer button reads "Request booking →" for GPU (still "Request reserve →" for non-GPU), both submit the existing `Lots.RequestReserveAsync` → RSV- demand.
  - Deleted: deposit drawer (amount/name/email/phone/wire-instructions panel), `DepositTarget`, `_depositAmount` & friends, `_wire`, `DepositProjectedFraction`, `OpenDeposit`×3, `OpenDepositFromDetail`, "Place deposit instead" ghost button, subscription-closed footer state. `DrawerMode.Deposit` → `DrawerMode.ForwardBooking`.
  - Copy updated: header comment, Forward Lots subtitle ("request a booking, hold your place before it ships"), hw-note, "Opens with first deposit" → "Opens with first booking".
  - Subscription momentum bar kept — it renders historical LotDeposit pledges honestly; no new deposits accrue from this page.

Both repos build with 0 errors.

## Notes (non-blocking, by design)
- Ops-side linking of capacity to open BKG demands: **built later the same day** — see [demand-to-capacity-matching-pass](demand-to-capacity-matching-pass.md) (Match Engine "Link" action).
- Buyer refinement of count/term deferred until the lot is live — explicit product call by Mason ("simple for now").
- Wire-deposit machinery elsewhere (public `PlaceDeposit` endpoint, MyDeals deposit rows, unused `.wire-panel` CSS) intentionally left in place — only marketplace-v3 stopped using it.
