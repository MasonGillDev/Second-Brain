---
title: CRM Accounts
route: /v3/crm/accounts
audience: revenue-ops, deal-ops, account-management
slug: crm-accounts
surface: admin
---

# CRM Accounts

CRM Accounts is the V3 **company directory** across the entire deal loop — every counterparty SLYD touches lives here: buyers, operators, brokers, lenders, suppliers, and offtake counterparties. Each account rolls up its contacts, deals, attributed lifetime value, and CRM lifecycle stage on a single screen. Open it at **V3 CRM → Accounts** (`/v3/crm/accounts`).

Accounts are the records that **brokers**, **customers**, and **operators** sign in *against* — the account binds an Auth0 login to a SLYD identity. The platform's account resolver maps Auth0 sub → User.AuthId → this Account, which is how the **[Broker portal](/broker)**, the deal-OS dashboard, auctions, and every other V3 surface know which counterparty is logged in.

For per-person view, see **[Platform Users](/v3/platform/users)**. For the V3 buyer/supplier directory, this page is the start.

## Page layout

- **Header** — page title and a **+ New Account** button (top right) that toggles the inline create form
- **Create form** (when opened) — five fields in a grid
- **KPI strip** — four cards: Total Accounts, Total LTV, Operators, Buyers
- **Filter bar** — type pills + search input + counter
- **Left panel** — accounts table
- **Right panel** — drawer with detail, contacts, recent deals, activity timeline, and the link-user form
- **Banners** at the top — error feedback

Clicking a row opens the drawer.

## Account types

The page is filtered first by **Account Type** — what side of the deal loop this counterparty sits on:

- **Buyer** — direct buyer (most common consumer-side type)
- **Operator** — capacity-side counterparty
- **Broker** — broker firm (the same account that pairs with the **[Brokers](/v3/platform/brokers)** roster — name match must be exact)
- **Lender** — financing counterparty
- **Offtake** — long-term offtake buyer (rendered from the internal `OfftakeBuyer` value with the label **Offtake**)
- **Supplier** — hardware / capacity supplier
- **Mixed** — counterparty that plays multiple roles

The type pill order on this page is: **Buyer → Operator → Broker → Lender → Offtake → Supplier → Mixed**.

## Account stage

Every account also has a CRM lifecycle **Stage** (shown next to the type pill on every row and in the drawer header):

- Stages are loaded from the V3 `AccountStage` enum and rendered as pills (e.g. `Prospecting`, `Qualified`, `Active`, etc.).
- Default stage on creation is **Prospecting**.

## Account tier

A separate **Tier** field (Bronze / Silver / Gold / etc. depending on the V3 `AccountTier` enum) is shown in the drawer's detail grid. Default tier on creation is **Bronze**.

## KPI strip

Four cards across the top, all reflecting the **currently-filtered** view:

- **Total Accounts** — count across all counterparty types. Sub-line *"across all counterparty types."*
- **Total LTV** — sum of attributed lifetime deal value across the visible accounts. Sub-line *"attributed deal value · FK + party, deduped."* (The number rolls up direct buyer/operator/offtake FKs *plus* DealParty attributions, deduped per (account, deal) — so a broker who sourced a deal won't get double-credit.)
- **Operators** — count of `Operator` accounts. Sub-line *"capacity-side counterparties."*
- **Buyers** — combined count of `Buyer` + `OfftakeBuyer`. Sub-line breaks it down: `N direct · N offtake · N broker · N lender`.

The Buyers sub-line is the only place on the page that shows broker, lender, and offtake counts side by side without filtering — useful for a quick mix snapshot.

## Filter the list

- **Type pills** — single-select. `All` + one pill per type, each with a count. Counts are unfiltered totals per type.
- **Search input** — free-text search across account names. Applies live (no debounce visible).
- **Counter** on the right: `N ACCOUNTS · $M LTV` for the current filter.

## Create a new account

1. Click **+ New Account** in the header. The inline form expands.
2. Fill the fields:
   - **Name *** (required) — e.g. *"Acme Power LLC"*
   - **Display ID** (optional) — e.g. *"OP-ACME-1"*. Leave blank to auto-assign.
   - **Type *** — default `Buyer`
   - **Tier** — default `Bronze`
   - **Stage** — default `Prospecting`
3. Click **Create account**.

Validation: *"Account name is required."* Server errors surface verbatim in the error banner.

On success the form closes, the table reloads, and the drawer opens on the newly-created account.

## Inspect an account

Click any row. The drawer shows:

- **Header** — account name
- **Sub-header** — DisplayId, the type pill (with an inline edit button — see below), and the stage pill
- **Detail grid** — Tier · Owner · Lifetime Value (accent green) · Deals · Delivery Rate · Capacity (in kW for operators, `—` otherwise) · Created date
- **Link customer user** card — bind a platform User to this account (see "Link a user" below)
- **Capabilities** tag list — only shown for accounts that have operator capabilities tagged
- **Contacts · N** — list of the contacts on this account with name, title, email (see **[CRM Contacts](/v3/crm/contacts)** for the contact concept)
- **Recent Deals · N of M** — recent deals attributed to this account with DisplayId, stage pill, dollar value
- **Recent Activity** — the activity timeline (see **[CRM Activities](/v3/crm/activities)** for the activity concept)

## Change an account's type

The type pill in the drawer header has a small pencil icon next to it.

1. Click the pencil.
2. The pill turns into a dropdown showing all seven types.
3. Pick the new type.
4. Click the green **check** to save (or the **×** to cancel).
5. The drawer reloads with the new type.

Use this when an account was misclassified at creation or has evolved into a different role.

## Link a customer user (Auth0 binding)

The **Link customer user** card binds a platform User account to this CRM Account. This is what makes the V3 user-facing surfaces work for that account — without the binding, a buyer who signs in won't see their deals on the deal-OS dashboard, won't see their submissions in **[Broker portal](/broker)** (if they're a broker), and won't get auction visibility.

1. Open the account in the drawer.
2. In the **Link customer user** card, type the user's email into the input (placeholder: *"user@example.com"*).
3. Click **Link user**.
4. The drawer reloads with the user bound as **Owner**.

Validation: *"User email is required."* If no platform User with that email exists, the error banner surfaces a server-side message verbatim.

## Things ops *cannot* do here

- Edit the account name, tier, stage, owner (beyond the link-user form), or capabilities after creation — only the **Type** has an inline editor on this page
- Delete an account
- Add contacts directly — those live in **[CRM Contacts](/v3/crm/contacts)**; they're shown read-only here
- Add deals directly — those live in **[Deal Pipeline](/v3/deal-flow/pipeline)**; shown read-only here
- Add a manual activity entry — activities are driven by mutations
- See or change Auth0 settings — only the email-to-account binding is exposed via **Link customer user**

## Things to know

- **Accounts are the sign-in target.** Every authenticated customer/broker/operator is signed in against an Account — that's how the V3 surfaces light up. If a customer says "I logged in but can't see anything," the most common cause is no account binding; check **Owner** in the drawer.
- **Broker accounts and the broker roster are bound by name match.** When ops adds a broker on **[Brokers](/v3/platform/brokers)**, the **Firm** field must match this account's **Name** exactly. There is no FK — it's a string match.
- **LTV double-counts are deduped per (account, deal).** A broker that sourced a buyer's deal counts once for the buyer (FK) and once for the broker (DealParty), but the total LTV across all accounts isn't inflated by that.
- **The search box is name-only.** It does not match against DisplayId, owner, or any other column. To find an account by DisplayId, filter to the right type first then scan.
- **Delivery Rate is a percentage shown in the drawer.** It's the share of attributed deals delivered (vs. canceled / failed). Useful for ranking counterparties — but it's a rollup, not a per-deal status.
- **Capacity is kW for operators.** The Capacity field in the drawer detail grid shows the operator's stated capacity in kW. For non-operator accounts it shows `—`.
- **Default stage is `Prospecting`.** Newly-created accounts always start there and need to be moved through the CRM stages via downstream workflows.
- **Recent Deals shows recent N of total.** The total is in the heading (`Recent Deals · N of M`); the full list lives in **[Deal Pipeline](/v3/deal-flow/pipeline)** filtered to this account.
- **Audit trail.** Account creation, type changes, and user binding all write to the Audit Log on **[Platform Audit](/v3/platform/audit)**.
