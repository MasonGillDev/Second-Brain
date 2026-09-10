# Admin Intake Cleanup — bulk removal of form-spam intake

**Project:** SLYD Platform / admin
**Date:** 2026-08-18
**Author:** 77c36516-5536-431f-af97-455eb95551c4
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Built an admin UI at `/v3/platform/intake-cleanup` for bulk-deleting junk public
intake. This is the **cleanup half of the incident triaged in
[build-intake-sqli-attack-triage.md](build-intake-sqli-attack-triage.md)** — ~200
sqlmap-style blind-SQLi probes against `POST /api/v3/configure/submit` in 6 minutes,
all using contact email `sample@email.tst`. That doc's verdict: **the injection
failed, no breach** (the whole write path is parameterized EF Core); the real damage
was amplification. It also closed the "cleanup gap" item on that doc's To Do list.

No direct DB access was available, so SQL and a data-fixup migration were both off
the table — this had to be a UI. The absent `IpAddress` on these rows is explained
there too: `ConfigureController.cs:557-559` passes `ipAddress: null, userAgent: null`
despite the columns existing.

### Why a dedicated feature instead of "delete the form submissions"

Tracing the public intake controllers showed one spam POST fans out well past the
obvious table:

- `PublicV3IntakeController.SubmitNeed` (`/need`) → a `Demand` **and** a parallel
  `FormSubmission` **and** (via `FormLeadCapture`) a `Lead`, plus an `AuditEvent`.
- `ConfigureController` (`/configure`) → a `DeploymentBuild` **and** a child `Demand`.
- `SubmitHardwareSales` / `SubmitEnergySite` → `SellSubmission` / `SiteSubmission`
  plus their own parallel form submissions.
- The Hangfire matching workers then write `MatchCandidate` and `Alert` rows against
  every open demand.

Four findings drove the design:

0. **`SalesLead` lives in a different DbContext with no foreign key.**
   `SalesLeadService.SyncFromFormSubmissionsAsync` mints one `SalesLead` (in
   `AdminDbContext`) per non-Spam `FormSubmission` (in `SlydDbContext`), linked by a
   bare `FormSubmissionId` Guid across the context boundary. Deleting submissions
   alone strands them in the sales queue forever. This was flagged by the triage doc
   and initially missed here. They are deleted *first*, deliberately: the two
   contexts cannot share a transaction, and if the main purge then rolls back, the
   surviving submissions are simply re-synced on the next run — a partial failure
   self-heals instead of leaving orphans.


1. **`MatchCandidate` and `Alert` have no foreign key to `Demand`.**
   `MatchCandidate.SubjectId` is a `varchar(100)` holding the demand GUID as text;
   `Alert.TargetEntityId` is a bare `uuid`. Deleting demands orphans these rows
   permanently and invisibly — they keep scoring against real lots. Nothing cascades
   them, so the cleanup sweeps them explicitly.

2. **`/configure`-spawned demands are unreachable via the ref fields.** The intake
   controllers write a ref field into `FormSubmissionFields` pointing at what each
   form spawned (`demandRef`, `submissionRef`, `siteSubmissionRef`, `buildRef`). But
   `/configure` writes only `buildRef` — the demand it creates has no `demandRef` at
   all and is reachable **solely** through `Demand.BuildId`. Filtering on `demandRef`
   alone silently leaves every configure-sourced spam demand in the matching pool.
   This is pinned by a test, and mutation-checked (breaking the `BuildId` leg fails 2 tests).

3. **The lead count is ~1, not hundreds.** `FormLeadCapture.FindOpenLeadAsync`
   dedupes on lowercased email against any lead with `AccountId IS NULL`, so an
   entire flood from one address collapses into a single lead that later submissions
   merely `Enrich()`. The corollary risk — a spam email colliding with a real open
   lead and corrupting it — did not apply here because `sample@email.tst` matches
   nothing real. It *would* apply to a flood using a plausible address.

### Design decisions

- **Preview-then-purge.** `ResolveAsync` walks the selector to the full id set once;
  both preview and purge use it, so the counts an operator approves are the rows that
  get deleted. The preview also samples the newest 50 matched submissions with their
  contact fields — a too-broad selector shows up as a real customer in that list.
- **Identity selector required.** The filter refuses to run on a date range alone;
  at least one of email / IP must be set. IP is included even though it was not
  captured for this incident, because it will be the natural selector next time.
- **Email compared case-insensitively.** Only `Leads.Email` is normalized to
  lowercase; `FormSubmission.ContactEmail` and `SellSubmission.SubmitterEmail` are
  stored as submitted, so a case-varied flood would otherwise slip through.
- **`RemoveRange` + one `SaveChanges`, not `ExecuteDeleteAsync`.** One SaveChanges is
  one implicit transaction on Npgsql (a Restrict-FK violation rolls the whole graph
  back), and the admin test suite runs on the EF InMemory provider, which does not
  implement the ExecuteDelete bulk operators at all. Volumes are hundreds of rows, so
  tracking overhead is irrelevant.
- **Blockers surfaced, not thrown.** `Auction.SellSubmissionId` is `Restrict`. The
  preview reports any auction pinning a matched sell submission rather than letting
  SaveChanges explode.
- **Never deleted:** `AuditEvents` (SHA-256 hash chain — removing rows breaks
  verification for every subsequent event, and the spam events are the forensic
  record), and any demand not in `Open`/`ReVerify` (Matched means bound to a Deal).
- **Leads guarded twice:** only deleted if no *surviving* form submission references
  them and `AccountId IS NULL` (a converted lead is a real customer).

### Files

| File | Role |
|---|---|
| `src/Admin.Application/Models/DealOS/IntakeCleanupModels.cs` | filter / preview / result records |
| `src/Admin.Application/Interfaces/Features/DealOS/IIntakeCleanupFeatures.cs` | interface |
| `src/Admin.Application/Features/DealOS/IntakeCleanupFeatures.cs` | resolve → preview → purge |
| `src/Admin.Application/DependencyInjection.cs` | scoped registration |
| `src/Admin.Application/Navigation/NavRegistry.cs` | nav entry under V3 · Platform |
| `src/Admin/Components/Pages/V3/Platform/IntakeCleanup.razor` (+`.css`) | the UI |
| `tests/Admin.Tests/Features/V3/Platform/IntakeCleanupFeaturesTests.cs` | 13 tests |

Confirmation phrase to arm the purge: `DELETE JUNK INTAKE`.

### Verification

`dotnet build src/Admin.sln` — 0 errors. `dotnet test tests/Admin.Tests` — 344/344
passing. The `BuildId` resolution path was mutation-checked to confirm its test
actually fails when the logic is broken (breaking it fails 2 tests).

## To Do Next

- **Run it against a restored production snapshot before touching prod.** The
  feature is tested only on the EF InMemory provider, which does not prove the LINQ
  translates to Postgres (see [[admin-tests-inmemory-provider-caveat]]). The
  `Contains` clauses over Guid lists and the `.ToLower()` comparisons are the parts
  worth proving out.
- Consider forcing a match refresh after a purge so candidate tables rebuild against
  the surviving demand set. Currently manual.
- Still open from the triage doc and not addressed here: capture `IpAddress`/
  `UserAgent` in `ConfigureController` (the columns exist and the cleanup UI already
  accepts IP as a selector); apply the ALB/WAF rate-limit rule; honeypot field and
  length caps on unbounded text columns.
- The dead `FormSubmissionRepository.DeleteOldSubmissionsAsync` (zero callers, no
  id/window filter, no derived-row cleanup) is now fully superseded — worth deleting
  so nobody reaches for it thinking it does this.
