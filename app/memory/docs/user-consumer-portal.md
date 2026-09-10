---
title: Consumer portal (customer flow)
route: /consumer/dashboard
audience: support, customer-success, deal-ops
slug: user-consumer-portal
surface: user
---

# Consumer portal — customer flow

The consumer portal is what a **buyer** (compute renter) sees once they sign in as a consumer. It lives under `/consumer/*` and covers their dashboard, wallet, rented instances, usage history, account management, and the consumer-side marketplace. This doc is the **map** of those surfaces — what each page is for, what the customer can do there, and which admin surface owns the underlying state.

This doc doesn't replace the dedicated docs for surfaces that already have one. See:

- **[Demand Book](/v3/crm/demand)** for buyer demand records and **[Post a need (customer flow)](/need)** for the `/need` intake flow
- **[Auctions (customer flow)](/auctions)** for sealed-bid component lots
- **[Deal Room (customer flow)](/deals/{DealId})** for the per-deal record
- **[Support tickets (customer flow)](/consumer/support-tickets)** for the help-center / tickets surfaces
- **[Sell hardware (customer flow)](/hardware-sales)** for the sell intake
- **[Marketplace (customer flow)](/marketplace)** for public marketplace browsing

## Where the customer starts

A signed-in consumer typically lands at `/consumer/dashboard`. The nav rail then exposes:

- **Dashboard** — `/consumer/dashboard`
- **Compute Marketplace** — `/consumer/compute-marketplace`
- **App Marketplace** — `/consumer/app-marketplace`
- **My Instances** — `/consumer/my-resources`
- **Custom Instances** — `/my-resources/custom-instances`
- **My Applications** — `/consumer/my-applications`
- **Resources** — `/consumer/resources`
- **Usage History** — `/consumer/usage-history`
- **Wallet** — `/consumer/wallet`
- **Request Quote** — `/consumer/request-quote`
- **Help Center** — `/consumer/help-center`
- **Support Tickets** — `/consumer/support-tickets`
- **Ask Benson** — `/consumer/ask-benson`
- **Notifications** — `/consumer/notifications`
- **My Account** — `/consumer/my-account`

## `/consumer/dashboard` — the consumer dashboard

The buyer's daily landing. Carries headline counters (active instances, current spend), shortcuts to launch instances, and a recent-activity strip.

For the *deal-OS* dashboard that customers also see at `/v3/dashboard` (My Demands, My Sell Submissions, Your Deals panels), see **[V3 Dashboard](/v3/dashboard)** — note the route collision.

## `/consumer/compute-marketplace` — Compute Marketplace (consumer view)

The buyer's view of available compute. Pulls the same data as the public **[Marketplace](/marketplace)** but signed-in, so banded pricing collapses to exact lot-level pricing for the customer's eligibility.

Launches from this page go to **My Instances**.

## `/consumer/app-marketplace` — App Marketplace

Third-party AI tooling (frameworks, dev environments, monitoring stacks, etc.) integrated with SLYD. Install or browse.

## `/consumer/my-resources` — My Instances

The buyer's **live rented instances** — name, status (running / stopped / pending / error), CPU, memory, GPUs, server, created date. Clicking an instance opens its detail page at `/consumer/instance/{InstanceId}`.

The admin-side equivalent is **[Customers](/customers)** → row drawer → Instances tab (legacy) or **[Deployments](/v3/deal-flow/deployments)** for the deployment-level rollup.

## `/consumer/instance/{InstanceId}` — instance detail

Per-instance detail: live metrics, SSH connect info, container management, lifecycle (start / stop / terminate). The page the buyer uses to actually use their rented capacity.

## `/my-resources/custom-instances` — Custom Instances

For buyers running custom-configured (non-template) instances. Separate management surface for the more advanced cases.

## `/consumer/my-applications` — My Applications

The buyer's applications they've spun up from the App Marketplace.

## `/consumer/resources` — Resources

Documentation, tutorials, code samples, getting-started.

## `/consumer/usage-history` — Usage History

Time-series of compute usage and spend. Title says it: *"Usage History"*, with a **Total Hours Used** stat card and a per-instance / per-day breakdown.

The admin-side billing source-of-truth for these numbers is **[Daily Billing Summary](/admin/financials/daily-billing)** + **[Rental Billing History](/admin/financials/rental-billing)**. If a customer disputes a charge, the discrepancy column on the Rental Billing History page is the source-of-truth.

## `/consumer/wallet` — Wallet

The buyer's prepaid wallet:

- Current balance
- Funding history (Stripe-driven)
- Debits for compute usage
- Refunds and adjustments

Top-up flow lives here. Wallet balance is the same number admin sees on the **[Customers](/customers)** page → **Wallet Balance** column.

## `/consumer/request-quote` — Request Quote

A request-for-quote intake — the buyer asks for a custom quote on an unusual config. Lands on the admin side as a Form Submission in **[Forms](/admin/forms)** and (likely) a Lead in **[Leads Inbox](/v3/crm/leads)**.

## `/consumer/help-center` — Help Center

**Currently shows a "Coming Soon" overlay.** See **[Support tickets (customer flow)](/consumer/support-tickets)** for the detail — don't route customers to Help Center for ticket actions.

## `/consumer/support-tickets` — Support Tickets

See **[Support tickets (customer flow)](/consumer/support-tickets)** for the full walkthrough. Same UI is at `/provider/support-tickets`.

## `/consumer/ask-benson` and `/dashboard/ask-benson` — Ask Benson AI

The AI assistant surface for customers. They can ask questions about their account, instances, billing, and platform behaviour.

## `/consumer/notifications` — Notifications

The customer's notification feed — instance state changes, support replies, etc.

## `/consumer/my-account` — My Account

Account settings: profile, contact info, organization membership (when the customer is part of an org), security settings.

The admin-side equivalent for the account record itself is **[CRM Accounts](/v3/crm/accounts)** (account-level) and **[Platform Users](/v3/platform/users)** (user-level, internal-ops only — not where customer accounts live).

## Things to know

- **This portal is just the consumer side.** The same SLYD account, if it's also a provider, sees the **[Provider portal](/provider/dashboard)** under `/provider/*`. A user can be both.
- **`/consumer/help-center` is non-functional in v1.** Renders a "Coming Soon" overlay. Send customers to **Support Tickets** instead.
- **Save Draft on Create Ticket does nothing.** See **[Support tickets (customer flow)](/consumer/support-tickets)** "Things to know."
- **Usage History numbers come from daily billing.** The source-of-truth is **[Daily Billing Summary](/admin/financials/daily-billing)** on the admin side. If a customer disputes a charge, cross-reference **[Rental Billing History](/admin/financials/rental-billing)** for the reconciliation (RBR vs Daily vs Wallet).
- **Wallet balance is the same number admin sees on [Customers](/customers).** If a customer says "my balance shows X but admin shows Y," it's a sync question — escalate to finance with both screenshots.
- **Two dashboard surfaces.** Customers see both `/consumer/dashboard` (consumer landing) and `/v3/dashboard` (Deal-OS dashboard with My Demands / My Submissions / Your Deals). Different pages; both legitimate. Confirm which one the customer is talking about.
- **Account binding is the prerequisite for everything.** If the customer isn't bound to a SLYD account (`/v3/dashboard`, `/broker`, `/deals`, `/auctions` all show a "No account linked" notice). The fix is admin-side: **[CRM Accounts](/v3/crm/accounts)** → **Link customer user**.
- **Ask Benson is AI-driven.** Customers may quote answers Benson gave them; treat those as helpful summaries, not authoritative answers. If Benson gave a wrong answer, escalate the conversation log via support.
- **Notifications are not the same as Match Alerts.** `/consumer/notifications` is the buyer's per-account notification feed; **[Match Alerts](/v3/crm/alerts)** is the internal matching-worker feed for ops. They don't share rows.
