---
title: Automations
route: /v3/crm/automations
audience: revenue-ops, deal-ops, supply-ops
slug: automations
surface: admin
---

# Automations

Automations are **trigger → action** rules that wire buyer-facing app events into the CRM without a human in the loop. Every event that should produce a sales signal — a configurator save, a hardware-sell intake submission, a deal that crosses a value threshold — runs through an automation rule that creates a lead, routes ownership, or otherwise fans the event out. Open the page at **V3 CRM → Automations** (`/v3/crm/automations`).

## Page layout

- **Header** — page title, the page-level subhead, and a top-right **N ACTIVE · M PAUSED** counter
- **Card grid** — one card per automation, two-up on wide screens
- **Banners** at the top of the page — green success / red error feedback

There is no detail drawer, no search, no list view — the whole rule set fits on one page as cards.

## What each card shows

Each automation is rendered as a card with the following parts:

- **Name** (top-left, e.g. *Configurator save → Operator lead*)
- **Description** — a sentence explaining what the rule does in plain English
- **On / Off toggle** (top-right) — pill-style switch; on (lit) = enabled, off (dim) = paused
- **When** block — human-readable trigger summary (e.g. `on configurator.save`, `on sell.submit`, `on deal.created`)
- **→ arrow** between trigger and action
- **Then** block — human-readable action summary (e.g. `create operator lead`, `create supply lead`, `route to H. Gandhi`)
- **Footer stats** —
  - Total run count (`23 runs`, `1 run`, `0 runs`)
  - Last-run timestamp as a relative phrase (`last 1d ago`, `last 4h ago`, `last just now`), or `never run`
  - Error count from the last run — `0 errors` in green text, or `N errors` in red text
  - Display ID on the right (e.g. `AUTO-DEMO-1`)

Cards for paused automations render in a dimmed style so the active set stands out at a glance.

## Pause or enable an automation

This is the **only** mutating action on the page.

1. Find the automation card.
2. Click the **on/off toggle** in the top-right corner of the card.
3. The toggle flips immediately (optimistic update) and a green success banner reads `<DisplayId> enabled — logged to Audit Log.` or `<DisplayId> paused — logged to Audit Log.`
4. If the server rejects the change, the toggle flips back and an error banner explains what failed.
5. The header counter (`N ACTIVE · M PAUSED`) updates to reflect the new state.

Every toggle is audited — pausing and re-enabling both write hash-chained Audit Log entries (`automation.enabled` / `automation.disabled`).

## What ops *cannot* do on this page

The page is enable/disable-only in v1. The following are **not** available here:

- Create a new automation
- Edit the name, description, trigger, or action of an existing rule
- See the per-run log or the events that fired against each rule
- Click into a card for a detail view
- Filter or search the card grid
- Re-run a failed automation
- Test-fire a rule against a sample event

Rule authoring and edits happen out-of-band; only the enable/disable toggle is admin-exposed.

## Concrete examples — what these rules look like in practice

These are the seeded examples that ship with demo data; production rules will use the same shape.

- **Configurator save → Operator lead** (`AUTO-DEMO-1`) — *When a configurator build is saved, create an Operator lead with the build attached.* Trigger: `on configurator.save`. Action: `create operator lead`.
- **Sell submit → Supply lead** (`AUTO-DEMO-2`) — *When a hardware sell intake is submitted, create a Supply lead and link the submission.* Trigger: `on sell.submit`. Action: `create supply lead`.
- **ERCOT > $10M → route to owner** (`AUTO-DEMO-3`) — *Deals created in ERCOT above $10M route to the named deal owner.* Trigger: `on deal.created` (with `region: ERCOT`, `minValue: 10000000` filters). Action: `route to H. Gandhi`.

When a trigger or action doesn't match a well-known shape, the chip falls back to a compact raw-JSON one-liner — useful as a "this rule is here" indicator even when ops can't read the JSON.

## What happens when a rule fires

This page does not show per-fire detail; the only fire-time signal here is the footer's run count, last-run timestamp, and last-run error count. Actual outcomes land elsewhere:

- **`create-lead` actions** drop a new lead into the [Leads Inbox](/v3/crm/leads) attached to the originating event (the configurator build, the sell submission).
- **`route` actions** assign deal ownership; the routed deal appears in the named owner's queue.
- **Errors** during a run increment the card's error count for the next page load — there is no per-event error log on this page.

To trace what an automation actually did, look at the downstream surface (Leads Inbox, the routed deal record) rather than this page.

## Things to know

- **Toggling is the only mutation.** Cards are read-only otherwise — name, description, trigger, and action are all display-only.
- **The toggle is optimistic.** The card flips before the server confirms. If the server rejects the change, you'll see the toggle revert and a red error banner with the reason.
- **Every toggle is audited.** Pausing and re-enabling both write to the Audit Log so the on/off history is recoverable.
- **Paused ≠ deleted.** A paused automation stops firing but stays on the page, retains its `RunCount` and `LastRunAt`, and can be flipped back on. There is no "delete" action.
- **Run count is cumulative across pauses.** Pausing does not reset the counter — the number reflects the rule's whole lifetime.
- **`last … ago` is computed from the last run.** A long-paused rule keeps its old `last 20d ago` timestamp; it doesn't show "paused" instead. Cross-reference the **on/off** state, not the timestamp, to know if the rule is currently active.
- **Errors on the card are *last run only*.** A green `0 errors` doesn't mean the rule has been clean for its whole history — only that the most recent run had no errors.
- **No rule authoring UI.** New automation definitions are created out-of-band. To add a new rule, file the request through the usual CRM-config workflow.
- **Related surface — [Match Alerts](/v3/crm/alerts).** Automations are the *outbound* glue from app events to the CRM; Match Alerts are the *inbound* notification feed from the matching engine. Both are read here by ops but they fire on different signals.
