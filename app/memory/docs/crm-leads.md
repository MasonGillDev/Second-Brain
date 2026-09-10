---
title: Leads Inbox
route: /v3/crm/leads
audience: revenue-ops, deal-ops, partnership-ops
slug: crm-leads
surface: admin
---

# Leads Inbox

Leads Inbox is **channel-first lead capture** — how the lead arrived comes before what it is. App events, web forms, forwarded email, switchboard calls, LinkedIn DMs, and broker submissions all land here as **Lead** records waiting to be assigned an owner and converted into a Contact (and then, downstream, into an Account / Deal). Open it at **V3 CRM → Leads** (`/v3/crm/leads`).

This is the central capture point for everything inbound — including the public **[Contact sales (customer flow)](/contact-sales)** form on slyd.com.

## Page layout

- **Header** — page title, page subhead, and a **+ New Lead** button (top right) for manual capture
- **Channel filter row** — the first-class filter. Pills: `All`, `Form`, `Email`, `Phone`, `LinkedIn`, `Broker`, `App Event`, `Unknown`. Each has its own icon and a count.
- **Type filter row** — second-class classification. Pills: `All`, `Operator`, `Supply`, `Offtake`, `Energy`, `Triage`. Counts beside each.
- **Counter** at the right of the channel row: `SHOWING N OF M LEADS`
- **Left panel** — leads table
- **Right panel** — detail drawer with activity timeline + actions
- **Banners** at the top — success / error feedback

Clicking a row in the table opens the drawer.

## Channels — how the lead arrived

The **Channel** is the page's primary filter and the first column on every row. It tells ops *how* the lead got to SLYD, before anyone asks *what* it's about.

- **Form** — a public form submission (e.g. **[Contact sales](/contact-sales)**, **[Post a need](/need)**, **[Sell hardware](/hardware-sales)**, configurator save). Icon: rectangle list.
- **Email** — forwarded or replied inbound email. Icon: envelope.
- **Phone** — switchboard or routed call. Icon: phone.
- **LinkedIn** — inbound DM. Icon: LinkedIn brand mark.
- **Broker** — a submission from a broker via the **[Broker portal](/broker)**. Icon: user-tie.
- **App Event** — a system-fired lead from an automation (e.g. a configurator save). Icon: lightning bolt. See **[Automations](/v3/crm/automations)** for which app events generate leads.
- **Unknown** — couldn't be classified at capture. Icon: question mark.

The order of channel pills (Form → Email → Phone → LinkedIn → Broker → App Event → Unknown) is the order ops scans the queue: synchronous web forms first, async inbound channels next, broker-sourced behind those, system-generated last.

## Types — what the lead is about

The **Type** classifies the business motion:

- **Operator** — a buyer-side lead (someone who wants to consume compute or hardware)
- **Supply** — a supplier-side lead (capacity or hardware available)
- **Offtake** — long-term capacity commitment
- **Energy** — a power / site lead (see **[Sites](/v3/intake/sites)** for the downstream surface)
- **Triage** — untyped, needs ops to classify (rendered from the internal `Unknown` value as the label **Triage**)

Type filters compose on top of the Channel filter — pick a channel and a type together to narrow further.

## Table columns

- **Lead ID** — mono display ID (e.g. `LEAD-…`)
- **Contact** — captured name on top, **title** below if present
- **Channel** — channel chip with icon and label
- **Source** — free-text mono source string (e.g. `inbound-call`, `linkedin-dm`, `partner-referral`, or a `?source=…` query param value from a public form). Captured verbatim; not validated against an enum.
- **Type** — type pill
- **Account** — linked V3 Account name, or `—` if not yet linked
- **Owner** — owner admin's name (mono), or **unassigned**
- **Age** — relative age (`12m`, `4h`, `2d`)

There is no free-text search and no sort control — order is set server-side.

## Create a lead by hand

Use this when a lead came in through a channel that doesn't auto-capture (a phone call, a hallway intro, a LinkedIn message).

1. Click **+ New Lead** in the header.
2. Fill the inline form:
   - **Name** (required) — placeholder *"Jane Doe"*
   - **Title** (optional) — placeholder *"VP Infrastructure"*
   - **Channel** — dropdown of all eight channels (default `Form`)
   - **Type** — dropdown of all five types (default `Triage`)
   - **Source** (required) — placeholder *"inbound-call, linkedin-dm, partner-referral…"*
3. Click **Create lead**.

A success banner reads `<DisplayId> captured via <Channel> — logged to Audit Log.` Validation: *"Name and source are required."*

## Inspect a lead

1. Click any row in the table.
2. The drawer opens on the right showing:
   - **Header** — the lead's name + the **DisplayId** and **Title** (if set)
   - **Channel** — chip with icon
   - **Type** — pill
   - **Source** — mono string
   - **Captured** — date and time (`Jun 25, 14:32`)
   - **Account** — linked account name or `—`
   - **Owner** — owner name or **unassigned**

## Activity Timeline

Below the detail grid is **Activity Timeline · N logged** — every action against the lead in reverse chronological order, with the most recent marked as **current**.

Each timeline item shows:
- Timestamp (`MMM dd, HH:mm`)
- The activity kind (e.g. `Captured`, `Assigned`, `Converted`)
- The acting admin's name and a short description

Empty state: *"No activity recorded yet."*

## Assign a lead to yourself

1. Open the lead in the drawer.
2. If the lead has no owner, an **Assign to me** button appears in the action row at the bottom of the drawer.
3. Click **Assign to me**. The drawer updates with your name in **Owner**, the table refreshes, and a success banner reads `<DisplayId> assigned to <Your Name> — logged to Audit Log.`

There is no UI to assign a lead to *another* admin from this page — only self-assign. Reassignment happens through a separate CRM workflow.

## Convert a lead to a Contact

The terminal action — promote the lead into a Contact record (the start of the CRM funnel proper).

1. Open the lead in the drawer.
2. Click **Convert to Contact →** at the bottom.
3. The convert form expands:
   - **Email** — placeholder *"jane@example.com"*
   - **Phone** — placeholder *"+1 512 555 0100"*
   - **Contact type** — dropdown of contact types (default **Decision**)
4. Click **Confirm conversion**.

A success banner reads `<DisplayId> converted to contact — see the Contacts directory.` The activity timeline gets a new entry. The new Contact appears in **[CRM Contacts](/v3/crm/contacts)** (which owns the Contact concept end-to-end).

Either field on the conversion form is optional — leave both blank if you don't have them yet.

## How leads arrive — the full picture

Most rows on this page **were not typed by an admin** — they were captured automatically from elsewhere:

| Channel | Where it came from |
|---|---|
| **Form** | Public form submissions: **[Contact sales](/contact-sales)**, **[Post a need](/need)**, **[Sell hardware](/hardware-sales)**. Form submissions also land in **[Forms](/admin/forms)** with their full field payload. |
| **App Event** | Automations on **[Automations](/v3/crm/automations)** — e.g. *Configurator save → Operator lead*, *Sell submit → Supply lead*. |
| **Broker** | Deals submitted from the **[Broker portal](/broker)** Submit-a-deal drawer. |
| **Email / Phone / LinkedIn** | Manually captured by ops via **+ New Lead** when an inbound came through that channel. |

The **Source** field carries the finer-grained tag — when a public form sends a `?source=…` query param (e.g. links from V3 marketing pages like *sell*, *energy*, *financing*, *trust-diligence*), that value lands on the lead so ops can route by origin.

## What ops *cannot* do on this page

- Transition a lead through downstream states beyond Convert (the rest of the funnel happens in **[Contacts](/v3/crm/contacts)** / **[Accounts](/v3/crm/accounts)** / **[Deal Pipeline](/v3/deal-flow/pipeline)**)
- Edit the captured name, title, source, channel, or type after capture
- Assign a lead to a different admin (only self-assign)
- Delete a lead
- Add a manual activity-timeline entry (the timeline is driven by mutations)
- Re-fire an automation against an existing lead

## Things to know

- **Channel beats Type.** The page is intentionally channel-first so ops can route the queue by where leads arrived from. If you're looking for a specific lead, find the channel first, then narrow by type.
- **Source is verbatim.** It's not validated against an enum and never normalized. Two leads from `linkedin-dm` and `linkedin-message` are not deduped — treat **Source** as a free-text routing hint, not a strict category.
- **Public-form leads land twice.** A submission from **[Contact sales](/contact-sales)** lands as a **Lead** here *and* as a Form Submission in **[Forms](/admin/forms)** with the full original field payload. The Lead is the routing record; the Form is the source-of-truth payload.
- **App Event leads are automation-driven.** Every App Event channel row was created by an automation rule on **[Automations](/v3/crm/automations)**. If those rules are paused there, no App Event leads will appear here.
- **Broker channel leads come from the broker themselves.** The broker submits via the **[Broker portal](/broker)** Submit-a-deal drawer. Those land here as `Broker` channel; they do *not* appear in the **[Brokers](/v3/platform/brokers)** Broker Submissions panel — that panel is for a separate "broker-sourced deals" surface.
- **Triage is the type to clear first.** A `Triage` row hasn't been classified yet — clearing the Triage queue is the daily ops job.
- **Self-assign only.** The drawer's **Assign to me** button is the only assignment control; to hand a lead to a teammate, file the request through a CRM workflow.
- **Every mutation is audited.** Create, assign, convert all write to the Audit Log on **[Platform Audit](/v3/platform/audit)**.
- **No re-conversion.** Once a lead is converted to a Contact, the Convert button still shows but conversion will fail — re-converting the same lead is blocked server-side.
