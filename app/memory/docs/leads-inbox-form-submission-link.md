# Leads Inbox → Form Submission Link

**Project:** SLYD Platform — Admin
**Date:** 2026-08-13
**Author:** db573a0e-2c34-4a76-b41a-0676c6af891e
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Implements the 2026-08-13 13:09 TODO: *"Leads Inbox rows need a link to the form submission
that minted the lead — from a lead in the inbox, ops must be able to open the actual form the
person submitted."* Admin-only change; no core, no migration.

### Why the existing artifacts list didn't already cover it

The lead drawer had an "Artifacts · N claimed by this login" section, built by
`LoadArtifactsAsync`, which joins demands / sell submissions / site submissions **through
`Lead.UserId`**. A lead captured from a public form has no platform login, so that method
returns `[]` immediately — the submission that *created* the lead was unreachable from the
inbox in exactly the case where it's the only evidence ops has.

`FormSubmission.LeadId` (stamped at insert by `FormLeadCapture`, in the same transaction) is
the only edge that survives an anonymous submit. Its own docstring already said so.

**Confirmed against the local DB:** all 5 submission↔lead links are on leads with
`UserId IS NULL` — two are literally named "Anonymous · HardwareSalesIntake" / "Anonymous ·
NeedIntake". Every single linked lead was in the blind spot.

### The link target

`/admin/forms/{id}` is **the submission detail page**, not a form-definition page — the route
parameter is named `FormId` but `FormDetails.razor` loads a `FormSubmission` via
`FormRepository.GetSubmissionByIdAsync(FormId)`. Worth knowing before someone "fixes" that name.

### What was built

- `LeadSubmissionItem(Id, FormType, Subject, Status, SubmittedAt)` — deliberately a **separate
  record from `LeadArtifactItem`**, because the two answer different questions: artifacts are
  what this login has claimed, a submission is where the lead came from. Folding them together
  would have made the existing "claimed by this login" heading a lie.
- `LeadDetailView.Submissions` — a **list**, not a single value: a repeat submitter joins the
  existing lead rather than minting a second one, so a lead can legitimately have several.
- `LeadListRow.SubmissionCount` / `LatestSubmissionId` — one grouped query over the slice,
  same no-N+1 shape as the existing artifact counts.
- Drawer: a "Source form · N" section above Artifacts; each row is a link opening in a new tab.
- Row: a small file icon in the Source column (`×N` when there's more than one, opening the
  most recent) with `@onclick:stopPropagation` so it doesn't also select the row.

### Two things fixed along the way

1. **`AssignOwnerAsync` returned a detail with no artifacts.** The drawer does
   `_detail = await Crm.AssignOwnerAsync(...)` — it swaps its entire view for the result — so
   taking ownership of a lead silently blanked its Artifacts section. Submissions would have
   inherited the same bug, so both are now loaded on that path. `ConvertToContactAsync` got
   submissions too (it already loaded artifacts).
2. **`FormSubmission.SubmittedAt` is a `DateTime`**, not a `DateTimeOffset` — the Forms module
   predates the CRM convention. Converting inside the EF projection would let the provider infer
   an offset from the server locale, so the rows are projected raw and stamped
   `DateTimeKind.Utc` in memory.

**Verification:** admin builds clean; 276 tests pass (9 new in `LeadSubmissionLinkTests`,
including the anonymous-lead case that is the whole point). Not clicked through in a running app.

## To Do Next

- Visual pass in a running app — the local DB has 5 real linked submissions to check against.
- The remaining TODO from 2026-08-13 is **capacity deals can't be created from the pipeline
  page** (`Pipeline.razor:42-43` offers only Hardware and Three-sided). Not a one-line dropdown
  addition: capacity deals need a `CapacityListingId`, a stamped `CapacityKind`, and a
  `GpuCount`, all of which the close gate and `CommittedRatio` bump depend on — so it needs a
  listing picker and quantity. See [pipeline-kanban-redesign.md](pipeline-kanban-redesign.md).
