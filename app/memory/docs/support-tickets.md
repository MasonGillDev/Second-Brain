---
title: Support Tickets
route: /admin/support-tickets
audience: support, customer-success
slug: support-tickets
surface: admin
---

# Support Tickets

The Support Tickets page is the support team's central queue for customer support requests. Admins browse, filter, reply to, and manage tickets across statuses and priorities, with real-time chat collaboration via SignalR. Open it at **Support → Tickets** (`/admin/support-tickets`).

## Page layout

- **Statistics bar** at top — four stat cards: Open Tickets, In Progress, Resolved This Month, Avg. Resolution Time (Hours)
- **Filter bar** — Status dropdown, Priority dropdown, Search field, Reset button
- **Ticket list (DataGrid)** — sortable columns with pagination (default 25 per page; selector adjusts)
- **Detail modal** — opens on row click; left side is the conversation thread, right sidebar is metadata + actions

## Statuses and priorities

**Statuses:** Open / In Progress / Awaiting Response / Resolved.

**Priorities:** Low / Medium / High. High-priority rows are highlighted in the list.

## List columns

Ticket # (mono font), Subject, Status (badge), Priority (badge), Customer (email), Assigned To (admin name or "Unassigned"), Created, Updated.

## Filter and find a ticket

1. **Status** dropdown — narrow to Open / In Progress / Awaiting Response / Resolved.
2. **Priority** dropdown — narrow to Low / Medium / High.
3. **Search** field — matches Subject, Ticket #, or Customer email in real time.
4. Click **Reset** to clear all filters.

## Open a ticket

1. Click any row in the ticket list.
2. The detail modal opens. The initial ticket message (description) is at the top, followed by the conversation thread ordered by `SentAt`.

## Reply to a customer

1. Scroll to the **Reply Box** at the bottom of the modal.
2. Type your response in the textarea (placeholder: *"Type your response here…"*).
3. Click **Send Reply**. The button is disabled when the textarea is empty.
4. The message appears in the chat immediately.

**Auto-assignment on reply:** if the ticket is **Unassigned** and you send a reply, the ticket is automatically assigned to you.

Messages can include **attachments** (the conversation renders a download button per file with size formatted in B/KB/MB/GB). The UI auto-scrolls to the bottom of the conversation when new messages arrive or after you send a reply.

## Assign a ticket

1. Open the ticket detail.
2. In the right sidebar, click the **Assign To** dropdown button.
3. Pick an admin from the list.
4. The assignment is immediate; the sidebar updates and the change broadcasts via SignalR to other open viewers.

## Change ticket status

In the right sidebar under **Actions**:

- **Mark In Progress** — appears when the ticket is **Open**; moves it to In Progress.
- **Mark as Resolved** — appears unless the ticket is already Resolved; closes the ticket and opens a fresh conversation thread.

There is no Reopen button in the current UI — once a ticket is Resolved, no in-page action returns it to an open state.

## Change priority

1. Open the ticket detail.
2. In the right sidebar, click the **Change Priority** dropdown.
3. Pick Low / Medium / High.
4. The priority updates immediately in both the detail view and the list.

## Real-time behavior (SignalR)

The page is wired to the `/hubs/supportTicket` SignalR hub. Without refreshing:

- **New customer or admin messages** appear live in the conversation.
- **Typing indicator** — when the customer is typing, *"Customer is typing…"* appears in the thread (debounced every 2s; disappears after 3s of inactivity).
- **Ticket field changes** — status, priority, and assignment updates broadcast to all open viewers and refresh both list and detail.
- **New tickets** are pushed into the list in real time.
- **Connection state** — the sidebar shows *"Customer is online"* or *"Customer is offline"*.

## Notifications

The page does not expose user-facing toggles for email/SMS notifications — they are triggered by the backend `IAdminSupportFeatures` service when you send a reply or change status. Treat reply-send as customer-visible communication; there's no separate "internal note" UI.

## Customer / org context in the sidebar

The right sidebar shows the customer's email and the organization name (from the ticket creator's OrganizationUsers relationship). If a ticket has a related resource, it appears as **Related Resource** with the ResourceId — no link is rendered, you'll need to navigate manually.

## Things to know

- **No internal notes** — all messages in the thread are customer-visible. There is no "internal-only" reply mode.
- **No ticket merging or reopening** in the current UI. Resolved is terminal from this page.
- **Pagination** — page size selector adjusts; changing it resets the current page to 1.
- **Export Tickets** button exists in the header but has no implementation yet — clicking does nothing.
- **No edit/delete history** on individual messages; the conversation is append-only.
- **No role gates** — all actions are available to any logged-in admin.
- **High-priority rows are highlighted** in the list to draw triage attention.
- **The customer's side of the same ticket** lives at `/consumer/support-tickets` (consumer) or `/provider/support-tickets` (provider). The customer sees their own tickets in **Active** / **Closed** / **Create New Ticket** tabs and can create, reply, escalate priority, or mark resolved themselves. See **[Support tickets (customer flow)](/consumer/support-tickets)**.