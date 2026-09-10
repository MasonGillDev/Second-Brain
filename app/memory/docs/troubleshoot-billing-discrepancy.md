---
title: Troubleshoot — customer disputes a billing charge
audience: finance, support
slug: troubleshoot-billing-discrepancy
surface: troubleshooting
---

# Troubleshoot — customer disputes a billing charge

## Symptom

A customer says: *"Your invoice shows $X but I think it should be $Y"* or *"My wallet was debited but I don't see the rental that explains it."*

## Common causes

1. **RBR and Daily Summary disagree** — the canonical reconciliation: the **end-of-rental Rental Billing Record** doesn't match the **sum of daily records**. The **Discrepancy** column on **[Rental Billing History](/admin/financials/rental-billing)** is the source of truth for this disagreement.
2. **Missing Daily Summaries** — RBR exists but daily records don't; the customer is looking at one of the two views and not seeing what the other shows.
3. **Daily Only, not yet finalized** — the rental is `Active` or `Ended` but not `Finalized`. The customer sees daily totals; finance hasn't cut the RBR yet.
4. **Wallet Only** — money moved but neither RBR nor daily records exist. The worst case — investigate immediately.
5. **Wrong period selected on Usage History** — the customer's `/consumer/usage-history` filter is set to a period that excludes the rental.
6. **Sub-cent precision drift** — both pages show 4-decimal currency. A small diff (`$0.0023`) is real precision, not a bug.
7. **Rental is on a different account** — customer is signed in as a different user than the one that owned the rental.

## Where to verify (admin side)

- **Open [Rental Billing History](/admin/financials/rental-billing)** and search for the customer's instance or server name. Pull the row.
  - **Discrepancy column** — colour tells the story:
    - Green (< $1 absolute) — RBR and Daily agree. The dispute is probably about something else (wrong period, wrong account).
    - Red (positive) — RBR is *higher* than Daily. Customer was billed more on the finalized record than daily records account for. Common cause: a billing-period correction at finalization.
    - Yellow (negative) — RBR is *lower* than Daily. Under-charged.
    - Muted dash — one of the sources is missing entirely.
  - **Coverage column** — `Full` (both sources), `RBR Only`, `Daily Only`, `Wallet Only`. Tells you which source is absent.
  - **Expected column** — what the RBR *should* total based on hours × rate. If RBR Total disagrees with Expected, the RBR has internal inconsistency.
- **Open [Daily Billing Summary](/admin/financials/daily-billing)** filtered to the same period for date-accurate per-day numbers.
- **Cross-check with [Customers](/customers)** → row drawer → Instances tab to confirm the rental belongs to the disputing customer.

## Resolution steps

- **If Discrepancy is green (< $1):** the books agree. The issue is somewhere else — wrong account, wrong period, or a customer misunderstanding. Walk them through Usage History on `/consumer/usage-history` showing the matching period.
- **If Discrepancy is red (RBR > Daily):** the finalized record is higher. Surface the **Expected** column — if Expected and RBR agree, the daily records were incomplete (Missing Daily Summaries — a backfill job is the eventual fix; until then, RBR is authoritative). If Expected disagrees with RBR, the RBR has its own internal issue — escalate to finance.
- **If Discrepancy is yellow (RBR < Daily):** under-charge. Confirm whether finance issued the under-charged amount intentionally (e.g. a service-credit). If not, the daily records were over-counting — escalate.
- **If Coverage = Daily Only:** the rental hasn't been finalized yet. The RBR will be cut later. Tell the customer the daily total is provisional; the finalized number may differ slightly.
- **If Coverage = Wallet Only:** **escalate immediately**. Money moved with no billing record explaining why. This is the worst state.
- **If wrong account:** check **[CRM Accounts](/v3/crm/accounts)** to confirm the binding. If the customer signed in with a different account than expected, route them to the correct one.

## Related docs

- **[Rental Billing History](/admin/financials/rental-billing)** — the per-rental reconciliation view (RBR vs Daily vs Wallet)
- **[Daily Billing Summary](/admin/financials/daily-billing)** — date-accurate per-day totals
- **[Customers](/customers)** — customer directory with wallet + instance context
- **[Consumer portal (customer flow)](/consumer/dashboard)** — what the customer sees on `/consumer/usage-history` and `/consumer/wallet`
- **[Troubleshoot — missing daily summaries](/admin/financials/rental-billing)** — when the Coverage filter shows Missing Daily Summaries
