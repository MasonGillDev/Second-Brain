# Hardware Subpage Cluster Rebuild (18 routes under /hardware)

**Project:** SLYD Platform website
**Date:** 2026-08-18
**Author:** 3d03f149-0de7-49d6-975d-45f036b6bf58
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Implemented the coordinated rebuild of all 18 in-scope hardware subpages
per the `hardware-cluster-2026-08-17` handoff package. Every `.razor` page
was rewritten; the 18 per-page scoped stylesheets were deleted and
replaced by one shared stylesheet.

### Shared infrastructure

- **`wwwroot/css/v3hwsub.css`** (new, `v3hs-` namespace), registered in
  `Components/App.razor`. One design system for the cluster with four
  family accents (`--accel` cyan, `--oem` purple, `--infra` gold,
  `--svc` green) so the families stay visually distinct without 18 copies
  of near-identical CSS. Focus ring is scoped to interactive elements
  only, because a blanket `:focus-visible` overrode the site's existing
  `h1:focus { outline: none }` and drew a stray box around every H1 after
  Blazor's enhanced-navigation focus.
- **`documentation/hardware-cluster/source-register.md`** (new). Every
  externally sourced fact with its class (durable / manufacturer / slyd /
  volatile), source URL, and review date, plus the blocked claims and the
  release validation record. Reviewer is explicitly recorded as *not
  assigned*, so no page renders a reviewer byline.
- **`V3Nav.razor`**: hardware mega menu and mobile accordion now expose
  `ai-infrastructure`, `nvidia-rtx-pro`, `deployment`, and
  `custom-solutions`, which were previously orphaned or unevenly exposed.

### CTA attribution

`/contact-sales` preserved `?source=` already but did not preselect an
interest for `hardware-*` tags. Added a prefix mapping to
`gpu-hardware`. `/configure` had a hard-coded `source=configure` on its
"Talk to us" link, so attribution died there; it now reads and forwards
an incoming `source`. Both verified end to end against the running app.

**Deviation worth knowing:** the package specifies `/configure` as the
primary CTA for the two service pages. `/configure` is an
energy-backwards *sizing* calculator with no requirement-intake or
attribution capture, so the primary CTA on all 18 pages is
`/contact-sales?source=hardware-<route>` (attribution verified working)
and `/configure` is secondary. Recorded rather than silently swapped.

### Content governance

The rebuild's substance is removing unsupportable claims, not rewording
them. Removed across the cluster: static pricing everywhere, lead times,
availability and stock language, OEM partner / authorized / factory-direct
claims, universal warranty and support and SLA claims, 24/7 monitoring and
emergency response, certification and certified-specialist claims,
fabricated case studies and project counts, and unsourced efficiency and
performance percentages.

Two P0 specification corrections, both verified against the vendor's own
current spec page:

- **AMD MI355X FP4**: page claimed 20 PFLOPS. AMD publishes **10.1 PFLOPs
  peak MXFP4**. Corrected.
- **Universal liquid cooling**: page claimed all Instinct accelerators
  require it. AMD publishes cooling as **Passive OAM** for MI300X/MI325X/
  MI350X and **Passive & Active** for MI355X. Claim removed and replaced
  with configuration-specific guidance.

Broken links fixed: `/contact` (404, robots-disallowed) on deployment and
GIGABYTE, retired `/hardware/nvidia-a100` on ai-infrastructure and also on
`/resources/PowerCalculator` (out of the 18 but the same defect class).

### Verification tooling built

Two scripts in the session scratchpad, both worth keeping if this work
recurs:

- `validate.py` — static checks on the razor sources. Notably it catches
  **odd quote runs inside `@"..."` JSON-LD blocks**, which is a razor
  *compile* error rather than a JSON error and therefore invisible to
  `json.loads`. I hit that failure mode twice; the check caught every
  later instance.
- `runtime.py` + `cdp.mjs` + `shoot.mjs` — validation against the running
  server: rendered JSON-LD parsing, character-exact FAQ/JSON-LD parity,
  link resolution, and a CDP-driven accessibility and overflow audit at
  six viewports.

**Screenshot gotcha:** Chrome headless `--screenshot --window-size=360,800`
crops a desktop render rather than emulating a mobile viewport, which
produces convincing but false "clipped layout" evidence. Use CDP
`Emulation.setDeviceMetricsOverride` with `mobile: true`.

## Results

Build clean, 96/96 tests pass, all 18 routes 200, zero problems across
the static and runtime validators, no horizontal overflow or a11y break
at any of the six required viewports, 108 screenshots captured.

One pre-existing issue reported and deliberately not fixed: the shared
`V3Footer` uses `h5` for column headings, producing an `h2 → h5` step on
every page site-wide including the already-shipped `/hardware` and
homepage. Fixing it would modify previously approved pages.

## To Do Next

- **Human sign-off on the source register.** Reviewer is currently
  unassigned; no page may claim a reviewer until that changes.
- **HPE, Supermicro, GIGABYTE direct retrieval was blocked** from this
  environment (timeouts and 403s). Facts came from vendor-published pages
  surfaced via search, each cited. Re-verify from the vendor sites
  directly before release.
- **Dell XE9685L and XE9785L** were omitted from the model table because
  their accelerator column could not be read unambiguously. Add them once
  confirmed from Dell's spec sheets.
- **Blocked claims needing internal records** if they are ever to return:
  any OEM partner/authorization status, deployment history and project
  counts, support SLAs and response times, geographic coverage,
  compliance attestations, and Lenovo/Supermicro efficiency percentages.
- **Governed listings module** is still absent by design across the
  cluster (fail-closed). Nothing to render until a governed public
  projection exists.
- Not committed and not deployed, per the package instruction.
