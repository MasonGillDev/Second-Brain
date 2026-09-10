---
title: Sites Registry
route: /v3/sites
audience: supply-ops, deal-ops
slug: sites
surface: admin
---

# Sites Registry

Sites Registry is the admin view of every **ops-managed energy site** on the platform — the `Site` entity that **[Matching · 3-sided](/v3/deal-flow/matching)** joins with operators and offtake buyers to assemble deals. Each row carries kW capacity, voltage class, ISO region, lat/lon, and a site type. Sites land here after ops promotes them out of the public intake queue (see **[Site Submissions](/v3/intake/site-submissions)**) or by direct creation out-of-band.

Open at **V3 Overview → Sites Registry** (`/v3/sites`).

> **Naming note.** Earlier versions of the admin called this page "Site Submissions" at `/v3/intake/sites`. As of the cohesion rework it's now the registry of *ops-managed* sites, and the actual public intake from `/marketplace/power-opportunities` lives at **[Site Submissions](/v3/intake/site-submissions)**. The Sites Registry only shows rows ops has accepted into supply.

The Site entity has **no lifecycle field** — there's no "draft / approved / rejected" state machine. Instead the page derives a binary **MATCHED** / **INTAKE** state from whether the site is bound to a deal yet. The only mutation on the page is editing **Available kW** (the field that drives PowerFit scoring).

## Page layout

- **Header** — page title + the "public Bring-Energy intake" subhead
- **Type filter bar** — pills + a counter on the right showing `N SITES · N kW · N kW AVAIL`
- **ISO filter bar** (second row) — appears when sites span multiple ISOs; pills + a **Clear** chip
- **Left panel** — sites table
- **Right panel** — drawer with detail, capabilities, Available kW editor, and matching state
- **Banners** at the top — success / error feedback

Clicking a row opens the drawer.

## Site types

The page filters first by **Site Type** — the energy source / configuration:

- **Stranded Gas** — gas wells with no pipeline takeaway
- **Hydro** — hydroelectric baseload
- **Flare** — flare-gas mitigation
- **Retired BTC** — sites that previously ran Bitcoin mining
- **Grid** — grid-connected industrial
- **Solar** — solar arrays
- **Wind** — wind farms

The `Unknown` value isn't in the filter — it shows up if a submission came in without a classifiable source, and ops should pick a real type when reclassifying. Single-select.

## Voltage class

Sites carry a voltage class shown in a column and in the drawer:

- **LV** — Low Voltage
- **MV** — Medium Voltage
- **HV** — High Voltage
- **UHV** — Ultra High Voltage
- `—` if unset

## Table columns

- **Site** — name on top, DisplayId below
- **Type** — site-type chip (coloured by type — stranded-gas / hydro / flare / retired-btc all get distinct colours)
- **ISO / Region** — ISO code if set (e.g. `ERCOT`), otherwise the freeform region
- **Voltage** — voltage class label
- **kW** — nameplate capacity
- **Available kW** — currently bound-available capacity (≤ nameplate)
- **Matched** — deal DisplayId chip if bound to a deal (accent), otherwise `—`

## Filter the list

- **Type pills** — `All` + one pill per site type (excluding Unknown). Single-select.
- **ISO chips** (second row) — `All` ISOs that appear in the current filter, each as a clickable chip. Pick one to scope further; the **Clear** chip removes it.
- **Counter** on the right of the type bar: `N SITES · N kW · N kW AVAIL` for the current filter.

There is no free-text search.

## Inspect a site

Click any row. The drawer shows:

### Header

- **Site name** as the heading
- **DisplayId** · the **site-type chip** · a **MATCHED** badge (if bound) or **INTAKE** badge

### Detail grid

- **Type** — site type
- **ISO / Region** — ISO code (or region)
- **Voltage** — voltage class
- **Owner** — owning account name (from **[CRM Accounts](/v3/crm/accounts)**), or `—`
- **Nameplate** — full capacity (`N,NNN kW · X.X MW`)
- **Available** — currently available capacity (same format)
- **Lat / Long** — coordinates to 4 decimals
- **Origin** — intake channel (e.g. the public `/marketplace/power-opportunities` form), or `—`

### Required Capabilities

A chip row of capability tags the site requires (e.g. `liquid-cooling`, `dust-rated`). If empty, the panel reads: *"None — any operator capability set scores full credit."* These are hard filters on **[Matching · 3-sided](/v3/deal-flow/matching)** — operators without the required capabilities won't appear as candidates.

### Available kW editor (the only mutation)

The page lets ops edit **Available kW** to drive the PowerFit scoring dimension on **[Matching · 3-sided](/v3/deal-flow/matching)**.

1. Type a new value in **Available kW (PowerFit scoring)** (clamped between 0 and the nameplate).
2. Click **Save**. Disabled until the value differs from the current value.
3. Success banner reads: `<DisplayId> available capacity → N kW · X.X MW — logged to Audit Log.`

Hint text below the field: *"Capacity edits are logged to the Audit Log with before/after values."*

### Matching block

- If bound to a deal: *"Bound to deal `<DealDisplayId>` — this site is consumed by an assembled deal and is no longer free supply."*
- Otherwise: *"Not yet bound to a deal — this site is live supply for the three-sided matcher (PowerFit · distance · operator capability scoring)."*

## What ops *cannot* do here

- Edit site name, type, voltage, lat/long, owner, or required capabilities (only Available kW is editable)
- Create a site from scratch on this page (sites come in via the public intake or are seeded out-of-band)
- Reject a submission (no state machine; if a site is unusable, drop its Available kW to 0)
- Unbind a matched site from its deal (that's a deal-pipeline action)
- See the public form fields the visitor filled before submitting (the page only carries the resulting Site fields)

## Things to know

- **No site state machine.** A site is either bound to a deal (**MATCHED**) or it isn't (**INTAKE**). There is no draft / approved / rejected lifecycle.
- **Available kW is the only PowerFit lever.** Lower it to make the site less attractive in matching without removing it from supply. Raise it (up to nameplate) to surface it more. Every change writes a hash-chained Audit Log entry on **[Platform Audit](/v3/platform/audit)** with before/after values.
- **Required Capabilities are hard filters.** A site that requires capabilities the operator doesn't claim won't pair on **[Matching · 3-sided](/v3/deal-flow/matching)** — it's a hard exclusion, not a penalty. If a site has zero candidates, check its capability chips.
- **`Matched` means consumed.** Once a site is bound to a deal, it's removed from free supply. The matcher won't re-rank it. To make it available again, the deal needs to be unbound upstream — escalate.
- **Sites land here from the intake queue.** The public **[Bring energy to SLYD](/marketplace/power-opportunities)** form on slyd.com creates a `SiteSubmission` row on **[Site Submissions](/v3/intake/site-submissions)**. Ops reviews the submission there; once it clears due diligence ops converts it into a real Site row, which is what shows up on this Registry. The intake queue is the triage surface; Sites Registry is the live supply surface.
- **Origin channel tracks where the submission came from.** The Origin field on the drawer detail shows the intake channel — useful when a submitter calls and ops needs to know which surface they used.
- **No search.** Use the type pills and ISO chips to narrow the list.
- **Lat/Long is 4 decimal places.** Roughly 11 m precision. If two sites share a name, lat/long is the disambiguator.
