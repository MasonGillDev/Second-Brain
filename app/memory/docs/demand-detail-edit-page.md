# Demand Detail + Edit Page (`/demands/{id}`)

**Project:** SLYD Platform
**Date:** 2026-08-04
**Author:** 951270e3-cd9c-4187-b234-c353501d807d
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Built the buy-side counterpart to `/sell/submissions/{id}`. On `/v3/dashboard` the "My Demands"
rows were non-clickable `<div class="deal-row deal-row--static">` with the comment *"Non-clickable
until the /demands/{id} detail page lands."* That page now exists, and NEED-sourced rows link to it.

Spans two repos (`core` + `platform`) and must deploy in lockstep per ADR-0004/0005.

### Core (`/Users/masongill/Slyd-Platform/core`)

- **`Demand.cs`** — added `CustomerUpdatedAt` / `CustomerUpdatedById` / `CustomerUpdatedBy`,
  mirroring `SellSubmission`, `SiteSubmission`, and `DeploymentBuild`, which all already had them.
- **`Demand.WithdrawByCustomer(User by, DateTimeOffset at)`** — new transition, `Open`/`ReVerify` →
  `Withdrawn`.
  - **Why it bypasses `Transition()`:** that private helper stamps `UpdatedById`, which is FK'd to
    **`AdminUser`**. Writing a customer's `User` id there is a foreign-key violation. EF InMemory
    accepts it silently; Postgres rejects it in production. This was the single highest-risk trap in
    the change, and the domain tests assert `UpdatedById` stays null specifically to guard it.
- **`SlydDbContext.cs`** — index + FK to `Users` with `SetNull`, inside the existing `Entity<Demand>`
  block.
- **`FormTypes.NeedIntakeEdit`** — one constant covering both edit and withdraw; the payload's
  `action` field distinguishes them, so ops keeps a single filterable queue.
- **Migration `20260804153516_AddDemandCustomerEditFields`** — reviewed before trusting: exactly two
  nullable `AddColumn`s, one index, one FK. No snapshot drift.
- **`EntityChangedHandler.cs`** — widened the `Demand` case. It previously fired **only** on
  `Added` or a `State` change, so a customer editing quantity/model/region left stale
  `MatchCandidate` rows until the next recurring `RefreshAll` sweep (up to 15 min). Now fires on
  every want-field. Follows the shape the `Site` case already used.

### Platform (`/Users/masongill/Slyd-Platform/platform`)

- **`DemandEditService.cs`** + **`DemandEditContracts.cs`** — owner-scoped `GetAsync` /
  `ApplyAsync` / `WithdrawAsync`, modelled on `SellSubmissionEditService`. Contracts live beside the
  service rather than at the bottom of the 1,200-line `PublicV3IntakeController` where the sell
  records ended up.
- **`DemandDetail.razor`** + `.razor.css` — `@page "/demands/{Id:guid}"`, `[Authorize]`,
  `@rendermode InteractiveServer` (interactivity is per-page in this app; `App.razor:114-117`).
  Three editable sections, a summary rail, and an inline two-step withdraw confirm (no JS interop —
  this page, like the sell page, never injects `IJSRuntime`). CSS is 100% `--slyd-*` tokens.
- **`DealOsDashboard.razor`** — demand row body factored into a `RenderFragment<Demand>` so the row
  renders as either an anchor or a static div without duplicating ~30 lines of chip markup.
- **`Source` stamping** — `PublicV3IntakeController.SubmitNeed` now sets `DemandSource.Website`;
  `ConfigureController` sets `DemandSource.Configure`.

## Key Decisions and Why

### 1. `ReVerify` permits spec edits — this reversed the originally approved plan

The plan locked the spec in `ReVerify` on the assumption it meant "ops has begun matching." Reading
the engine disproved that:

- `MatchRefreshJob:46,121`, `MatchAlertJob:47`, `RegionalBalanceJob:50`, `AssemblyRefreshJob:88` all
  treat `Open` and `ReVerify` **identically**.
- `Demand.cs:286`: *"Only Open and ReVerify participate in matching."*
- `MarkReVerify` is `Open → ReVerify` — it literally means *"confirm this is still what you want."*

Locking the spec there would force a buyer to phone ops to change a number they're looking at. So
`ReVerify` is fully editable and renders as a **call-to-action banner**, not a lock. The customer's
save deliberately does **not** auto-transition `ReVerify → Open` — all state transitions require an
`AdminUser`, and ops clears the flag.

### 2. The channel predicate cannot use `Demand.Source`

`Source` was unreliable at the time of writing. `/need` intake never stamped it, so **every existing
real need row is `DemandSource.Unknown`**. Worse, the `/configure` auto-demand is *also* `NEED-`
prefixed *and also* `Unknown` — only `BuildId` separates the two.

`IsCustomerNeed` is therefore positive channel evidence **plus** hard exclusions:

```csharp
d.Type == DemandType.Hardware      // booking demands are Compute
&& d.BuildId is null               // /configure auto-demand
&& d.BrokerId is null
&& d.CapacityListingId is null
&& d.Source is DemandSource.Unknown or DemandSource.Website
&& d.DisplayId.StartsWith("NEED-")
```

**No data backfill was written on purpose** — it would bake a heuristic into data where it can't be
corrected. `Unknown` stays permanently accepted. The new `Source` stamping only helps future rows.

### 3. Explicit `ClearX` flags, deviating from the sell precedent

`SellSubmissionEditRequest` uses `null = unchanged`, which works because every editable field on a
`SellSubmission` is non-nullable in practice. A `Demand` has five genuinely nullable columns
(`WantSubcategory`, `IsoCode`, `NeedByDate`, `PreferredGrade`, `PriceCeiling`) a buyer legitimately
wants to reset. Without a clear signal, setting a price ceiling would be a **one-way door**. Hence
`ClearSubcategory`, `ClearIsoCode`, `ClearNeedByDate`, `ClearPreferredGrade`, `ClearPriceCeiling`.

### 4. Deliberate omissions

- **No `DbUpdateConcurrencyException` catch.** There is no concurrency token anywhere in the DealOS
  model (`grep RowVersion|IsConcurrencyToken` returns nothing), so
  `SellSubmissionEditService.cs:212`'s catch is unreachable dead code. Copying it would be a lie.
  Consequence: a customer edit racing an ops edit is silent last-write-wins. See To Do Next.
- **`PriorTopMatchIdsJson` is never touched.** Clearing it would make every current top-3 entry read
  as "new" on `MatchAlertJob`'s next 2-min pass, spamming the buyer about a change they just made
  themselves. Pinned by a test.
- **No JSON API.** Grep confirms **zero** callers of `/api/v3/sell/submissions/{id}` inside the
  platform — that API exists only because slyd.com (separate repo) needed it. Adding
  `GET`/`PATCH /api/v3/demands/{id}` would double the auth surface for no consumer.
- **No match-candidate detail on the response.** The admin `DemandDetailView` carries
  `TopCandidates` with counterparty identity; the buyer response exposes only a bare count, per the
  auth-boundary rule.
- **No-op saves short-circuit** — if the diff is empty, no FormSubmission, no notification, no
  `CustomerUpdatedAt` stamp. (The sell service writes one regardless; this is a deliberate
  improvement, not an oversight.)

## Verification

- `core`: builds clean; **961/961 tests pass** (593 Core + 311 Matching + 57 Integration).
- `admin` (`src/Admin.sln`): builds clean — it project-references core, so the `Demand` change was
  checked there too.
- `platform` (`src/Platform.sln`): builds clean. **39 new tests pass.**
- **6 platform test failures are pre-existing and unrelated.** Verified by stashing all work in both
  repos and re-running: HEAD fails the same 6 (`AccountResolverTests` ×2, `MarketplaceIntakeTests`
  ×3, `AuthPipelineTests` ×1). All are account-resolution assertions, consistent with commit
  `ce4098e` ("claim flows stop provisioning accounts") removing auto-provisioning without updating
  the tests.

Not yet exercised against a real Postgres or in the running app.

## To Do Next

- **Smoke the withdraw path against real Postgres before merge.** EF InMemory does not enforce
  foreign keys, so the `UpdatedById == null` assertions are the *only* automated guard against the
  AdminUser-FK bug. Postgres is where a regression would actually surface.
- **Walk it in the app**: `/v3/dashboard` → NEED row is a link, RESERVE/BOOKING rows are not →
  `/demands/{id}` → edit → save → confirm the `NeedIntakeEdit` row in `/admin/forms` → withdraw.
- **Fix the 6 pre-existing failures** (separate task) — they predate this work but leave the platform
  suite red.
- **Consider a concurrency token.** Adding Npgsql `xmin` to `Demand`
  (`entity.Property<uint>("xmin").IsRowVersion()`) is one line and free in Postgres; it would make
  the `Conflict` arm real and close the customer-vs-ops last-write-wins gap. Ideally applied to
  `SellSubmission` at the same time so its dead catch becomes live.
- **`Withdrawn` is terminal with no way back** — no `AdminUser` transition returns from it, so a
  mis-click is unrecoverable without raw SQL. Consider `Reopen(AdminUser, DateTimeOffset)`.
- **Dashboard `Take(5)`** with no `/demands` index means a buyer with more than 5 demands can only
  reach the 5 most recent.
- **Optional:** redirect `NeedClaim.razor:196` to `/demands/{id}` instead of the dashboard, mirroring
  `SellClaim.razor:225`.
- **No tests exist for `SellSubmissionEditService`** — `DemandEditServiceTests` is now the template
  to mirror.
