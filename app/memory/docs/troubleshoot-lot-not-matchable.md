---
title: Troubleshoot — lot isn't appearing in matching
audience: supply-ops, deal-ops
slug: troubleshoot-lot-not-matchable
surface: troubleshooting
---

# Troubleshoot — lot isn't appearing in matching

## Symptom

- Supply ops can see a lot on **[Inventory Lots](/v3/supply/inventory)** but it doesn't appear on **[Match Engine](/v3/deal-flow/match-engine)** when ops opens the lot picker.
- A buyer's demand on **[Demand Book](/v3/crm/demand)** shows "No candidates computed yet" or a small candidate list missing a lot ops expected to see.
- A lot doesn't show on the public **[Marketplace · Spot tab](/marketplace)** Spot board even though it looks complete on the admin side.

## Common causes

1. **Lot hasn't reached `LISTED` yet.** The single most common cause. **[Match Engine](/v3/deal-flow/match-engine)** only shows lots in `LISTED` state — `CLAIMED`, `SOURCED`, and `GRADED` are all pre-LISTED and won't appear in the picker. The in-app cure-banner on **[Inventory Lots](/v3/supply/inventory)** focuses on the most common gate (*"Claimed ≠ matchable. Broker / inbound inventory enters as CLAIMED (unverified)…"*) but the same logic applies to anything before LISTED: not published yet means not in the matching console.
2. **Lot is already past `LISTED`** — once bound to a deal (`RESERVED` / `ALLOCATED` / `DEPLOYED`), it's no longer free supply and won't appear in matching for new demands.
3. **Spec mismatch is a hard exclusion on the 3-sided matcher** — a site that requires capabilities the lot's matching operator doesn't claim is excluded by hard filter, not penalised.
4. **Match-refresh worker hasn't run yet** — the **Top Ranked Lots** section on **[Demand Book](/v3/crm/demand)** populates in the background. New lots / demands won't have rankings until the worker's next run.

## Where to verify (admin side)

- **[Inventory Lots](/v3/supply/inventory)** — find the lot. Check the **State** column:
  - `CLAIMED` / `SOURCED` / `GRADED` — pre-LISTED; won't appear in the Match Engine picker
  - `LISTED` — eligible; should appear
  - `RESERVED` / `ALLOCATED` / `DEPLOYED` — already bound to a deal; out of free supply
- **[Match Engine](/v3/deal-flow/match-engine)** — if the lot is `LISTED`, search for it in the typeahead. If it still doesn't appear, the matching service isn't seeing it as eligible — escalate.
- **[Demand Book](/v3/crm/demand)** — if a buyer's demand has empty **Top Ranked Lots**, check whether the demand state is `OPEN` or `REVERIFY` (only those participate in matching).
- **[Sites](/v3/intake/sites)** (for 3-sided) — if the operator-side mismatch is suspected, check the site's **Required Capabilities** chips against the operator's capabilities on **[CRM Accounts](/v3/crm/accounts)**.

## Resolution steps

- **If pre-LISTED (`CLAIMED` / `SOURCED` / `GRADED`):** open the lot drawer and walk it forward through the lifecycle one advance at a time — **Confirm & Source →**, then **Mark Graded →**, then **Publish to Inventory →**. The lot enters the Match Engine picker the moment it reaches `LISTED`. (See the seven-state lifecycle in **[Inventory Lots](/v3/supply/inventory)**.)
- **If bound to a deal:** that's expected. The lot is consumed. Don't try to re-list it; if the deal needs to be unwound, that's a separate workflow.
- **If hard-excluded by capability:** decide whether to relax the site's **Required Capabilities** on **[Sites](/v3/intake/sites)** (the only mutation that page allows is **Available kW**, so a capability edit needs a separate workflow), or accept the exclusion.
- **If the matcher just hasn't run yet:** wait for the next match-refresh cycle. Newly-created lots and demands take a refresh interval before showing up. There's no in-page "refresh now" button on the demand or the lot pages.

## Related docs

- **[Inventory Lots](/v3/supply/inventory)** — the seven-state lifecycle and the `CLAIMED ≠ matchable` gate
- **[Match Engine](/v3/deal-flow/match-engine)** — lot-driven matching (two-sided)
- **[Matching · 3-sided](/v3/deal-flow/matching)** — site-driven matching (three-sided) including the hard capability filter
- **[Demand Book](/v3/crm/demand)** — the Top Ranked Lots ranking and the async match-refresh worker
- **[Sites](/v3/intake/sites)** — Required Capabilities chips
