# /platform/cloud Rebuild: GPU Cloud Marketplace (Aug 2026 Spec)

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
**Update (same day):** Mason had the "Current marketplace listings" live preview board removed from the hero (it was surfacing LOT-DEMO seed rows locally). Stripped the board markup, the IV3MarketplaceService/ILogger injections, and the OnInitializedAsync fetch from Cloud.razor; hero is now copy + CTAs only. Board CSS left in Cloud.razor.css (harmless, reusable if the preview returns once backend listing governance exists).

Rebuilt `/platform/cloud` from the License/Connect orchestration story into the two-sided **GPU Cloud Marketplace** page per the implementation prompt. `Cloud.razor` fully rewritten (exact spec copy, 13 sections in order); marketplace CSS appended to `Cloud.razor.css` (reused v3cloud base tokens/hero/section classes).

**Key implementation decisions:**
- **Hero visual = real governed data:** no approved screenshot exists, so the hero renders a live 3-row listing preview from the existing `IV3MarketplaceService.GetSpotAsync` (platform marketplace API), hidden entirely on failure/empty; never fake listings. try/catch boundary + ILogger so a dependency failure can't break the page.
- **Marketplace Truth Rule enforcement:** local verification found the API serving demo-seeded lots (LOT-DEMO-330 at $30,500) that made the marketplace page's own "/GPU·hr" label untrustworthy, and the anonymous DTO has NO pricing-basis field, so the preview asserts no basis: price cell says "PRICING IN LISTING", status badge "PROVIDER SUPPLIED" (the only status the implementation can back), footer defers basis/terms to the full listing. Only two statuses published (Provider supplied, Unavailable/expired) with an explicit note that richer verification labels require the backend record.
- Legal role copy verified against CloudMarketplaceTerms.razor ("SLYD acts solely as a facilitator and is not a provider of compute services", operated by SLYD Cloud LLC) — spec wording aligns.
- Removed: $0.04/GPU·hr, zero up-front, no-minimums, "customers remain 100% yours", clearing-fee, white-label, 1 MW minimum, 3-50 MW personas, LXD-vs-Kubernetes, "battle-tested", all-features/quarterly/24-7 claims, TechArticle schema, all 22 em dashes.
- Schema: WebPage + BreadcrumbList (Home/Platform/GPU Cloud Marketplace) + Service (spec verbatim) + FAQPage (11 Q&As, parity 11/11). Shared ContentReviewDateIso const pattern.
- Analytics: all 12 spec event names via the v3events.js data-attribute bridge (built during the /platform rebuild). v3faq.js narrowed to /financing only (Cloud now uses native details).
- Nav/footer labels: "SLYD Cloud"/"Connect · plug into SLYD" links → "GPU cloud marketplace" (mobile accordion, mega column, footer). Homepage clarify-links gained a "GPU cloud marketplace" anchor sentence.

**Validated:** build 0 errors; 23/23 tests; page 200; one H1; exact title/canonical/robots; 0 em dashes; 0 removed-claim matches; definition in SSR HTML; schema types exactly the six allowed; FAQ parity 11/11; all 15 routes 200 (incl. both contact-sales source params); TechArticle gone; preview verified with live data and with no basis claims.

**Update 2 (content-phase finalization):** Applied the "Finalize the Cloud Page for the Current Content Phase" prompt: header comment corrected (no longer claims a live IV3MarketplaceService preview; states dynamic availability is deferred to the governed-endpoint phase), the 3 comment em dashes removed, inventory section confirmed as evergreen navigation. Phase decision honored: NO temporary endpoint, NO placeholder/static/inferred inventory, previous V3SpotOfferDto preview NOT restored. Validated: build 0 errors, 23/23 tests, 200, one H1, approved title/canonical, 0 em dashes anywhere, 0 fake records/empty panels, 0 markdown artifacts, schema types exactly the six allowed, FAQ parity 11/11, all legal + core routes 200. Hero is TEXT-ONLY (no image exists after Mason rejected the AI renders) and og-cloud.png is 1200×630 but still shows the old "Multi-tenant. LXD. Zero Kubernetes." art: both are open asset dependencies for Mason.

## Named Follow-Ups (dynamic integration phase, per cloud-page-dynamic-inventory-claude-prompt-2026-08-17.md)
1. Governed public marketplace listing endpoint (platform backend).
2. Public listing DTO + publication contract (approval, expiry, verification scope, pricing basis).
3. Dynamic Cloud availability preview with fail-closed behavior.
4. Full /marketplace/compute publication audit (it still renders ungoverned lot data labeled /GPU·hr, plus escrow/banded claims).
5. Provider onboarding content cleanup: /docs/provider/onboarding still claims global demand, passive income, immediate earnings, automated payouts, broad support. Do not copy these claims anywhere.
6. Hero image + og-cloud.png replacement assets from Mason.

## To Do Next
- **og-cloud.png replacement (3rd OG image needing new art):** current says "SLYD Cloud / Multi-tenant. LXD. Zero Kubernetes." — orchestration framing + removed claim.
- **Backend marketplace governance gap:** the anonymous spot API has none of the spec's publication fields (verificationStatus/scope, pricingBasis, availabilityAsOf, publicationStatus...) and locally serves LOT-DEMO seed rows; production data governance needs a backend owner. Also flag: Marketplace.razor labels the same Price field "/GPU·hr" — likely mislabeled for lot-priced records; out of scope here but should be audited.
- HubSpot: verify source=gpu-cloud-provider/operator reach the attribution field without dup records.
- Cross-page anchors from /marketplace, /marketplace/compute, /docs/provider/onboarding not added (those pages have their own governing specs); homepage/nav/footer done.
- Viewport screenshots pending (no browser tooling this session).
- Commit + push session batch on approval.
