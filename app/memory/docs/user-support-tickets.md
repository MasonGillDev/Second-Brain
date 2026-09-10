---
title: Support tickets (customer flow)
route: /consumer/support-tickets
audience: support, customer-success
slug: user-support-tickets
surface: user
---

# Support tickets — customer flow

End-to-end walkthrough of what a signed-in customer or provider sees when they open their support tickets. The page lives at **two routes** that render the same UI:

- **`/consumer/support-tickets`** — when accessed from the consumer portal
- **`/provider/support-tickets`** — when accessed from the provider portal

The admin counterpart is **[Support Tickets](/admin/support-tickets)**, which owns the canonical definitions of statuses (`Open` / `In Progress` / `Awaiting Response` / `Resolved`), priorities (`Low` / `Medium` / `High`), and the SignalR-driven real-time behaviour. This doc covers only what the customer themselves sees and clicks.

## Page layout

- **Page header** — *Support Tickets* title with the tagline *"Manage your support tickets and get help."*
- **Tab navigation** — three tabs: **Active Tickets**, **Closed Tickets**, **Create New Ticket**
- **Stats cards** — four KPI cards: Open Tickets, In Progress, Resolved This Month, Average Resolution Time (Hours). Scoped to **this customer's own tickets**, not platform-wide.
- **Search bar** (on Active and Closed tabs)
- **Filter chips** (on Active tab only) — All Tickets · Open · In Progress · Awaiting Response
- **Ticket list** — paginated (kicks in after 10 tickets)
- **Ticket detail modal** — opens on row click

## The three tabs

### Active Tickets

The default tab. Shows every ticket the customer has open or in flight (not yet `Resolved`).

Above the list are:
- A **search bar** matching subject / ticket number
- Filter chips: **All Tickets**, **Open**, **In Progress**, **Awaiting Response** — each with its own icon
- A **Create Ticket** button that jumps to the Create New Ticket tab

### Closed Tickets

Shows the customer's `Resolved` tickets. Same row layout as Active, no filter chips (everything in this tab is one status).

### Create New Ticket

The intake form for a new ticket. Below the form, a **Suggested Solutions** card appears with knowledge-base articles related to what the customer is typing — populated live from subject + description with a 750ms debounce.

## Create a new ticket

1. Click **Create New Ticket** in the tab nav (or **Create Ticket** in the Active tab toolbar).
2. Fill the form in the **Create a New Support Ticket** card:
   - **Subject** (required) — placeholder *"Brief description of your issue."* Inline validation: *"Please enter a subject."*
   - **Category** (required) — dropdown: `Technical Issue` / `Billing Question` / `Account Management` / `Feature Request` / `Security Concern` / `Other`. Inline validation: *"Please select a category."*
   - **Priority** — dropdown: `Low - General question or feature request` / `Medium - Issue affecting work but has workaround` / `High - Critical issue blocking work`. Default: **Low**.
   - **Related Resource** (optional) — dropdown of the customer's resources by ID (e.g. *"A100 GPU Instance (ID: 947f9d3e)"*).
   - **Description** (required) — textarea, placeholder *"Please provide as much detail as possible about your issue…"* Inline validation: *"Please enter a description."*
   - **Attachments** (optional) — **Add Files** button. Limits shown next to it: *"Max 5 files, 10MB each."*
3. While the customer types Subject and Description, the **Suggested Solutions** card to the right populates with related knowledge-base articles. Clicking an article opens it.
4. Click **Submit Ticket**. The button shows a spinner and *"Submitting ticket…"* while it sends.
5. On success the form clears and the tab returns to Active Tickets with the new ticket at the top.
6. On failure, an inline error reads *"An error occurred while creating the ticket. Please try again."*

A **Save Draft** button is also visible — it does not persist anything in v1 (no draft storage), so treat it as a no-op.

## Open and reply to a ticket

1. Click a row in the Active or Closed list. The **Ticket Detail Modal** opens.
2. The thread shows the customer's original message at the top, then admin replies and customer replies in chronological order. Each message renders its attachments inline with **download** buttons and file-size labels.
3. To reply, scroll to the **reply box** at the bottom:
   - Type into the textarea (placeholder: *"Type your reply here…"*).
   - Optionally click the **paperclip** button to attach files. Attached-but-not-sent files appear in a **Pending Attachments** strip with **×** buttons to remove them.
   - Click **Send Reply** (paper-plane icon). The message appears in the thread immediately.

A typing indicator from the admin side shows up live (driven by SignalR — see [Support Tickets](/admin/support-tickets) for the admin-side behaviour). The customer's own typing is broadcast back to the admin.

## Mark resolved or escalate priority

In the ticket detail modal sidebar, the customer has two self-serve actions:

- **Mark as Resolved** (green check icon) — closes the ticket. After this, the ticket leaves the Active list and shows up under Closed Tickets.
- **Escalate Priority** — bumps the ticket's priority one level (Low → Medium → High). Use this when the customer's situation got more urgent after they opened the ticket.

Both actions take effect immediately and broadcast to the admin's view via SignalR.

## Find a ticket

The **search bar** above the list matches:
- The ticket subject
- The ticket number

It does **not** match against message bodies — only the ticket's own metadata.

On the Active tab, filter chips compose on top of the search:

- **All Tickets** — every active ticket
- **Open** — newly created, no admin reply yet
- **In Progress** — admin actively working
- **Awaiting Response** — admin is waiting for the customer to reply

These mirror the admin-side **Status** filter on [Support Tickets](/admin/support-tickets).

## Stats card numbers — what they mean

The four cards at the top are scoped to **this customer's own tickets only**:

- **Open Tickets** — count currently in `Open` state
- **In Progress** — count currently in `In Progress` state
- **Resolved This Month** — how many of this customer's tickets the admin marked resolved this calendar month
- **Average Resolution Time (Hours)** — avg time from creation to resolution across this customer's resolved tickets

If a customer says "your stats card shows N but I see fewer tickets," it's because the stats card counts include all states for this customer, not just the active tab's filter.

## Things to know

- **Same UI for consumer and provider.** The page renders identically at `/consumer/support-tickets` and `/provider/support-tickets`. The only difference is which portal nav the customer arrived from. If support needs to know which side a customer is on, ask which nav they used.
- **No internal notes.** Every message in the thread is visible to both sides — the admin doesn't have an "internal-only" reply mode, and the customer sees everything the admin types. (Mirror of the admin-side rule on [Support Tickets](/admin/support-tickets).)
- **Customer-driven resolve is real.** **Mark as Resolved** is a customer action, not an admin-only one. If a customer says their ticket got closed but they didn't mean to close it, they clicked the button themselves — there's no "auto-close after X days" behaviour today.
- **Escalate Priority only goes up.** There is no de-escalate button on the customer side; if the customer's situation calmed down, the admin can lower priority from **[Support Tickets](/admin/support-tickets)** — the customer cannot.
- **Save Draft does nothing in v1.** The button exists but no draft is stored. Customers who close the Create tab lose their unsaved input.
- **Suggested Solutions are live.** They update as the customer types subject and description, with a 750ms debounce. A customer who reports the panel didn't show anything likely typed too little — minimum useful subject + description is needed.
- **Resource picker in Create form is a fixed list of the customer's resources.** It's not free-text. If their issue is about a resource not in the dropdown, they should pick **Select a resource** (empty) and describe it in the body.
- **Customer cannot reassign the ticket.** Only the admin can change the assignee, and only from the admin **[Support Tickets](/admin/support-tickets)** page.
- **Customer cannot reopen a Resolved ticket from the page.** Once they (or the admin) hit **Mark as Resolved**, the ticket is terminal from the page UI. The customer would need to open a new ticket and reference the old one in the description.
- **Help Center is "Coming Soon."** The customer also has a **Help Center** link in their nav (`/consumer/help-center` or `/provider/help-center`), but the page currently renders a *"Help Center Coming Soon"* overlay. The buttons under that overlay just take the customer back or to the public docs. Don't direct customers to **Help Center** for ticket actions — only the **Support Tickets** page.
