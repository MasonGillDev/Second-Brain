---
title: Customers
route: /customers
audience: account-management, finance, support
slug: customers
surface: admin
---

# Customers

The Customers page is the central directory for every customer on the SLYD platform. Admins use it to find customers, inspect funding and wallet activity, see their instances and users, and jump to the deeper management surfaces (Organizations, Credits). Open it at **Users & Orgs → Customers** (`/customers`).

The page itself is **read-only** for customer details — it's a search/dashboard surface. Edits happen via the linked pages.

## Page layout

- **Header** with the page title and an **Export Excel** button
- **Growth chart card** — signups, cards added, and wallets first funded over time
- **Stat cards** — total customers, lifetime funded aggregate, total wallet balance
- **Filter card** — search + two dropdown filters
- **Data table** — paginated customer rows with expandable inline detail
- **Pagination** at the bottom (default page size 25; options 10 / 25 / 50 / 100)

## Find a customer

1. Type into the **Search** field (placeholder: *"Search organization or email…"*). It matches the organization name or the primary user's email, case-insensitive.
2. Use the **Wallet Balance** dropdown to filter to **Positive Balance**, **Negative Balance**, **Zero Balance**, or **All**.
3. Use the **Active Instances** dropdown to filter to **Has Active Instances**, **No Active Instances**, or **All**.

Filters apply automatically — no Apply button. Sortable columns: Organization, Primary User, Lifetime Funded, Wallet Balance, Active (instance count), Created. Default sort is newest Created first. Location and Total instance count are not sortable.

## Open a customer's detail

1. Click any row in the table.
2. The row expands into an inline drawer with two tabs: **Instances** and **Users** (each shows a count badge).
3. Click the row again to collapse it. Drawer data is loaded on first expand and cached — re-expanding does not re-fetch.

### Instances tab
- Columns: Name, Status, Server, CPU, Memory, GPUs, Created
- Status badge colors: green = running, gray = stopped, orange = pending, red = error/failed

### Users tab
- Columns: Email, Role, Status (Approved / Pending), Created

## Manage the customer (cross-page links)

The Actions column on each customer row has two icon buttons. The Customers page itself does not edit customer info — these are how you reach the management surfaces:

- **View Organization** (building icon) → `/organizations/{organizationId}/users` — see all organization members, edit org-level info
- **View Credits** (credit card icon) → `/credits?organizationId={organizationId}` — manage wallet balance, view funding history, Stripe integration

## Change a customer's account type

**Not on this page.** Account-type changes live in the **V3 CRM Accounts** drawer (separate admin surface). The Customers page does not surface this control. If you need it, navigate to V3 CRM → Accounts, open the account drawer, and change the type there.

## Add notes or suspend / close an account

Neither is available on the Customers page. Customer notes and account lifecycle actions are managed through the Organizations page or dedicated workflows — not here.

## Export the filtered list

1. Apply any filters you want included.
2. Click **Export Excel** in the header.
3. The download includes **all currently filtered customers**, not just the current page. The button is disabled while an export is in progress or if the list is empty.

## Growth chart

The chart at the top tracks three series:

- **Signups** (blue) — new customer signups
- **Cards Added** (amber) — Stripe card-add events
- **Wallets First Funded** (green) — first successful funding event per wallet

Use the **Range** dropdown (Last 30 / 90 / 180 days, Last 12 months, Year-to-date, All time) and **Bucket** dropdown (Daily / Weekly / Monthly) to change resolution. Changing chart settings does not affect the table.

## Things to know

- **Excluded emails** — the platform has a `Customers:ExcludedEmails` config (e.g. internal `@slyd.com` accounts). These customers are filtered out at the backend; the UI does not expose a toggle.
- **No destructive actions** on this page — every button is read-only or navigational.
- **Lifetime Funded** is total amount ever paid to wallet via Stripe (lifetime). **Wallet Balance** is current available balance.
- **Pagination resets expanded rows** — changing page size or paging will collapse any open drawers.
- **Legacy V2 page.** This is the consolidated V2 customer directory and is still day-to-day for support and finance. The V3 successors split the same data across **[Platform Users](/v3/platform/users)** (per-person view) and **[CRM Accounts](/v3/crm/accounts)** (per-account view). Use whichever fits the question.