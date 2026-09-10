---
title: Pricing Engine
route: /v3/pricing/engine
audience: revenue-ops, finance, exec
slug: pricing-engine
---

# Pricing Engine

The Pricing Engine is the source of truth for every buyer-facing number on the SLYD platform — compute rates, hardware valuations, financing parameters, GPU buyback ladders, and operational cost lines. Open it at **V3 Pricing → Pricing Engine** (`/v3/pricing/engine`).

## Draft vs published — read this first

Most edits on this page are made on the **DRAFT** PricingConfig and are **invisible to buyers until you publish**. A `DRAFT v#` / `published v#` badge in the top right shows where you are.

The two catalog tabs (**GPU Catalog** and **Hardware Catalog**) are the exception — row changes there publish **immediately**.

Buttons at the top:

- **Save draft** — commits draft changes without publishing. Buyers still see the published version.
- **Publish** — saves the draft, then promotes it to published. Propagates to Configurator, Financing, and Finance surfaces. The button label shows the count: e.g. **Publish 5 changes**.
- **Discard draft** — reverts unpublished changes to the last published version. Requires confirmation.

Dirty fields are highlighted with a "was [old value]" inline note. An **Unpublished changes pending** banner appears when DirtyCount > 0.

## Tabs

1. **GPU Catalog** — GPU model SKUs (TDP, HBM, $/GPU, $/GPU·hr, optional secondary-market buy-in). **Publishes immediately.**
2. **Hardware Catalog** — Non-GPU SKUs (servers, networking, storage, power, cooling) with base valuation refs. **Publishes immediately.**
3. **Hardware Curves** — Valuation curve equations per non-GPU category. Enabled curves reach intake on publish; disabled categories return manual ops quotes.
4. **GPU Buyback** — Global multiplier ladder for `/hardware-sales` buyback (ADR 0009): grade × age × warranty × volume × logistics × payout-path multipliers.
5. **Cost Lines** — Hardware cost basis (GPU markup, networking, electrical, enclosure, install) and margin/fee lines.
6. **Cooling & PUE** — Cooling costs per kW by method, PUE, IT overhead, rack density, install costs.
7. **Offtake Terms** — Marketplace clearing: escrow %, offtake threshold %, broker rates, auction fee %.
8. **Configurator** — Public output: grade cost multipliers and public band ± %.

Each tab shows a dirty-change counter when edits differ from the published version.

## Add a GPU model

1. Open the **GPU Catalog** tab.
2. Click **+ Add model** at the bottom of the table.
3. Fill the row: **Model** (e.g. "B200"), **Label** ("NVIDIA B200"), **TDP** (W), **HBM** (GB), **$ / GPU**, **GPUs / Server**, **$/GPU·hr**.
4. Optionally fill **Buy-in $** for a secondary-market reference price ($/GPU). Leave blank to fall back to the global buyback ladder.
5. Optionally check **Low conf?** to widen the indicative band from ±5% to ±12% for thin-market parts.
6. Pick a **Status**: Active, Preview, Deprecated, or Retired. Use Preview to stage rows that should be hidden from buyers.
7. Click **Save**. The row is live for buyers immediately — there is no draft phase for catalog rows.

To bulk-import: download **CSV template** at the top, fill it in (`model, label, tdp_watts, hbm_gb, cost_usd, gpus_per_server, rate_per_gpu_hour, status, secondary_buy_in_usd, buy_in_low_confidence`), then click **Import CSV**. Up to 20 errors are surfaced inline; more are summarized.

## Add a hardware catalog entry / catalog buy-in field

1. Open the **Hardware Catalog** tab.
2. Click **+ Add model**.
3. Pick a **Category** (Server, Networking, Power, Storage, Cooling — GPU is excluded from this tab).
4. Fill **Subcategory**, **Manufacturer**, **Model**, **Label**, **Family** (optional), **Base Price (USD)**.
5. Pick **Status** (Active / Preview / Deprecated / Retired).
6. Click **Save**. Row publishes immediately to intake validation and family-match scoring.

Bulk import works the same way as GPU Catalog (`category, subcategory, manufacturer, model, label, family, base_price_usd, status`).

## Enable a valuation curve for a hardware category

1. Open **Hardware Curves**.
2. Find the category row (Server, Networking, Power, Storage, Cooling).
3. Check **Banded** — the row shows a "was: manual quote" subtitle, confirming the transition.
4. Fill in all six percentage fields: **New %**, **A %**, **B %**, **C %**, **Dep %/mo**, **Floor %**, **Band ± %**. The fields only become editable once Banded is checked.
5. Click **Save draft** or **Publish** at the top. Until published, intake still uses the previous behavior (manual quote or the old curve).

To revert a category to manual quotes, uncheck **Banded** and publish.

## Work the GPU Buyback ladder

Open the **GPU Buyback** tab. Edits here always go through draft → publish.

- **Grade Multipliers** — `× base buy-in` for grades A, A-, B, C. Must be ≥ 0 and in descending order (A ≥ A- ≥ B ≥ C). Publish warns if out of order.
- **Age Penalty** — `% reduction (applied as 1 − x)` for buckets 0–12, 12–24, 24–36, 36+ months. Each must be ≥ 0 and < 1 (1.0 would zero the price).
- **Warranty** — single **Warranty bonus** field (applied as `1 + x` when active OEM warranty).
- **Volume Adjustment** — lot size buckets (<8, 8–64, 64+ GPUs), `1 + x`. Publish warns if any is outside ±20%.
- **Logistics** — CONUS standard, Canada cross-border, Onsite derack. Onsite derack stacks **on top of** CONUS (additive).
- **Payout Paths** — three customer options: Inspection-clear (50/50, 1–4 weeks), Consignment (8–17 weeks, SLYD absorbs upside), Buy-out upfront (1 day). Each must be > 0 and < 2.
- **Indicative Band** — Standard band and Low-confidence band, both fractions in (0, 0.5].

Hard validation (publish blocks): grade multipliers negative, age penalties ≥ 1, payout multipliers outside (0, 2), bands outside (0, 0.5]. Soft warnings (publish allows with confirmation): grade-order violation, volume/logistics outside ±20%.

## Things to know

- **Catalog rows publish immediately.** Curves and the rest of the config are draft-only until you click Publish.
- **Financing Curve fields** (APR base/partial/best, advance rate base/best) are edited on `/v3/pricing/financing-curve` but are part of this draft — they count toward DirtyCount. A chip at the top of the tabs links over.
- **Percent rounding** — fields display value × 100 with `%` but bind to the fraction. Fractions round to 4 decimals on write so round-tripping never drifts.
- **Auction fee snapshotting** — the auction fee is snapshotted onto each auction at publication. Later publishes never drift live auctions (ADR 0008).
- **Configurator public band** — the ± % shown publicly is intentionally a band, not an exact figure. Exact-to-the-cent pricing only appears after a buyer signs in tied to a real lot.
- **Audit trail** — every Save draft / Publish / Discard is audited in core.