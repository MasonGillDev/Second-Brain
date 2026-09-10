# Deals Carry Zero or Many Reps

**Project:** SLYD Platform — core + admin
**Date:** 2026-08-13
**Author:** db573a0e-2c34-4a76-b41a-0676c6af891e
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Implements the 2026-08-13 12:57 TODO: *"deals need to support zero or many reps attached
to them — a deal should be able to carry no rep or several, not a single fixed one."*

### Resolving what "rep" meant

The codebase had two candidates and they mean very different things:

- `Broker` — the **external** roster, with its own tiers, submissions and `LedgerEntry`
  commission chain. External counterparties on a deal are already handled by `DealParty`
  (account + `DealPartyRole`, including `Broker`).
- `AdminUser` — internal SLYD staff. `AccountDirectoryModels.cs:122` defines `CrmRepOption`
  as "the per-account CRM rep dropdown — **an admin user**", assigned through
  `Account.OwnerAdminUserId`.

So a rep is internal staff, and the existing pattern (`OwnerAdminUserId`, also on `Contact`,
`Lead`, `TrackerFirm`) is a single nullable FK — literally the "single fixed one" the TODO
wanted replaced. Note `Admin.Application/Models/Sales/Rep.cs` is a **different, legacy** sales
module hanging off `CloudDeal`/`HardwareDeal`; it is not the V3 `Deal` and was left alone.

### The model

New `DealRep` join entity (core) — `DealId`, `AdminUserId`, `CreatedAt`, `CreatedById`.
Unique index on `(DealId, AdminUserId)`; second index on `AdminUserId` because "which deals
am I on" is the query the table exists for. Cascade from Deal, **Restrict** from AdminUser —
an admin row disappearing must not silently erase who worked a closed deal.

Deliberately **no role and no commission split** on the link. The ask was zero-or-many
attribution; the Broker roster and its ledger remain the commission system of record, and
the hero's "Your commission" is still the flat 0.10 placeholder it was on the kanban.

Migration `20260813192556_AddDealReps` — purely additive, applied to the local SLYD2 DB.

### Behaviour

- `AssignRepAsync` is **idempotent** — re-adding an existing rep writes no row and no audit event.
- `RemoveRepAsync` on someone not on the deal is a no-op.
- **Removing the last rep is allowed.** There is no minimum; an unstaffed deal is a real
  state, not an error, so the UI says "Unassigned" rather than blocking.
- Audited as `deal.rep.added` / `deal.rep.removed`.

### Surfaces

- **Deal workspace** — the "Owner / coming soon" spec cell became a live Reps cell: chips
  with an × per rep, an "Add" button, and a picker filtered to admins not already on the deal.
- **Kanban card** — a rep line under the footer: one name, or `First +N`, full list in the
  title attribute. "Unassigned" in italics when empty.
- **Pipeline drawer** — a read-only `Reps · N` mini-section beside Parties.
- **Platform** — nothing. Reps are internal; grep confirms zero `DealRep`/`.Reps` references
  in the platform repo.

### The EF trap this surfaced (worth remembering)

The first implementation added the link through the navigation collection
(`deal.Reps.Add(new DealRep { Id = Guid.NewGuid(), ... })`) and every save threw
`DbUpdateConcurrencyException: Attempted to update or delete an entity that does not exist
in the store`. A change-tracker probe showed the row entering as **`Modified`, not `Added`**.

Cause: the entity carries a **client-set Guid primary key**, and an entity discovered that
way through a tracked navigation is taken for an existing row — so EF saves an UPDATE against
a row that was never inserted. **This is not an in-memory-provider quirk; it would fail the
same way on Postgres.** Fix is `db.DealReps.Add(link)`, which forces `Added` — the same reason
`AddDocumentAsync` in that file goes through `db.DealDocuments` rather than `deal.Documents`.
The comment explaining this is in `DealPipelineFeatures.AssignRepAsync`.

**Verification:** core 657 + 311 + 74; admin 267 (12 new in `DealRepAssignmentTests`);
platform builds clean. Not clicked through in a running app.

## To Do Next

- Visual pass in a running app.
- **Deploy impact:** this adds a *second* uncommitted core migration on top of
  `RemapDealStageToSalesPipeline` (see
  [deal-stage-sales-pipeline-migration.md](deal-stage-sales-pipeline-migration.md) for the
  deploy-order hazard that one carries). `AddDealReps` is additive and safe in either order;
  the stage remap is the one that needs the low-traffic window.
- Obvious follow-ons, none requested yet: a "My deals" filter on the pipeline (the
  `AdminUserId` index is already there for it), rep assignment from the kanban drawer rather
  than only the workspace, and defaulting the creating admin onto a new deal as its first rep.
- If commission ever needs splitting across reps, that's a `SplitPct` on `DealRep` plus a
  decision about how it interacts with the Broker ledger — deliberately not modelled now.
