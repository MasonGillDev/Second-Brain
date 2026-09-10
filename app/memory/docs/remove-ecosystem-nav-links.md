# Remove Platform Nav Links + Full /platform/ecosystem Teardown

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
**Update 5 (same day):** Moved the Tools column (Configure energy-backwards, TCO calculator, Power calculator) from the Financing mega-menu into the Resources mega-menu; widened `.v3nav-mega-resources .v3nav-mega-grid` to 6 tracks in `V3Nav.razor.css`. Removed the Guides column's "Power planning" link (would have duplicated the Power calculator in the same menu). Mirrored on mobile: "Configure (energy-backwards)" moved from the Financing accordion to the top of the Resources accordion. Also added "Financing overview" (→ /financing) to the top of the Financing mega-menu column (previous request). Financing mega-menu now: feature block + Financing + For lenders columns.

**Update 4 (same day):** Removed "Forward · escrow lots" (mobile accordion + Marketplace mega-menu Compute column) and "Pricing engine" (→ /resources/tco-calculator, mega-menu Compute column) from `V3Nav.razor`. Kept per nav-only scope: the V3Footer "Forward escrow" link and the mega-menu For-buyers links "How escrow works"/"Refund mechanics" (all → /marketplace/compute#forward) — flag to Mason if those should go too. (Follow-up: Mason then had "How escrow works" and "Refund mechanics" removed too — For-buyers column is down to "Tell SLYD what you need". The footer "Forward escrow" link was then removed too — no #forward links remain anywhere in the V3 nav or footer. Also removed the Hardware mega-menu's "GPU comparison database" and "Server comparison" links, which duplicated the Resources Compare column.)

**Update 3 (same day):** Removed two duplicate-target links from the Platform mega-menu Trust column in `V3Nav.razor`: "Audit log & lender oversight" (→ /platform/governance, duplicated "Zero principal risk") and "SOC 2 · HIPAA · FedRAMP" (→ /platform/security, duplicated "Security & compliance"). Trust column now: Security & compliance, Benson. Mobile accordion had no dupes.

**Update 2 (same day):** Mason reversed the earlier "keep the page alive" call — `/platform/ecosystem` is now fully stripped like case studies. Deleted `Components/Pages/Platform/Ecosystem.razor` + `.razor.css`, removed the sitemap entry from `SitemapController.cs`, and added `/platform/ecosystem` to `GonePages` in `SeoRedirectMiddleware.cs` → returns **410 Gone** (runtime-verified; siblings /platform and /platform/cloud still 200, unknown URLs still 404). Left the "ECOSYSTEM PAGE" CSS block in `wwwroot/css/platform.css` because `categories-grid`/`category-card`/`category-icon` are shared with InfrastructureFinancing, TCOCalculator, and the CategoryCard component. Gotcha hit during verification: a stale `Website` process from an earlier test was still holding port 5200 and serving old code — always `lsof -iTCP:5200` if status codes look wrong.

**Update (same day):** Also removed three links from the Platform mega-menu "SLYD Cloud" column in `V3Nav.razor`: "The operating layer", "License · on your metal", and "Orchestration & billing". All three pointed to `/platform/cloud`. The page stays alive and remains linked via "Connect · plug into SLYD" (kept, not named by Mason) and the mobile accordion's SLYD Cloud link.

Mason originally asked to remove `/platform/ecosystem` "in the same fashion" as the case studies page, then narrowed scope mid-task: **only remove the nav links; keep the page alive.**

Removed:
- `Components/Shared/V3/V3Nav.razor` — "Three revenue lines per deal" link in the mobile accordion (The Fabric panel) and in the Platform mega-menu Overview column.
- `Models/Navigation/NavigationModel.cs` — "App Store & Ecosystem" entry in the Platform dropdown.

Deliberately kept: `Components/Pages/Platform/Ecosystem.razor` (+ scoped CSS), the `/platform/ecosystem` sitemap entry in `SitemapController.cs`, and the `ECOSYSTEM PAGE` CSS block in `wwwroot/css/platform.css` (~lines 1147–1275 — note: `.apps-grid`/`.app-*` classes there appear unused by any razor file, dead-CSS cleanup candidate).

Verified with `dotnet build` (0 errors). Not committed — working tree also carries unrelated pre-existing edits (MainLayout.razor.css, app.css, docs.js, gpu-marketplace.js); stage only V3Nav.razor and NavigationModel.cs when committing this.

## To Do Next
- Commit/push the two nav files once Mason approves (push to `development`).
