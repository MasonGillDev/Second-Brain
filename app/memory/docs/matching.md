---
title: Matching · 3-sided
route: /v3/deal-flow/matching
audience: deal-ops, supply-ops, revenue-ops
slug: matching
surface: admin
---

# Matching · 3-sided

Matching · 3-sided is the **site-driven assembly console** — pick a power/data-centre site and the page assembles the best **(site + operator + offtake-buyer)** triples that could become a deal. It also surfaces the **regional balance** for the site's ISO so ops can see how energy supply, operator demand, and offtake demand stack against each other in that region. Open at **V3 Deal Flow → Matching** (`/v3/deal-flow/matching`).

This is the three-sided counterpart to **[Match Engine](/v3/deal-flow/match-engine)** (which is two-sided: lot ↔ demand). Same scoring infrastructure under the hood, different starting entity.

Site definitions live on **[Sites](/v3/intake/sites)**. Operator and offtake-buyer account definitions live on **[CRM Accounts](/v3/crm/accounts)**.

## Page layout

- **Header** — page title (*"Matching · 3-sided"*) + a dynamic subhead that reads:
  - *"Loading sites…"* while sites load
  - *"N sites ready · choose one to assemble energy + operator + offtake into a deal draft"* before a site is selected
  - *"Assembling triples for <site name>…"* while the page is scoring
  - *"N assembly candidates · top 10 by score"* once results are loaded
- **Choose a site** section — typeahead picker (plus a quick-pick chip row in demo with ≤25 sites)
- **Site details** card (after selection) — site summary
- **Regional balance** card — three-bar comparison for the site's ISO
- **Assembly candidates** grid — top 10 triples, each rendered as a candidate card
- **Assemble modal** — opens when ops clicks **Assemble** on a candidate
- **Success banner** at the top after a successful Assemble

## Choose a site

The picker is a typeahead. It matches on:

- **DisplayId**
- **Name**
- **ISO** code

Placeholder text: *"Search by display id, name, or ISO…"*

For demos with fewer than 25 sites, a **quick-pick chip row** appears as a secondary affordance. Each chip shows `<DisplayId> · <Name> · <ISO> · <Available kW>`.

Only sites the page's assembler considers actionable appear — typically those past intake on **[Sites](/v3/intake/sites)**.

## Site details card

After a site is picked, the page shows:

- **Site** — DisplayId
- **Name** — site name
- **ISO** — region code
- **Available kW** — site's stated available capacity
- **Owner** — site owner account name (from **[CRM Accounts](/v3/crm/accounts)**)
- **Coordinates** — lat/long to 3 decimal places
- **Required capabilities** — a row of capability chips, or *"— none —"* if none required

## Regional balance

A three-bar card showing the **most recent snapshot** for the site's ISO. Three rows:

- **Energy supply** — total available kW
- **Operator demand** — operator-side demand kW
- **Offtake demand** — offtake-side demand kW

Each row is a horizontal bar coloured by lane (supply / operator / offtake). The bar widths are normalised against the **largest of the three** in the snapshot — so the longest bar always fills the track, and the others scale relative to it.

A timestamp in the section header shows when the snapshot was computed (local time).

If no snapshot exists yet for the region, the card reads: *"No snapshot for <ISO> yet. The balance bonus defaults to 0 until the next snapshot job runs."* This means matches against this site won't carry the regional-balance dimension bonus until the snapshot refreshes.

## Assembly candidates grid

The page shows the **top 10** assembled (site + operator + offtake-buyer) triples, ranked by score. Each is rendered as a **candidate card** with:

### Header strip

- **Rank** (`#1`, `#2`, …)
- **Score** — banded score pill (hot / warm / cold)
- **Assemble** button (link icon)

### Three triple columns

- **Site** — the picked site's name + sub-line `<ISO> · <Available kW>`
- **Operator** — operator account name (or *"Unnamed operator"*) + sub-line `<capacity kW> · delivery <%>`
- **Offtake** — offtake-buyer account name (or *"Unnamed buyer"*) + sub-line `<wanted quantity> × <GPU model>`

### Dimension breakdown row

Below the columns, a row of **dimension chips** — every dimension the scorer considered, ordered by absolute point magnitude (largest first). Each chip shows the dimension name and signed points, colour-coded by direction. Hover for the full explanation.

Unlike **[Match Engine](/v3/deal-flow/match-engine)** (which only previews the top 3 dimensions and reveals the rest on expand), the 3-sided page shows the **full breakdown by default** — no expand needed.

Empty state for the grid: *"No assembly candidates found for this site."*

## Assemble — the terminal action

The action that creates a new deal from this site + operator + offtake-buyer triple.

1. On the candidate card, click **Assemble** (link icon).
2. The **Assemble modal** opens, pre-loaded with the site and the candidate triple.
3. Review the triple and click the confirm button in the modal.
4. On success, the modal closes and a green banner reads: *"Deal SLY-YYYY-NNNN created — offtake demand attached."*

The Assemble action commits in one step:

- A new **Deal** is created in the **CONFIGURING** stage on **[Deal Pipeline](/v3/deal-flow/pipeline)**, with the operator account, offtake-buyer account, and site already bound. Value and power default to 0 — ops fills those in on the Pipeline drawer.
- The offtake demand transitions from **OPEN** to **MATCHED** and is attached to the new deal.

Each step is written to the **[Audit Log](/v3/platform/audit)** as `deal.created` and the demand attach. The deal is immediately visible on **[Deal Pipeline](/v3/deal-flow/pipeline)**.

Hardware lots are not part of the 3-sided assembly — they get added later through the supply path on **[Inventory Lots](/v3/supply/inventory)**.

## What ops *cannot* do here

- Edit the site (read-only here; mutations live on **[Sites](/v3/intake/sites)**)
- Edit the operator's capacity, delivery rate, or capabilities
- Edit the offtake-buyer's wanted quantity / GPU model
- Re-rank or change the assembly algorithm
- Force a regional-balance snapshot refresh (the snapshot runs on its own schedule)
- Pick multiple sites at once

## Things to know

- **Top 10 candidates only.** Capped at 10. If a likely triple isn't there, refine the site first (capability requirements, available kW) and reload.
- **Full breakdown is always visible.** Every dimension's points and explanation are inline on the card — no expand state. Compare against [Match Engine](/v3/deal-flow/match-engine), which previews the top 3 and reveals the rest on click.
- **Regional balance is a snapshot.** It's not live. The timestamp in the section header tells you when it was last computed. A stale snapshot means the balance dimension on the score is stale too.
- **No snapshot ⇒ balance bonus = 0.** A region without a snapshot won't penalise candidates but won't reward them either. The dimension defaults to neutral.
- **Cancellation is built in.** Picking a different site mid-assembly cancels the in-flight load and starts a fresh one.
- **Quick-pick is demo-only.** Only appears with ≤25 sites in the pool. In production it's typeahead-only.
- **Site coordinates are visible.** Lat/long to 3 decimals shows on the details card. Useful for verifying you've got the right site if multiple share a name.
- **Required capabilities act as hard filters.** A site that requires `liquid-cooling` won't pair with an operator that doesn't claim it. If you see a small candidate list, check the site's capability chips first.
- **Assembling creates a real deal.** The new deal lands in **[Deal Pipeline](/v3/deal-flow/pipeline)** under **CONFIGURING** immediately, with site + operator + offtake-buyer bound and the offtake demand attached. Value and power default to 0 — finish populating those on the Pipeline drawer's **Edit** form.
- **No hardware lots yet.** The 3-sided deal is created without any lots. Add them via the supply path: open a **LISTED** lot on **[Inventory Lots](/v3/supply/inventory)** and bind it to the deal during the **RESERVED → ALLOCATED** step.
- **Related surface — [Match Engine](/v3/deal-flow/match-engine).** That page pairs lot ↔ demand (two-sided). This page pairs site + operator + offtake-buyer (three-sided). Pick the page that matches what you have on hand: supply you want to place, or a site you want to assemble around.
