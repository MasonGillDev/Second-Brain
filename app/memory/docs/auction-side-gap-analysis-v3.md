# Auction-Side Gap Analysis — DealOS V3 Sealed-Bid Auctions

**Project:** SLYD Platform (core / platform / admin)
**Date:** 2026-07-14
**Author:** b13a711e-6622-434c-9082-fba21a5678db

## What Was Done

Mapped the entire sealed-bid auction feature (ADR 0008) across the V3 platform and identified where the gaps are. Sources: a fresh Explore-agent sweep of `core` (domain models, `AuctionService`, close job, migrations, tests) cross-checked against the 2026-07-13 DealOS cross-repo audit (`/Users/masongill/Second Brain/memory/docs/2026-07-13-dealos-v3-cross-repo-audit.md`), with the key findings re-verified against the current working tree by grep/read — not just trusted from the audit.

**What's solid:** the sealed-bid core design. Commit-reveal integrity via `AuctionCommitment`, confidentiality matrix enforced in `AuctionService` (not UI), append-only bid versions, fee snapshot at publish, hard close, and a real test suite (placement rules, sealing invariants, close/award/reveal, house-win, reserve/idempotency, bidder/seller receipts, fee-snapshot agreement) in `tests/SLYD.Matching.Tests/Auctions/AuctionServiceTests.cs`.

**Gaps, in priority order:**

1. **Concurrency — double-award risk (verified open today).** `CloseDueAuctionsAsync` runs every minute with no `DisableConcurrentExecution` (grep across core + platform: zero hits) and no concurrency token anywhere in `SlydDbContext`. Overlapping runs both see `Open`, both award → duplicate `SellerPayout` + duplicate `Deal`. Tests cover sequential idempotency only, never interleaving. `core/src/SLYD.Infrastructure/Services/Auctions/AuctionService.cs:229-343`.
2. **No per-auction try/catch in the close loop (verified — zero `try` in AuctionService.cs).** One failing auction aborts the loop. Worse: the ADR-0008 reveal audit event is written *after* `SaveChanges` — if it throws, the auction has left `Open`, is never re-selected, and its reveal never reaches the audit chain. The commit-reveal guarantee silently fails for that auction.
3. **Commitment hash is culture/scale-sensitive (verified unchanged).** `AuctionCommitment.Compute` interpolates `{amountUsd}` with CurrentCulture and raw decimal scale (`core/src/SLYD.Domain/Models/DealOS/AuctionCommitment.cs:18`). Holds only because bids are whole-dollar and Npgsql round-trips scale. Adding `HasPrecision(18,2)` (repo convention, currently missing on all auction money columns) would break verification of every stored commitment. Must canonicalize (`ToString("0.##", InvariantCulture)`) + migration story BEFORE any money-precision hygiene work.
4. **Count-based DisplayId minting** (`COUNT(prefix)+1` for AUC-/PAYOUT- at `AuctionService.cs:454-460, 483-488`) breaks permanently after any hard delete. Live trigger exists: `DemoSeedJob.PurgeAsync` hard-deletes rows. Fix is a shared `MAX(suffix)+1` helper in core (fixes ~12 admin call sites too).
5. **No `Deal.AuctionId` (verified — property doesn't exist).** Ops cockpit links auction→deal via `(BuyerAccountId, Value)` heuristic (`AuctionService.cs:580-587`) — wrong deal on value collisions. Natural add now the deal-shape migration landed.
6. **`"SLYD-RECOVERY"` magic string** decides house-win vs customer-deal at award (`AuctionService.cs:479`).
7. **Verified gate is soft upstream.** Bidding requires `ComplianceStatus == Verified`, but admin can one-click a zero-document account to Verified with no confirm/doc check (`admin/.../ComplianceAdminFeatures.cs:83-99`).
8. **Broker attribution never runs on the auction path** — award creates `SellerPayout` + Deal directly, bypassing `BrokerAttributionService`; broker-sourced submissions put to auction appear to earn no commission. Unconfirmed whether policy or omission.
9. **Admin polish:** `AuctionsAdmin` doesn't handle `Draft` state; mismatch pill unstyled; hard-close time has no TZ marker; Reject/Cancel lacks the repo's two-click confirm.
10. **Test gaps:** no interleaved-close test (failure mode of #1), no audit-write-failure test, no assertion pinning `Type = DealType.Hardware` on the award-created deal, thin coverage on `MarkSettledAsync`/payout reconciliation.

**Key context:** all core fixes ride the same v0.2.10 tag that platform/admin CI pin-bumps are already blocked on (release-blocker from the 2026-07-13 audit §0).

## To Do Next

- Concurrency pair: `[DisableConcurrentExecution]` on the close job + rowversion/xmin token on `Auction`; per-auction try/catch with audit-before-transition ordering; add an interleaved-close test.
- Canonicalize `AuctionCommitment.Compute` (InvariantCulture, fixed scale) with a migration/verification story — before any `HasPrecision` sweep.
- Add `Deal.AuctionId`; replace the `(BuyerAccountId, Value)` heuristic.
- Shared DisplayId minting helper (`MAX(suffix)+1` + retry-on-unique-violation) in core, consumed by auction + admin call sites.
- Decide broker-commission policy for auctioned submissions; wire `BrokerAttributionService` into award if commissions should accrue.
- Admin follow-ups: Draft state handling, TZ marker, two-click confirm on Cancel, doc-presence check before Verified.
