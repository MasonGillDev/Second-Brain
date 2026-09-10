---
title: Troubleshoot — Missing Daily Summaries on a rental
audience: finance
slug: troubleshoot-missing-daily-summaries
surface: troubleshooting
---

# Troubleshoot — Missing Daily Summaries on a rental

## Symptom

- The **Missing Daily Summaries** KPI card on **[Rental Billing History](/admin/financials/rental-billing)** is non-zero (yellow).
- The **Coverage** filter set to **Missing Daily Summaries** returns rentals.
- An individual rental's Coverage badge reads `RBR Only`.
- A customer dispute lands on **[Rental Billing History](/admin/financials/rental-billing)** with the `RBR Only` badge and a muted `—` in the Discrepancy column (no Daily total to compare against).

## Common causes

1. **The rental started before daily summary recording was enabled** — historical data; backfill candidates.
2. **A telemetry gap during the rental period** — daily summary writes were missed for a window.
3. **A rental that was finalized via a manual / out-of-band path** — the RBR was created but no daily-records pipeline ran.

## Where to verify

- **[Rental Billing History](/admin/financials/rental-billing)** — set Coverage filter to **Missing Daily Summaries**. Every row in the result needs daily-records backfill.
- The **Top KPI card** (Missing Daily Summaries) shows the count for the current period filter — useful for "how big is the backlog."
- For an individual rental, check the **Daily Total** column — if it's a muted dash with the RBR Total populated, it's a Missing Daily case.

## Resolution steps

- **Backfill is an out-of-band ops process.** The page itself doesn't run a backfill — the **[Rental Billing History](/admin/financials/rental-billing)** page is read-only for these mutations.
- **Export the rentals needing backfill** using the page's **Export** group with Coverage = **Missing Daily Summaries**. The resulting Excel file is the worklist for the backfill task.
- **Until backfill runs, treat the RBR as authoritative for those rentals.** The Discrepancy column will continue showing a muted dash, but the RBR Total is the canonical bill.
- **For customer-facing reporting:** a `RBR Only` rental will not appear on **[Daily Billing Summary](/admin/financials/daily-billing)** for that period — which can confuse a customer comparing the two views. Walk them through the difference: Daily Billing Summary is *date-accurate from daily records*; if those records don't exist, the rental doesn't show.

## Related docs

- **[Rental Billing History](/admin/financials/rental-billing)** — the Coverage filter and the Discrepancy column
- **[Daily Billing Summary](/admin/financials/daily-billing)** — date-accurate view (skips RBR Only rentals)
- **[Troubleshoot — customer disputes a billing charge](/admin/financials/rental-billing)** — the broader dispute playbook
