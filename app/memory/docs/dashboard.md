---
title: V3 Dashboard
route: /v3/dashboard
audience: deal-ops, supply-ops, revenue-ops, exec
slug: dashboard
surface: admin
---

# V3 Dashboard

The V3 Dashboard is the **cross-cutting landing view** of the deal-OS pipeline — one screen that summarises intake pressure, active pipeline value, matchable inventory, escrow exposure, and the work that needs ops attention right now. Open at the admin landing (`/v3`) or directly at **V3 → Dashboard** (`/v3/dashboard`).

> **Route collision.** The same URL `/v3/dashboard` also exists on the **platform** (customer-facing portal) — there it renders the buyer-side Deal-OS Dashboard with **My Demands**, **My Sell Submissions**, **My Builds**, **Your Deals**, etc. The two pages render very different content depending on which app domain the user landed on. If a customer says "I'm on /v3/dashboard and I see X," ask whether they're in the admin portal or their own portal — same URL, different page. The customer-side surface is summarised in **[Post a need (customer flow)](/need)** under "My Demands panel," **[Sell hardware (customer flow)](/hardware-sales)** under "My Sell Submissions," and **[Configurator (customer flow)](/configure)** under "My Builds."

## Page layout

- **Header** — page title + subhead
- **KPI strip** — four cards: Pending Submissions · Active Pipeline · Inventory GPUs · Escrow Held
- **Two-column row**:
  - **Pending Actions** (left) — a queue of items needing ops review, with severity colour-coding and deep-links into each surface
  - **Recent Activity** (right) — the unified CRM activity feed (latest events)
- **Banners** at the top — error feedback

The page makes one read call and renders everything; no filters, no mutations.

## The four KPI cards

All numbers are live across the admin platform.

- **Pending Submissions** — count of sell-side submissions in `NEW · REVIEW` state on **[Submissions](/v3/intake/submissions)**. Sub-line: *"sell intake in NEW · REVIEW awaiting an offer."*
- **Active Pipeline** — sum of deal value across deals **not yet LIVE** on **[Deal Pipeline](/v3/deal-flow/pipeline)**. Sub-line: *"deal value not yet LIVE."*
- **Inventory GPUs** — total GPUs across lots in `LISTED · RESERVED · ALLOCATED` state on **[Inventory Lots](/v3/supply/inventory)** + the lot count. Sub-line: *"N lots in LISTED · RESERVED · ALLOCATED."*
- **Escrow Held** — sum of deposits in `HELD · AT-RISK · PARTIAL · LATE` state on **[Escrow](/v3/settlement/escrow)**. Sub-line: *"deposits in HELD · AT-RISK · PARTIAL · LATE."*

The values use compact money format (`$12.5M`, `$840K`).

## Pending Actions queue

The left panel of the row-two grid. The page hands ops the work queue across surfaces — every action row deep-links to the place that work happens.

If the queue is empty, the panel shows: *"Queue clear — No at-risk escrows, no submissions waiting, no unverified lots, no unacknowledged alerts."* with a green check icon.

When the queue has items, the panel header shows: `<N> items · needs ops review`. Each action row has:

- A **count badge** (e.g. `12`, `3`)
- A **label** describing what needs doing (e.g. *"Submissions awaiting first offer"*, *"At-risk escrows"*, *"Lots claimed but not sourced"*, *"Unacknowledged alerts"*)
- An **Open →** link button that jumps to the right surface (e.g. **[Submissions](/v3/intake/submissions)**, **[Escrow](/v3/settlement/escrow)**, **[Inventory Lots](/v3/supply/inventory)**, **[Match Alerts](/v3/crm/alerts)**)
- A **severity colour** (low / medium / high) applied to the row

The queue rolls up from across the platform — there's no per-team filter; everything ops should know about lands here.

## Recent Activity feed

The right panel — the unified CRM activity stream. Each item shows:

- **Actor initials** (avatar)
- **Description** — the activity description, with the actor's name bolded
- **Meta line** — activity kind chip + relative timestamp (`47m ago`, `9d ago`, or a full date for older entries)

This is the same feed visible on **[CRM Activities](/v3/crm/activities)** but **summarised** — latest N items, no filter, no log-activity button. For full feed + the **+ Log Activity** form + filters, jump to **[CRM Activities](/v3/crm/activities)**.

Empty state: *"No activity recorded yet."* with a wave-square icon.

## What ops *cannot* do here

- Edit any KPI value (rollups, not editable)
- Open a detail drawer (no drawer)
- Filter the activity feed (use **[CRM Activities](/v3/crm/activities)** instead)
- Filter the pending actions queue
- Mark a pending action complete in-place (each one routes you to the page where that mutation lives)
- Log an activity from here (use **[CRM Activities](/v3/crm/activities)**)

The page is **all-read, no-write** by design. Every actionable signal funnels to the right surface via the **Open →** links.

## Things to know

- **Single landing.** This is the page admin lands on at `/v3` and `/v3/dashboard`. Use it to triage the day; jump out to the surface that needs work via the Pending Actions deep-links.
- **Route collision is real.** Same URL on the buyer portal renders the **customer-side** Deal-OS Dashboard (with **My Demands**, **My Sell Submissions**, **My Builds**, **Your Deals**, **Needs You**, etc.). When debugging a customer issue, confirm which domain they're on before reading the screen. See **[Post a need (customer flow)](/need)** for the buyer-side "My Demands" panel, **[Sell hardware (customer flow)](/hardware-sales)** for "My Sell Submissions," and **[Configurator (customer flow)](/configure)** for "My Builds."
- **KPI thresholds aren't fixed.** The cards just sum + count the underlying state — there's no "good / bad / red zone" threshold built into them. Read each in context.
- **The Pending Actions queue spans surfaces.** A single ops day's worklist might be: `12 submissions awaiting offer` (Submissions), `3 at-risk escrows` (Escrow), `47 lots claimed but not sourced` (Inventory Lots), `8 unacknowledged alerts` (Match Alerts). All four hit the queue here; the **Open →** link gets you to each.
- **No mutations.** Don't expect a "settle this" button here. Open the source surface.
- **Recent Activity is a summary.** It's the same feed as **[CRM Activities](/v3/crm/activities)** but with no filter and limited rows. For full triage, use the dedicated page.
- **Customer-side dashboard.** A customer's `/v3/dashboard` shows them their own deals, demands, submissions, action queue ("Needs You"), and the activity on their deals — all party-scoped. The structure is similar to this page, but the content is the customer's own, never ops's.
