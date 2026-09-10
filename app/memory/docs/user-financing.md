---
title: Financing (customer flow)
route: /financing
audience: support, revenue-ops, deal-ops
slug: user-financing
surface: user
---

# Financing — customer flow

End-to-end walkthrough of what a public visitor sees on the SLYD financing pages. The marketing surface lays out the three financing paths SLYD offers and points visitors at the pre-qualification flow. Page family:

- **`/financing`** — landing / overview (three paths)
- **`/financing/gpu`** — GPU-specific financing
- **`/financing/infrastructure`** — Data-centre infrastructure financing
- **`/financing/leasing-vs-buying`** — Lease vs buy comparison
- **`/financing/apply`** — Pre-qualification / application form

The admin counterpart that owns the **APR** and **advance rate** numbers shown on these pages is **[Financing Curve](/v3/pricing/financing-curve)**. Other rates and assumptions come from the broader **[Pricing Engine](/v3/pricing/engine)** config. The customer-facing equivalent for the deal-time What-if dial is on **[Deal Room](/deals/{DealId})**.

## `/financing` — the landing page

Headline: *"Finance the build. Keep the title."*

Lede: *"SLYD originates and arranges the financing for your deployment. You take title to the cluster; the lender takes the lien; SLYD takes a clearing fee. Three paths, indicative terms in thirty seconds, no credit pull to start."*

### The three financing paths

Three side-by-side path cards on the hero:

#### PATH 01 · SLYD-FINANCED (most chosen)

- **Own it, financed.** *"36-month term, title to the buyer from day one. The lender holds the lien; you build equity in the cluster."*
- Example: **$236K/mo** on a `$6.3M build · 36mo`
- Features:
  - **Title to buyer** from close — build equity, depreciate the asset
  - **8.0–9.8% APR** indicative — pre-secured offtake lowers it
  - **No recourse** beyond the cluster collateral
- CTA: **Pre-qualify →** (links to `/configure#qualify`)

#### PATH 02 · LEASE-ONLY

- **Operating lease.** *"36-month operating lease. Residual to SLYD, fair-market buyout option. Off your balance sheet."*
- Example: **$212K/mo** on a `$6.3M build · 36mo`
- Features:
  - **Lower monthly** — residual value stays with SLYD
  - **Off balance sheet** — operating-lease treatment
  - **FMV buyout** at term, or refresh to current-gen
- CTA: **See lease terms →** (links to `/configure#qualify`)

#### PATH 03 · CASH PURCHASE

- **Buy outright.** *"Pay for hardware and install up front. Operating expense (power, cooling, maintenance) handled separately."*
- Example: **$6.3M total** on `hardware + install`
- Features:
  - **No financing cost** — lowest total outlay
  - **Full ownership** immediately, depreciate in full
  - **SLYD still sources**, installs, and can operate via SLYD Cloud
- CTA: **Configure a build →** (links to `/configure`)

### The offtake lever section

Below the three-path strip, the page explains how pre-securing forward offtake unlocks better terms — the same step-curve behaviour the **[Financing Curve](/v3/pricing/financing-curve)** admin page edits. Visitors see a marketing version of the curve here; the admin source of truth lives there.

## `/financing/gpu` — GPU Financing

A more specific marketing page focused on **GPU-only** financing (no full data-centre infrastructure). The numbers come from the same pricing engine; the framing is narrower.

## `/financing/infrastructure` — Infrastructure Financing

The complement of `/financing/gpu` — full-stack data centre buildout financing (power, cooling, racks, networking, storage in addition to GPUs).

## `/financing/leasing-vs-buying` — Leasing vs Buying

A comparison page laying out the trade-offs between Path 02 (Lease) and Path 03 (Cash). Helpful for visitors who haven't picked a path.

## `/financing/apply` — Apply / Pre-qualify

The pre-qualification form. The page promises *"no credit pull to start"* — the form gathers indicative info (build size, region, financing path, contact) and lands as a Lead in **[Leads Inbox](/v3/crm/leads)** (channel `Form`) plus a Form Submission in **[Forms](/admin/forms)**.

A `?source=financing` (or path-specific tag) query param often rides along, surfacing in the Lead's Source column for routing.

## Numbers — where they come from

Every published rate on these pages traces to the admin side:

- **APR (8.0–9.8% indicative on Path 01)** — comes from the **[Financing Curve](/v3/pricing/financing-curve)** published config (Base / Partial / Best APR)
- **Advance rate** — same source
- **36-month term** — assumption used by the worked example
- **Build cost examples ($6.3M)** — sized via the same pricing engine that powers **[Configurator (customer flow)](/configure)**
- **Monthly payment examples ($236K, $212K)** — computed via the same `FinancingMath` calculator the configurator and the deal-room What-if dial use

If a visitor's pre-qual estimate diverges from the marketing numbers here, the marketing page is **indicative**; the actual quote comes after the form is submitted and a real-deal record is created — and that record uses the **same calculator** as everything else.

## Things to know

- **Public, anonymous.** No login required. Visitors can browse the marketing pages and submit pre-qual without an account.
- **Pre-qual is no credit pull.** That's the promise on the apply page — gathered info is indicative-only. Real credit work happens during the deal flow, not at intake.
- **Marketing numbers are indicative.** The hero card amounts ($236K/mo, $212K/mo, $6.3M total) are worked examples on a specific build size. A visitor's actual quote depends on their inputs and the live published config.
- **Path 01 is "most chosen" by SLYD's framing.** That's marketing emphasis, not a technical default — visitors can pick any path.
- **Offtake lowers APR.** That's the core financing pitch — pre-securing forward offtake (committing to use the capacity later) drops APR from Base → Partial → Best. The threshold and tier values live on **[Financing Curve](/v3/pricing/financing-curve)**.
- **All paths still involve SLYD.** Cash Purchase still uses SLYD for sourcing, installation, and (optionally) operation via SLYD Cloud — paying cash doesn't mean cutting SLYD out.
- **Pre-qual form lands as a Lead with `?source=financing`** (or sub-page tag). See **[Leads Inbox](/v3/crm/leads)** for the routing.
- **Customer-facing peers.** **[Configurator (customer flow)](/configure)** sizes the build (cost + APR); **[Hardware buyback (customer flow)](/hardware-buyback)** is the resale side of the lifecycle; **[Marketplace](/marketplace)** is for already-listed capacity. All four read from the same Pricing Engine.
- **The same APR / advance / monthly math lives on the [Deal Room](/deals/{DealId})'s What-if dial.** Once a buyer has a deal record, the What-if dial uses the same `FinancingMath` calculator the marketing page numbers come from — so a buyer's deal-time What-if estimate should match the marketing-page hero amounts at the same parameters.
