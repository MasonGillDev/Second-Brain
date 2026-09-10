# V3Nav Mobile Drawer — Full-Height and Accordion Collapse Fix

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Mason reported the mobile nav drawer not rendering properly (screenshot: drawer ending
mid-screen, "The Fabric" clipped, Sign in / Start a deal overlapping the links). Confirmed as a
known pre-existing issue — `V3Nav.razor` and `V3Nav.razor.css` had **zero working-tree changes**,
so the drawer was exactly as committed and the same-day hover sweep was not implicated.

Two independent defects, both found by measuring the live DOM rather than reading CSS.

### Defect 1 — drawer was 74px tall instead of 844px

`<header class="v3nav-top">` carries `backdrop-filter: blur(12px)`. **An element with a
`backdrop-filter` other than `none` becomes the containing block for its `position: fixed`
descendants.** The drawer was markup-nested inside that header, so its `top: 0; bottom: 0`
resolved against the 74px header instead of the viewport.

Measured before fix (390×844):

```
drawer rect: top=0 bottom=74 height=74     viewport height=844
  .v3nav-drawer-head  h=75
  .v3nav-drawer-body  h=24     <- squashed, hence the clipped "The Fabric"
  .v3nav-drawer-foot  h=77     <- overflowed past the panel, hence the overlap
ancestors that trap position:fixed:
  <header class='v3nav-top'>  backdrop-filter=blur(12px)
```

**Fix:** moved `.v3nav-scrim` and `.v3nav-drawer` out of `</header>` to component top level.
The 5 mega-menu panels stay inside the header — they are desktop dropdowns anchored to it.

Same trap would be sprung by `transform`, `filter`, `perspective`, `will-change`, or `contain`
on any ancestor. The diagnostic script checks all of them, not just `backdrop-filter`.

### Defect 2 — accordion sections never collapsed

Collapse uses the `grid-template-rows: 0fr → 1fr` idiom. **That sizes only the *first* row.**
The five `<a>` elements were direct children of `.v3nav-acc-panel`, so four of them landed in
auto-sized *implicit* rows and stayed open regardless of `aria-expanded`.

This was invisible while defect 1 was present — the drawer was too short to show it. It only
surfaced after the height fix, which is why measuring after each change mattered.

Measured: collapsed panel = **193px** (should be ~0), expanded = 214px — a 21px difference,
exactly one row.

**Fix:** wrapped each panel's children in a single `.v3nav-acc-panel-inner` element — which the
CSS comment already assumed existed ("Wrap the children so the grid 0fr→1fr collapse works
cleanly") but the markup never provided. Added a CSS comment recording that the wrapper is
load-bearing, so nobody flattens it back.

### Verification

All measured live over CDP at 390×844 with touch emulation:

| | before | after |
|---|---|---|
| drawer height | 74px | **844px** (= viewport) |
| drawer body | 24px | **692px** |
| collapsed panel | 193px | **0px** |
| expanded panel | 214px | 214px |
| trapping ancestors | 1 | **0** |

Also confirmed: scrim covers the full 390×844 viewport, close button returns the drawer
off-screen, and on desktop all 5 mega panels remain inside the header. Build clean,
**250/250 tests pass**. Visual screenshot check confirmed by Mason.

### Commits

Committed on `content-governance-2026-08-18` at Mason's request, as three separate commits so
the changesets stay reviewable:

- `133ea96` Remove hover animations from non-interactive elements (see
  [[website-hover-affordance-sweep]])
- `f94a420` Fix mobile nav drawer rendering — this doc
- `d353266` Extend hero slide-up reveal to the v3 pages — **authored by a concurrent Claude Code
  session** working in the same tree, committed at Mason's explicit request

`wwwroot/css/shared-components.css` contained hunks from both the hover sweep and the hero
reveal; split by hunk with `git apply --cached` so each commit got only its own changes.

**Not pushed** — repo CLAUDE.md requires asking before pushing, and pushes go to `development`,
never `main`.

## To Do Next

1. **Not pushed.** Branch `content-governance-2026-08-18` now carries four content-governance
   commits plus these three. Confirm the intended target before pushing.
2. The concurrent session may have continued working after `d353266` was committed at 10:30 —
   its last write was 10:20. Check whether it has further uncommitted hero-reveal work.
3. Audit other `position: fixed` elements for the same containing-block trap. Any overlay,
   modal, or dropdown nested inside an ancestor with `backdrop-filter`/`transform`/`filter`
   will be silently mispositioned. `Components/Shared/BensonWaitlistModal.razor` is worth
   checking first.
4. Search for the `grid-template-rows: 0fr` idiom elsewhere — the same multiple-direct-children
   bug applies anywhere it is used without a single wrapper child.
