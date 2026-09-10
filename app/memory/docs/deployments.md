---
title: Deployments
route: /v3/deal-flow/deployments
audience: deal-ops, supply-ops, finance
slug: deployments
surface: admin
---

# Deployments

Deployments is the live-clusters view — every deal that has reached **LIVE** on **[Deal Pipeline](/v3/deal-flow/pipeline)** turns into a **Deployment** here, carrying its power envelope, GPU count, pre-sold offtake ratio, and monthly recurring revenue. Use it to answer "what's in production right now," "what's our MRR," and "what's degraded." Open at **V3 Deal Flow → Deployments** (`/v3/deal-flow/deployments`).

The page is **read-only**. Deployment status transitions are driven by the SLYD Cloud telemetry layer, not by an admin click. Customer-side, what these deployments look like to a buyer or operator lives in the **[Consumer portal](/consumer/dashboard)** and the **[Provider portal](/provider/dashboard)** respectively.

## Page layout

- **Header** — page title + subhead reminding ops these are powered by SLYD Cloud and that every LIVE deal becomes a deployment
- **KPI strip** — four cards: Live Clusters, GPUs Deployed, Total MRR, Avg Offtake
- **Filter bar** — status pills + counter on the right
- **Data grid** — one row per deployment

There is no detail drawer — every row is fully self-contained. To dig into a deployment, open its parent **[Deal Pipeline](/v3/deal-flow/pipeline)** record.

## The six deployment statuses

Each deployment moves through a six-status lifecycle, driven by SLYD Cloud:

1. **PROVISIONING** — being stood up; not yet earning
2. **BURN-IN** — under burn-in / qualification; not yet earning
3. **LIVE** — in production, earning MRR
4. **DEGRADED** — running but operating below SLA; usually still earning but flagged
5. **DECOMMISSIONING** — being taken down
6. **RETIRED** — terminal; off the active fleet

The filter pills appear in that order: All → Provisioning → Burn-In → Live → Degraded → Decommissioning → Retired.

Status pill rendering is consistent — green for live, amber for degraded, neutral for terminal/pre-launch states.

## The four KPI cards

All reflect the **currently-filtered** view.

- **Live Clusters** — count of deployments currently in `Live` status. Sub-line *"deployments in LIVE status."*
- **GPUs Deployed** — total GPU count across the visible deployments. Sub-line *"across all deployments."*
- **Total MRR** — sum of monthly recurring revenue across the visible deployments. Sub-line *"monthly recurring revenue."*
- **Avg Offtake** — average pre-sold offtake ratio across the visible deployments (e.g. `64%`). Sub-line *"pre-sold capacity across listed deployments."* Shows `—` when the visible set is empty.

## Filter the list

- **Status pills** — `All` + one pill per status. Single-select.
- **Counter** on the right: `N DEPLOYMENTS · N.N MW SHOWN` for the current filter (MW is `kW / 1000` summed).

There is no free-text search.

## Columns

- **Deploy** — DisplayId (accent mono)
- **Deal** — the parent deal's DisplayId chip, or `—` if not bound to a deal
- **Site** — site name, or `—`
- **Power MW** — `kW / 1000` to one decimal
- **GPUs** — count
- **Offtake** — horizontal bar with the **pre-sold offtake ratio** as a percentage (0–100%), colour-banded:
  - **High** (≥ 70%) — strong green
  - **Mid** (40–69%) — amber
  - **Low** (< 40%) — neutral
- **MRR** — monthly recurring revenue in dollars, or **pre-launch** if zero (deployment hasn't started earning yet)
- **Status** — status pill (Provisioning / Burn-In / Live / Degraded / Decommissioning / Retired)

## How a deployment comes into existence

A deployment is created when the parent **Deal** advances to the **LIVE** stage on **[Deal Pipeline](/v3/deal-flow/pipeline)**:

- **Deal** stage `LIVE` (the four-stage state machine on Deal Pipeline) is the trigger
- The new Deployment starts at status `PROVISIONING`
- It progresses through `BURN-IN` and then `LIVE` driven by SLYD Cloud telemetry, not by admin action
- It can later be marked `DEGRADED` automatically when SLA telemetry slips, and eventually `DECOMMISSIONING` → `RETIRED`

No deployments are created from this page — it's a downstream view.

## What ops *cannot* do here

- Create a deployment manually
- Change a deployment's status (driven by SLYD Cloud telemetry)
- Edit power, GPU count, MRR, or offtake ratio
- Click a row for a detail drawer (no drawer)
- Click the **Deal** chip to navigate (display-only)
- Trigger a re-scan or refresh manually
- Export to CSV / Excel

## Things to know

- **MRR `pre-launch` means $0 today, not "never."** A deployment that's still `PROVISIONING` or `BURN-IN` shows MRR `pre-launch`. It will flip to a dollar amount when the deployment moves to `LIVE`.
- **The Avg Offtake KPI includes every visible deployment.** If you filter to `Live` only, the average is across live deployments. If you filter to `Provisioning`, you see the pre-launch offtake target — useful for sizing.
- **Status is admin-read-only.** SLYD Cloud telemetry owns transitions. If ops thinks a `LIVE` deployment is actually degraded, that's a telemetry-side fix, not an in-page action.
- **A deployment without a parent deal shows `—` in the Deal column.** Rare; usually indicates the deal record was deleted or never bound. Investigate via **[Deal Pipeline](/v3/deal-flow/pipeline)**.
- **Offtake bar colour bands are fixed thresholds.** `<40%` low, `40-69%` mid, `≥70%` high. Use them as a quick triage signal, not a precise number — the percentage is also printed next to the bar.
- **Counter MW is summed kW.** `N DEPLOYMENTS · X.X MW SHOWN` — that MW is the sum of `PowerKw` across the filter, divided by 1000.
- **Customer-side equivalents.** A buyer sees their resources of these deployments in **[Consumer portal](/consumer/dashboard)** at `/consumer/my-resources`; a provider sees their hosted clusters in **[Provider portal](/provider/dashboard)** at `/provider/active-instances`.
- **Related surface — [Deal Pipeline](/v3/deal-flow/pipeline).** Every deployment has a parent deal in pipeline. Open the deal to see the full party / escrow / document / lot history. The deployment is the post-LIVE operational record.
