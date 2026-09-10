---
title: CRM Contacts
route: /v3/crm/contacts
audience: revenue-ops, deal-ops, account-management
slug: crm-contacts
surface: admin
---

# CRM Contacts

CRM Contacts is the **unified person directory** across the entire deal loop. Every individual SLYD has touched — buyers, technical decision-makers, finance owners, procurement leads — lives here once they've been converted from a **Lead** or auto-populated by an automation. Open it at **V3 CRM → Contacts** (`/v3/crm/contacts`).

The page is **read-only in v1** — no inline create, no inline edit. New contacts arrive only via:

- **Convert to Contact →** on a Lead from **[Leads Inbox](/v3/crm/leads)**
- Sell-side submissions (from the public **[Sell hardware](/hardware-sales)** intake)
- Configurator saves (auto-captured by **[Automations](/v3/crm/automations)**)

## Page layout

- **Header** — page title + subhead
- **Filter bar** — type pills with counts + search input + counter
- **Contacts table** — flat list, paginated server-side
- **Banners** — error feedback (no mutation surfaces; only loading errors)

There is **no detail drawer** on this page. Everything about a contact fits in the table row; deeper context lives on the account (see **[CRM Accounts](/v3/crm/accounts)**) or the deal.

## Contact types

The page is filtered by **Contact Type** — what role this person plays at their company. Pills:

- **Decision** — the decision-maker
- **Technical** — engineering / infrastructure lead
- **Finance** — CFO, controller, finance owner
- **Procurement** — sourcing / vendor management
- **Other** — none of the above
- **Unknown** — not yet classified

The default `ContactType` when ops converts a Lead from **[Leads Inbox](/v3/crm/leads)** is **Decision**. Conversion is the only place this type is set — the page itself has no editor.

## Filter the list

- **Type pills** — `All` + one pill per type with a live count. Single-select.
- **Search input** — matches against **name, email, or account name** (debounced as you type).
- **Counter** on the right: `N OF M CONTACTS` for the current filter.

## Table columns

- **Contact** — name on top, **title** below if present
- **Account** — linked account name (from **[CRM Accounts](/v3/crm/accounts)**) or `—`
- **Type** — type pill
- **Email / Phone** — email on top (mono), phone below (mono, dim). Either field shows `—` if missing.
- **Owner** — owner admin's name (mono) or `—`
- **Engagement** — engagement score 0–100 rendered as a horizontal bar with three colour bands:
  - **Cold** (< 50) — neutral
  - **Warm** (50–79) — amber
  - **Hot** (≥ 80) — green
- **Last Engagement** — relative date (`47m ago`, `3h ago`, `9d ago`, or a full date for older entries). `—` if never engaged.
- **Tags** — free-text tag chips (e.g. `priority`, `pilot`, `q3-renewal`), or `—` if untagged

## Engagement score — what it means

The **Engagement** column is a 0–100 rollup of how recently and how often SLYD has touched this contact. The bar widens with the score and changes colour at the cold/warm/hot bands. The exact algorithm is the matching/scoring worker's; on this page it's a read.

Use the score to find quiet contacts that need re-engagement (low cold bar + old last-engagement date) or hot contacts ready for a follow-up.

## Where contacts come from

The empty state on this page reads: *"No contacts match this filter. Convert a lead from the Leads Inbox to populate the directory."* That's the single source of seeded contacts:

| Source | How it lands here |
|---|---|
| **[Leads Inbox](/v3/crm/leads)** | Ops clicks **Convert to Contact →** on a Lead drawer, picks a Contact type, and the new Contact appears here. |
| **[Sell hardware](/hardware-sales)** intake | The seller's contact info on the submission becomes a Contact via an automation. See **[Submissions](/v3/intake/submissions)** for the admin view of the intake. |
| **Configurator save** | When a buyer saves a build on `/configure`, an automation (`configurator.save → Operator lead`) creates the Lead, which can then be converted. See **[Automations](/v3/crm/automations)**. |

There is no direct UI to type a contact in by hand — the page is downstream of capture, never the capture point.

## What ops *cannot* do on this page

- Create a contact directly
- Edit name, title, email, phone, type, owner, tags, or engagement
- Click into a contact for a detail drawer (there is no drawer)
- Reassign owner
- Add or remove tags
- Trigger an outreach from the page
- See the contact's per-touch timeline (that lives in **[CRM Activities](/v3/crm/activities)**, filtered to that contact)

Mutating a contact happens through downstream workflows. The page is intentionally a read.

## Things to know

- **Read-only.** v1 has no create / edit / delete on the page. If a contact's info is wrong, the fix is upstream (the Lead or the form submission that produced them).
- **Account binding may be empty.** A contact converted from a Lead with no Account binding will show `—` in the Account column. The fix is to bind the underlying Account first via **[CRM Accounts](/v3/crm/accounts)** → **Link customer user**, then re-engage to refresh.
- **Search matches name, email, or account.** It does not match title, owner, or tags. To find a contact by title, scroll the filtered list.
- **Type defaults to `Decision` at conversion.** When the Convert form on **[Leads Inbox](/v3/crm/leads)** is filled, the dropdown defaults to `Decision`. If you see a contact misclassified, it's because ops accepted the default during conversion.
- **Engagement is rolled up by the worker.** It's not editable here. A contact that hasn't been touched in a while will drift cold automatically.
- **Activities live elsewhere.** This page shows *who* the person is — to see what was said and when, open **[CRM Activities](/v3/crm/activities)** and filter by the contact (or by the related deal / account).
