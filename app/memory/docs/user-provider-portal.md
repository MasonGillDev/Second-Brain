---
title: Provider portal (customer flow)
route: /provider/dashboard
audience: support, customer-success, partnership-ops
slug: user-provider-portal
surface: user
---

# Provider portal — customer flow

The provider portal is what a **provider** (compute capacity supplier) sees once they sign in as a provider. It lives under `/provider/*` and covers their dashboard, rented-out servers, financials, Stripe Connect setup, organisation info, and support. This doc is the **map** of those surfaces — what each page is for, what the provider can do there, and which admin surface owns the underlying state.

Dedicated docs covering surfaces that aren't repeated here:

- **[Support tickets (customer flow)](/consumer/support-tickets)** — same UI at `/provider/support-tickets`
- **[Brokers (admin)](/v3/platform/brokers)** — note that **broker portal** is separate (`/broker`, see **[Broker portal (customer flow)](/broker)**)

## Where the provider starts

A signed-in provider lands at `/provider/dashboard`. The nav exposes:

- **Dashboard** — `/provider/dashboard`
- **My Servers** — `/provider/my-servers`
- **Active Instances** — `/provider/active-instances`
- **Rental History** — `/provider/rental-history`
- **Financials** — `/provider/financials`
- **Stripe Connect** — `/provider/stripe-connect`
- **Organization Info** — `/provider/organization-info`
- **Company Info** — `/provider/company-info`
- **Help Center** — `/provider/help-center`
- **Support Tickets** — `/provider/support-tickets`
- **Ask Benson** — `/provider/ask-benson`
- **Notifications** — `/provider/notifications`

## `/provider/dashboard` — the provider dashboard

The provider's daily landing. Shows utilization, current MRR, server health summary, and shortcuts.

## `/provider/my-servers` — My Servers

The provider's registered physical / virtual servers they're offering to the SLYD platform: server name, hardware spec (CPU, RAM, GPU model + count, storage, networking), online status, current rental binding (if any), and configuration controls.

This is the provider-side of supply. Admin-side, the corresponding aggregate views are **[Deployments](/v3/deal-flow/deployments)** (per-deployment / per-cluster) and **[Inventory Lots](/v3/supply/inventory)** (per-lot).

## `/provider/active-instances` — Active Instances

Currently-running customer instances on the provider's servers. The provider can see what's live, monitor health, and (if escalating) intervene.

The admin-side equivalent for full per-deployment context is **[Deployments](/v3/deal-flow/deployments)**.

## `/provider/rental-history` — Rental History

Historical record of every rental the provider hosted — start, end, customer (often anonymised), GPU·hours billed, revenue earned.

The numbers here come from the same source-of-truth as **[Daily Billing Summary](/admin/financials/daily-billing)** (provider-side view) and **[Rental Billing History](/admin/financials/rental-billing)**. If the provider disputes a number, ops cross-references those admin pages.

## `/provider/financials` — Financials

Earnings, payouts, Stripe Connect status, scheduled payouts, year-to-date revenue. The provider's accounting view.

The admin-side source-of-truth is **[Rental Billing History](/admin/financials/rental-billing)** (Discrepancy column is the canonical check) plus the provider's Stripe Connect record (out-of-band).

## `/provider/stripe-connect` — Stripe Connect

The Stripe Connect setup / status page. Providers need a connected Stripe account to receive payouts. The page shows connection status and walks them through onboarding if not connected.

If a provider says "I'm not receiving payouts," this is the first place to check; if the status here is *not connected*, the rest of the payouts won't fire regardless of what admin sees.

## `/provider/organization-info` and `/provider/company-info`

Two related but distinct pages for the provider's organisational record:

- **Organization Info** — operational details (name, address, contacts)
- **Company Info** — corporate / legal details (legal name, tax info, financial onboarding)

Admin-side, the same account record lives in **[CRM Accounts](/v3/crm/accounts)**.

## `/provider/help-center` — Help Center

**Currently shows a "Coming Soon" overlay** (same component as `/consumer/help-center`). Don't route providers here for support; use **Support Tickets** instead.

## `/provider/support-tickets` — Support Tickets

Same UI as `/consumer/support-tickets`. See **[Support tickets (customer flow)](/consumer/support-tickets)** — the doc covers both routes.

## `/provider/ask-benson` — Ask Benson AI

Provider-side AI assistant — same Benson as on the consumer side, scoped to the provider's questions and data.

## `/provider/notifications` — Notifications

Provider's notification feed — instance state changes, payout updates, support replies, server-health alerts.

## Things to know

- **A user can be both consumer and provider.** Same SLYD account, different portals on different URLs. If a user mentions surfacing they expected to see and didn't, ask which portal they were in.
- **Stripe Connect is the payout gate.** Without a connected Stripe account on **/provider/stripe-connect**, payouts won't move. Always check this first when a provider says they haven't been paid.
- **`/provider/help-center` is non-functional in v1.** Coming Soon overlay. Send providers to **Support Tickets** for any help-center–style request.
- **Two information pages overlap.** Organization Info (operational) and Company Info (legal / corporate) are split for legitimate reasons (different teams update each), but providers sometimes ask "why are there two?" — it's intentional.
- **Rental History and Financials numbers come from billing reconciliation.** Same source as the admin's **[Daily Billing Summary](/admin/financials/daily-billing)** + **[Rental Billing History](/admin/financials/rental-billing)**. The Discrepancy column on Rental Billing History is where disputes get resolved.
- **Account binding is the prerequisite.** A provider without a linked SLYD account sees the "No account linked" notice on every cross-portal surface. Fix is admin-side: **[CRM Accounts](/v3/crm/accounts)** → **Link customer user** with `Provider` (or `Supplier` / `Operator`) account type.
- **Provider ≠ Operator ≠ Supplier in the account-type taxonomy.** The **[CRM Accounts](/v3/crm/accounts)** doc has the full list. A provider in the day-to-day product sense might be an `Operator` account in the CRM; check the account type when binding.
- **Notifications are per-account.** Not the same as **[Match Alerts](/v3/crm/alerts)** (admin-only). Provider's notifications don't show ops's matching-engine signals.
- **No cross-customer visibility.** A provider can see their own active instances, but the customer renting each instance is typically anonymised in the rental-history surface. Don't promise visibility you can't deliver.
- **Provider portal vs Broker portal.** Brokers have their own portal at `/broker` (see **[Broker portal (customer flow)](/broker)**). A broker-flagged account who also operates capacity could be in both — but the day-to-day is the provider portal for hosting and the broker portal for commission. Confirm which one they mean.
