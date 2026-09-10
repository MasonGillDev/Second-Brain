# Leads Inbox — form submission overview in the drawer

**Project:** SLYD Platform — Admin
**Date:** 2026-08-24
**Author:** 9556c277-fb2e-43c2-b649-cd1d0fe7dfd8
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Two related changes, both about reaching the actual thing a person filled in.

### 1. Notification deep link to the submission

`FormSubmissionCheck` published `Href: "/admin/forms"` — the list page — for every
new-submission signal. It now publishes `$"/admin/forms/{f.Id}"`, so the target chip in
the Notification Center opens that submission's detail page (`/admin/forms/{FormId:guid}`).

Note: `Href` is persisted on the notification row at publish time, so notifications
already in the table keep the old list link. Only new ones deep-link. A backfill would be
a one-line UPDATE using the row's `RelatedEntityId` (it already stores the submission id);
not done, as it wasn't asked for.

### 2. Lead drawer shows the form contents at a glance

Most leads arrive by form, and the drawer previously showed only a one-line link row per
submission (form type, subject, status, date). Ops had to open a second tab to see what
the person actually asked for.

- `LeadSubmissionItem` now carries the submitter contact block (name/email/phone/company),
  `SourceUrl`, an attachment count, and the submitted field values via a new
  `LeadSubmissionFieldItem` (label, type, value, group).
- `CrmLeadFeatures.LoadSubmissionsAsync` loads fields and attachment counts in one round
  trip each across all of the lead's submissions (keyed by id, grouped in memory) rather
  than per submission — the drawer loads on every row click.
- Field label falls back to `FieldName` when `FieldLabel` is null, ordering is by
  `DisplayOrder`, and grouping is by `GroupName` — all mirroring the Form Details page so
  the two views read identically.
- The drawer's "Source form" block became "Where this lead came from": an expandable card
  per submission. The **newest opens by default**, which covers the common one-submission
  case with zero clicks. The body shows the contact meta grid, grouped field rows,
  attachment count, and an "Open full submission" link.
- Checkbox fields render Yes/No (same as Form Details); everything else prints the raw
  value with `white-space: pre-wrap` so multi-line textarea answers survive.

CSS: the old `a.sub-row` link styles were replaced by `.sub-card` / `.sub-head` /
`.sub-body` / `.sf-*` rules in `LeadsInbox.razor.css`. The unused `.sub-open` rule was
removed. The row-level `.src-form` shortcut in the Source column is unchanged.

### Verification

`dotnet build` clean on Admin and Admin.Application. Four new tests in
`LeadSubmissionLinkTests` cover field content/order/grouping, the label fallback,
per-submission field scoping across multiple submissions, and the attachment count.
Full suite: 404 passed, 0 failed.

Caveat worth remembering: the admin tests use the EF InMemory provider, so a green run
does not prove the new `ids.Contains(...)` + `GroupBy/Count` queries translate on Postgres
(they are ordinary constructs Npgsql handles, but they haven't been run against a real DB).

## To Do Next

- Optional: backfill `Href` on existing `forms.new-submission` notification rows from
  `RelatedEntityId` so historical notifications deep-link too.
- Exercise the lead drawer against a real Postgres dataset to confirm the field query
  translates and performs on leads with many submissions.
