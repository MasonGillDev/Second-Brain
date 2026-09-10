# Admin docs — coverage plan (working file, do NOT upload to Pinecone)

This is a coordination document, not a knowledge-base doc. It exists so I (and you) have one shared map of:
- every admin route that exists
- every customer-facing route that an admin doc should reference
- what's already documented
- what's worth documenting (and what isn't)
- what pairs with what

The leading `_` prefix keeps it from being mistaken for a real doc; it's not picked up by my "every `.md` here is a knowledge file" rule.

---

## Legend

- **✓** — already documented in `admin-docs/`
- **→** — planned, has a clear paired user-facing surface
- **(admin-only)** — no customer-facing counterpart
- **(skip)** — internal infrastructure / dev / deprecated; not worth a knowledge doc
- **(merge into X)** — small enough that it should be a section of another doc, not its own file

If you disagree with any classification, change it here and I'll work from your edits.

---

## Phase 1 — V3 surfaces already documented (verify, do not re-do)

| Doc | Admin route | Customer-facing pair |
|---|---|---|
| `brokers.md` ✓ | `/v3/platform/brokers` | `/broker` (broker portal) — **not yet documented from user perspective** |
| `customers.md` ✓ | `/customers` (legacy) | `/consumer/*` portal — needs cross-link audit |
| `pricing-engine.md` ✓ | `/v3/pricing/engine` | `/configure`, `/financing/*`, `/hardware-buyback` — surfaces that read from the engine |
| `submissions.md` ✓ | `/v3/intake/submissions` | `/hardware-sales`, `/sell/claim/{token}` — pair doc `user-sell-hardware.md` ✓ |
| `support-tickets.md` ✓ | `/admin/support-tickets` | `/consumer/support-tickets`, `/provider/support-tickets`, `/consumer/help-center`, `/provider/help-center` |
| `inventory-lots.md` ✓ | `/v3/supply/inventory` | `/marketplace/compute` (Forward subscription terms render here) |
| `demand-book.md` ✓ | `/v3/crm/demand` | `/need`, `/need/claim/{token}`, `My Demands` panel on `/v3/dashboard` — pair doc `user-post-need.md` ✓ |
| `automations.md` ✓ | `/v3/crm/automations` | (admin-only — fires on internal events) |
| `match-alerts.md` ✓ | `/v3/crm/alerts` | (admin-only) |
| `daily-billing-summary.md` ✓ | `/admin/financials/daily-billing` | `/consumer/wallet`, `/consumer/usage-history`, `/provider/financials`, `/provider/rental-history` — what the customer/provider sees of the same charges |
| `rental-billing-history.md` ✓ | `/admin/financials/rental-billing` | same as above |
| `user-post-need.md` ✓ | (user-side companion to `demand-book.md`) | `/need` |
| `user-sell-hardware.md` ✓ | (user-side companion to `submissions.md`) | `/hardware-sales` |

### Verification debt against existing docs

- `brokers.md` — needs a paired user-facing doc for the broker portal at `/broker` (broker views their commission ledger / submissions there).
- `customers.md` — predates the user-doc convention; verify it covers the consumer portal pairing or split off a user-side doc.
- `support-tickets.md` — same; needs explicit pairing with the user help-center surfaces.

I'll audit those three before adding new pages.

---

## Phase 2 — V3 admin pages not yet documented (the bulk of the work)

Sorted by namespace.

### CRM (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/crm/accounts` | `crm-accounts.md` | (admin-only — internal CRM) |
| `/v3/crm/activities` | `crm-activities.md` | (admin-only) |
| `/v3/crm/contacts` | `crm-contacts.md` | (admin-only — though contacts are people who fill `/contact-sales`) |
| `/v3/crm/leads` | `crm-leads.md` | `/contact-sales`, `/configure` (configurator-save → lead), every form intake — **important pair to document** |

### Deal flow (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/deal-flow/pipeline` | `deal-pipeline.md` | `/deals`, `/deals/{DealId}` (the deal room a customer sees) |
| `/v3/deal-flow/match-engine` | `match-engine.md` | (admin-only — the matching worker UI) |
| `/v3/deal-flow/matching` | `matching.md` or merge into match-engine | (admin-only) — **decide: one doc or two?** |
| `/v3/deal-flow/deployments` | `deployments.md` | `/consumer/my-resources`, `/consumer/instance/{id}`, `/provider/active-instances` |

### Intake (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/intake/submissions` ✓ | (already done) | `/hardware-sales` |
| `/v3/intake/auctions` | `auctions.md` | `/auctions`, `/auctions/{AuctionId}`, `/auctions/new` (platform-side auction views) |
| `/v3/intake/sites` | `sites.md` | `/marketplace/power-opportunities`, `/marketplace/power-opportunities/{slug-id}` |

### Platform (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/platform/users` | `platform-users.md` | `/user-profile`, `/consumer/my-account`, `/provider/organization-info`, `/provider/company-info` |
| `/v3/platform/brokers` ✓ | (already done) | `/broker` — **needs `user-broker-portal.md`** |
| `/v3/platform/audit` | `audit-log.md` | (admin-only) |
| `/v3/platform/compliance` | `compliance.md` | (admin-only) |

### Pricing (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/pricing/engine` ✓ | (already done) | many — `/configure`, `/financing/*`, `/hardware-buyback`, `/marketplace/*` |
| `/v3/pricing/financing-curve` | merge into `pricing-engine.md` (it's already cross-linked there) or `financing-curve.md` standalone — **decide** | `/financing`, `/financing/apply`, `/financing/gpu`, `/financing/infrastructure`, `/financing/leasing-vs-buying` |

### Settlement (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/settlement/escrow` | `escrow.md` | (admin-only — escrow ledger) — but customer experiences escrow via `/deals/{DealId}` and `/consumer/wallet` |

### Supply (V3)

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3/supply/inventory` ✓ | (already done) | `/marketplace/compute` |
| `/v3/supply/listings` | `supply-listings.md` | `/marketplace`, `/marketplace/{category}`, `/marketplace/item/{slug}` |
| `/v3/supply/tracker` | `supply-tracker.md` | `/consumer/my-resources`, `/provider/active-instances`, `/provider/my-servers` |

### Dashboard

| Route | Doc slug | User-facing pair |
|---|---|---|
| `/v3` | merge into `dashboard.md` | — |
| `/v3/dashboard` | `dashboard.md` (admin) | `/dashboard`, `/consumer/dashboard`, `/provider/dashboard`, `/v3/dashboard` (platform side — same route exists on user portal). **The route collision is itself worth a "things to know" footnote.** |

---

## Phase 3 — Customer-facing user docs (the right-hand column of Phase 2, broken out)

Most of these will be paired with an admin doc above, but they deserve their own files when the user surface is substantial enough to stand alone:

- `user-broker-portal.md` — `/broker` (paired with `brokers.md`)
- `user-deal-room.md` — `/deals/{DealId}` (paired with `deal-pipeline.md`)
- `user-configurator.md` — `/configure` (paired with `pricing-engine.md`)
- `user-marketplace.md` — `/marketplace`, `/marketplace/compute`, `/marketplace/hardware` (paired with `inventory-lots.md` + `supply-listings.md`)
- `user-financing.md` — `/financing/*` (paired with `pricing-engine.md` financing tab)
- `user-hardware-buyback.md` — `/hardware-buyback` (paired with `pricing-engine.md` GPU Buyback tab)
- `user-consumer-portal.md` — `/consumer/*` overview + key surfaces (dashboard, wallet, my-resources)
- `user-provider-portal.md` — `/provider/*` overview + key surfaces (dashboard, financials, my-servers, stripe-connect)
- `user-power-opportunities.md` — `/marketplace/power-opportunities` (paired with `sites.md`)
- `user-auctions.md` — `/auctions/*` (paired with `auctions.md`)
- `user-contact-sales.md` — `/contact-sales` (paired with `crm-leads.md`)
- `user-platform-docs.md` — `/docs/*` (the public docs hub; useful for support to reference)
- `user-resources-calculators.md` — `/resources/*` (TCO calc, power calc, GPU database)

`user-post-need.md` ✓ and `user-sell-hardware.md` ✓ already exist.

---

## Phase 4 — Troubleshooting playbooks

Cross-cutting "user says X / admin checks Y" runbooks. These should come AFTER both ends are documented so I can cite existing docs by route, not duplicate them.

Strong candidates from what we already have:
- `troubleshoot-need-not-on-dashboard.md` — buyer posted `/need` but doesn't see it in **My Demands**. Maps to claim-link expiry / failure modes already in `user-post-need.md`.
- `troubleshoot-sell-submission-stuck.md` — seller posted on `/hardware-sales` but submission isn't progressing. Maps to `submissions.md`.
- `troubleshoot-billing-discrepancy.md` — customer disputes a charge. Maps to `rental-billing-history.md` Discrepancy column + `daily-billing-summary.md`.
- `troubleshoot-missing-daily-summaries.md` — RBR exists, daily records don't. Maps to the **Missing Daily Summaries** Coverage filter on `rental-billing-history.md`.
- `troubleshoot-broker-firm-mismatch.md` — broker signs in but doesn't see their deals. Maps to the firm-name-match gotcha in `brokers.md`.
- `troubleshoot-lot-not-matchable.md` — supply ops can't see a lot in the matching pool. Maps to the `CLAIMED ≠ matchable` gate in `inventory-lots.md`.

---

## Phase 5 — Pages I'd skip (not docs-worthy or out of scope)

### Internal infrastructure / dev tooling
- `/admin/admin-scripts` — internal ops scripts UI
- `/admin/admin-users` — admin user CRUD (audit-relevant but not a knowledge surface)
- `/admin/roles` — role assignment
- `/admin/image-libraries` — image library admin
- `/admin/knowledge-base` — knowledge base admin (meta — the assistant doesn't need to know about its own admin UI)
- `/admin/blog` — blog CMS
- `/admin/forms`, `/admin/forms/{id}` — form admin (low traffic; skip unless asked)
- `/admin/benson-conversations` — Benson AI logs
- `/admin-error`, `/Error`, `/nav-test`, `/pending-approval` — error/utility pages
- `/profile` — admin's own profile
- `/platform/*` — internal infra (api-keys, containers, internal-servers, server-bootstrap, spoke-registrations, ssh-keys) — **skip all**

### Legacy V2 (pre-V3 CRM)
- `/sales/*` — predates `/v3/crm/*` — **skip; users should use V3**
- `/marketplace/*` (admin) — predates `/v3/supply/listings` — skip
- `/marketplace/import`, `/marketplace/orders` — legacy
- `/providers`, `/users`, `/organizations`, `/instances`, `/instances/{id}`, `/instances/create-custom` — V2 list pages, mostly superseded
- `/pending-payments`, `/provider-transactions`, `/transfers`, `/credits`, `/create-credit`, `/create-transfer` — V2 finance pages, superseded by `/admin/financials/*`
- `/provider-servers`, `/admin/provider-servers`, `/admin/server-gpus` — V2 inventory pages
- `/massed-*` — Massed Compute–specific ingestion (specialized, low traffic for general support)
- `/data-sync/*` — legacy data migration UI (one-time/internal; skip)
- `/billing-backfill`, `/billing-debug`, `/billing-maintenance` — ops tooling

### Open question — keep or replace?
- `customers.md` ✓ — currently documents `/customers` (V2). Is this still the canonical customer view, or has it been replaced by `/v3/platform/users` + `/v3/crm/accounts`? **Need your call.**
- `/admin/financials` (parent index), `/admin/financials/internal`, `/admin/financials/account`, `/admin/financials/rbr-backfill`, `/admin/financials/daily-summary-backfill` — worth documenting as a `financials-index.md` overview + small docs for backfill pages, or skip backfills as low-traffic ops?

---

## Pairing principle (the contradiction-avoidance rule)

When the admin doc and the user doc both touch the same concept (a state, a status, a numeric field), the **admin doc owns the definition** and the user doc says "this is what the user sees of [linked admin term]." Same for cross-admin links: the doc that's about the entity owns the definition; other admin docs link rather than restate.

For example:
- "Demand state machine" is defined once in `demand-book.md` and referenced by `user-post-need.md`, `crm-leads.md`, `troubleshoot-need-not-on-dashboard.md`.
- "Lot lifecycle" is defined once in `inventory-lots.md` and referenced by `supply-listings.md`, `supply-tracker.md`, `user-marketplace.md`.
- "Discrepancy column" is defined once in `rental-billing-history.md` and referenced by `daily-billing-summary.md` and `troubleshoot-billing-discrepancy.md`.

---

## Proposed working order

1. **Audit pass** on the three legacy-format docs (`brokers.md`, `customers.md`, `support-tickets.md`) — confirm or split user-facing pairs.
2. **CRM block** — `crm-leads.md` first (highest cross-link value, gathers from many surfaces), then `crm-accounts.md` / `crm-contacts.md` / `crm-activities.md`.
3. **Deal flow block** — `deal-pipeline.md` + `user-deal-room.md` together, then `deployments.md`, then `match-engine.md`.
4. **Intake block** — `auctions.md` + `user-auctions.md`, then `sites.md` + `user-power-opportunities.md`.
5. **Supply block** — `supply-listings.md` + `user-marketplace.md`, then `supply-tracker.md`.
6. **Platform block** — `platform-users.md`, `audit-log.md`, `compliance.md`, then `user-broker-portal.md` to pair with existing brokers doc.
7. **Pricing satellite** — `user-configurator.md`, `user-financing.md`, `user-hardware-buyback.md` (all anchor on existing `pricing-engine.md`).
8. **Settlement** — `escrow.md`.
9. **Dashboards & portals** — `dashboard.md` + `user-consumer-portal.md` + `user-provider-portal.md`.
10. **Troubleshooting playbooks** — Phase 4 docs.

After each block, I'll re-read the new docs against this `_PLAN.md` to confirm I haven't introduced contradictions with prior blocks.

---

## Decisions (locked in 2026-06-25)

1. **Customers doc** — **keep** `customers.md` (legacy `/customers`) AND add separate docs for `/v3/platform/users` + `/v3/crm/accounts`.
2. **`/v3/pricing/financing-curve`** — **its own doc** (`financing-curve.md`).
3. **`/v3/deal-flow/matching` vs `/v3/deal-flow/match-engine`** — **two docs** (`matching.md` and `match-engine.md`).
4. **Backfill pages** — **skip** (low-traffic ops).
5. **Legacy V2 pages** — author's call; sticking with "skip all" as planned.
6. **`/v3/dashboard` collision** — **both are real**; document both as same-route-different-context. Admin context goes in `dashboard.md`; user context goes in `user-platform-dashboard.md` (or merged into the consumer/provider portal docs — decide while writing).
