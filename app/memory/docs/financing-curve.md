---
title: Financing Curve
route: /v3/pricing/financing-curve
audience: revenue-ops, finance, exec
slug: financing-curve
surface: admin
---

# Financing Curve

The Financing Curve is **the financing rule** (spec §5.2) for every SLYD deal: **APR drops** and **advance rate climbs** as the buyer pre-secures forward offtake (escrowed against the deal). Buyers stuck on the base case (zero offtake) pay the highest APR with the lowest advance rate; buyers hitting the threshold get the best terms. Open at **V3 Pricing → Financing Curve** (`/v3/pricing/financing-curve`).

This page edits the **same PricingConfig draft** as **[Pricing Engine](/v3/pricing/engine)** — the Financing Curve fields count toward the same DirtyCount on that page. Published values from here drive the public **[Financing pages](/financing)**, the **[Configurator](/configure)**, the deal-room's What-if dial on **[Deal Room](/deals/{DealId})**, and pre-quals.

## Page layout

- **Header** — page title + subhead, plus version badges and the standard pricing buttons (top right): **Discard** · **Save draft** · **Publish**
- **Curve grid** — two-column split:
  - **Left:** two stacked SVG charts (APR vs offtake; advance rate vs offtake) sharing the x-axis
  - **Right:** the endpoint editor + worked example calculator
- **Banners** at the top — success / error feedback

## Draft vs published — same rule as Pricing Engine

Three version badges in the header:

- **DRAFT V<N>** — current draft version
- **PUBLISHED V<N>** — version buyers are currently seeing
- **<N> CHANGED** — count of endpoint fields differing from published (the page-local DirtyCount)

Same convention as **[Pricing Engine](/v3/pricing/engine)**:

- **Save draft** — commits draft changes without publishing. Buyers still see the published version.
- **Publish** — saves the draft, then promotes it to published. Two-click confirm: first click arms the button (text becomes **Confirm publish v<N>**), second click commits. Disabled when violations exist.
- **Discard** — reverts unpublished changes to the last published version.

## The APR curve

The top chart on the left renders the APR step curve over `0% → 100%` offtake. Three tiers:

- **Base APR** — applies at **exactly 0%** offtake (no escrow at all)
- **Partial APR** — applies for any `0% < offtake < threshold` (any escrow, but not enough to clear the threshold)
- **Best APR** — applies at `offtake ≥ threshold`

The chart shows the discontinuity at `x = 0` clearly: a closed dot at Base, an open dot just to the right at Partial, then a flat Partial line until the threshold, then a step drop to Best.

Each segment is annotated with its current value (`BASE N%`, `PARTIAL N%`, `BEST N%`).

## The advance rate curve

The bottom chart renders the advance rate over `0% → 100%` offtake:

- **Advance rate at 0%** — the floor
- **Advance rate at threshold** — the ceiling

Between 0% and the threshold, advance rate is **linear** (climbs steadily). At and above the threshold, it's flat at the threshold value.

The chart shows the line plus an area fill below; dots at `(0%, base)` and `(threshold, best)` annotate the endpoints.

## The threshold

A dashed vertical line on both charts marks the **Offtake threshold** — the percentage of capacity escrowed that earns the best terms. A **THRESHOLD N%** label sits at the top of the dashed line. A shaded band fills the chart area to the right (the "best terms" zone).

The threshold is one of the editable endpoints — moving it shifts the dashed line live as you edit.

## Endpoint editor (right column)

Six editable fields, grouped:

### APR tiers

- **Base APR** — `% · no offtake`
- **Partial APR** — `% · 0 < offtake < threshold`
- **Best APR** — `% · ≥ threshold`
- **Offtake threshold** — `% escrowed for best terms`

### Advance rate

- **Advance rate at 0%** — `% of principal`
- **Advance rate at threshold** — `% of principal`

Each field is a percent input (the display value is `fraction × 100`; the underlying fraction is rounded to 4 decimal places on write so round-trips don't drift).

Dirty fields are highlighted with a small **was N%** subtitle showing the published value. The count surfaces in the **<N> CHANGED** badge in the header.

## Worked example calculator

Below the editor:

- **Escrowed offtake** — percent input (0–100, default 60%)
- **APR** output — computed from the draft via the `FinancingMath` calculator
- **Advance rate** output — same calculator

The note below reads: *"Computed via FinancingMath on the draft — the same calculator the Configurator and pre-quals run against the published row."*

This is the way ops sanity-checks the curve: type a sample escrow percentage, see the resulting APR + advance rate, decide if those numbers tell the story you want buyers to see.

## Validation — publish gates

Hard rules. Publish is **disabled** whenever any rule is violated; a yellow violation box explains which rules are broken.

- **Best APR ≤ Partial APR** — APR can only get better (lower) with more escrow
- **Partial APR ≤ Base APR** — same intuition
- **Advance rate at threshold ≥ advance rate at 0%** — advance can only get better (higher) with more escrow
- **Offtake threshold > 0% and ≤ 100%** — must be a real percentage

If any of those fail, the violation box reads each broken rule and a note at the bottom: *"Publish is disabled until the curve is consistent."*

## What ops *cannot* do here

- Add additional APR tiers (the three-tier shape is fixed: Base / Partial / Best)
- Change the curve shape (APR is always a step at threshold; Advance is always linear-to-threshold-then-flat)
- Edit any field on this page after publish without going through the draft → save → publish cycle again
- Override a violation (the rules are hard gates)
- Set per-buyer or per-deal financing curves (the curve is system-wide; per-deal exceptions live elsewhere)

## Things to know

- **Same PricingConfig draft as [Pricing Engine](/v3/pricing/engine).** Edits here count toward the same draft. If you publish here, every Pricing Engine surface (including the Configurator's banded preview) updates on the next load.
- **The shape is intentional.** APR steps; advance rate is linear-to-threshold. That's the **FinancingMath** calculator's shape; it's the same math as the public **[Configurator](/configure)** and pre-quals.
- **Buyers see published only.** Until you publish, the draft is invisible to buyers. They keep seeing the published Financing page, Configurator numbers, and pre-qual outputs.
- **What-if dial on the deal room uses this curve.** When a deal party plays with the What-if slider on **[Deal Room](/deals/{DealId})**, the APR / Advance / Monthly outputs are computed against the **published** curve — same `FinancingMath` calculator as here. If a party's What-if numbers differ from the worked-example numbers here, that's because they're on the published curve and you're editing the draft.
- **Validations are hard gates.** A violation can't be force-published. Fix the curve or revert.
- **Two-click publish.** First click arms, second click commits — same pattern as `Mark earned` on **[Brokers](/v3/platform/brokers)** and stage transitions on **[Deal Pipeline](/v3/deal-flow/pipeline)**.
- **Percent rounding.** Display is `value × 100` with `%`; underlying fraction is rounded to 4 decimals on write so round-trips don't drift.
- **Customer-side surfaces.** The public **[Financing](/financing)** family of pages, the **[Configurator](/configure)** banded preview, the deal-room's **What-if dial**, and pre-quals all read the **published** curve. See **[user-financing.md](/financing)** for the buyer-side view.
- **Related surface — [Pricing Engine](/v3/pricing/engine)**. This page is one tab's worth of the larger Pricing Engine config — promoted to its own page because the financing rule is the single most-impactful number on the platform. The page is cross-linked from Pricing Engine's tabs.
- **Audit trail.** Save draft, Publish, and Discard all write to the Audit Log on **[Platform Audit](/v3/platform/audit)**. The hash chain records every endpoint change.
