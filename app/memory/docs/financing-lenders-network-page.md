# /financing/lenders: AI Infrastructure Lender Network Page (Aug 2026 Spec)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Built the capital-side counterpart to the borrower financing pages per the lender-network implementation prompt. New files: `Components/Pages/Financing/Lenders.razor` + `Lenders.razor.css` (namespace `v3lend-`, base tokens/patterns from v3fin, details/summary FAQ from v3cloud). Part of the coordinated commercial-page release; NOT to be deployed separately.

**Structure (12 sections):** text-only hero (breadcrumb, eyebrow "Capital partners", H1 "Join the SLYD AI infrastructure lender network", lead, 2 CTAs, qualification line) → direct answer → mandate fit (4-col) → who should join (7 participant types + boundary, with broker-program redirect for non-capital intermediaries → /broker) → 6 opportunity categories + "no category automatically financeable" note → 10-item transaction-workspace list + evidence-standard note → 7-step engagement workflow (with /platform link) → role-clarity two-column (SLYD coordinates / lender controls) + boundary statement → confidentiality → contact-handoff callout → 12 FAQs (details/summary, JSON-LD parity 12/12) → final CTA + qualification + freshness line (ContentReviewDateIso = 2026-08-18).

**Contact handoff (no new form):** every lender CTA → `/contact-sales?source=financing-lenders`. Added `{ "financing-lenders", "Lender or Capital Partner" }` to ContactSales `interestOptions` — the existing source-preselect logic (ContactSales.razor ~L292) auto-selects it, so lender inquiries carry both a distinct Interest value AND the source tag on the FormSubmission (visible in /admin/forms, email subject "Sales Inquiry [financing-lenders]: ..."). Borrower /financing/apply intake deliberately not linked as a lender action.

**Schema:** graph of WebPage + BreadcrumbList (Home/Financing/Lenders) + Service ("SLYD AI Infrastructure Lender Network", serviceType "AI infrastructure financing opportunity coordination and lender mandate matching", provider = existing #organization @id, Audience "Commercial and institutional capital providers", areaServed omitted) + separate FAQPage. No FinancialProduct/LoanOrCredit/Offer/rating types; no numbers anywhere in schema.

**Role language decision:** the "Does SLYD lend its own capital?" FAQ reuses the Mason-approved /financing wording verbatim ("SLYD originates and arranges financing opportunities with third-party capital providers...") instead of the spec's preferred "SLYD is not the lender" phrasing, which the spec itself gates on legal confirmation. Consistent role record across pages.

**OG image:** og-financing-lenders.png does not exist; og-financing.png shows retired claims ($500K-$50M, Fast Approval, Competitive Rates) so it was NOT reused. og:image tags omitted with an in-file comment until Mason supplies real-infrastructure art (5th OG asset dependency). Hero is text-only per the standing no-AI-render rule.

**Nav/links:** financing mobile accordion + mega gained "Lender network"; the mega's existing "For lenders" column now leads with it and the duplicate "Deal audit trail" → /platform/governance link was removed (Mason's dedupe pattern). Sitemap entry added. Internal links added on /financing (lender-record section) and /platform (Finance step boundary). /financing/gpu + /financing/infrastructure links deferred (those pages are still old-style, pre-rebuild, per spec's "after those pages are updated").

**Analytics (v3events.js bridge, no PII):** lender_page_view (hero view), lender_hero_join_click, lender_contact_click (x2), lender_process_expand (workflow section view), lender_faq_expand (12 details toggles), lender_final_join_click, lender_financing_overview_click.

**Validated:** build 0 errors; 23/23 tests; page 200 SSR; one H1; exact title/canonical/robots; 0 em dashes; 0 prohibited-claim regex hits (no rates/returns/counts/guarantees); FAQ parity 12/12; sitemap contains route; contact-sales preselect option renders; all 11 linked routes 200.

## To Do Next
- **Legal gate (blocking publication):** operating entity, role/program terminology ("network", "capital partner", "mandate matching"), licensing review, accepted participant types + jurisdictions, compensation disclosure, final disclaimer. The page ships in the gated coordinated release only.
- **og-financing-lenders.png** (real AI-infrastructure photography, 1200x630) + hero photo from Mason; og:image tags then restored.
- Commercial ops: confirm an accountable internal owner + response workflow for [financing-lenders] inquiries in /admin/forms / HubSpot routing.
- Add lender-network links from /financing/gpu and /financing/infrastructure when those pages get their rebuilds.
- Viewport screenshots (no browser tooling this session).
- Commit with the coordinated batch on Mason's approval.
