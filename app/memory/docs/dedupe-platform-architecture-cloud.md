# Dedupe /platform/architecture into /platform/cloud (301)

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Mason noticed `/platform/architecture` and `/platform/cloud` were the same page. Confirmed: `Cloud.razor` is a section-for-section V3 port of the same SLYD Cloud content (identical H2 structure — "Run SLYD Cloud on your metal", "Plug into our cloud", "Two paths. Honest pricing", etc.); Architecture was the older copy with weaker meta tags.

Kept `/platform/cloud` as canonical, and:
- Deleted `Components/Pages/Platform/Architecture.razor` + `.razor.css`.
- Added a **301 redirect** `/platform/architecture` → `/platform/cloud` in `SeoRedirectMiddleware.ExactRedirects` (redirect, not 410, since the content lives on — consolidates SEO equity).
- Removed the `/platform/architecture` sitemap entry.
- `V3Nav.razor`: removed the "The 5-step pipeline" links (mobile accordion + mega-menu) — that label was mislabeled anyway (the 5-step pipeline content actually lives at `/platform`), and SLYD Cloud already has its own nav links.
- Repointed internal links to `/platform/cloud`: `Platform.razor` "SLYD Cloud detail" button, `PlatformStack.razor` SLYD OS block, and both `NavigationModel.cs` entries (retitled "SLYD OS Architecture" → "SLYD Cloud").

Runtime-verified: /platform/architecture → 301 to /platform/cloud; /platform/cloud and /platform → 200; /platform/ecosystem and /case-studies → 410. Build 0 errors.

Related context: earlier the same day Mason flagged "How SLYD works" and "The 5-step pipeline" as seeming duplicates — root cause was this crossed labeling; resolved by this dedupe.

## To Do Next
- Commit and push everything from this session to `development` when Mason approves (nav de-linking, 410s, this dedupe).
