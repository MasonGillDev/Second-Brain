# Compute Marketplace Page Listing Truth Rebuild (/marketplace/compute)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `https://slyd.com/marketplace/compute` per the three-file package at `/Users/masongill/Slyd/compute-marketplace-claude-package-2026-08-17`. Content, SEO, AEO, metadata, schema, internal links, and presentation only. Every listing, price, status, filter toggle, and transaction CTA is functionally untouched.

Fourth in the series after [[broker-page-program-governance-rebuild]], [[hardware-sales-page-commercial-truth-rebuild]], and [[power-opportunities-page-commercial-truth-rebuild]]. Different shape from the other three: there is no external or inline JavaScript. This is an `InteractiveServer` Blazor component whose listings, prices, statuses, view toggle, and deploy URLs all come from the `@code` block via `MarketplaceService`.

### Files changed (four)

- `Components/Pages/Marketplace/Compute.razor`
- `wwwroot/css/marketplace.css` (12 lines added, nothing modified or removed)
- `tests/Website.Tests/Pages/ComputeMarketplacePageContentTests.cs` (new, 46 tests)

No controller, service, model, migration, admin screen, CRM mapping, analytics event, redirect, or route changed. `SeoRedirectMiddleware`, `MarketplaceService`, `Breadcrumb.razor`, and `CoverageMeter.razor` are untouched.

### Claims removed

All were universal platform promises with no listing record behind them: instant deployment, deploy in minutes, the two-to-five-minute deployment time, scale 1 to 1,000+, no commitment, real-time availability, "Live Inventory", "all servers include CUDA, drivers, and popular ML frameworks", universal per-second billing, universal preinstalled PyTorch/TensorFlow/vLLM/TensorRT templates, universal autoscaling, load balancing, private networking, low latency, encryption at rest, 24/7 support, "50+ one-click AI tools", and the "under 5 minutes, no credit card required" close.

Replaced with listing-specific framing: software, support, networking, tenancy, billing basis, fees, and deployment path all belong to the individual listing and never carry across from one to another.

### What was deliberately kept

**Hero "from" prices.** They come from `GetHeroGpuModels()` over live listings. The specification only permits removing a hero price when it is hard-coded marketing outside the marketplace component.

**The `AVAILABLE NOW` label.** Produced by `GetStatusText` from the listing's own `AvailabilityStatus`, so it is operational output, not a static claim. Adjacent static copy now states that provider-supplied status is subject to confirmation.

**The `Deploy Server` / `Start Deploying` / `Get Started Free` CTA labels and destinations.** All six resolve through `GetDeployUrl()` and keep their `data-enhance-nav="false"` opt-out for the external platform handoff.

**`og-marketplace-compute.png`.** Unlike the previous three pages, this asset carries no retired claim: no price, availability, provider count, or performance figure, and its proposition matches the new metadata. It is an interface illustration rather than the photograph of a real compute environment the spec prefers, so it is flagged as an asset upgrade rather than removed.

**The existing `/contact-sales` CTAs.** Spec section 10 asks for `?source=compute-marketplace` attribution, but adding a parameter to an existing operational CTA changes what it reports into the admin queue, which the implementation boundary forbids. Left unchanged and flagged; a test pins the decision.

### Three real defects found and fixed during QA

1. **A broken query string I introduced.** Writing `&amp;` in Razor markup gets encoded again on render, producing `/need?type=compute&amp;amp;source=...`, so the second parameter was literally named `amp;source`. A bare `&` in the markup is required. Caught by reading the resolved DOM URL, not the source.

2. **Duplicate BreadcrumbList schema.** The shared `Breadcrumb` component already emits a `BreadcrumbList` from `breadcrumbItems`. Adding one to the page-level graph produced two on the rendered page. Removed mine and kept the component's, which is the operational one.

3. **Mobile horizontal overflow.** An inline `style="grid-template-columns: repeat(3, 1fr)"` on a card row out-specified the responsive breakpoints in `marketplace.css` and held three columns down to 360px, pushing the page to 778px wide at a 390px viewport. Pre-existing, but in a section being rewritten, so fixed by replacing the inline style with a class scoped above the collapse breakpoint. First attempt made it worse: an unscoped `.intro-cards-grid.intro-cards-grid--three` still out-specified the media queries. The page now measures 730px, identical to its untouched sibling `/marketplace/hardware`, where the remaining overflow is the shared nav drawer.

### Verification method

Two harnesses in the session scratchpad, run before and after:

- `computecontract.py` extracts the operational contract: a SHA-256 of the `@code` block plus every Razor binding, event handler, helper call, loop, conditional, component tag, and `data-enhance-nav` opt-out in the markup.
- `computeprobe.mjs` drives the real page over CDP with the platform API running, reads all twelve server cards field by field, toggles to GPU Types **through the live Blazor circuit**, reads all eight GPU cards, toggles back, and collects every CTA.

Contract diff: `code_sha256`, `code_len`, directives, bindings, event handlers, method calls, loops, conditionals, component tags, `data-enhance-nav` count, and ids all identical. Only `/gpu-marketplace` removed from hrefs, six editorial links added.

Runtime diff: 12 server cards byte-identical including status, tier, title, category, specs, location, price, and CTA; hero nav identical; 8 GPU cards identical; view toggle identical; return-to-servers identical; zero console errors.

**A stale-process trap worth remembering.** The executable is `bin/Debug/net10.0/Website`, not `Website.dll`, so `pkill -f "Website.dll"` silently missed it and a stale instance kept serving port 5180. Two verification rounds were checked against old output before this surfaced. Kill by port (`lsof -ti:5180 | xargs kill -9`) and confirm the port is free before trusting a served-page check.

### Verification results

- Build: succeeded, 0 errors, 2 pre-existing NuGet advisory warnings.
- Tests: 192/192. 46 are this page's; 165 across the four page suites; 23 pre-existing. A `GpuDatabaseCountTests.cs` (4 tests) appeared in the same folder mid-session from other work and is not part of this change.
- Served HTML: one title, description, canonical, robots tag, h1; no `meta keywords`; exactly one BreadcrumbList; three JSON-LD blocks all valid; FAQ byte-identical to the FAQPage JSON-LD across all 10 questions; zero retired-claim hits. The phrase "instant deployment" survives only as the spec's own FAQ question, whose answer is "No."
- `/gpu-marketplace`: 301, single hop, query string preserved.
- Links: all 9 targets return 200, including the parameterised `/need` URL.
- Layout: no overflow at 1440x900 or 1024x768; 730px at 390x844 and 677px at 360x800, matching the untouched sibling page. No JS exceptions at any viewport.
- Accessibility: one h1, no images without alt, no empty link text, no positive tabindex, all 10 FAQ summaries keyboard focusable, both view-toggle buttons keyboard focusable.

## To Do Next

1. **Contact-sales attribution decision.** Spec section 10 wants `/contact-sales?source=compute-marketplace`. Adding it to the existing CTAs changes admin-queue attribution, so it needs ops approval rather than a content pass. A test currently pins the parameterless destination.
2. **`/need` query parameters are inert.** `Need.razor` does not read query parameters today, so `?type=compute&source=compute-marketplace` carries no prepopulation or attribution. The link matches the spec and is ready for when Need consumes them; until then it is decorative.
3. **Pre-existing heading skip.** The hero GPU nav cards use `h3` directly after the `h1`. They sit inside the preserved operational block and `marketplace.css` styles them through the tag-qualified selector `.mp-nav-content h3`, so the tag cannot change in a content pass. A test pins the count at exactly one skip so no new one can be added.
4. **og:image upgrade.** The current asset is compliant but is an interface illustration. The spec prefers a real, clearly visible GPU server or compute environment, with no price, availability, provider count, or performance claim.
5. **Derived daily and monthly prices.** `GpuModelSummary.DailyPrice` and `MonthlyPrice` are computed in the `@code` block from hard-coded assumptions (20 hours per day, a 20 percent monthly discount) and rendered as "Daily" and "Monthly" rows. They are operational output and were left alone, but they are derived marketing arithmetic presented as pricing tiers and deserve a governance review.
6. **Shared nav-drawer overflow.** The `v3nav-drawer` extends past the viewport on several pages at mobile widths. `/marketplace` contains it and `/marketplace/hardware` does not, so the containment is inconsistent. Site-wide, not introduced here.
