---
title: Rental Billing History
route: /admin/financials/rental-billing
audience: finance, support
slug: rental-billing-history
surface: admin
---

# Rental Billing History

The Rental Billing History page is the **per-rental reconciliation** view. It puts the three independent billing sources for each rental — the end-of-rental **RBR** (Rental Billing Record), the **Daily Summaries** built up day by day, and the **Wallet Transactions** that actually debited the customer and credited the provider — side-by-side so finance can see at a glance whether they agree. Use it whenever revenue numbers don't match, whenever a customer disputes a charge, or whenever you need to confirm a rental's three sources are all on file. Open it at **Financials → Rental Billing** (`/admin/financials/rental-billing`).

The companion view is [Daily Billing Summary](/admin/financials/daily-billing), which gives the date-accurate totals without the cross-source reconciliation.

## Page layout

- **Header** — page title, page description, the **Back to Financials** link, and the **Export** group
- **Filter card** — period, organization search/picker, status, **Coverage**, and free-text search
- **Top stat-card row (4 cards)** — totals and exception counters
- **Second stat-card row (4 cards)** — coverage breakdown
- **Data grid** — one row per rental, paginated 50 per page
- **Pagination footer** — `Showing X–Y of N rentals` on the left, **Previous** / **Next** on the right

## The eight KPI cards

All cards reflect the **currently-filtered** result set, not all-time totals.

**Top row — totals and exceptions:**

- **Total Rentals** — count of rentals with any billing data inside the period
- **Customer Charges** — total billed to customers across those rentals
- **Missing Daily Summaries** — count of rentals where the RBR exists but daily records don't. Card goes **yellow** when above zero, **green** when clean.
- **Discrepancies** — count of rentals where the RBR total and the daily-summary total don't agree (more than $1 apart). Card goes **red** when above zero, **green** when clean.

**Second row — coverage breakdown:**

- **Both Sources** — rentals that have **both** an RBR and daily summaries (the healthy state). Always green.
- **RBR Only** — rentals with a finalized RBR but no daily summary records. Yellow when above zero.
- **Daily Only** — rentals with daily records but no RBR (rental hasn't been finalized yet). Blue when above zero.
- **Wallet Txns** — count of rentals that have at least one debit/credit recorded against the wallet.

## Filter the list

All filters apply server-side and reset to page 1 when changed.

### Period

Same options as on [Daily Billing Summary](/admin/financials/daily-billing): **All Time** (default), **Current Month**, **Last Month**, **Q1–Q4**, **Last Year**, **Year 2025**, **Year 2026**, **Custom Range**.

**Custom Range** does not auto-apply — click **Apply** after picking dates.

### Organization

Two controls:

1. **Search Org** — type-to-filter input that narrows the dropdown choices below.
2. **Organization** — dropdown defaulting to **All Organizations**. Picking an org filters to rentals where that org is the customer **or** the provider.

### Status

- **All** (default)
- **Active** — rental still running
- **Finalized** — rental has been closed out

### Coverage — the reconciliation filter

This is the filter unique to this page and the primary triage lever. Options:

- **All** (default)
- **Missing RBR** — rentals with daily summaries but no end-of-rental record. Use this to find rentals that need finalization.
- **Missing Daily Summaries** — rentals with an RBR but no daily records. Use this to find candidates for the daily-summary backfill.
- **Missing Wallet Txns** — rentals billed but not actually debited/credited.
- **Has All Data** — clean rentals with all three sources present.

### Search

Free-text **Search** matches against **instance name** or **server name**. Applies on a 400ms debounce.

## Columns — the reconciliation grid

One row per rental, twelve columns. The first four identify the rental; the middle six are the reconciliation numbers; the last two summarize state.

- **Instance** — instance name (or first 8 chars of the rental ID), with **server name** beneath
- **Customer** — customer organization name
- **Provider** — provider organization name
- **Period** — rental start date on top (`MMM dd`), end date below or **Active** if still running
- **RBR Total** — customer-side amount on the end-of-rental record. Light blue when the RBR exists; muted when missing.
- **Daily Total** — customer-side amount summed from daily records. Light green when daily records exist; muted when missing. A sub-line shows `N days` of data.
- **Expected** — what the RBR *should* total based on its billing period (hours × rate). Lavender. The sub-line shows `N.N hrs` from the billing period.
- **Discrepancy** — `RBR Total − Daily Total`. Colour-coded:
  - **Light green** — under $1 in absolute value (healthy)
  - **Red (`#f38ba8`)** — positive (RBR > Daily — customer over-charged relative to daily records)
  - **Yellow** — negative (RBR < Daily — under-charged)
  - Muted dash — not computable (one of the sources is missing)
- **RBR Hours** — total hours on the RBR with the **implied rate** beneath (`@$0.1234/hr`)
- **Rate** — the rate-card hourly rate
- **Coverage** — badge:
  - **Full** (green) — RBR + daily summaries both present
  - **RBR Only** (yellow)
  - **Daily Only** (yellow)
  - **Wallet Only** (red) — neither RBR nor daily records
- **Status** — pill: **Active** (green) / **Finalized** (dark) / **Ended** (yellow)

All currency renders to four decimal places.

## Export to Excel

Three export buttons in the **Export** group in the page header. Each downloads an `.xlsx` containing the **currently-filtered** rentals (period, org, status, **coverage**, and search all applied).

- **Consumer** — customer-side view
- **Provider** — provider-side view
- **Both** — combined workbook

Buttons are disabled while an export runs; the file downloads automatically when ready. When an org is selected, its name is woven into the filename.

## Pagination

50 rentals per page. **Previous** disabled on page 1; **Next** disabled when the current page returns fewer than 50 rows. The counter on the left shows `Showing X–Y of N rentals` for the current filter — not the grand total.

## Reading the discrepancy column — how to triage

The Discrepancy column is the heart of the page. Common patterns:

- **Green (< $1 absolute)** — RBR and Daily agree within rounding. Nothing to do.
- **Red (positive)** — RBR is **higher** than Daily. The customer was billed more on the finalized record than the daily records account for. Common cause: a billing-period correction made at finalization. Verify against the **Expected** column.
- **Yellow (negative)** — RBR is **lower** than Daily. Often means daily records overshot what was actually finalized. Look at the per-day records via [Daily Billing Summary](/admin/financials/daily-billing) for the same rental.
- **Muted dash** — One of the sources is missing entirely. Check the **Coverage** badge: RBR Only, Daily Only, or Wallet Only tells you which side is absent.

For active rentals, expect Discrepancy to be **muted** until finalization runs.

## What the coverage states tell you

The Coverage column and the four breakdown cards classify every rental into one of four states:

- **Full** — RBR + daily records both present. The reconciliation can be performed; check the Discrepancy column.
- **RBR Only** — finalized record exists but no per-day records were ever written. Candidates for the daily-summary backfill workflow.
- **Daily Only** — per-day records exist but no end-of-rental record. Usually means the rental is still **Active** or **Ended** but not yet **Finalized**.
- **Wallet Only** — money moved but neither billing source exists. This is the worst state and warrants investigation — the customer was charged but there's no record explaining why.

The **Coverage** filter lets you scope the grid to any one of those four states.

## Things to know

- **This page is the only place all three sources are aligned.** RBR alone, daily alone, or wallet alone won't catch reconciliation errors. The Discrepancy column is the source of truth for "do these agree."
- **Coverage and Discrepancy are independent.** A rental can have **Full** coverage *and* a non-zero Discrepancy — both sources are present but they disagree. Both columns matter.
- **Yellow KPI cards flip green when the count hits zero.** **Missing Daily Summaries** and **Discrepancies** go green when the current filter has none — that's a healthy reconciliation, not a missing card.
- **Currency is 4-decimal everywhere.** GPU-hour rates are sub-cent. A `$0.0001` discrepancy is real precision drift, not a display artifact.
- **The Expected column is computed.** `Expected = hours × rate` from the RBR's own billing period. If RBR Total and Expected disagree, the RBR itself has internal inconsistency.
- **Active rentals usually show muted Discrepancy.** Until the rental is finalized and an RBR exists, there's nothing to compare daily records against.
- **The Period column shows rental dates, not billing dates.** The filter scopes by activity in the period, but the column always shows the rental's own start/end.
- **Search is debounced 400ms.** Wait briefly after typing before assuming results.
- **Custom date range needs Apply.** Presets auto-apply; Custom Range doesn't.
- **Org filter is "either side."** Picking an organization includes rentals where that org is customer **or** provider.
- **Exports include every active filter.** That includes the **Coverage** filter — exporting with Coverage = **Missing Daily Summaries** gives a worklist of rentals to backfill.
- **For the date-accurate revenue view, use [Daily Billing Summary](/admin/financials/daily-billing).** That page sums per-day records cleanly for a given period without trying to reconcile against finalized records.
