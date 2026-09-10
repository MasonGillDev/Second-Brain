# Core v0.2.12 Release and Platform Pin Bump

**Project:** SLYD Platform (core, platform)
**Date:** 2026-08-06
**Author:** 77543760-4471-47c4-946a-2ab2ba6308e0
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

### Core v0.2.12 published

PR #17 (`feat/crm-accounts-quote-builder`) had already been merged to `main` via the GitHub
UI, landing at `3d89740`. Released it as `v0.2.12`.

Verified before tagging, because the publish workflow runs the full test suite and a failure
there would leave a dangling tag on the remote with no packages behind it:

- `dotnet build SLYD.Core.sln -c Release` — 0 errors, 17 warnings (all pre-existing)
- Full suite green: 637 unit + 311 matching + 57 integration = **1005 passing, 0 failures**

Then pushed an annotated `v0.2.12` tag, which triggered `publish-packages.yml`
(run `31110675460`). Every step succeeded. All four packages pushed to
`https://nuget.pkg.github.com/SLYD-Platform/index.json`:

| Package | Version |
|---|---|
| SLYD.Domain | 0.2.12 |
| SLYD.Application | 0.2.12 |
| SLYD.Infrastructure | 0.2.12 |
| SLYD.Matching | 0.2.12 |

GitHub Release also carries `efbundle-linux-x64.tar.gz` (64 MB EF migration bundle) —
this release contains **9 EF migrations**, so that bundle matters for deploys.

Release contents: CRM multi-user accounts (`AccountMember`), lead minting from inbound form
submissions, customer-editable/withdrawable demands, `DealLineFulfillment` for partial BOM
line coverage, shared latest-pricing helper for provider servers, capacity matching scorers.

### Version choice — why patch, not minor

Went `0.2.11 → 0.2.12` to stay consistent with how this repo has always versioned; it bumped
patch across all 62 of the `v0.1.x` releases regardless of content. But **this release is
substantively bigger than a patch**: 9 migrations, new tables (`AccountMember`,
`DealLineFulfillment`, `Rfq`, `SupplierQuote`, `DealLineItem`, `ContactEngagement`), and a
deleted file (`AccountProvisioning.cs`). Flagged to Mason that `v0.3.0` would have
communicated migration risk better. Decision left open — a `v0.3.0` tag can still be added
to the same commit if desired.

### Platform pin bump

Bumped six `PackageReference` pins from `0.2.11` to `0.2.12`:

- `platform/src/Platform.WebUI/Platform.WebUI.csproj` — Domain, Application, Infrastructure, Matching
- `platform/src/Platform.HangFire/Platform.HangFire.csproj` — Infrastructure, Matching

Note "platform-web" and "platform-hangfire" are **not separate repos** — both projects live in
the single `platform` repo under `src/`. The Phase 2/3 repo split described in core's CLAUDE.md
has not happened.

**Verification gotcha worth remembering:** the pins sit in `ItemGroup Condition="'$(UseLocalCore)' != 'true'"`,
and `platform/Directory.Build.props` sets `UseLocalCore=true`. So a normal local build resolves
Core through *project references* and never touches the NuGet pins — editing them changes
nothing locally. Only CI/production (`UseLocalCore=false`) exercises them.

Tried to verify a real feed restore with `-p:UseLocalCore=false`, but it 403s: the `gh` CLI
token lacks the `read:packages` scope. A PAT with `read:packages` would be needed to restore
GitHub Packages locally.

Instead verified the thing that actually carries risk — source compatibility. Local core `main`
is byte-identical to the `v0.2.12` tag, so building platform against it (via `UseLocalCore=true`)
proves platform compiles against v0.2.12 sources:

- `Platform.HangFire` — Build succeeded, 0 errors, 9 warnings
- `Platform.WebUI` — Build succeeded, 0 errors, 449 warnings

### Known issue carried into the release

Pre-existing dependency vulnerabilities, not introduced here but now shipped in the published
packages:

- **`System.Security.Cryptography.Xml` 9.0.0** — two HIGH severity advisories. This one is in
  `SLYD.Infrastructure`, so it **reaches consumers**. The one that actually matters.
- `Azure.Identity` 1.3.0 — one high, two moderate. Integration tests only, not shipped.

## To Do Next

- Platform pin bump committed as `bd897cd` on `feat/crm-accounts-quote-builder` — **unpushed**.
  Before pushing, run the TaskTracking pre-push step (check `TaskTracking/Pending/` for tasks
  this completes, mark Completed + add a "Changes Made" section, close the GitHub issue, move
  to `Complete/`).
- Decide whether to also tag `v0.3.0` on `3d89740` to signal the migration-heavy release.
- Bump `System.Security.Cryptography.Xml` off 9.0.0 in `SLYD.Infrastructure` and cut a patch.
- `admin` was **already** bumped to 0.2.12 in an earlier session today (commit `11d04c5`,
  unpushed). That session flagged "packages actually published to the feed is unverified" —
  **this release resolves that**; all four 0.2.12 packages are now confirmed on the feed.
  Admin's remaining work is just pushing `11d04c5`.
- Minor divergence noticed: admin pins `SLYD.Components` 0.5.0, platform pins 0.5.1. Not
  investigated, may be intentional.
- Deploys off this release need the EF migration bundle (9 migrations).
