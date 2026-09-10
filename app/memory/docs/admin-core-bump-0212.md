# Admin: Bump Core Packages to 0.2.12

**Project:** SLYD Admin
**Date:** 2026-08-06
**Author:** 67e19de6-7021-4882-aa88-e24b1ab8c23b
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Committed as `11d04c5` on `feat/crm-accounts-quote-builder` (not pushed).

Bumped `SLYD.Domain`, `SLYD.Application`, `SLYD.Infrastructure` and
`SLYD.Matching` from 0.2.11 → 0.2.12 in both `src/Admin/Admin.csproj` and
`src/Admin.Application/Admin.Application.csproj`. Eight lines, nothing else.
`SLYD.Components` stays at 0.5.0 — it versions independently and the 0.2.11
bump left it alone too.

**What 0.2.12 contains** (core `v0.2.11..v0.2.12`, tag → commit `3d89740`):
multi-user accounts (`AccountMember`), deal party contacts, contact
relationship status, intake contact links, lead capture minting a Lead from
every inbound form submission, the deal quote builder schema,
`DealLineFulfillment` for partial BOM line coverage, customer-editable/
withdrawable demands, and a shared latest-pricing helper for provider servers.
This is precisely the work the admin branch consumes, so the bump is the
matching half of that feature.

### Verification and its limit

Local build: **0 errors**, 144 warnings all pre-existing (nullable/style in
AdminScripts.razor, MainLayout, Program.cs). The warning count jumped from 10
to 144 only because touching the csproj forced a full recompile instead of an
incremental one — not a regression.

The limit worth remembering: `Directory.Build.props` sets `UseLocalCore=true`,
so the local build uses **project references and never touches the
`PackageReference` lines this commit edits**. The build is only meaningful
evidence because local core is at `main` = commit `3d89740`, which is exactly
what the annotated tag `v0.2.12` dereferences to, with a clean working tree —
so it compiles against byte-identical source to what the package ships.

What is therefore still *unverified*: that the 0.2.12 packages are actually
published to the GitHub Packages feed. Restoring with `-p:UseLocalCore=false`
would prove it but needs `NUGET_AUTH_TOKEN` for
`nuget.pkg.github.com/SLYD-Platform`. CI will be the first thing to find out.

Note when comparing tags by hand: these are annotated tags, so
`git rev-parse v0.2.12` returns the *tag object* SHA, not the commit. Use
`v0.2.12^{commit}`. A naive comparison looks like a mismatch and isn't.

## Migration Risk on Deploy

0.2.12 adds **nine** migrations: AddAccountMembers, AddDealPartyContact,
AddContactRelationshipStatus, AddIntakeContactLinks, AddLeadCaptureFields,
AddDealQuoteBuilder, AddDealLineFulfillment, AddDemandCustomerEditFields,
AddFormSubmissionLeadLink.

CI derives the efbundle from the `SLYD.Infrastructure` version in
`Admin.csproj`, so this bump is what causes all nine to run. Nothing
auto-applies them (no `Database.Migrate` anywhere) — schema must lead code.

A prior session (`slyd-migration-drift-and-branch-topology.md`) recorded
hitting `42P07 "DealLineFulfillments already exists"` on SLYD2, attributed to
`20260721145707_AddProcurementLoop` being deleted and regenerated as
`20260722172745_AddDealLineFulfillment` — leaving DBs migrated before
2026-07-22 with a history row pointing at an ID no longer in source.

**I could not confirm that from core's history**: no trace of
`20260721145707` or any `*ProcurementLoop*` migration file in `git log --all`.
It was likely never pushed, or lived on a rebased-away branch. But the risk is
still live regardless of provenance — `20260722172745_AddDealLineFulfillment.cs`
is a bare `migrationBuilder.CreateTable` with no `IfNotExists` guard, so *any*
target DB that already has that table fails the whole bundle.

## To Do Next

- Both commits (`49479d4`, `11d04c5`) are unpushed. Push to `development`,
  never `main`.
- **Before running the efbundle on staging/prod**: query
  `__EFMigrationsHistory` for `%ProcurementLoop%` and check whether
  `DealLineFulfillments` already exists. If the table is present and matches
  the migration's shape (6 cols + PK + 3 indexes), record the migration as
  applied rather than re-running it.
- Confirm 0.2.12 is actually published to GitHub Packages, or expect CI
  restore to fail.
