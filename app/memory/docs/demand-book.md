---
title: Demand Book
route: /v3/crm/demand
audience: deal-ops, supply-ops, revenue-ops
slug: demand-book
surface: admin
---

# Demand Book

The Demand Book is every buyer's standing wish list — the admin-side queue for every demand record on the platform. Each row carries a buyer, an urgency, an optional price ceiling, and a match state; in the background the matching engine ranks inventory lots against the book and writes ranked candidates onto each demand. Open it at **V3 CRM → Demand** (`/v3/crm/demand`).

The page is **read-only in v1.** Ops can inspect, filter, and see the top-ranked candidate lots per demand, but state transitions, edits, and ranked-lot management happen elsewhere (see "What ops cannot do on this page" below).

The buyer-facing counterpart — what the customer sees when they create a demand and where it shows up on their dashboard — is **[Post a need (customer flow)](/need)**.

## Page layout

- **Filter bar** at the top — type tabs (`All` / `Hardware` / `Compute`) with live counts, then category pills (`All categories` + one per asset category), then the `N of N records` counter on the right
- **Left panel** — the demand table
- **Right panel** — detail drawer with full demand data + the Top Ranked Lots ranking
- **Banners** at page top — green success banner, red error banner

Clicking a row in the table opens the drawer on the right.

## Demand types — Hardware vs Compute

Two flavours of demand live in the same book, distinguished by a chip on every row and in the drawer header:

- **HARDWARE BUY** — the buyer wants to take ownership of physical units (GPUs, servers, networking, power, cooling, memory, storage)
- **COMPUTE CONTRACT** — the buyer wants to contract GPU-hours, not own gear

The type tabs at the top filter the list to one flavour. Each tab shows its count — the count reflects the unfiltered total for that type regardless of which category pill is active.

## Demand states

A demand moves through these states. Only **OPEN** and **REVERIFY** participate in active matching — the engine ignores the others.

- **OPEN** — actively matching against inventory
- **REVERIFY** — ops has flagged the demand for buyer re-confirmation (spec changes, urgency drift)
- **MATCHED** — a candidate lot has been identified and the demand is parked
- **EXPIRED** — the need-by date passed without a match
- **WITHDRAWN** — the buyer pulled the demand from their dashboard

**EXPIRED** and **WITHDRAWN** are terminal. Expired demands stay on the page for provenance and can re-enter matching if ops manually moves them back to **OPEN** via a CRM workflow (not done from this page).

## Display ID prefixes — where the demand came from

The mono `ID` chip on every row tells you the source of the record:

- **NEED-** — came in through the public **[/need form on slyd.com](/need)** (buyer-driven intake). Most rows.
- **DEM-** — created by ops by hand from a CRM workflow.

Both prefixes go through the same matching pipeline once on the book — there is no behavioural difference downstream.

## Filter the list

1. Click a type tab — **All**, **Hardware**, or **Compute** — to scope to one demand flavour. The tab count shows the total for that type.
2. Click a category pill — **All categories** or a specific asset category (`Gpu`, `Server`, `Cpu`, `Networking`, `Power`, `Cooling`, `Memory`, `Storage`, `Other`) — to scope further. Categories filter on top of the type tab.
3. The `N of N records` counter on the right shows the currently-displayed slice vs the unfiltered total.

There is **no free-text search** on this page — no buyer name search, no display-ID search.

## Inspect a demand

1. Click any row in the table. The row highlights and the right drawer populates.
2. The drawer header shows `<GPU model> × <quantity>`, the demand ID, the type chip, and the state pill.
3. Below that, the detail grid shows:
   - **Buyer** — the SLYD account that owns the demand, or `—`
   - **Contact** — the person ops should reach (can differ from the account owner), or `—`
   - **Urgency** — pill (Standard / Elevated / Critical)
   - **ISO** — buyer's preferred ISO region code (`ERCOT`, `CAISO`, `PJM`, `MISO`, `SPP`, `NYISO`, `ISO-NE`, `AESO`), or `—` if any region is acceptable
   - **Need-by** — date + relative days (`in 47d`, `due today`, `12d overdue`), or `flexible` if no date was specified
   - **Ceiling** — buyer's price ceiling in dollars, or `—`
   - **Preferred Grade** — buyer's grade preference (`New`, `A`, `B`, `C`), or `any`
   - **Created** — record creation date

## Table columns

- **ID** — Demand display ID (mono). `NEED-…` or `DEM-…` prefix.
- **Want** — Category (e.g. `Gpu`, `Server`), with subcategory below if set
- **Buyer** — `<GPU model> × <quantity>` on top, type chip (`HARDWARE BUY` / `COMPUTE CONTRACT`) below
- **ISO** — Buyer's preferred ISO region, or `—`
- **Urgency** — Pill (Standard / Elevated / Critical)
- **Need-by** — Date + relative-days sub-text (`in 47d`, `due today`, `12d overdue`), or `flexible`
- **Ceiling** — Buyer's price ceiling in dollars, or `—`
- **State** — Pill (Open / ReVerify / Matched / Expired / Withdrawn)

## Top Ranked Lots

Below the drawer detail grid is the **Top Ranked Lots · N of 5** section. This is **the only place on the page** that surfaces matching results.

- The matching engine populates this in the background via a match-refresh worker — it is **not** computed when you click a row. Click is a read.
- Each candidate row shows:
  - **Lot ID** chip (mono)
  - `<GPU model> × <quantity>` of the candidate lot
  - **Tenure chip** (`CONSIGNED` or `BROKERED`) if the lot's ownership isn't `Owned` — owned lots get no chip
  - **Match score** (percentage) on the right
  - A horizontal score-fill bar visualising the percentage
  - The largest-magnitude scoring-dimension explanation below (e.g. *"GPU model exact match: H200"*, *"Region distance: 0 mi"*)
- **Empty state**: `"No candidates computed yet — match-refresh job populates this."` This is normal for a freshly-posted demand. The background job typically fills it on its next run.

There is no button to trigger a re-rank from this page — the worker runs on its own schedule.

## What ops *cannot* do on this page

Demand Book is intentionally inspect-only in v1. The following are **not** available here:

- Transition a demand's state (OPEN → MATCHED, REVERIFY flag, expire, etc.)
- Edit any field on the demand (urgency, ceiling, need-by, contact, GPU model, ISO, grade preference)
- Trigger a re-rank of the candidate lots
- Reach out to the buyer from the page
- Convert a demand directly into a deal record
- Withdraw a demand on behalf of the buyer
- Click into a candidate lot (the lot chip is display-only today)

State changes and matching actions happen via dedicated CRM workflows outside this page or by the buyer in their own portal. If a buyer needs a demand changed, they self-serve via their dashboard (when the per-demand edit page lands) or ops files a request.

## Where these demands come from — the full picture

Most rows arrive through the public **[/need form on slyd.com](/need)** (display IDs prefixed `NEED-`). The end-to-end buyer journey:

1. The buyer lands anonymously on `slyd.com/need` and previews matches (no sign-in needed).
2. When they click **Post requirement to ops**, they are redirected to **Sign in** at `/Account/Login`. **Sign-in is required to post** — anonymous demands are no longer accepted.
3. After sign-in (or sign-up) through Auth0, they land on **Linking your demand to your account…** at `/need/claim/{token}`.
4. The platform atomically binds the demand to their account and bounces them to **Deal Dashboard** at `/v3/dashboard`.
5. The demand appears in the **My Demands** panel on their dashboard.

See **[Post a need (customer flow)](/need)** for the full buyer-side walkthrough — what they fill, the banded match preview, the hardware want-list (non-GPU intake), the claim flow, what shows on **My Demands**, and the four claim-link failure modes (expired token, mistyped token, already-claimed, generic error).

In every claim failure mode, **the underlying demand is not lost** — ops always has it here in the Demand Book; only the buyer's auto-link failed.

Demands ops creates by hand from CRM workflows use the `DEM-` prefix. They have no claim flow because they're created directly against an existing account.

## Things to know

- **Read-only in v1.** No transitions, no edits, no re-rank trigger, no buyer outreach. If a buyer needs a demand changed, they self-serve in their dashboard or ops files a request through a CRM workflow.
- **Top Ranked Lots is asynchronous.** Newly-posted demands will show `"No candidates computed yet"` until the background match-refresh job runs. This is **not** a bug — wait for the next refresh.
- **Buyer ≠ Contact.** The **Buyer** is the SLYD account that owns the demand; the **Contact** is whoever the buyer specified during intake as the right person to reach. Use the **Contact** name, not the account email, when reaching out — buyers commonly post on behalf of a colleague.
- **Empty ISO means *any region*.** Don't treat the `—` in the ISO column as missing data. The buyer explicitly said any region works. Compare against the drawer's `ISO: —` text to be sure.
- **`flexible` need-by is not the same as overdue.** A `flexible` value means the buyer never set a date — they're not in a hurry. An overdue value (`12d overdue`) means the date passed without a match; the demand may have moved to **EXPIRED**.
- **Expired demands stay on the page.** They're retained for provenance under the Expired state pill and can re-enter matching if ops manually moves them back to **OPEN** via a CRM workflow.
- **Withdrawn means the buyer pulled it, not ops.** Buyers can withdraw their own demands from their dashboard. If you see **WITHDRAWN**, the buyer made that choice.
- **A buyer is signed in for every NEED-prefixed demand.** Anonymous demands are no longer accepted at intake — every `NEED-…` row has a real account binding.
- **The candidate lot tenure chip matters at resale.** `CONSIGNED` means SLYD holds the asset for the seller and a seller payout happens at resale; `BROKERED` means SLYD never touches the asset. Owned lots have no chip and live on SLYD's balance sheet.
- **No deep search.** If you need to find a specific demand by display ID or buyer name, you'll have to scroll the filtered list. There is no search box.
