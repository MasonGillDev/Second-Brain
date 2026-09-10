---
title: Capacity Listings
route: /v3/supply/listings
audience: supply-ops, deal-ops, revenue-ops
slug: supply-listings
surface: admin
---

# Capacity Listings

Capacity Listings is the admin board for **live and forward compute capacity** feeding the public marketplace. Each listing pins a site, GPU model, power envelope, online date, and rate — and tracks **committed %** so ops can see at a glance how much of the listed capacity is already sold versus still available. Open it at **V3 Supply → Listings** (`/v3/supply/listings`).

This is the **compute** side of supply. The hardware-side equivalent is **[Inventory Lots](/v3/supply/inventory)** (per-lot physical units). The customer-facing equivalents are the **[Marketplace (customer flow)](/marketplace)** family of pages.

## Page layout

- **Header** — page title + a **+ New Listing** button (top right)
- **KPI strip** — four cards: Live Listings · Forward Listings · Total GPUs · Avg Committed
- **New listing form** (when opened) — six-field inline card
- **Filter bar** — All / Live / Forward pills + counter on the right
- **Data table** — one row per listing, with inline editors for Rate and Committed %
- **Banners** at the top — success / error feedback

## Live vs Forward — the only state distinction

There is no formal state machine for listings. The single binary is whether the listing's **Online date** has been reached:

- **LIVE** — Online date ≤ today; capacity is online and bookable
- **FORWARD** — Online date is in the future; capacity is sold via refundable deposit and converts to LIVE when the date hits

A small chip on each row's Online cell tags the state, with the Forward chip adding `FORWARD · in <N>d` (or `in <N>mo` for far-out listings).

## The four KPI cards

All reflect the **currently-filtered** view.

- **Live Listings** — count where Online ≤ today
- **Forward Listings** — count where Online > today
- **Total GPUs** — sum of GPU counts across visible listings
- **Avg Committed** — mean committed ratio across visible listings, as a percentage

## Create a new listing

1. Click **+ New Listing**. The form expands.
2. Fill the fields:
   - **Site** — dropdown of sites from **[Site Submissions](/v3/intake/sites)**
   - **GPU Model** — text input (e.g. `B200`)
   - **Power kW** — number input (must be ≥ 1)
   - **GPU Count** — number input (must be ≥ 1)
   - **Online Date** — date picker (default: today; pick the future for a forward listing)
   - **Rate $/GPU·hr** — number input (must be > 0)
3. Click **Create listing**.

Validation: *"GPU model, a positive GPU count, power, and rate are required."* On success: `<DisplayId> created — listed as LIVE/FORWARD capacity and logged to the Audit Log.`

## Filter the list

- **Live / Forward** pills with counts. Single-select.
- **Counter** on the right: `N LISTINGS · N GPUs` for the current filter.

There is no free-text search and no per-site filter — to find a specific site's listings, scan visually.

## Table columns

- **Cap ID** — listing DisplayId
- **Site** — site name (from **[Site Submissions](/v3/intake/sites)**)
- **GPU** — GPU model (accent)
- **Power (MW)** — `kW / 1000` to two decimals
- **GPUs** — count
- **Online** — date + a **LIVE** chip (green) or **FORWARD · in <Nd>** chip (blue)
- **$/GPU·hr** — current rate (with an inline pencil to edit)
- **Committed %** — horizontal bar + percentage (with an inline pencil to edit)

## Inline editing — the two mutations

The page has **two field-level mutations**, both with inline edit controls. Each opens an edit row, accepts the new value, and saves to the Audit Log on confirm.

### Edit the rate

1. Click the pencil next to the **$/GPU·hr** value on a row.
2. The cell expands into a number input plus **✓** / **✕** buttons.
3. Type the new rate (≥ 0).
4. Click **✓** to save.
5. Success banner: `<DisplayId> rate → $<rate>/GPU·hr — change logged to the Audit Log.`

Validation: *"Rate cannot be negative."*

### Edit committed %

The same pattern on the **Committed %** column:

1. Click the pencil next to the percentage.
2. Cell becomes a 0–100 number input plus **✓** / **✕**.
3. Type the new percentage.
4. Click **✓** to save.
5. Success banner: `<DisplayId> committed → N% — change logged to the Audit Log.`

Validation: *"Committed % must be between 0 and 100."*

The bar widens/narrows to reflect the new value on reload.

## What ops *cannot* do here

- Edit Site, GPU Model, Power kW, GPU Count, or Online Date after creation (only Rate and Committed % have inline editors)
- Delete a listing
- Click a row for a detail drawer (no drawer)
- Bulk-edit
- Bind a listing directly to a deal from this page

## Things to know

- **Two field-level mutations: Rate and Committed %.** Both are audited via the Audit Log on **[Platform Audit](/v3/platform/audit)** with before/after values. Everything else on the listing is immutable post-create.
- **No detail drawer.** Listings are flat records; every column visible in the row is the whole record (plus the audit history off-page).
- **LIVE vs FORWARD is computed.** Time, not state. A FORWARD listing flips to LIVE the moment its Online date passes; there's no manual flip.
- **Listings don't model individual lots.** A listing is "N GPUs of model X at site Y at rate Z." For per-lot physical inventory, see **[Inventory Lots](/v3/supply/inventory)**.
- **Committed % drives the public Forward board.** The marketplace's Forward board shows what fraction of each listing is escrowed already. Edit committed % here to update the public board on the next load.
- **The site dropdown comes from [Site Submissions](/v3/intake/sites).** If a site you want to list capacity at isn't in the dropdown, it has to exist on the Sites page first.
- **No search.** Use the Live/Forward pills and scan. If the listing count grows past what's scannable, escalate for a search add.
- **Customer-facing surfaces.** Live capacity appears on **[Marketplace · Spot tab](/marketplace)** and **[Compute Marketplace](/marketplace/compute)**; Forward capacity (with refundable deposits) appears on **[Marketplace · Forward tab](/marketplace)**. The numbers shown there are read from the listings created here.
