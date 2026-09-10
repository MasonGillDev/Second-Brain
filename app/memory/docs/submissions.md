---
title: Submissions
route: /v3/intake/submissions
audience: deal-ops, supply-ops
slug: submissions
---

# Submissions (V3 Intake)

The Submissions page is the deal-intake queue for hardware-sell submissions that come in from the public Sell surface. Ops review incoming seller offers, issue firm recovery offers, and on acceptance convert submissions into sourced inventory lots. Open it at **V3 Intake → Submissions** (`/v3/intake/submissions`).

Every submission is logged regardless of outcome — closed, rejected, and lost states are terminal and stay on record.

## Where these come from

Sellers fill the public form at **[slyd.com/hardware-sales](/hardware-sales)** and sign in on submit. The submission lands on this page in **New** status with the seller's account already linked — see **[Sell hardware to SLYD (customer flow)](/hardware-sales)** for the buyer-side walkthrough including what the seller sees on their own dashboard and the per-submission edit page at **/sell/submissions/{id}**.

## Page layout

Split-grid two-panel layout:

- **Left panel** — filterable list view with status pills
- **Right panel** — detail drawer with full submission data, manifest, actions, and settlement tracking
- **Filter bar above the list** — status pills (All / New / Review / Offered / Closed / Rejected / Lost) with counts, plus a "SHOWN · TOTAL" counter
- **Banners at page top** — success/error feedback from actions

## Statuses

A submission moves through these states in order. The first four are working states; the last three are terminal.

1. **New** — initial state, awaiting review
2. **Review** (In Review) — admin has begun evaluation
3. **Offered** — firm recovery offer issued to the submitter
4. **Closed** — converted to inventory lot(s) (terminal)
5. **Rejected** — admin declined the submission (terminal)
6. **Lost** — submission lost after offer (terminal)

Every transition is enforced by the SellSubmission entity's state machine and writes a hash-chained AuditEvent.

## List columns

- **ID** — Submission display ID; if converted, the converted lot ID appears below in accent color
- **Hardware** — Type × Quantity (e.g. "H100 × 2000"); sub-text shows line count and manual-quote count if present
- **Est. Range** — Indicative valuation band (e.g. "$960K – $1.18M")
- **Submitter** — Name; email as sub-text
- **Age** — Time since submission (e.g. "3d", "5h", "47m")
- **Status** — Color-coded pill

## Filter and open a submission

1. Click a status pill in the filter bar to narrow the list. The pill badge shows the count in that status. "All" shows the total.
2. Click any row to select it. The detail drawer on the right populates with the full submission. The row highlights with a "selected" background.

## Begin reviewing a New submission

1. Open a submission in **New** status.
2. In the drawer, click **Begin Review →**.
3. The submission moves to **In Review** and the Firm Recovery Offer section becomes editable.

## Issue a firm recovery offer

1. Open a submission in **In Review** status.
2. In the **Firm Recovery Offer · editable** section, the engine pre-fills the indicative range mid-point.
3. Override the amount in the dollar input field if needed.
4. Click **Issue Offer →**.
5. Submission moves to **Offered**; the offer is locked and the submitter is notified.

## Reject a submission

Available from **New**, **In Review**, or **Offered**.

1. In the drawer, click **Mark Rejected**.
2. The submission moves to **Rejected** (terminal) and is logged for record-keeping.

## Mark an offer as lost

Available only from **Offered**.

1. In the drawer, click **Mark Lost**.
2. The submission moves to **Lost** (terminal) and is logged.

## Accept an offer and convert to inventory

This is the path that converts an Offered submission into one or more sourced lots. The drawer behavior depends on whether the submission has multiple manifest lines.

### Multi-line submission (batch convert)

When the submission has multiple manifest lines, the **Accept & bring into inventory** card appears with line checkboxes:

1. In the manifest table, check the lines you want to accept. **Unchecked lines are declined** — no lot is created and no payout is owed, but they stay on the submission record as a permanent decision for the audit chain.
2. For checked lines flagged **MANUAL QUOTE** (no indicative band), fill in the **Sale $/unit** column — required for those rows.
3. Fill the conversion fields:
   - **Location (ISO)** — e.g. "ERCOT"
   - **Payout path** — Pay on inspect (50/50) / Consignment / Buy-out upfront
   - **Amount owed to seller** — optional
4. Click **Accept N line(s) → create N lot(s) →**.
5. Each checked line becomes one **SOURCED** inventory lot. The submission moves to **Closed**.

### Single-line or manual conversion

When the submission has no lines (or you choose manual conversion), click **Accept & Convert to Lot →** to open a single form: GPU Model, Quantity, Grade (dropdown), ISO, Rate $/GPU·hr, Cost basis $/GPU·hr, Payout path, Amount owed. Submit to create one lot and close the submission.

## Payout paths

The payout path determines ownership and timing:

- **Buy-out upfront (1 day)** — SLYD owns the lot
- **Pay on inspect (50/50, 1–4 weeks)** — SLYD owns the lot
- **Consignment (8–17 weeks)** — SLYD sells the lot **for the seller**; lot status is CONSIGNED rather than owned

A fourth path, **Auction sale**, is settlement-only — written by the auction close job. It's not a manual conversion option.

## Record a seller settlement payment

When a Payout record exists for an accepted submission (status Scheduled or PartiallyPaid), the **Record payment** card appears in the drawer:

1. Enter the **Amount $** paid.
2. Enter the **Wire reference** (placeholder *FED-…*).
3. Click **Record payment →**.

> The platform records settlement; the bank executes it. Every record lands on the audit chain.

The Settlement section shows: Settlement ID, Path label, Status pill, Scheduled amount, Paid amount + wire reference.

## Things to know

- **Declined lines are permanent.** Once you accept a multi-line submission, unchecked lines are recorded as declined in the audit event and cannot be retroactively accepted from this submission.
- **Manual quote lines** require a per-line **Sale $/unit** during batch convert — the indicative band is absent for those.
- **Default offer is mid-point.** If you don't override, the offer defaults to the rounded mid-point of the indicative band.
- **Terminal states are forever.** Closed, Rejected, and Lost cannot be reverted — they exist for provenance.
- **No role gates visible** in this page; all actions assume admin privilege.
- **The seller sees a parallel view of every submission** on their own dashboard at **/v3/dashboard** under the **My Sell Submissions** panel, and can self-serve edit certain fields on **/sell/submissions/{id}** while the status is still early. Customer edits stamp a separate timestamp from ops edits — you can tell which side made the last change. Full walkthrough: **[Sell hardware to SLYD (customer flow)](/hardware-sales)**.
- **Submitter sign-in is required on the website.** Every row here is already linked to a SLYD user account. There are no anonymous submissions in v1; if you see one without a linked account, the seller hit a stale claim link and ops can link by hand.