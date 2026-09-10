---
title: Broker portal (broker flow)
route: /broker
audience: partnership-ops, support
slug: user-broker-portal
surface: user
---

# Broker portal — broker flow

End-to-end walkthrough of what a signed-in broker sees when they open their own portal at `/broker`. The page is fully scoped to the signed-in broker's account — they only ever see their own roster row, their own submissions, and their own commission ledger.

The admin counterpart is **[Brokers](/v3/platform/brokers)**, which owns the definitions of every concept on this page (tier, submission states, commission ledger states, settlement basis). This doc only describes what the broker themselves sees and clicks.

## Where the broker starts

The broker signs in and lands at `/broker` (linked as **Broker Portal** in their nav).

The page resolves the broker's account through two gates: (1) is the login bound to a V3 Account, and (2) what does the broker's roster row look like. If anything is off, the broker sees one of these notice cards instead of the portal. The wording is exact — if a broker calls in saying they "can't see anything in their portal," ask which notice they're staring at and use the table below to land on the fix.

| Notice the broker sees | What's wrong | Where ops fixes it |
|---|---|---|
| **No account linked** — *"No SLYD account is linked to your login yet — contact ops or your broker to claim your account."* | The auth identity isn't bound to a V3 Account at all. | [CRM Accounts](/v3/crm/accounts) — claim the user to an Account. |
| **No broker profile** — *"This account isn't flagged as a broker — contact partnerships@slyd.com."* | Account exists but Type isn't Broker. | [CRM Accounts](/v3/crm/accounts) — open the Account drawer and switch Type to Broker. Then create the roster row (next notice). |
| **Broker profile pending** — *"Your account is flagged as a broker but ops hasn't created your roster row yet. Reach out to partnerships@slyd.com to finalize your profile."* | Account.Type is Broker but no matching roster row exists. | [Brokers](/v3/platform/brokers) → **+ Add broker**; select this user's Account from **Link to Account**. |
| **Pending approval** — *"Your broker profile is in review. Ops is verifying your application — once approved you'll see your portal and be able to submit deals."* | Roster row exists but is in **PENDINGREVIEW** state. Every newly added broker lands here. | [Brokers](/v3/platform/brokers) → click **Approve** on the roster row (twice for confirm). |
| **Broker access paused** — *"Your broker access is paused. New submissions are blocked until ops reinstates you."* | Ops paused the broker. | [Brokers](/v3/platform/brokers) → click **Reinstate** on the roster row. |
| **Broker access suspended** — *"Your broker access has been suspended. Contact partnerships@slyd.com to discuss reinstatement."* | Ops suspended the broker. | [Brokers](/v3/platform/brokers) → click **Reinstate** on the roster row. |

A terminated broker doesn't see any notice — they get the **No broker profile** card because the resolver filters terminated rows out entirely.

## Page layout (when the binding is healthy)

- **Page header** — *Broker Portal* title and tagline *"Your submissions, your commission ledger, your clearing fees."*
- **Header actions row** — broker's **tier pill** on the left, the fee summary line beside it, and a gold **Submit a deal +** button on the right
- **KPI strip** — four cards: Accrued Commission, Paid · LTM, Submissions · 30d, Open Deals
- **Submissions** section — two-column kanban: **In review** and **Matched**
- **Commission ledger** — recent ledger entries
- **Submit-a-deal drawer** — opens from the **Submit a deal +** button

## Tier and fee summary

Top-left of the action row shows the broker's **tier pill** (the same tier ops set in **[Brokers](/v3/platform/brokers)**), followed by a fee summary in bold reading e.g. **"1% of deal value, 0.6% above $25M"**. The numbers come from the published Pricing Engine config and are identical to the rates admin sees on the Brokers page.

## KPI cards

Four cards, scoped to this broker:

- **Accrued Commission** (hero card) — total earned, awaiting payout. Sub-line: *"earned, awaiting payout."*
- **Paid · LTM** — paid commission in the trailing twelve months. Sub-line: *"trailing twelve months."*
- **Submissions · 30d** — count of submissions made in the last 30 days. Sub-line shows *"N in review now."*
- **Open Deals** — attributed deals not yet closed. Sub-line: *"attributed, not yet closed."*

These tie directly to the **Accrued**, **Paid LTM**, **Subs · 30d**, and **Open Deals** columns of the broker's row on the admin **[Brokers](/v3/platform/brokers)** roster — same numbers, different vantage point.

## Submissions kanban

Two columns, side-by-side, showing the broker's own submissions only. Column membership is driven by submission state:

- **Under review** — submissions in **REVIEW** or **SCREENED** state (ops working them but not yet committed). Empty state: *"Nothing in review — submit a deal to start one."*
- **Accepted · in flight** — submissions in **CONVERTED**, **MATCHED**, or **DEAL** state (your party is engaged — ops has accepted the submission and it's flowing toward a deal / commission). Empty state: *"Nothing accepted yet — once SLYD ops takes a submission, your party is engaged and the deal lands here."*

Each card shows:

- The submission **DisplayId** chip on top, a kind chip (`DEMAND` or `SUPPLY`), and a **state pill** in the actual submission state (`REVIEW`, `SCREENED`, `CONVERTED`, `MATCHED`, `DEAL`). The state pill is how a broker tells where in the lifecycle their card is within the Accepted column.
- A **structured summary** chip (`H100 × 64 · ERCOT` for demand, `2 line(s) · 48 total units · CAISO` for supply) — the broker's own structured fields, never SLYD-side info.
- The broker's free-text notes if any (truncated under 80 chars).
- Footer: estimated value (`$12.5M`, `$840K`, or `value tbd`), the **attribution** label if present (e.g. `referral`, `conference`), and the age (`just now`, `47m ago`, `3h ago`, `9d ago`).

Submissions in **SETTLED** or **DECLINED** state aren't shown in the kanban — Settled drops into the commission ledger as a paid entry; Declined silently disappears.

## Commission ledger

A table of the broker's ledger entries. If they have none, a notice reads *"No ledger entries yet — when a submission becomes an attributed deal, its commission row appears here."*

When populated, the table columns are:

- **Entry** — the ledger entry's DisplayId (dim chip)
- **Deal** — the deal's DisplayId (id chip)
- **Deal value** — the deal's dollar value
- **Rate** — the broker rate applied (e.g. `1%`, `0.6%`)
- **Commission** — the dollar commission earned
- **Basis** — settlement basis chip: `HARDWARE` (one-time at delivery) or `COMPUTE` (over the contract term). Same as the **Basis** column on the admin [Brokers](/v3/platform/brokers) Commission Ledger panel.
- **State** — pill: `PIPELINE` / `EARNED` / `PAID` / `REVERSED`. Definitions live in [Brokers](/v3/platform/brokers); the broker just sees the current state, they can't move it.
- **Date** — the entry's on-date or creation date

The broker can **read** the ledger but cannot transition entries — every state change (Pipeline → Earned → Paid, or Reverse) is an admin action on the **[Brokers](/v3/platform/brokers)** page.

## Submit a deal — the drawer

Clicking **Submit a deal +** opens a right-side drawer titled *Submit a deal* with tagline *"Source a deal into SLYD — we originate, finance, and close."*

### Side selector

First field, **Side**, with two options:

- **Demand — buyer needs compute**
- **Supply — capacity or hardware available**

Switching sides swaps the form below.

### Demand form

When **Side = Demand**, the form is a structured demand spec:

- **Category** — dropdown of asset categories (`Gpu`, `Server`, `Cpu`, `Networking`, `Power`, `Cooling`, `Memory`, `Storage`, `Other`)
- **Subcategory** — text input, shows only when category is not `Gpu`
- **Model** — text input, e.g. `H100`, `B200`, `MI300`
- **Quantity** — number input
- **Preferred grade** — dropdown (`Any` default + `New`, `A`, `B`, `C`)
- **Region (ISO)** — dropdown (`Any` default + `ERCOT`, `CAISO`, `PJM`, `MISO`, `SPP`, `NYISO`, `ISO-NE`, `AESO`)
- **Price ceiling ($)** — optional
- **Need by** — date picker
- **Advanced specs (JSON)** — collapsed expander; click *Advanced specs (JSON)* to reveal a textarea (placeholder e.g. `{"interconnect":"NVLink","formFactor":"SXM5"}`)

### Supply form

When **Side = Supply**, the form is a multi-line manifest:

- **Region (ISO)** — single dropdown for the whole manifest (default `Any` + same 8 ISOs as above)
- **Manifest** — repeating block. Header reads `Manifest · N lines` with a **+ Add line** button. Each line has:
  - **Category** dropdown
  - **Subcategory** input (only when category isn't `Gpu`)
  - **Model** input
  - **Quantity** input
  - **Grade** dropdown (`New`, `A`, `B`, `C`)
- Each line beyond the first has a small **×** in its header to remove that line.

The form opens with one empty line; the broker can keep adding lines for as many products as the deal covers.

### Shared fields (both sides)

Below the side-specific form:

- **Notes (optional)** — free text. Placeholder: *"Anything that didn't fit above — context, urgency, who the end party is…"*
- **Estimated deal value ($)** — optional
- **Attribution** — text input. Placeholder: *"direct, referral, conference…"*

### Live clearing-fee estimator

Below the form, a callout card shows:

- **Estimated clearing fee · N%** — the rate the system would apply
- A large dollar figure showing the estimated commission (or `—` if no value yet)
- Fine print: *"PAID ON CLOSE · 0.6% ABOVE $25M · SERVER MATH OVER THE PUBLISHED CONFIG IS AUTHORITATIVE"*

The estimator is **display-only**. It uses the broker's gut estimate when filled, otherwise infers from `price ceiling × quantity` for demand. The authoritative commission is recomputed server-side over the published Pricing Engine config when the ledger entry is created — the broker may see a slightly different number on the ledger.

### Submit

The footer has **Submit to SLYD →** with the fine print *"SLYD CONFIRMS RECEIPT · YOU STAY ON THE DEAL RECORD AS BROKER."*

On a successful submit:

- The drawer closes.
- A green banner reads *"Submission `<DisplayId>` received — it's in review and you stay on the deal record as broker."*
- The kanban and KPI strip reload — the new submission appears in the **In review** column.

If validation fails, the drawer stays open with an inline error explaining what to fix:

- Missing model: *"Model is required."*
- Quantity ≤ 0: *"Quantity must be at least 1."*
- Supply with no lines: *"Add at least one line to the manifest."*
- Per-line errors: *"Line N: model is required."* / *"Line N: quantity must be at least 1."*
- Negative estimate: *"Estimate can't be negative."*

Server-side validation (taxonomy mismatches, missing broker profile, etc.) shows verbatim in the drawer error line.

## What the broker *cannot* do here

- Edit the broker's own roster row (name, firm, tier, status) — all admin actions on **[Brokers](/v3/platform/brokers)**.
- Move submissions through states (Screen / Accept / Decline) — all admin actions.
- Move ledger entries through states (Pipeline → Earned → Paid → Reversed) — all admin actions.
- See other brokers' submissions, ledger entries, or deals (information wall).
- See SLYD's broader lot/demand pool or other brokers' counterparties.
- See the matching engine's scoring or candidate lists.
- Edit or withdraw a submission once submitted (would have to ask ops to Decline it).

## Things to know

- **Information wall — the portal is fully scoped to the signed-in broker.** No other broker's data is visible. If a broker says they see someone else's deals, something is wrong with the account binding — escalate.
- **Every new broker lands in PENDINGREVIEW.** The first time a freshly added broker logs in they see the *"Pending approval"* notice, not the portal. Ops has to click **Approve** on the roster row before the portal appears. There is no self-service application flow.
- **Submit-side wording is `direct, referral, conference` for Attribution.** The broker can type anything, but those are the placeholder hints.
- **The estimator is approximate.** The fine print explicitly says server math over the published config is authoritative. If a broker complains their commission came in different than the estimator showed, that's expected; the difference is usually because the published config changed between estimate and ledger entry.
- **Submissions land as `Review` on the admin page.** Every broker-submitted deal shows up in the **Broker Submissions** panel on **[Brokers](/v3/platform/brokers)** in **Review** state, where ops can **Screen** (optional DD gate), **Accept** (commits the conversion and creates a Lot or Demand), or **Decline**.
- **State pill on the card is the broker's only signal that ops moved their submission forward.** Watching that pill is how they know what's happening: REVIEW → SCREENED (ops started DD) → CONVERTED (Accepted — Lot or Demand created and in the matching pool) → DEAL (auto-attribution minted a commission entry — deal has formed) → SETTLED (paid out).
- **Brokers stay on the deal record.** Both the fine print on the submit button and the success banner say *"you stay on the deal record as broker"* — broker attribution is preserved for commission accounting regardless of who closes the deal.
- **Commission entries appear automatically.** When a broker's Lot or Demand attaches to a Deal, a Pipeline commission entry shows up in their ledger without any ops keystroke. The broker can watch it move PIPELINE → EARNED → PAID over the deal's lifecycle.
- **No filter, no search.** The kanban shows everything in the two columns; there is no kind / category / value filter.
- **The ledger shows the 25 most recent entries.** It's not paged — older ledger history may not appear. For full audit, refer the broker to ops who can pull the full ledger on the admin [Brokers](/v3/platform/brokers) page.
- **Commission rate and threshold come from the published Pricing Engine config.** If those numbers ever change, both the fee summary line at the top and the live estimator update on next page load. The admin owner is **[Pricing Engine](/v3/pricing/engine)**.
