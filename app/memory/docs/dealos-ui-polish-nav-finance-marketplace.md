# DealOS UI Polish: Route-Aware Nav, Finance De-Slop, Marketplace Copy

**Project:** SLYD Platform (Platform.WebUI)
**Date:** 2026-07-16
**Author:** 03cffc02-2e8e-447d-906d-8347231fd42b
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Committed as platform `2f3a972`. Three strands, driven by honest-critique passes on the Marketplace, Dashboard-vs-old comparison, and Finance pages:

### Route-aware exclusive nav expansion (`UnifiedNavMenu.razor`)
The nav had grown too long — Overview + Deal OS + Use Compute all expanded by default pushed Provide Compute/Account/Support off-screen. Now `SectionForCurrentRoute()` maps the current path to its owning section (specific paths claim first: `provider/company-info`→Account, `consumer/support-tickets|notifications`→Support, then `provider*`→Provide, `consumer*`→Use, DealOS route list). `ApplyRouteExpansion()` opens that section and collapses the rest, on init and every `LocationChanged`. Chevrons still work manually between navigations. Disabled routes (auctions/benson/organization-info) pre-mapped.

### Marketplace de-jargoning (`GatedMarketplace.razor` + css)
Insider-speak removed from customer-facing strings; "demand"/"offtake"/pipeline vocab stays in code, comments, IDs (per CLAUDE.md):
- Header: "The signed-in board — exact pricing, bookable…" → "Live GPU capacity and hardware at exact prices…"
- Tab "Offtake" → "Compute"; "Post a demand" → "Request hardware" (button + drawer title)
- All "X DEMAND FILED" footnotes → "…REQUEST SENT/POSTED"; "matching sweep"/"(BKG-)"/"(NEED-)" plumbing removed from copy
- `.post-btn` upgraded from 10.5px mono-uppercase ghost pills to real actions (Space Grotesk 13px semibold, primary-tinted fill/border)
- Service-returned `result.Message` strings NOT swept (would need GatedMarketplaceService/IntakeService edits)

### Finance page de-slop (`Finance.razor` + css)
The page read as "AI slop" — the tells were mono-uppercase micro-labels everywhere, self-referential copy, cutesy metaphor headings, hollow layout:
- Mono-caps demoted everywhere except ONE deliberate accent: the CTA footnote ("NO COMMITMENT · NO CREDIT PULL · TERMS COME TO YOU FOR REVIEW")
- Deleted: "PUBLISHED CONFIG · SAME MATH AS THE CONFIGURATOR", "PATH 01/02/03" codes, the floating green gate pill (promise now lives in header + CTA footnote only)
- "The offtake lever" → "How escrow moves your rate"; header description shortened to fit the 2-line clamp (was truncating mid-sentence)
- Dashed ghost slot after deal cards ("Deals appear here while terms are open") so a lone card doesn't float in a void
- Kept deliberately: KPI stat micro-labels, −bps chips, stage pills, the slider mechanic itself

### Machined slider (Finance.razor.css)
Old: 6px flat track + flat primary dot + a gold threshold div slicing through the thumb. New: 14px recessed channel (inset lip shadows, lit lower lip, brushed vertical grain, dark step-zone tints) with the **threshold machined into the track floor as a gradient notch layer** — the ball rolls over it, progress fill covers it when passed. Thumb: 20px polished-steel ball (specular radial highlights, seat ring, drop shadow into the groove). `.slider-threshold` div survives only to position the label. Material rgba literals follow the marketplace-glass convention; semantic colors stay tokens.

## To Do Next
- Push `2f3a972` (development is 1 ahead).
- Optional: sweep "demand" from service-layer result messages.
- Finance critique leftovers: toy seed data ($2.5K deal, $28 fee) is a data problem, not UI.
