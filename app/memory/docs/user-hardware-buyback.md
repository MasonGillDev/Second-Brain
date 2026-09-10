---
title: Hardware buyback (customer flow)
route: /hardware-buyback
audience: support, supply-ops, partnership-ops
slug: user-hardware-buyback
surface: user
---

# Hardware buyback — customer flow

End-to-end walkthrough of what a public visitor sees on `slyd.com/hardware-buyback` — SLYD's **enterprise IT asset recovery / GPU buyback** marketing surface. The page pitches sellers on selling their used enterprise GPUs, servers, and data-centre hardware to SLYD for cash.

The actual seller intake flow (where a seller submits a manifest of what they want to sell) is **[Sell hardware (customer flow)](/hardware-sales)** — `/hardware-buyback` is the **marketing landing**, `/hardware-sales` is the **intake form**.

The admin counterpart that owns every multiplier and band shown on this page is the **GPU Buyback** tab of **[Pricing Engine](/v3/pricing/engine)** (grade × age × warranty × volume × logistics × payout-path multipliers + indicative bands).

## Where the seller starts

The visitor lands on `slyd.com/hardware-buyback`. The page is **public** — no login, no claim flow on this page. They get marketing copy + FAQ + CTAs that route them to either the actual intake (`/hardware-sales`) or contact (`/contact-sales`).

## Page structure

The page is a long-form marketing page covering:

- Hero — *"Sell Enterprise Hardware. Turn your enterprise GPUs, servers, and IT hardware into capital."*
- What SLYD buys — enterprise-grade GPUs (NVIDIA H100, A100, V100, AMD Instinct), servers (Dell, HPE, Supermicro, Lenovo), InfiniBand networking, enterprise storage. Specifically *not* consumer hardware.
- The valuation process timeline — initial valuations within 24-48 hours of equipment list receipt; final pricing after physical inspection within 3-5 business days
- How pricing is determined — current market demand, equipment condition, remaining warranty, buyer network needs
- Data destruction services — certified data destruction is part of the offering
- FAQ accordion at the bottom

## What SLYD buys

The page is explicit about the scope:

- **GPUs** — NVIDIA H100, A100, V100; AMD Instinct
- **Servers** — Dell, HPE, Supermicro, Lenovo (data-centre grade)
- **Networking** — InfiniBand and similar enterprise networking
- **Storage** — enterprise storage systems

Out of scope: consumer hardware, gaming rigs, single-GPU workstations.

## The valuation process

The page sets these expectations:

1. **Initial valuation** — within 24-48 hours of receiving the seller's equipment list
2. **Final pricing** — confirmed after physical inspection, typically within 3-5 business days of receiving the hardware

These are the SLAs ops are committed to on this surface. If a seller calls in citing the 24-48 hour promise, that's the page they're quoting.

## How pricing works (the visitor-facing version)

The page explains:

- Pricing based on current market demand, equipment condition, remaining warranty, buyer network needs
- Transparent valuations with itemized breakdowns
- Three payout-path options (the same three on the admin's **[Pricing Engine](/v3/pricing/engine)** GPU Buyback tab):
  - **Inspection-clear (50/50)** — half on inspection, half at delivery (1–4 weeks)
  - **Consignment** — pay on resale (SLYD absorbs upside, 8–17 weeks)
  - **Buy-out upfront** — full payment day 1
- Indicative band — the seller will see a banded valuation, exact number after inspection

The actual multipliers (grade × age × warranty × volume × logistics × payout-path) live in the admin **[Pricing Engine](/v3/pricing/engine)** GPU Buyback tab. This page describes the **outcomes**; that page edits the **rules**.

## CTAs

The page funnels visitors to:

- **[Sell hardware](/hardware-sales)** — the actual intake form (sign-in required to post a real submission)
- **[Contact sales](/contact-sales)** — for sellers with custom situations

## Data destruction

Certified data destruction is part of the offering — SLYD handles wipe / destruction per industry standards. This is part of what makes the hardware-buyback story different from a generic resale market.

## Things to know

- **Marketing only.** This page is read-only marketing copy. The actual seller workflow is **[Sell hardware](/hardware-sales)** — that's where the seller submits a manifest, gets a banded quote, and (after sign-in) claims their submission.
- **Pricing rules live in [Pricing Engine](/v3/pricing/engine).** The GPU Buyback tab is the source of truth for grade / age / warranty / volume / logistics multipliers and the indicative band. If the marketing page mentions a percentage or multiplier, the admin owner is there.
- **24–48 hour initial valuation SLA.** This is a published promise on the page. Ops should be ready to honour it (or escalate visibility if it's drifting).
- **3–5 business days for final pricing post-inspection.** Same — published SLA.
- **Three payout paths.** The seller picks one. They're defined and edited on the admin's **[Pricing Engine](/v3/pricing/engine)** GPU Buyback tab.
- **Consumer hardware is out of scope.** A seller showing up with gaming gear should be politely declined. The page is explicit about enterprise data-centre grade only.
- **Marketing-page numbers don't get quoted verbatim.** A seller's actual quote comes from the live Pricing Engine with their specific grade / age / volume — not from any number on this marketing page. If a seller cites a number from this page, treat it as setting expectations, not as a commitment.
- **Customer-facing peers.** **[Sell hardware](/hardware-sales)** is the intake form (sign-in required to claim, lands as a submission on **[Submissions](/v3/intake/submissions)**). **[Auctions (customer flow)](/auctions)** is the alternative — sellers can list a sealed-bid auction instead of taking a buyback quote.
- **Auctions vs Buyback — the seller picks the path.** Auctions are sealed-bid, market-priced, take their own clearing time. Buyback is a banded quote + 3 payout paths, faster but at SLYD's published multipliers. Sellers with low-confidence inventory or high time pressure usually take Buyback; sellers with strong product or patience often take Auction. The page steers toward Buyback as the default.
- **Data destruction promise is part of the value.** If a seller asks "what about my data," the page commits to certified destruction — not just resale.
