---
title: Match Alerts
route: /v3/crm/alerts
audience: deal-ops, supply-ops, revenue-ops
slug: match-alerts
surface: admin
---

# Match Alerts

Match Alerts is the matching worker's notification feed — the spine-side proof that the matching round-trip closes. The matching engine fires an alert here every time standing demand or an energy site gets matched, a top candidate changes, a record fails and needs re-verification, or a candidate score moves enough to matter. Ops works the feed by acknowledging each alert, which both takes it off the unacknowledged queue and writes a hash-chained Audit Log entry. Open it at **V3 CRM → Alerts** (`/v3/crm/alerts`).

## Page layout

- **Header** — page title, page subhead, and an **Acknowledge all** button (top right)
- **Filter bar** — kind pills with counts, then an **Unacked only** toggle pill, then an `N UNACKNOWLEDGED` counter on the right
- **Alert feed** — vertically stacked rows, one per alert, newest at the top
- **Banners** at page top — green success / red error feedback

There is no detail drawer — every alert is fully self-contained in its row.

## Alert kinds

Each alert has a kind, shown as a coloured chip on the left side of the row. The filter bar at the top has one pill per kind with its current count.

- **Matched** — the matching worker found a high-confidence pairing between two records (e.g. *"Standing demand DEM-DEMO-002 matched LOT-DEMO-001 (score 91)"*).
- **Failed** — a record failed and needs re-verification (e.g. standing demand whose spec drift puts it past retention).
- **New Top Candidate** — a different candidate took the top slot for a given subject; the previous #1 was displaced.
- **Drop-Off** — a previously-ranked candidate fell off the candidate list entirely.
- **Score Moved** — the top candidate stayed the same but its composite score moved by more than the threshold (e.g. *"Top candidate for DEM-DEMO-004 moved +12 points after new H200 lot"*).

The kind chip on each row is the easiest way to scan the feed — colours are kind-coded.

## Acknowledged vs unacknowledged

This is the only state an alert can be in.

- **Unacknowledged** — the row is visually emphasized (highlighted edge / chip) and has a black **Acknowledge** button on the right.
- **Acknowledged** — the row is dimmer, and the right side shows a green `✓ <admin name>` chip with the name of the admin who acknowledged it.

Acknowledged alerts stay on the page for history. They are never deleted.

## What each alert row shows

- **Kind chip** (left) — `Matched`, `Failed`, `New Top Candidate`, `Drop-Off`, or `Score Moved`
- **Body** — the human-readable summary fired by the matching worker (includes display IDs and any relevant score)
- **Target chip** below the body — `→ Demand`, `→ Lot`, `→ Site` — the entity type the alert points at (only shown if the worker tagged a target)
- **Fired-at relative timestamp** — `just now`, `47m ago`, `3h ago`, `9d ago`, or a full date for older entries
- **Right side** — either an **Acknowledge** button (unacked) or `✓ <admin name>` (acked)

## Acknowledge a single alert

1. Find the alert in the feed.
2. Click the **Acknowledge** button on the right side of its row.
3. The row immediately switches to acknowledged styling and the right side shows `✓ <your name>`.
4. The `N UNACKNOWLEDGED` counter at the top decreases by one.
5. The action is logged to the Audit Log as `alert.acknowledged`.

There is no confirmation dialog and no two-click pattern — acknowledging is a single click.

## Acknowledge all visible alerts

Use this to clear the unacked queue in one go.

1. (Optional) Click a kind pill to scope to one alert kind (`Matched`, `Failed`, `New Top Candidate`, `Drop-Off`, `Score Moved`).
2. Click **Acknowledge all** in the top-right corner of the page.
3. A success banner reads `<N> alerts acknowledged — logged to Audit Log.` (or `<N> alerts (<Kind>) acknowledged — logged to Audit Log.` when a kind filter is active).
4. If there were no unacked alerts in the current scope, the banner reads `Nothing to acknowledge.` instead.
5. The feed reloads — all newly-acked rows now show `✓ <your name>`.

**`Acknowledge all` respects the current kind filter** but **ignores** the `Unacked only` pill — it acknowledges whatever is unacked in the current kind scope. The button is disabled when the unacked counter is zero.

## Filter the feed

Filters compose: the kind pill scopes by alert type, and the `Unacked only` pill independently scopes by ack state.

1. **Kind pills** — click `All`, `Matched`, `Failed`, `New Top Candidate`, `Drop-Off`, or `Score Moved`. Each pill shows the count for that kind. Single-select.
2. **Unacked only** — click to toggle between *all alerts* and *only unacknowledged alerts*. The pill lights up when active.
3. The `N UNACKNOWLEDGED` counter on the right always reflects the total across all kinds, regardless of which filter is active.

There is no free-text search and no date-range filter.

## What ops *cannot* do on this page

- Trigger a re-rank or force a fresh match run from this page
- Click into an alert to see the matching record (the target chip is informational; lot/demand IDs in the body are display-only)
- Un-acknowledge an alert (acks are permanent)
- Delete an alert
- Snooze an alert without acknowledging it
- Reach out to a buyer or seller from the page

To act on an alert, jump to the relevant entity page yourself (Demand Book, Inventory Lots, etc.) using the IDs in the alert body.

## Things to know

- **Acknowledgement is permanent.** There is no un-ack. Once you click **Acknowledge**, that row is acked forever; the only thing that changes is the display style.
- **Single click, no confirm.** Unlike the two-click pattern on the Brokers page, acknowledgement is a single click. **Acknowledge all** is also single-click.
- **Acked alerts stay on the page.** They're retained for history under their kind. Use the **Unacked only** toggle to hide them while triaging the queue.
- **The unacked counter is total, not filtered.** `N UNACKNOWLEDGED` in the filter bar is the count across every kind — it doesn't shrink when you click a kind pill.
- **The kind pill count is total, not unacked.** `Matched (12)` means there are 12 Matched alerts on the page, acked or not — not 12 unacked Matched alerts. Cross-reference the **Unacked only** toggle if you want unacked totals per kind.
- **Body text is the source of truth for entity IDs.** Display IDs and scores are in the body string itself (e.g. *"…DEM-DEMO-002 matched LOT-DEMO-001 (score 91)"*) — not parsed into separate fields. Read the body to know what to look up.
- **Target chip is informational.** `→ Demand` / `→ Lot` / `→ Site` tells you the entity type the alert refers to, but there is no click-through. Open the relevant page yourself.
- **`Acknowledge all` respects the current kind, not the `Unacked only` toggle.** If you're in `All` kinds + `Unacked only`, clicking **Acknowledge all** acknowledges every unacked alert across every kind.
- **Empty state.** When the current filter has no rows, the page shows *"No alerts match this filter."* with a bell-slash icon. Switch the filter to see whether there are alerts in other kinds or states.
- **Related surface — [Automations](/v3/crm/automations).** Automations are the *outbound* glue from app events into the CRM; Match Alerts is the *inbound* notification feed from the matching engine. Both show up here for ops but they fire on different signals.
