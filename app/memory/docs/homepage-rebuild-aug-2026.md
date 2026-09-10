# SLYD Homepage Rebuild (Aug 2026 Spec)

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
**Update (identity pass):** Mason felt the rebuilt homepage lost visual identity (flat dark sheet). Added a CSS-only "IDENTITY PASS" block at the end of Home.razor.css (no markup/content changes): stronger hero glow + gradient headline + enlarged brand line with glowing dots; kickers get the eyebrow's leading-dash mark; alternating sections get indigo washes/radial glows; buyer column keyed to indigo and supplier column to gold (dots, hover glows, circular arrow chips) echoing the old three-doors color coding; workflow steps sit on a top rail with glowing tick; capability cards get palette-cycled top bars + hover lift; clarification headline gets a primary→gold spine; record list items become bordered chips; metrics strip gets a glow edge. All within existing tokens; prefers-reduced-motion respected.

**Update (same day, finish-and-validate review pass):** Applied the "Finish and Validate" review corrections:
1. Metrics fail closed at every layer: ordered allowlist of 6 metric keys (mw_coming_online, available_compute_capacity, active_hardware_inventory, active_regions, qualified_deployment_opportunities, marketplace_capacity), first-wins dedupe, allowlist-order rendering, bounded count, rejects negative values / future asOf / control chars / oversized labels (60) units (12) definitions (240); HTTP timeout cut 5s→2s; component try/catches with ILogger so metric failure can never break the page; null-safe AsOf rendering. Test suite now 23 (added: unknown key, duplicate keys, allowlist ordering, negative/future/control-char, DTO-field reflection guard, confidential-fields-ignored).
2. Metric definitions now render as visible text under each metric (was inaccessible title-attr tooltip).
3. dateModified + visible "Last updated" now derive from ONE const (ContentReviewDateIso in Home.razor @code) — bump only on material content review. JSON-LD switched to parenthesized (MarkupString)(concat) — cast precedence would otherwise HTML-encode it.
4. Terminal CTA band added after FAQ ("Start with the infrastructure requirement." → /configure + /platform), freshness line moved beneath it.
5. Social meta: og:site_name, og:image dims + og:image:alt added; twitter:site deliberately OMITTED (review requires confirming the official handle first — unresolved, owner Mason).
6. Shared chrome: footer brand paragraph + © line rewritten to the approved entity definition (was "Full-stack AI infrastructure... match the offtake"); footer + mega-menu column "The Fabric"/"Overview" → "Platform"; nav "in 90 seconds" claim dropped; v3nav.js ticker fake fallbacks ("3.4 MW LIVE"/"12 DEALS THIS WEEK") replaced with null fail-closed (markup for the ticker doesn't currently render, but the landmine is gone).
7. Financing-role wording "originates and arranges" KEPT — basis: Mason's approved financing post-update review the same day endorsed originator/arranger language.
Validated: build 0 errors, 23/23 tests, structured data parses (2 blocks, 1 FAQPage, 8/8 parity, dateModified matches visible), all 10 routes 200, 0 em dashes, 0 volatile values. NOT done (human owners): viewport screenshots (Chrome extension declined this session), hero immersive media treatment (conflicts with Mason's explicit removal of the rack image — needs an approved asset + decision), og-image.png replacement, GA4/HubSpot event verification, X handle confirmation.

Implemented Mason's "SLYD Homepage Rebuild: Exact Changes" spec (the revised implementation-prompt version with governed live metrics and a strict no-em-dash rule).

**Home.razor rewritten:** new metadata (title "AI Infrastructure Platform | Power, Hardware & Compute | SLYD"), text hero (eyebrow / H1 "AI Infrastructure, From Power to Compute" / brand line "Energy in. Compute out." / direct answer / supporting paragraph / Start a deal + Explore the platform), buyer + supplier path columns (8 route cards), 5-step workflow, 5 capability cards, category + role clarification with the 8 required contextual anchors, governed-record feature list, 8-item FAQ as details/summary (works without JS) mirrored 1:1 in FAQPage JSON-LD, WebPage schema with dateModified 2026-08-17, visible "Last updated: August 17, 2026". Removed ALL hard-coded volatile content: live-stats strip ($184M/47 deals/12.4 MW), forward-rail lots, marketplace teaser table, fictional logo strip (Ravencrest etc.). Mason rejected the hero rack image (RenderedServer2.png) after seeing a screenshot; hero is text-only.

**Governed metrics plumbing (new):** `Models/PublicMetrics/PublicMetricDto.cs`, `Services/IPublicMetricsService` + `PublicMetricsService` (GET `api/public/site-metrics` on PlatformUrl; drops records missing key/label/unit/asOf or expired; null on non-2xx/malformed/transport failure → module hides entirely, never stale values), registered in Program.cs (5s timeout), rendered server-side in Home.razor with per-metric "Verified {date}" label and accessible definition text. **Backend dependency: the platform has NO api/public/site-metrics endpoint yet** — admin needs the publication contract (metricKey, displayLabel, value, unit, definition, sourceSystem, sourceRecordCount, asOf, approvedBy, approvedAt, expiresAt, publicationStatus, publicVisibility) and an anonymous endpoint returning only approved+visible+unexpired aggregates. Until then the module is invisible.

**Tests:** `tests/Website.Tests/Services/PublicMetricsServiceTests.cs` — 10 tests (approved, expired-only, expired+valid mix, incomplete records, 404/403/500, empty, malformed JSON, transport failure). All pass; full suite 17/17.

**V3Nav cleanup (renders on every page):** mega-menu feature blocks had volatile claims + em dashes — Hardware block ("5.2 MW B200... 24% subscribed... Lot 0224") replaced with claim-free hardware promo; Marketplace block ("12.4 MW under refundable deposit") replaced with claim-free marketplace promo; Financing block reworded (dropped "without pulling credit" + "30 seconds"); Platform block em dash → comma.

**Verified:** build 0 errors, 17/17 tests, homepage 200, one H1/title/meta-desc, canonical /, direct answer in SSR HTML, all 9 CTA routes 200, 0 em dashes, 0 volatile values, FAQ JSON-LD/visible parity 8/8 exact, freshness line visible, metrics module correctly hidden with no endpoint.

## To Do Next
- **Backend:** implement platform `api/public/site-metrics` per the contract above (spec's recommended metrics: MW coming online, available/qualified capacity, aggregate inventory, regions, qualified opportunities).
- **OG image:** current og-image.png says "Full-stack AI infrastructure / Five steps / One deal record" + mock LIVE deal card — conflicts with new entity definition; needs replacement before deploy (meta still points at it).
- Old section CSS (doors/rail/mkt/logo/live-stats) left in Home.razor.css as dead rules — harmless, can strip later.
- Human gates: visual QA, Search Console baseline, GA4/HubSpot checks, review/release process; commit+push whole session batch on approval.
