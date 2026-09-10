---
title: Marketplace (customer flow)
route: /marketplace
audience: support, deal-ops, supply-ops
slug: user-marketplace
surface: user
---

# Marketplace — customer flow

End-to-end walkthrough of what a public visitor (signed in or not) sees on the SLYD marketplace family of pages. The marketplace is the customer-facing showcase of supply — **compute** capacity (hourly GPU rental + forward escrow lots) and **hardware** for direct purchase.

The page family:

- **`/marketplace`** — the unified V3 marketplace landing. Two tabs: **Spot** (live capacity) and **Forward** (refundable-deposit forward lots).
- **`/marketplace/compute`** — the Cloud GPU Rental product page (long-form marketing + spec for hourly rental)
- **`/marketplace/hardware`** — Hardware-for-sale showcase
- **`/marketplace/{CategorySlug}`** and **`/marketplace/{CategorySlug}/{Subcategory}`** — taxonomy browsing for hardware
- **`/marketplace/apps`** — Apps marketplace (third-party AI tooling)
- **`/marketplace/item/{Slug}`** — product detail page

The admin counterpart for compute capacity is **[Capacity Listings](/v3/supply/listings)**; for hardware lots it's **[Inventory Lots](/v3/supply/inventory)**. The numbers shown on the marketplace are read from those admin surfaces.

For the seller-facing (hardware sell) intake, see **[Sell hardware (customer flow)](/hardware-sales)**.

## `/marketplace` — the V3 landing

The unified V3 marketplace landing. Headline: *"Compute marketplace. Spot now. Forward next."*

Lede: *"Live spot capacity available today. Forward escrow lots with refundable deposits for future delivery. One canonical surface, one set of filters — book by the hour or place escrow on capacity that hasn't come online yet."*

### Head stats

Three stats at the top, computed live from real Lot data on the admin side:

- **SPOT LIVE** — count of live lots (currently available right now)
- **FORWARD BOOK** — count of forward lots
- **DEPOSITS OPEN** — listings that are accepting deposits

MW totals are **deliberately hidden** — the Lot entity carries GPU quantity but no MW field, and inferring MW from GPUs would be a vanity number. The page rule (and the SLYD convention): if a number can't be sourced live, hide it. So all the rail shows is lot counts.

### Tabs — Spot and Forward

A two-tab toggle:

- **Spot** — live capacity available today
- **Forward** — refundable-deposit forward lots

A meta-line under the tabs reads: *"PRICES · HOURLY REFRESH · BANDED ±5%"*

Prices on the marketplace are **banded ±5%** for marketing display. The exact price for a specific lot only becomes visible after the buyer signs in and ties to a real reservation.

### Filter row

Filters above the results:

- **Accelerator** — GPU model
- **Region** — ISO
- **Cooling** — cooling type
- **Delivery** — delivery window
- **Search** — free-text
- **Reset** — clears filters

**In v1 these are visual selects but don't actually filter** — the backend wiring is deferred. Treat them as a UI preview. (If a customer says "the filters don't work," that's expected behaviour today; route them to **[Post a need](/need)** for a structured intake instead.)

### Spot board

Below the filters, a board of currently-live capacity rows. Each row shows the lot's GPU model × quantity, region, rate ($/GPU·hr) banded ±5%, and a CTA.

### Forward grid

Forward listings show as cards. Each carries:

- The GPU model × quantity
- Online date (when capacity flips from forward to live)
- The deposit % required to hold
- A CTA to escrow the lot (refundable until close)

### CTA strip

Bottom of the page: *"Need a custom build? Configure it."* — links to **[Configure (customer flow)](/configure)**.

## `/marketplace/compute` — the Cloud GPU Rental product page

A long-form marketing page for hourly GPU rental. Headlined as *"Cloud GPU Rental | Rent H100, H200, A100 by the Hour."*

The page covers:

- The available GPU types (H100, H200, A100, RTX 6000 Blackwell Pro, etc.) — list driven by the public Pricing Engine config
- Pay-as-you-go pricing
- Instant deployment
- Customer use cases (training, inference)
- A FAQ accordion at the bottom

Pricing here mirrors the published Pricing Engine GPU Catalog (see **[Pricing Engine](/v3/pricing/engine)**).

For a buyer who's already signed in, the CTA from this page typically routes to the **[Consumer portal](/consumer/dashboard)** for instance launch.

## `/marketplace/hardware` — Hardware showcase

The hardware-purchase landing page. Shows hardware catalog entries (servers, networking, power, cooling, storage) — driven by the Pricing Engine Hardware Catalog.

For the seller-facing intake (sellers listing hardware they want to sell to SLYD), see **[Sell hardware (customer flow)](/hardware-sales)**. This page is the *buy*-side of hardware.

## `/marketplace/{CategorySlug}` and `/marketplace/{CategorySlug}/{Subcategory}`

Taxonomy browsing pages. The CategorySlug and Subcategory map to the asset taxonomy used everywhere else (defined for the admin in **[Inventory Lots](/v3/supply/inventory)** and **[CRM Contacts](/v3/crm/contacts)**):

- `/marketplace/gpu` — GPU category
- `/marketplace/server` — Servers
- `/marketplace/networking` — Networking gear
- `/marketplace/server/gpu-server` — example sub-category
- etc.

These pages browse the **public**-flagged catalog entries from the Pricing Engine Hardware Catalog. Pricing is banded ±5% display, same as the Spot board.

## `/marketplace/apps`

The Apps marketplace — third-party AI tooling (frameworks, dev tools, monitoring stacks, etc.) integrated with SLYD. Browse-only; clicking an app routes to its detail or to an external install/install-instructions flow.

## `/marketplace/item/{Slug}` — Product detail

Per-product detail page. Each slug ties to a hardware catalog entry or a compute lot.

Shows:

- Product images
- Hardware spec
- Condition / Source / Availability badges
- Banded price
- Compare bar (cross-product comparison)

Add-to-compare and compare-bar UX let the visitor stack up to ~4 products side-by-side.

## Things to know

- **Visitors are anonymous by default.** Every marketplace page is public; no sign-in is required to browse. Pricing is banded ±5% for that reason — exact pricing comes after sign-in tied to a real lot.
- **Filters on `/marketplace` are visual-only in v1.** They render but don't actually filter. For a structured intake, route the visitor to **[Post a need](/need)**.
- **The Spot board reflects [Inventory Lots](/v3/supply/inventory) in `Listed` state.** A lot flips onto the Spot board when ops advances it to **LISTED** and disappears once it's bound to a deal (Reserved / Allocated / Deployed).
- **The Forward grid reflects [Capacity Listings](/v3/supply/listings) in Forward state.** A listing on the Forward grid converts to Spot the moment its Online date passes.
- **Pricing is banded ±5%.** Marketing display only. The buyer sees exact pricing after sign-in tied to a real lot.
- **No MW totals on the head rail.** SLYD deliberately doesn't show a MW total because the Lot entity carries GPU quantity but not MW, and inferring would be vanity. If a customer asks "how much total MW is on the platform," explain that we report lot counts, not MW.
- **Configure routes to the configurator.** The "Need a custom build? Configure it." CTA links to **[Configure (customer flow)](/configure)** — a buyer-side build configurator that ties to the Pricing Engine.
- **The numbers all trace back.** Spot lots = Inventory Lots in Listed state. Forward lots = Capacity Listings in Forward state. Hardware shown = Pricing Engine Hardware Catalog with public flag. Compute pricing = Pricing Engine GPU Catalog. There's no separate marketplace dataset — it's all derived from the admin surfaces.
