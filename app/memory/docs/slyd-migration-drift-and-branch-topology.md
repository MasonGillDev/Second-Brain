# SLYD migration drift + branch topology — what blocks a merge to development

**Project:** SLYD core + platform + website
**Date:** 2026-08-05
**Author:** d6631e24-35fd-4130-8ac9-ac2b19bfc81e
**Directory:** /Users/masongill/Slyd-Platform/platform

Findings from a merge-readiness check on
[form-lead-capture-implementation.md](form-lead-capture-implementation.md).
Recorded because two of these will recur on every future deploy, not just this one.

## 1. The `AddProcurementLoop` trap — will break staging/prod deploys

**Applying migrations to a database that predates the 2026-07-22 reversal fails
with `42P07: relation "DealLineFulfillments" already exists`.**

Cause: `20260721145707_AddProcurementLoop` was applied to those databases, then
**deleted from the repo and regenerated** as `20260722172745_AddDealLineFulfillment`
during the quote→lot reversal (see
[deal-workspace-quote-builder-ui.md](deal-workspace-quote-builder-ui.md)). The
physical tables exist; `__EFMigrationsHistory` records a migration ID that no
longer exists in source. EF therefore sees `AddDealLineFulfillment` as pending
and tries to `CreateTable` over a live table.

Confirmed on the local `SLYD2` database — history's newest row was
`20260721145707_AddProcurementLoop`, an ID absent from `dotnet ef migrations list`.

**Fix (verify first, then one row):** confirm the live table matches what the
replacement migration would create — for `DealLineFulfillments` that is 6 columns
(`Id`, `DealLineItemId`, `LotId`, `Quantity`, `CreatedAt`, `CreatedById`), plus
`PK_` and the three `IX_` indexes. Then record it as applied without running it:

```sql
INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20260722172745_AddDealLineFulfillment', '10.0.0');
```

Then `dotnet ef database update` proceeds normally. Reversible — delete the row.

**Check before any deploy:**
```sql
SELECT "MigrationId" FROM "__EFMigrationsHistory" WHERE "MigrationId" LIKE '%ProcurementLoop%';
```
A hit means that environment will fail. Five seconds now vs. a stalled release later.

Local `SLYD2` is now fully migrated — zero pending, `FormSubmissions.LeadId` +
FK + index verified present.

## 2. Migrations are NOT applied by deploying code

No `Database.Migrate()`, `MigrateAsync()` or `EnsureCreated()` anywhere in
`core/src`, `platform/src` or `website`. CI (`core/.github/workflows/publish-packages.yml`)
builds a **self-contained EF bundle** — `efbundle-linux-x64.tar.gz`, attached to
the GitHub release — which somebody runs deliberately.

Consequence: **schema must lead code.** `FormLeadCapture` stamps
`FormSubmission.LeadId` on insert, so code-live-before-migration means *every*
form submission fails — `/need`, `/sell`, `/site`, `/configure` and all website
forms, not merely the lead part.

Design-time default when no `ConnectionStrings__Conn` is set:
`Host=localhost;Database=SlydLocal;Username=postgres;Password=postgres`.

## 3. Branch topology — core's `development` is dead

Measured 2026-08-05 **after a fresh fetch** (numbers unchanged by the fetch, so
these refs were already current):

| repo | behind `origin/development` | ahead | `origin/development` tip |
|---|---|---|---|
| core | 0 | 145 | **2026-01-23** |
| platform | 0 | 7 | 2026-07-16 |
| website | **10** | 4 | 2026-07-22 |

**Core's `development` is ~6 months stale while `origin/main` is 2026-07-16.**
The real integration branch for core is `main`, not `development` — worth
resolving explicitly, because the repo CLAUDE.md says "always push to
`development`, NEVER directly to `main`" and that instruction does not match how
core is actually being used.

Core's branch already contains **every migration `origin/main` has**, and its
model snapshot is 533 lines ahead. So there is **no competing migration and no
`SlydDbContextModelSnapshot.cs` conflict** — the failure mode worth fearing on a
cross-branch merge is genuinely absent here.

## 4. Website has a total-overlap conflict

The 10 commits website is behind are a full **SEO/AEO + brand overhaul**
(`SEO Phase 0`–`5`, OG image generation, plus "purge all Sovereign-AI messaging"
and a CLAUDE.md rewrite to Energy-in/Compute-out voice).

**Every one of the 10 files in the lead-capture commit is also touched by them.**
Zero clean files. Worst: `Configure.razor` +150/−80 and `Configure.razor.css`
+123, because `SEO Phase 1` reworked V3 pages for "static SSR, crawlable tab
content" — the exact rendering model the new `/configure` contact block plugs
into. This is two people reshaping one page, not a mechanical conflict.

New UI copy ("Work email", "so we know who we're talking to") should also be
checked against the new brand voice after the rebase.

## To Do Next

1. **Rebase website `cc18a28` onto `origin/development`** and hand-resolve
   `Configure.razor` / `.css` against the SEO rewrite. Re-run build + click
   through `/configure` afterwards — a textual merge is not trustworthy here.
2. **Check staging/prod `__EFMigrationsHistory`** for `AddProcurementLoop`
   before running the efbundle.
3. **Decide core's integration branch** — `main` in practice vs `development`
   per CLAUDE.md.
4. `/configure` contact UI has still never been rendered in a browser. It gates
   the Save button, so a bad selector breaks Save for everyone; unit tests
   cannot catch it.
