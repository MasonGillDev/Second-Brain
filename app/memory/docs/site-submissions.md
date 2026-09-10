---
title: Site Submissions
route: /v3/intake/site-submissions
audience: supply-ops, deal-ops
slug: site-submissions
surface: admin
---

# Site Submissions

Site Submissions is the admin queue for the **public Bring-Energy intake** — every site capacity submitted through the public **[Bring energy to SLYD (customer flow)](/marketplace/power-opportunities)** form on slyd.com. Each row is a `SiteSubmission` record carrying the submitter's stated source, capacity, region, and contract terms. Ops triages, optionally declines, and (when due diligence clears) converts the submission into a real Site on **[Sites Registry](/v3/sites)** — that's the row the three-sided matching engine consumes.

Open at **V3 Overview → Site Submissions** (`/v3/intake/site-submissions`).

> **Naming note.** Earlier versions of the admin used the title "Site Submissions" for the Site-entity registry at `/v3/intake/sites`. That page has moved to **[Sites Registry](/v3/sites)**. This page is the new intake-queue surface that owns the public submissions before they become real Sites.

## Page layout

- **Header** — page title + subhead
- **Filter bar** — status pills (All / Submitted / In Review / Converted / Declined / Withdrawn) with counts
- **Left panel** — submissions table
- **Right panel** — drawer with the full submitted payload, owner info, and status-transition actions
- **Banners** at the top — success / error feedback

Clicking a row opens the drawer.

## Statuses

A submission moves through these states. The first two are working states; the last three are terminal.

1. **Submitted** — initial state, awaiting ops review
2. **In Review** — ops has begun due diligence
3. **Converted** — ops has promoted the submission into a Site on **[Sites Registry](/v3/sites)** (terminal). The Site DisplayId appears in the drawer.
4. **Declined** — ops decided not to promote (terminal)
5. **Withdrawn** — customer cancelled (terminal)

Every transition is enforced by the SiteSubmission entity's state machine and writes a hash-chained Audit Log entry.

## Table columns

- **ID** — Submission display ID (mono, `SITESUB-YYYYMMDD-XXXX`)
- **Source** — energy source descriptor (Stranded gas / Hydro / Grid / etc.), with the availability sub-line if set
- **Capacity** — available kW, with `$/MWh` sub-line if the submitter quoted one
- **Region** — ISO label or freeform region
- **Commercial** — purchase / lease / hosted, or `—`
- **Owner** — owning Account name + email if the submission has been claimed; **Unclaimed** in dim text otherwise
- **Age** — relative time since submission (`12m`, `4h`, `3d`)
- **Status** — color-coded pill

## Filter the list

1. Click a status pill — All / Submitted / In Review / Converted / Declined / Withdrawn. The count on each pill reflects the unfiltered total in that status.
2. The counter on the right shows `<N> SHOWN · <N> TOTAL`.

There is no free-text search and no ISO/source filter (yet) — use the source column or browse.

## Inspect a submission

Click any row. The drawer shows:

### Header

- **`Source · N kW`** as the heading
- **DisplayId · status pill · converted Site DisplayId** (if any)

### Detail grid

- **Source** — energy source descriptor
- **Available kW** — capacity the submitter said is available
- **Region** — ISO label or freeform
- **Availability** — when capacity comes online
- **Cost** — `$X/MWh` if quoted, `—` otherwise
- **Term** — months of commitment if quoted
- **Commercial** — purchase / lease / hosted
- **Move-in** — free-text window from the form
- **Structure** — building/pad/shell readiness
- **Water** — yes/no/descriptor
- **Fiber** — yes/no/descriptor
- **Created** — submission timestamp

### Owner section

- If the submission has been **claimed** (the submitter completed sign-in post-submit): shows owning Account name, the submitter's email, and the **Claimed at** timestamp.
- If **Unclaimed**: a dim note explains the submitter never completed sign-in. The row stays workable — ops can still triage it — but there's no linked SLYD user account.

### Notes

Free-form text the submitter typed in the **Notes** field on the public form. Renders only when present.

## Begin reviewing a Submitted submission

1. Open a submission in **Submitted** status.
2. In the drawer's actions row, click **Begin Review →**.
3. The submission moves to **In Review**; the drawer's action options change (Decline + Withdraw remain; Begin Review is gone).
4. The audit kind written is `site-submission.review` against the submission's DisplayId.

## Mark a submission Declined

Available from **Submitted** or **In Review**.

1. In the drawer, click **Mark Declined**.
2. The submission moves to **Declined** (terminal) and is logged for record-keeping.
3. Audit kind: `site-submission.declined`.

## Mark a submission Withdrawn

Available from **Submitted** or **In Review**.

1. In the drawer, click **Mark Withdrawn**.
2. The submission moves to **Withdrawn** (terminal).
3. Audit kind: `site-submission.withdrawn`.

Withdrawn vs Declined semantics: **Withdrawn** = customer pulled out, **Declined** = ops decided no. Use the right one for the audit trail.

## Convert a submission into a Site

**Not yet a button on this page.** The drawer shows a hint when the submission is in **In Review**: *"Conversion to a real Site is a separate workflow — coming in a follow-up phase."* When that workflow lands, the action will populate **Sites Registry** with a real `Site` row and stamp the submission's `ConvertedSiteId`, transitioning it to **Converted**.

For now, ops with the relevant permission creates the Site row directly on **[Sites Registry](/v3/sites)** and the submission stays in **In Review** (or gets marked **Declined**) until the conversion workflow ships.

## What ops *cannot* do here

- Edit any of the submitted fields (no inline edit; the submission is read-only after intake)
- Convert to a Site (the workflow isn't built yet — see above)
- See the public form fields that map differently from the entity (the page reads the persisted columns directly)
- Reach the buyer from the page (use the email shown in the Owner section)

## Things to know

- **Public intake only.** Every row here came from the public form at slyd.com/marketplace/power-opportunities. Ops-created sites skip this surface and land directly in **[Sites Registry](/v3/sites)**.
- **Claim status is independent of submission status.** A submission can be **Submitted** + Unclaimed (the typical fresh state if the submitter abandoned sign-in), **Submitted** + claimed (sign-in completed), or **Converted** + claimed. Ops can act on either; the claim state just controls who owns the linked Account.
- **The audit chain is hash-chained.** Every transition writes a before/after snapshot to **[Platform Audit](/v3/platform/audit)** — kinds: `site-submission.review`, `site-submission.declined`, `site-submission.withdrawn`. Includes the actor.
- **The legacy FormSubmission still lands in `/admin/forms`.** During the migration window the submit endpoint writes both the structured `SiteSubmission` row (visible here) AND a parallel `FormSubmission` (visible in the generic forms inbox). Same data, two places — the structured row is the system of record.
- **Terminal states are forever.** Declined, Withdrawn, and Converted cannot be reverted from this page — escalate.
- **No role gates visible** on this page; all actions assume admin privilege.
