# Marketplace Inset-Glass Mockup — Design Iteration (background, edges, listing bays)

**Project:** SLYD Platform (design mockups)
**Date:** 2026-07-16
**Author:** faebe893-bd61-4000-a888-20fff111ccfa
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Iterated `platform/mockups/marketplace-mockup-inset-glass.html` (rev 3) with the user (head of design) across several rounds:

### Listing bays (latest round)
Wrapped each capacity listing type in its own stylized "bay" — a wide shallow tray recessed into the page, extending the material story (page → bay → card socket → glass slab). Purpose: users outside the company don't know what "live capacity / forward capacity / forward lot" mean, and three bare carousels read as boring.
- Each bay: accent-colored glyph in an etched well + mono eyebrow + title + plain-English description + a right-side "how it works" fact rail (three etched grooves: *You book → a GPU count + term*, etc.).
- **Accent = the same color as the status pills on that bay's cards** so section and listings agree: Available Now = green, Forward Capacity = gold, Forward Lots = violet, Spot Lots (hardware tab) = indigo. Accent appears as glyph color, eyebrow color, and a diffused radial wash out of the bay's top-left corner.
- Eyebrows encode the real axis, not decoration: `RENT COMPUTE · RUNNING TODAY` / `RENT COMPUTE · POWERS ON AT A DATE` / `BUY HARDWARE · FUNDING TOWARD DEPLOYMENT` / `BUY HARDWARE · IN STOCK NOW`.
- Hardware tab got the same treatment (its `hw-note` paragraph folded into the bay description); old `.cat`/`.cat-head` CSS removed.

### Earlier rounds this session
- **Background:** replaced floating particles → laser beams (rejected) → **galaxies**: 5 CSS spiral discs (conic-gradient arms, radial mask, blur, tilt/squash, 75–200s revolve, static glowing core) + **8 twinkling suns** with periodic diffraction-spike flares. Blob opacities reduced to sit behind them.
- **Card edge roll-off:** rebuilt the box-shadow profile so the rounded edge reads correctly — outermost 1–2px ring is DARK (the edge turning down into the seam), bright crest peaks ~4px inside, falloff washes inward ~9px/~16px; bottom edge brightest. Border is a dark seam line, not a lit line.
- **Square-corner artifact (UNRESOLVED):** user's browser paints the backdrop-filtered frost to the square bounding box, worse on hover. Fixes kept: no `overflow:hidden` on `.card`, `isolation:isolate`, children clip via `border-radius:inherit`, table wrap uses opaque body instead of backdrop-filter, JS vignette animates opacity only (a `filter` would disable backdrop-filter). A Safari-targeted restructure (frost moved to `::before` + clip-path/mask) **broke something and was reverted** on user request. Established: headless Chrome (GPU and software) renders clean both ways — suspect user is on Safari/WebKit; awaiting user's answer on browser + what broke.

Debug harness lives in the session scratchpad: frozen-animation renders (`* {animation:none !important}` injection), sips crops, struct-based BMP pixel probes (no PIL; sips BMPs are top-down).

## To Do Next
- Square corners in the user's browser — need browser name + what the reverted fix broke before another attempt.
- If the bay design is approved, port it into `GatedMarketplace.razor` (see [marketplace-inset-glass-ui-port.md](marketplace-inset-glass-ui-port.md) for the port that predates the bays/galaxies — it deliberately cut galaxies/suns; revisit whether bays should carry over).
