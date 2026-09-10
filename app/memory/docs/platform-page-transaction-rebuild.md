# /platform Rebuild: Transaction Platform (Aug 2026 Spec)

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Rebuilt `/platform` per the "Rebuild the SLYD Platform Page" implementation prompt. `Components/Pages/Platform/Platform.razor` fully rewritten with the exact spec copy in the mandated order: hero (H1 "One AI Infrastructure Deal. One Governed Workflow.") + direct definition, five-step overview chips, detailed steps 01-05 each with Inputs / SLYD coordinates / Recorded output rails (left-border rails, not floating cards, 8px radius max), financing + SLYD Cloud boundary statements, shared-deal-record list (structured HTML, no fake screenshot), participant role table (6 rows, stacks on mobile), conditional governed metrics snapshot via the existing IPublicMetricsService (hidden until the backend endpoint exists), SLYD Cloud / sovereign-continuity section, 6 role-based entry points, 8-item FAQ (details/summary) mirrored exactly in FAQPage JSON-LD, final action band, "Last updated" tied to the same ContentReviewDateIso const as dateModified.

**Removed:** every fictional example card (source-feed lots SLYD-INV-0214/0218, 3.4 MW configure output with $8.4M-$8.8M TCO, $236K/$212K/$6.3M financing options, Permian Pad 7 telemetry 87%/$284K, forward Lot 0224 24%/$1.34/h), the revenue-lines table, "Zero principal risk", buyer-title/lender-lien universals, 70-100 bps, PUE numbers, forward-escrow deposit mechanics, "30 seconds", TechArticle schema, all em dashes.

**Schema now:** WebPage + BreadcrumbList (Home/Platform) + Service ("SLYD AI Infrastructure Transaction Platform", spec description, org provider) + FAQPage; Organization/WebSite from App.razor. Old FAQ (title/escrow claims) replaced by the spec's 8.

**Analytics (new mechanism):** `wwwroot/js/v3events.js` — declarative bridge pushing through the existing `slydAnalytics.pushToDataLayer`; delegated clicks via `data-analytics-event`, FAQ opens via `data-analytics-toggle`, step first-views via IntersectionObserver on `data-analytics-view` (re-observes on `enhancedload`). Registered deferred in App.razor. Platform page tagged with the spec's event names (platform_hero_start_deal, platform_hero_contact, platform_step_view, platform_step_action, platform_role_entry, platform_cloud_click, platform_faq_expand, platform_final_start_deal); payloads carry only page path, href, and public step name.

**Spec deviation (documented in the file header):** spec links "platform architecture" → /platform/architecture, but that route 301s to /platform/cloud (deduped earlier same day), so architecture anchors point at /platform/cloud directly.

**Validated:** build 0 errors; 23/23 tests; /platform 200; one H1; exact title/canonical; 0 em dashes; 0 old fake-data matches; direct definition in SSR HTML; schema parses with exactly the six allowed types; FAQ parity 8/8; all 12 CTA routes 200; metrics section absent (no endpoint yet).

## To Do Next
- **og-platform.png must be replaced before deploy:** current image says "The Sovereign AI Marketplace / Enterprise GPUs. Transparent pricing. Instant deploy." with a fake pricing UI ($0.39/h etc.) — stale positioning + ungoverned prices.
- Backend `api/public/site-metrics` endpoint still doesn't exist (shared dependency with homepage).
- Viewport screenshots (390/768/1440/1920) pending — no browser tooling this session.
- GA4/HubSpot: confirm the new dataLayer events are mapped to conversions.
- Commit + push whole session batch on Mason's approval.
