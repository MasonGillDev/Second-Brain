# Broker Page Program Governance Rebuild (/broker)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `https://slyd.com/broker` as a partner recruitment and governance surface, per the three-file package at `/Users/masongill/Slyd/broker-claude-package-2026-08-17`. Content, SEO, AEO, metadata, schema, internal links, and presentation only. No functional change.

### Files changed (three, all new or content-only)

- `Components/Pages/Broker.razor` (rewritten)
- `Components/Pages/Broker.razor.css` (rewritten, namespace `v3brk-`)
- `tests/Website.Tests/Pages/BrokerPageContentTests.cs` (new, 29 tests)

The working tree carries unrelated pre-existing modifications from prior sessions (Lenders network, hardware cluster, V3Nav). Those were not touched.

### Claims removed and why

The prior page promised compensation unconditionally and overstated SLYD's role. All four were unsupportable without the governing agreement:

- "you earn a clearing fee on every deal that closes"
- "SLYD originates, finances, and closes" as a universal claim
- "sourcing is the entire role"
- "brokers are not responsible for funding or executing the deals they source"

Compensation is now stated as governed by the applicable written agreement and the accepted opportunity record. No percentages, ranges, examples, or payment timing appear in copy or schema, and the `Service` block publishes no `Offer`.

### Key decisions

**Modeled on `/financing/lenders`.** That page is the closest sibling: same `BareLayout` + `V3Nav`/`V3Footer` chrome, same long-form governance shape, same `details`/`summary` FAQ, and it already solved the role-boundary copy problem for a trust-sensitive partner program. Reusing its structure and CSS tokens kept this page inside the design system instead of inventing a new one.

**og:image removed, not replaced.** `wwwroot/images/og-broker.png` renders "Become a broker", "We originate, finance, and close", and a rising CLEARING FEES chart. Every one of those claims was retired here, so shipping the asset would have leaked them into social cards and crawlers. Following the Lenders precedent, `og:image` is omitted until approved AI-infrastructure photography exists. The only candidates in the repo are the `Servers/` renders, which Mason previously rejected as hero art. This is a blocking approval, not an oversight.

**No analytics attributes.** Lenders carries `data-analytics-event` / `data-analytics-view` hooks. Adding equivalents here would have created new analytics events, which the package explicitly excludes from this phase. The page ships without them and a test asserts their absence so a later pass is a deliberate decision.

**Organization and WebSite not duplicated.** `Components/App.razor` already emits both site-wide with `@id` anchors. The page emits `WebPage` + `BreadcrumbList` + `Service` in one graph plus a separate `FAQPage`, referencing the site entities by `@id`. All six spec-required types are present in the served page.

**Shared nav labels left alone.** `V3Nav` and `V3Footer` still say "Become a broker" in three places. Those are site-wide chrome rendered on every page; changing them is out of scope for a single-page content task. Flagged as follow-up.

### Operational preservation

The contact path was treated as untouchable. Both CTAs still point at `/contact-sales?source=broker`, unchanged in href and query parameter. Verified end to end against the running app: `/contact-sales?source=broker` still preselects "Become a Broker" in the interest dropdown, and the bare `/contact-sales` still shows "Select an option". No route, form, endpoint, record, migration, service, admin screen, CRM mapping, analytics event, or notification was added or edited. The `/broker` sitemap entry is unchanged.

`BrokerPageContentTests` includes explicit preservation tests over `ContactSales.razor` (interest option, source parsing, preselect branch, `fields["source"]`, `FormName`, submission call, field ids) so a future content pass that disturbs the contact path fails at build time.

### Testing note worth remembering

The first test run failed 11 tests because the assertions scanned raw `.razor` source, and the component's own `@* *@` header comment documents the retired claims verbatim. Razor comments are stripped by the compiler and never ship. The tests now assert against a `BrokerMarkup` string with `@* *@` blocks removed, while HTML comments stay in scope because those do ship. The HTML comments were also reworded so they no longer restate retired claims.

### Verification

- Build: succeeded, 0 errors, 2 pre-existing NuGet advisory warnings (unchanged from baseline).
- Tests: 52/52 pass (23 pre-existing + 29 new). Baseline before the change was 23/23.
- Rendered page: exactly one title, description, canonical, robots tag, and h1. Three JSON-LD blocks, all valid JSON. FAQ visible text is byte-identical to the FAQPage JSON-LD across all 10 questions, checked against the served HTML rather than source.
- Links: all 12 internal targets return 200.
- Layout: `scrollWidth == clientWidth` at 1440x900, 1024x768, 390x844, 360x800. No page-level horizontal overflow.
- Accessibility: single h1, no heading-level skips, `lang="en"`, main landmark, skip link, labeled breadcrumb nav, no empty or ambiguous link text, no positive tabindex, all 10 FAQ summaries keyboard focusable and toggleable, decorative markers `aria-hidden`.

Mobile QA required driving Chrome over CDP (`scratchpad/shoot.mjs`, zero npm dependencies, Node 22 global WebSocket). Chrome's `--headless --window-size` CLI flag does not honor the viewport meta tag, so it crops a desktop layout and produces false overflow. The already-shipped Lenders page shows the identical artifact, which is how it was ruled out as a regression.

## To Do Next

Approvals and follow-ups, none blocking the content itself:

1. **Legal and finance sign-off** on the compensation, protection, duplicate, and conduct sections. The copy was written to the package's stated principles and invents no terms, but it describes how an agreement behaves and should be read by whoever maintains that agreement.
2. **og:image asset.** Produce an approved 1200x630 image showing real AI infrastructure commercial work, then restore the `og:image` / `twitter:image` tags. `og-broker.png` must be retired, not reused. A test currently asserts it stays out.
3. **Program terms link target.** The page links `/legal`, `/acceptable-use-policy`, and `/privacy-policy` because no broker-specific program terms page exists. If one is published, point the conduct section at it.
4. **Shared nav labels.** `V3Nav.razor` (3 links) and `V3Footer.razor` say "Become a broker" / "For brokers". Realigning them to "Broker and referral network" is a site-wide chrome change and needs its own pass.
5. **Analytics events.** Deliberately not added. If broker funnel measurement is wanted, mirror the Lenders `data-analytics-event` pattern in a separate approved change.
6. **Pre-existing site-wide observation.** The shared `v3nav-drawer` keeps ~46 focusable links inside an `aria-hidden="true"` container when closed. Present on every V3 page, not introduced here, worth a separate accessibility fix.
