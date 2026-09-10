# /hardware Rebuild: Enterprise GPU Hardware Sourcing (Aug 2026 Spec)

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Rebuilt `/hardware` per the enterprise-GPU-hardware implementation prompt (part of the coordinated commercial-page release; NOT deployed separately). `Hardware.razor` fully rewritten; sourcing-rebuild CSS appended to `Hardware.razor.css` (reused v3hw base + stacked the split section-head like the homepage fix).

**Structure:** hero (H1 "Enterprise GPU servers and AI infrastructure hardware", RenderedServer2.png as the hardware image, CTAs Source hardware → /configure?source=hardware / Sell hardware → /hardware-sales / Compare GPU specifications), direct-answer block, New vs Recovered sourcing paths with scoped channel language and per-path intake CTAs (?source=hardware-new / -recovered), hardware categories (6, full stack, no availability), 5-step requirement process + scope disclaimer, 16-item buyer diligence checklist + not-legal-advice note, financing/deployment paths + hardware-vs-cloud decision aid, 7 resource links, 10-item FAQ (details/summary, JSON-LD parity 10/10), final CTA, "Page updated" line tied to dateModified const.

**Claims removed (all previously static):** $184M inventory, ~1,200/~3,400 node counts, grade A- average, hourly refresh, factory-direct, OEM partner language, full-manufacturer-warranty, warranty-backed, universal inspection/burn-in/grading, ready-ship, fast payment, in-stock accelerators, "every current-generation accelerator", LIVE/DIRECT badges. Brand/accelerator links kept as descriptive references with an explicit no-endorsement/no-availability note.

**Route fixes:** buyer "OEM partner channel" self-link and buyer→/hardware-buyback (seller intake) links fixed in V3Nav (mobile + mega: now "New systems"/"Recovered systems" → /hardware anchors) and V3Footer ("New · OEM partners"/"Source · recovered" → same anchors).

**Sitewide claim fix found during validation:** the App.razor Organization schema description still said "full-stack AI infrastructure: hardware sourced from OEM partners..." — rewritten to the approved entity definition (this fixes Organization-schema consistency for ALL pages). Also softened my earlier V3Nav hardware feature block ("from OEM partners" → "through documented manufacturer and qualified channel supply").

**Dynamic listings module:** intentionally absent. IHardwareMarketplaceService has none of the required governance fields (publicationStatus, availabilityConfirmedAt/ExpiresAt, sellerAuthorityStatus, verificationScope, priceBasis/validThrough), so under fail-closed rules no record is eligible; a comment marks the slot and forbids wiring the ungoverned service. Backend dependency documented.

**Validated:** build 0 errors; 23/23 tests; page 200; one H1; exact title/canonical; 0 em dashes; 0 ungoverned-claim regex matches in rendered HTML; schema graph = Organization/WebSite/WebPage/BreadcrumbList/Service/FAQPage; FAQ parity 10/10; all 21 linked routes 200.

**Update (content-phase finalization):** Applied the finalize prompt: 3 comment em dashes removed; header comment no longer promises a hero image (documents Mason's rejection of the AI renders). **Attribution finding:** /configure does NOT read ?source= (only ContactSales does, storing it on the FormSubmission), so the unsupported ?source=hardware/-new/-recovered params were removed from all configure links; attribution continues via the dataLayer click events (page path + link URL). Financing-role FAQ wording "originates and arranges" KEPT, basis: Mason's approved financing post-update review (2026-08-17) explicitly endorsed originator/arranger language; visible/JSON-LD identical. Validated: build 0 errors, 23/23 tests, 200, one H1, approved title/canonical, 0 em dashes, 0 markdown artifacts, 0 inventory/claim matches (only the FAQ "in stock?" question + "node configuration" diligence fields), FAQ parity 10/10. Open asset gaps for Mason: hero photo (spec unmet, text-only by his instruction) and og-hardware.png (1200×630 but mock "LIVE INVENTORY" art).

## Named Follow-Ups (post-content integration)
1. Governed public hardware-listing endpoint (platform backend).
2. Public listing DTO + publication contract (approval/expiry/authority/verification/price-basis fields).
3. Conditional "Current hardware opportunities" module (fail-closed, hides when empty).
4. Hardware marketplace publication audit (IHardwareMarketplaceService data governance).
5. **/hardware-sales truth + SEO rebuild:** live page has static demand/price/quantity/buyback timing/inspection/payment/valuation claims needing their own review; none copied into Hardware.razor. Needed before or with the coordinated release.
6. /hardware-buyback truth review (seller/lifecycle claims).
7. Optional: add ?source= support to the /configure intake if per-channel attribution is wanted there (ContactSales pattern at ContactSales.razor:274-335).
8. Hero photo + og-hardware.png assets from Mason.

## To Do Next
- **og-hardware.png replacement (4th OG image):** current art shows a mock "INVENTORY · LIVE" panel + "Sourced, financed, deployed." — implies live inventory; needs real hardware imagery per spec.
- Hero image: Mason rejected RenderedServer2.png here too ("whats up with this image. get rid of it") — hero is now text-only. NEVER reuse the Servers/ renders as hero art. The spec's hardware-imagery requirement stays unmet until Mason supplies an approved photo.
- Backend: governed public hardware-listing projection for the "Current hardware opportunities" module.
- Viewport screenshots pending (no browser tooling).
- Coordinated release: commit/push whole batch on approval; do not deploy this page separately.
