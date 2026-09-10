# Remove Case Studies Page and All Links

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
**Update (same day):** `/case-studies` now returns **410 Gone** instead of 404. Added it to `SeoRedirectMappings.GonePages` in `Middleware/SeoRedirectMiddleware.cs` and introduced a new `GonePrefixes` list (`/case-studies/`) so old detail-page URLs also 410. Verified live: `/case-studies` and `/case-studies/{slug}` → 410, unknown URLs still → 404. Mason floated turning ALL 404s into 410s; recommended against (410 aggressively de-indexes — typos/bot probes/future pages would be harmed) and kept the per-page list approach instead.

Completely removed the case studies section from the website:

- **Deleted pages/model:** `Components/Pages/CaseStudies/` (CaseStudies.razor + CaseStudy.razor and their scoped CSS) and `Models/CaseStudies/CaseStudyModel.cs` (which held the static `CaseStudyData`).
- **SitemapController.cs:** removed the `Website.Models.CaseStudies` using, the loop emitting case-study detail URLs, and the static `/case-studies` sitemap entry.
- **V3Nav.razor:** removed the mobile-accordion and mega-menu "Case studies" links. The Resources mega-menu feature block promoted the Permian Basin case study ("3.4 MW H200 in 11 weeks") — since that content no longer exists, it was replaced with a blog promo linking to `/blog`.
- **V3Footer.razor:** removed the "Case studies" footer link.
- **NavigationModel.cs:** removed both nav/footer "Case Studies" entries (lines in the Resources column and FooterColumn).
- **Resources.razor:** removed the entire "Case Studies / Customer Success" column from the content split; `.resources-content-split` grid in `wwwroot/css/resources.css` changed from 2 columns to 1 so the remaining Blog column fills the width.

Left untouched (intentionally — not links to the page): the "Case Studies" section tag on `Hardware/Deployment.razor` (labels on-page example deployments), prose mentions in `Careers.razor` and `Legal/CloudMarketplaceTerms.razor`. Dead `.resources-case-*` CSS rules remain in resources.css (harmless; could be cleaned later).

Verified: no remaining `case-studies` / `CaseStud` references in source; `dotnet build` succeeds with 0 errors. Changes staged/working-tree only — not committed (project rule: always ask before committing).
