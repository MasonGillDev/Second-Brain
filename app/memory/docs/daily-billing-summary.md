---
title: Daily Billing Summary
route: /admin/financials/daily-billing
audience: finance, support
slug: daily-billing-summary
surface: admin
---

# Daily Billing Summary

The Daily Billing Summary is the **date-accurate** view of every rental's billing — totals are built up from per-day records rather than from end-of-rental finalization. Use it when finance needs revenue, provider earnings, and platform commission broken out by date range, or when support needs to confirm what a specific customer or provider was billed inside a given period. Open it at **Financials → Daily Billing** (`/admin/financials/daily-billing`).

The companion view is [Rental Billing History](/admin/financials/rental-billing), which reconciles daily totals against end-of-rental records.

## Page layout

- **Header** — page title, page description, and the **Back to Financials** link in the top right next to the **Export** group
- **Filter card** — period, organization search/picker, status, and free-text search
- **Stat-card grid** — four KPI cards: Total Rentals, Customer Charges, Provider Earnings, Commission
- **Data grid** — one row per rental, paginated 50 per page
- **Pagination footer** — `Showing X–Y of N rentals` on the left, **Previous** / **Next** on the right

## The four KPI cards

These always reflect the **currently-filtered** result set, not the all-time total.

- **Total Rentals** — count of rentals with daily billing data inside the period. Subtitle: *"With daily billing data."*
- **Customer Charges** — total billed to customers across those rentals.
- **Provider Earnings** — total credited to providers across those rentals.
- **Commission** — platform revenue = Customer Charges − Provider Earnings.

The numbers tie out exactly: Customer Charges = Provider Earnings + Commission for the same filter.

## Filter the list

All filters apply server-side and reset to page 1 when changed.

### Period

The **Period** dropdown is the primary filter. Options:

- **All Time** (default)
- **Current Month**
- **Last Month**
- **Q1 (Jan-Mar)**, **Q2 (Apr-Jun)**, **Q3 (Jul-Sep)**, **Q4 (Oct-Dec)** — current year
- **Last Year**
- **Year 2025**, **Year 2026** — specific calendar years
- **Custom Range** — reveals **Start Date** and **End Date** inputs plus an **Apply** button

When **Custom Range** is selected, the inputs appear inline and the filter does **not** auto-apply — click **Apply** to load.

### Organization

Two controls work together:

1. **Search Org** — type-to-filter input. Filters the choices that appear in the dropdown below; does not filter the rental list directly.
2. **Organization** — dropdown showing matching orgs. Default placeholder is **All Organizations**. Picking one filters the grid to rentals where that org is either the **customer** or the **provider**.

To clear the org filter, open the dropdown and pick the empty option.

### Status

The **Status** dropdown:

- **All** (default)
- **Active** — rentals still running
- **Finalized** — rentals that have been closed out

### Search

Free-text **Search** input at the right of the filter row matches against **instance name** or **server name**. Typing applies on a 400ms debounce — wait briefly after typing for the grid to refresh.

## Columns

One row per rental, twelve columns:

- **Instance** — instance name (or the first 8 chars of the rental ID if unnamed), with the **server name** beneath
- **Customer** — customer organization name
- **Provider** — provider organization name
- **Period** — rental start date on top (`MMM dd`), end date below or **Active** if still running
- **Days** — number of billed days
- **Hours** — total hours billed to two decimals
- **Rate** — hourly rate (`$0.1234/hr`) or `-` if zero
- **Customer Charges** — amount billed to the customer over the filtered period, in light blue
- **Provider Earnings** — amount credited to the provider, in light green
- **Commission** — platform's cut, in lavender (`#cba6f7`)
- **Status** — pill: **Active** (green) / **Finalized** (dark) / **Ended** (yellow)

All currency columns render with four decimal places (`$0.1234`) because GPU-hour rates routinely have sub-cent precision.

The grid does not support inline column sorting — order is set server-side. There is no row-click drawer; this is a flat report.

## Export to Excel

Three export buttons in the **Export** group in the page header. Each downloads an `.xlsx` file containing the **currently-filtered** rentals (period, org, status, and search all applied).

- **Consumer** — the customer-side view of the data
- **Provider** — the provider-side view
- **Both** — combined workbook

Click any button to start the export. The buttons are disabled while an export is running. When the file is ready, the browser downloads it automatically — no toast confirmation.

If an organization is selected in the **Organization** filter, its name is woven into the filename so the file is self-identifying.

## Pagination

Results are paginated **50 rentals per page**.

- **Previous** is disabled on page 1.
- **Next** is disabled when the current page returns fewer than 50 rows.
- The counter on the left reads `Showing X–Y of N rentals` — `N` is the total across the current filter, not the grand total.

There is no jump-to-page or page-size selector.

## Active vs Finalized vs Ended — what each status means

- **Active** — the rental is still running and daily records are still being appended.
- **Finalized** — the rental has been closed out and the totals are locked.
- **Ended** — the rental ended but hasn't been finalized yet; the totals on this page are still based on the last daily record.

Finance should treat **Ended** rows as provisional until they flip to **Finalized**.

## Things to know

- **Date-accurate, not finalization-accurate.** This page sums per-day records to give a date-aware total — exactly what you want for "how much was billed in March." For the canonical end-of-rental total, use the **RBR Total** column on [Rental Billing History](/admin/financials/rental-billing).
- **The KPI cards follow the filters.** Every card recalculates whenever a filter changes. There is no "all-time" hero number on this page.
- **Currency precision is 4 decimals.** Rates like `$0.1234/hr` mean sub-cent precision is real — don't round in your head when reconciling against another source.
- **Org filter is "either side."** Picking an organization shows rentals where that org is **customer or provider**. If you need just one side, scan the Customer / Provider columns after filtering.
- **Search is debounced.** After typing in the **Search** box, give it ~400ms before assuming results haven't loaded.
- **Custom date range needs Apply.** Standard period presets auto-apply on change, but Custom Range does not — click **Apply** after picking the start and end dates.
- **Daily-only rentals show up here.** A rental that has daily summary records but no end-of-rental record will still appear on this page (it just won't have a finalized total). The Rental Billing History page flags those rentals as **Daily Only** under its Coverage column.
- **No drill-down.** Rows are not clickable. To dig into a specific rental's full reconciliation (RBR vs daily vs wallet), open [Rental Billing History](/admin/financials/rental-billing) and search for the same instance.
- **Exports respect every active filter.** Changing the Period or Status, then exporting, gives you a file that contains only what the grid is currently showing. Verify the filter row before clicking export.
