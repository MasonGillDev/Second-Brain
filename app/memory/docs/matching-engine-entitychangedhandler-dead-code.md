# Matching Engine: EntityChangedHandler Is Structurally Dead

**Project:** SLYD Platform (core)
**Date:** 2026-08-04
**Author:** 951270e3-cd9c-4187-b234-c353501d807d
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Investigated backlog item 12 ("`EntityChangedHandler` never fires — event-driven match refresh is
dead code"). Confirmed the claim, found the exact mechanism, and scoped the blast radius.

### First, a correction

An earlier report in this session claimed `AddMatching()` had zero callers and the whole matching
engine was unwired in every host. **That was wrong.** The extension method is named
**`AddSlydMatching`**, and grepping for `AddMatching` matched nothing because that string does not
appear anywhere — not because nothing calls it.

It is called correctly in all three hosts:

- `platform/src/Platform.HangFire/Program.cs:62`
- `platform/src/Platform.WebUI/Program.cs:371`
- `admin/src/Admin/Program.cs:99`

DI is fine. The recurring jobs resolve and run. Nothing to fix there.

### The actual defect

`EntityChangedHandler` (`core/src/SLYD.Matching/Worker/EntityChangedHandler.cs`) hooks
`SavedChanges` / `SavedChangesAsync` — the **post-save** interceptor points. By the time those fire,
EF Core has already run `AcceptAllChanges()`, so every successfully-saved entry has been reset to
`Unchanged` and every `IsModified` flag is back to `false`.

`ProcessChanges` opens with:

```csharp
if (entry.State == EntityState.Unchanged || entry.State == EntityState.Detached) continue;
```

…which therefore skips **every** entry, on every save. And even if that guard were removed, the
`PropertyChanged(entry, nameof(...))` helper reads `prop.IsModified`, which is also false by then.
Both the `EntityState.Added` arm and every `PropertyChanged` arm are unreachable.

Proven with a throwaway probe interceptor on an InMemory context (written, run, deleted):

```
INSERT  SavingChanges : Demand:Added
INSERT  SavedChanges  : Demand:Unchanged      ← EntityChangedHandler runs here
UPDATE  SavingChanges : Demand:Modified
UPDATE  SavedChanges  : Demand:Unchanged      ← EntityChangedHandler runs here
SavedChanges saw IsModified=true on WantQuantity: False
```

This is a guaranteed no-op, not an intermittent one. Deleted entities become `Detached` and are
skipped by the same guard.

### Why it went unnoticed

`core/tests/SLYD.Matching.Tests/Worker/EntityChangedHandlerTests.cs` has seven tests. **Every single
one asserts only `NotThrowAsync()`.** Not one asserts that a job was enqueued. The class doc states
the intent plainly: *"Actual job enqueueing is exercised indirectly."* It isn't exercised at all.
The suite is 311/311 green and provides zero behavioural coverage of the thing it names.

## Blast Radius — smaller than it sounds

Matching is **not** broken. It is only never *event-driven*. Freshness rests entirely on the
Hangfire recurring sweeps, which do work:

| Job | Cadence | What it actually catches |
|---|---|---|
| `match-refresh-all` → `RefreshAll()` | every 15 min | full sweep — **this is what picks up an edit** |
| `match-refresh-stale` → `RefreshStale()` | every 1 min | only `ComputedAt < now − 1h` **or** `ConstantsVersion` mismatch |
| `match-alerts` → `DiffAndFire()` | every 2 min | diffs top-N, fires alerts |

Note `RefreshStale` does **not** catch a fresh edit — a just-recomputed candidate isn't stale, so the
1-minute job skips it. Worst-case propagation for any demand/lot mutation is therefore the
**15-minute `RefreshAll` cadence**. `RefreshStale` also caps at `PageSize = 200` subjects per run.

So: no data is wrong, nothing is silently mismatched. Matching is just up to 15 minutes behind
reality, always, with no way to make it responsive until the interceptor works.

## Who Should Be Calling It

The interceptor **is** the right choke point and should stay. It is the only place that catches
every writer at once — platform `DemandEditService`, admin formation paths, `ReserveDemandService`,
`BookingDemandService`, Hangfire jobs — without scattering `BackgroundJob.Enqueue` calls across a
dozen mutation sites. That matches architecture §7.2. The design is sound; only the hook point is
wrong.

**The fix shape:** split the work across both interceptor phases.

1. In `SavingChanges` / `SavingChangesAsync` (state is still `Added`/`Modified`), detect the
   interesting entries and stash the `(entityType, id)` pairs.
2. In `SavedChanges` / `SavedChangesAsync`, enqueue from that stash — so a rolled-back or failed
   save never enqueues a refresh.

**Trap for whoever does it:** `EntityChangedHandler` is registered as a **singleton**
(`DependencyInjection.cs:64`), so it cannot hold the stash in a mutable instance field — concurrent
`SaveChanges` calls across circuits would interleave and cross-contaminate. Key the stash by the
`DbContext` instance (`ConditionalWeakTable<DbContext, List<...>>`) or register the interceptor as
scoped instead.

Whoever fixes it should also replace the seven `NotThrowAsync` tests with ones that assert an
enqueue actually happened — via an injectable `IBackgroundJobClient` rather than the static
`BackgroundJob.Enqueue` the handler currently calls, which is untestable by construction.

## Consequences for Work Shipped Earlier Today

The `/demands/{id}` page (see [demand-detail-edit-page.md](demand-detail-edit-page.md)) widened the
handler's `Demand` case to fire on want-field edits, not just `State` changes. That change is
**correct in intent but currently inert** — the whole handler is inert. It becomes live the moment
the hook point is fixed, and needs no rework.

The page's summary copy — *"Saving changes re-runs matching against current inventory"* — is true but
implies immediacy. Today the real answer is "within 15 minutes." Either soften the copy or fix the
interceptor.

## To Do Next

- **Fix the hook point** (`SavingChanges` capture → `SavedChanges` enqueue), with the singleton-state
  trap above handled. Small change, high leverage: it makes the entire event-driven half of the
  matching architecture functional for the first time.
- **Replace the `NotThrowAsync` tests** with enqueue assertions behind an injectable
  `IBackgroundJobClient`.
- **Re-check backlog item 13** ("BKG- booking demands silently consumed") and item 15
  (`CommittedRatio` races) — both were filed as matching-correctness bugs and may partly be symptoms
  of staleness rather than independent defects.
- **Correct backlog item 12's framing** — it says "complexity 5", which reads as a large job. The
  diagnosis is done and the fix is contained; the real cost is the test rewrite.
- Decide on the `/demands/{id}` copy in the meantime.
