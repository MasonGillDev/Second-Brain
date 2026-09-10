---
title: Users & Roles
route: /v3/platform/users
audience: admin-management, support
slug: platform-users
surface: admin
---

# Users & Roles

Users & Roles is the V3-styled **read view** over internal ops users and the role / page-scope grants they hold. It shows who's on the admin side, what role they sit in, and how many page scopes that role grants — but it doesn't itself manage anything. Edits happen on the legacy CRUD pages it deep-links to. Open at **V3 Platform → Users & Roles** (`/v3/platform/users`).

This page is for *internal SLYD ops users only*. **It is not the same as customer/buyer user management** — buyer-side users live as platform Users bound to **[CRM Accounts](/v3/crm/accounts)** via *Link customer user*.

## Page layout

- **Header** — page title + a subhead, plus two link-out buttons (top right):
  - **Manage roles →** — deep-links to `/admin/roles` (legacy CRUD)
  - **Manage users →** — deep-links to `/admin/admin-users` (legacy CRUD)
- **Role summary row** — one card per role
- **Users table** — one row per admin user
- **Banners** at the top — error feedback (this page only reads)

## Role summary

A horizontal row of cards, one per role. Each card shows:

- **Role name** — e.g. `Admin`, `SupportLead`, `RevenueOps`
- **SYSTEM** chip — appears for roles flagged as system roles (special baked-in roles that can't be deleted from the legacy CRUD)
- **Stats** — `<N> users` and `<N> page scopes`

If no roles are defined yet, the row shows an empty card with *"No roles defined yet."*

## Users table columns

- **User** — initials avatar + display name
- **Email**
- **Title** — role title (e.g. *"VP Operations"*), or `—`
- **Role** — role pill (the role this user holds)
- **Permissions** — count chip showing how many page scopes the role grants
- **Auth** — auth source chip:
  - `Dev bypass` (the dev-only auth shim — only seen in non-prod)
  - The normal Auth0 / production auth label

## Role grants and page scopes

Roles grant **page scopes** — which admin sections each operator can see and act on. The numbers on the Role cards (`N page scopes`) reflect those grants. Specific scope assignments aren't visible on this page; for the granular grant editor, use the **Manage roles →** deep-link.

Roles are **independent of customer-side capabilities** — a SLYD admin's role on this page has no effect on what a customer sees on their portal. Customer-side bindings live on **[CRM Accounts](/v3/crm/accounts)** and **[Platform Audit](/v3/platform/audit)**.

## What ops *cannot* do on this page

- Create or edit a role
- Assign a user to a different role
- Add a new admin user
- Change a user's title or email
- Revoke a user's access
- See which specific page scopes each role grants (only the count)

All of those happen on the legacy CRUD pages (deep-linked from the header).

## Things to know

- **Read-only.** This page is a viewer; all mutations live on the legacy CRUD at `/admin/roles` and `/admin/admin-users`. Use the deep-link buttons in the header to get there.
- **SYSTEM roles can't be deleted.** A `SYSTEM` chip on a role card means it's a baked-in role enforced by the platform. Even on the legacy CRUD, you can't drop it.
- **`Dev bypass` auth is non-prod.** If you see `Dev bypass` in the Auth column on a production deploy, escalate — that's the development-only auth shim and shouldn't be active in prod.
- **Customer-side users live elsewhere.** This page is internal-ops only. Buyer / operator / broker users are bound to **[CRM Accounts](/v3/crm/accounts)** via *Link customer user*, not here.
- **Email is the identity anchor.** When the role / auth system needs to identify a user, email is the join column. If a user's email changes, the legacy CRUD is where the change happens.
- **Audit trail.** Every role / user mutation done on the legacy CRUD pages writes to the Audit Log on **[Platform Audit](/v3/platform/audit)**. This page itself writes nothing.
