# Marketplace UI Overhaul — Inset-Glass Design Ported to /marketplace-v3

**Project:** SLYD Platform (platform-web)
**Date:** 2026-07-14
**Author:** b13a711e-6622-434c-9082-fba21a5678db

## What Was Done

Replaced the rejected "The Floor" trading-terminal design on `GatedMarketplace.razor` (/marketplace-v3) with the user-approved **inset frosted glass** design from `platform/mockups/marketplace-mockup-inset-glass.html`. The user is head of design; iteration happened in standalone HTML mockups first, then this port. Note: the mockups folder had been emptied — the approved mockup was recovered from `~/.Trash` and restored to `platform/mockups/`.

### Design decisions (user-locked via Q&A)
- **Hardware tab = B·Cards** (carousel of glass cards), not the table variant.
- **My Desk dropped from this page** (deposits/booking-request positions no longer render here; `MyBookingsAsync` service method left intact).
- **Background:** standard SLYD page + a *slight* frosted atmosphere — 4 drifting color blobs (indigo/violet/green/cyan, 10–20% opacity), top indigo glow, fine grain. Mockup's galaxies and star/sun points deliberately cut.
- **Ghost sockets fill every carousel to 5 slots**; invite ghosts ("BECOME AN OPERATOR →" / "LIST YOUR POWER-ON DATE →" → both navigate to /deploy) lead the two capacity rails only.
- **Arrows must never point where the carousel can't move** — JS toggles `.off`; CSS makes `.off` fully gone (`opacity:0; visibility:hidden; pointer-events:none`) so it can't be hovered, clicked, or tab-focused.

### Structure
- `<StandardPageHeader Title="Marketplace">` (real shared chrome, not the mockup mimic).
- Tabs: **Offtake** (Available Now / Forward Capacity / Forward Lots carousels) and **Hardware** (spot-lot cards), gate label "EXACT PRICING · SIGNED IN".
- Card material: frosted slab seated in a recessed socket — the big layered box-shadow stacks from the mockup; NO `overflow:hidden` on `.card` (kills rounded-corner clipping of the filtered backdrop); vignette animates **opacity only** (a brightness() filter disables backdrop-filter and kills the frost).
- Forward-lot cards: subscription sub-hero (big %, etched groove bar, "$X of $Y target", close-condition with urgency warn), statuses "62% SUBSCRIBED / CLOSING · 78% / JUST LISTED / SUBSCRIPTION CLOSED".
- All existing plumbing preserved unchanged: book drawer (BKG demand w/ term), deposit drawer (bank-wire, PLEDGED, closed-state honesty), lot-detail drawer (spec · exact pricing · provenance trail · reserve — the /source consolidation), server-side guards.

### Files
- `platform/src/Platform.WebUI/Components/Pages/DealOS/GatedMarketplace.razor` + `.razor.css` — full rewrite of markup/styles on top of unchanged @code logic (minus `_mine`).
- `platform/src/Platform.WebUI/wwwroot/js/marketplace-floor.js` (new) — `window.slydFloor`: spotlight vignette with per-side scroll-gated caps (zone=260px, `f = t²·cap`, `opacity = 1 − 0.5f`), arrow `.off` gating (scrollLeft < 8 / > maxScroll − 8), idempotent binding via dataset flag, re-synced from `OnAfterRenderAsync` every render (tab switches rebuild rails). Registered in `App.razor` after site.js. CSP already allows the inline `onclick="slydFloor.slide(...)"` handlers (`'unsafe-inline'`).
- `platform/mockups/marketplace-mockup-inset-glass.html` — restored design reference.

Verified: Platform.WebUI builds clean (0 errors, warnings pre-existing), 49/49 platform tests green.

## To Do Next
- User to review live (restart Platform.WebUI first — new JS file + markup) and tweak blob opacities if the atmosphere reads too strong/faint.
- **Possible conflict to check:** a parallel session (276f1528) logged a drawer/header z-index fix on Source & Marketplace at 12:39 — verify it didn't land on the pre-rewrite `GatedMarketplace.razor.css`, and re-apply on the new file if needed.
- Commits pending user sign-off (repo rule: always ask) — this rides with the capacity-deal-shape work; core must be tagged/published before platform/admin CI.
