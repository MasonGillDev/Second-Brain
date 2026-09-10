# Timeline

### 2026-08-26 11:15 — Boomy M3: attachment ingestion, chunking, Claude vision; keyword AND-vs-OR fixed by measurement (100 tests green)
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** M4 (iOS client) or M5 (memory browser). Voice still unwired — needs the transcription decision, now the only open dependency. Voyage still free-tier 3 req/min.

### 2026-08-26 09:30 — Boomy M2 verified live: no bucket sprawl, recall across a session boundary, cache reads confirmed (75 tests green)
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** M3 — attachments, extractors, chunked ingestion via write_many(), Claude vision for images.

### 2026-08-25 20:45 — Boomy M2: 8 memory tools, tool-runner loop, session boundaries, chat endpoints (73 tests green)
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** Superseded by the live-verification entry above.

### 2026-08-25 19:55 — Boomy M1 measured: retrieval eval passes 1.00 on real Voyage vectors; batch embedding cut it 5min → 7s
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** Grow the eval corpus (near-duplicates, distractors, superseded pairs) — 1.00 on 12 records is a smoke test, not proof. Then M2 (agent runtime). Voyage free tier is 3 RPM; add a payment method before M3 ingestion.

### 2026-08-25 18:40 — Boomy M0 shipped: pgvector schema, MemoryStore, migrations round-tripping, 10 tests green
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** Pick the embeddings vendor — it blocks M1 (hybrid search). Voyage `voyage-3.5` recommended.

### 2026-08-25 18:05 — Boomy V1 build plan: stack, milestones, and the spec tensions that need product calls
- **File:** [boomy-v1-build-plan.md](Docs/boomy-v1-build-plan.md)
- **Session:** adf79393-82a8-4ae0-a659-199f0c21574e
- **Directory:** /Users/masongill/Boomy
- **Status:** Follow-up Work
- **TODO:** Decide embeddings vendor + transcription approach; start M0 scaffold. Scoped to a demo pass — 3s ack target and encryption-at-rest both cut (see §6), owed back before production.

### 2026-08-24 15:20 — Ops submission email now deep-links to the form submission (and is finally an absolute URL)
- **File:** [ops-submission-email-deep-link.md](Docs/ops-submission-email-deep-link.md)
- **Session:** 9556c277-fb2e-43c2-b649-cd1d0fe7dfd8
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work
- **TODO:** Set `Ops:AdminBaseUrl` per environment — unset means the link stays a bare path with no host.

### 2026-08-24 14:05 — Notification deep-links to the submission; lead drawer shows the form contents at a glance
- **File:** [leads-inbox-form-submission-overview.md](Docs/leads-inbox-form-submission-overview.md)
- **Session:** 9556c277-fb2e-43c2-b649-cd1d0fe7dfd8
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-21 12:39 — Compute demands: type fix (every demand was Hardware), /need buy-vs-rent toggle, per-GPU-hour ceiling, lead-conversion attach
- **File:** [compute-demand-type-and-ceiling.md](Docs/compute-demand-type-and-ceiling.md)
- **Session:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work
- **BLOCKED:** What unit is the hardware `Demand.PriceCeiling` — total or per GPU? Admin labels it "$/unit" and feeds `PartPriceObservation.UnitPriceUsd`; `/need` collects a total in $M. Until answered, `/need`'s budget stays unpersisted.
- **TODO:** Target quarter (WhenKey is submission-date + 90d, so ops can't tell Q4 from Q1); Demand Book editing (no update method); `FormSubmission.ContactId` column so the form itself follows the contact.

### 2026-08-20 12:31 — Energy intake rejected every valid email: Razor `@@` escape leaked into a moved .js file
- **File:** [energy-intake-email-regex-razor-escape.md](Docs/energy-intake-email-regex-razor-escape.md)
- **Session:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Done

### 2026-08-20 11:42 — Public capacity intake: CapacitySubmission entity, anonymous endpoint, website form, claim page, spam cleanup
- **File:** [public-capacity-intake.md](Docs/public-capacity-intake.md)
- **Session:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work
- **TODO:** Fix `PowerOpportunitiesPageContentTests` — 55 website tests fail at static-constructor time. The page has had no inline `<script>` since `6b0fa86`, so `InlineScript` is empty and `PageRazor.Replace("")` throws. Guard the empty case, then re-check the content assertions. Left alone this session because that page had in-flight uncommitted edits.
- **TODO:** Phase 4 — admin queue + conversion for CapacitySubmission (must mint the listing as PendingReview, not Approved).
- **TODO:** Confirm the twelve STATED fields on CapacitySubmission before the schema hardens.

### 2026-08-20 10:58 — SiteSubmission → Site conversion (Phase 0 of public capacity intake); no prod code created Sites before this
- **File:** [site-submission-to-site-conversion.md](Docs/site-submission-to-site-conversion.md)
- **Session:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-20 09:19 — Capacity listings can now be archived/restored (new Archived state across core, admin, platform)
- **File:** [capacity-listing-archive-state.md](Docs/capacity-listing-archive-state.md)
- **Session:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-19 14:48 — Fixed "Pending" estimate card on /marketplace/power-opportunities (inline script vs enhanced nav)
- **File:** [power-opportunities-inline-script.md](Docs/power-opportunities-inline-script.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 12:35 — New shared `glass-surface`/`glass-field` component; applied to home paths + capabilities, last row now fills width
- **File:** [glass-surface-shared-component.md](Docs/glass-surface-shared-component.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 12:13 — Scroll-triggered fade-in for every page section (auto-tagged, no markup changes)
- **File:** [hero-reveal-sitewide-opt-in.md](Docs/hero-reveal-sitewide-opt-in.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 12:00 — V3Nav item state: filled pill → underline; fixed two pre-existing specificity/spacing bugs
- **File:** [v3nav-item-state-underline.md](Docs/v3nav-item-state-underline.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 11:48 — Unified breadcrumbs on the /broker trail; fixed hero grid on 8 more pages
- **File:** [hero-reveal-sitewide-opt-in.md](Docs/hero-reveal-sitewide-opt-in.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 11:07 — Shared hero grid field: /broker's masked grid applied to 23 more page headers
- **File:** [hero-reveal-sitewide-opt-in.md](Docs/hero-reveal-sitewide-opt-in.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 11:05 — Rebuilt /platform/governance onto the V3 design language (all content preserved, 39 ornamental icons + stock hero image removed)
- **File:** [governance-page-v3-design-unification.md](Docs/governance-page-v3-design-unification.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 10:35 — Fixed V3Nav mobile drawer (backdrop-filter containing block + accordion collapse); committed 3 changesets
- **File:** [v3nav-mobile-drawer-fix.md](Docs/v3nav-mobile-drawer-fix.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 10:23 — Fixed invisible homepage h1 from the hero reveal (gradient-text headline)
- **File:** [hero-reveal-sitewide-opt-in.md](Docs/hero-reveal-sitewide-opt-in.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 10:15 — Hover affordance sweep: removed hover animations from non-interactive elements (247 selectors, 58 stylesheets)
- **File:** [website-hover-affordance-sweep.md](Docs/website-hover-affordance-sweep.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-19 10:07 — Hero slide-up reveal extended from /platform/governance to 34 v3 pages
- **File:** [hero-reveal-sitewide-opt-in.md](Docs/hero-reveal-sitewide-opt-in.md)
- **Session:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 22:15 — Consolidated summary of all website changes made on 2026-08-18 (4 commits, 101 files, 24 pages rebuilt + 1 new)
- **File:** [website-changes-2026-08-18.md](Docs/website-changes-2026-08-18.md)
- **Session:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 14:30 — Resources navigation cluster: content and truth governance pass
- **File:** [resources-nav-cluster-governance.md](Docs/resources-nav-cluster-governance.md)
- **Session:** 3d03f149-0de7-49d6-975d-45f036b6bf58
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 12:05 — Rebuilt /need for requirement truth (retired Live Match Preview, no-signup and no-credit-pull framings, ready-ship grade claim, and match-before-verification vocabulary; gave own/rent/advise equal weight; 14-Q FAQ + WebPage/Breadcrumb/Service/FAQ schema); form, preview and post flows proven unchanged by restore-and-compare against the original
- **File:** [need-intake-page-requirement-truth-rebuild.md](Docs/need-intake-page-requirement-truth-rebuild.md)
- **Session:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 11:20 — Rebuilt /marketplace/compute for listing truth (removed universal instant-deploy, scaling, per-second billing, preinstalled-framework, autoscaling and 24/7 claims; 10-Q FAQ + WebPage/FAQ schema); 12 live listings, GPU cards, view toggle and all deploy CTAs proven unchanged at runtime; fixed a broken query string, duplicate breadcrumb schema, and mobile overflow
- **File:** [compute-marketplace-page-listing-truth-rebuild.md](Docs/compute-marketplace-page-listing-truth-rebuild.md)
- **Session:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 10:35 — Rebuilt /marketplace/power-opportunities for commercial truth (removed fabricated demand rail and the whole match display incl. fit score, operator counts, forward books, 6-10wk close; 8-Q FAQ + WebPage/Breadcrumb/Service/FAQ schema); inline script preserved byte-for-byte by SHA-256, form and submit payload proven unchanged at runtime
- **File:** [power-opportunities-page-commercial-truth-rebuild.md](Docs/power-opportunities-page-commercial-truth-rebuild.md)
- **Session:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 10:20 — Hardware subpage cluster rebuild (18 routes under /hardware)
- **File:** [hardware-subpage-cluster-rebuild.md](Docs/hardware-subpage-cluster-rebuild.md)
- **Session:** 3d03f149-0de7-49d6-975d-45f036b6bf58
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 10:05 — Rebuilt /hardware-sales for commercial truth (removed fabricated demand rail, static prices, universal payment and timing claims; 10-Q FAQ + WebPage/Breadcrumb/Service/FAQ schema); seller form, manifest, and valuation output proven unchanged at runtime
- **File:** [hardware-sales-page-commercial-truth-rebuild.md](Docs/hardware-sales-page-commercial-truth-rebuild.md)
- **Session:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 — Admin Intake Cleanup UI: bulk-delete form-spam intake across the whole derived graph (closes the cleanup gap from the 08-17 SQLi triage)
- **File:** [admin-intake-cleanup-form-spam.md](Docs/admin-intake-cleanup-form-spam.md)
- **Session:** 77c36516-5536-431f-af97-455eb95551c4
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-18 09:25 — Rebuilt /broker as governed broker+referral program page (removed guaranteed clearing-fee and universal origination claims, 10-Q FAQ + WebPage/Breadcrumb/Service/FAQ schema, contact path preserved); legal/finance sign-off + OG asset open
- **File:** [broker-page-program-governance-rebuild.md](Docs/broker-page-program-governance-rebuild.md)
- **Session:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-18 — Built /financing/lenders capital-partner page (spec copy, Service+FAQ schema, contact-sales handoff with lender interest option); legal gate + OG asset open
- **File:** [financing-lenders-network-page.md](Docs/financing-lenders-network-page.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rate-limit hotfix on website anonymous submit endpoints (10/5min per IP, verified locally)
- **File:** [build-intake-sqli-attack-triage.md](Docs/build-intake-sqli-attack-triage.md)
- **Session:** c762ad9e-daa3-4d99-99bb-7a7a483d3be8
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-08-17 — Triaged BuildIntake SQLi scan burst (200 submissions/6 min); injection failed, hardening + cleanup needed
- **File:** [build-intake-sqli-attack-triage.md](Docs/build-intake-sqli-attack-triage.md)
- **Session:** c762ad9e-daa3-4d99-99bb-7a7a483d3be8
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-08-17 — Content-phase finalization: /platform/cloud and /hardware (comments, attribution, validation)
- **File:** [hardware-page-sourcing-rebuild.md](Docs/hardware-page-sourcing-rebuild.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rebuilt /hardware as governed GPU-sourcing page; fixed Organization schema sitewide
- **File:** [hardware-page-sourcing-rebuild.md](Docs/hardware-page-sourcing-rebuild.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rebuilt /platform/cloud as GPU Cloud Marketplace page with live governed preview
- **File:** [cloud-page-gpu-marketplace-rebuild.md](Docs/cloud-page-gpu-marketplace-rebuild.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rebuilt /platform as transaction-platform page; added declarative analytics bridge
- **File:** [platform-page-transaction-rebuild.md](Docs/platform-page-transaction-rebuild.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Homepage finish-and-validate pass: fail-closed metrics, footer repositioning, terminal CTA
- **File:** [homepage-rebuild-aug-2026.md](Docs/homepage-rebuild-aug-2026.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Applied financing post-update review corrections (hero, Service schema, apply page, nav)
- **File:** [financing-page-number-light-rewrite.md](Docs/financing-page-number-light-rewrite.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rebuilt homepage per Aug 2026 spec (governed metrics, no volatile claims)
- **File:** [homepage-rebuild-aug-2026.md](Docs/homepage-rebuild-aug-2026.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Rewrote /financing page per number-light spec (all rates/figures removed)
- **File:** [financing-page-number-light-rewrite.md](Docs/financing-page-number-light-rewrite.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Moved Tools column (Configure/TCO/Power) from Financing to Resources nav
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Removed Forward escrow lots + Pricing engine from V3 nav
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Replaced wwwroot/llms.txt with new discovery-map version
- **File:** [replace-llms-txt.md](Docs/replace-llms-txt.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Removed duplicate Trust-column nav links (audit log, SOC 2 line)
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Deduped /platform/architecture into /platform/cloud with 301
- **File:** [dedupe-platform-architecture-cloud.md](Docs/dedupe-platform-architecture-cloud.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Fully removed /platform/ecosystem page, now 410 Gone
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — /case-studies now returns 410 Gone (incl. detail-page prefix)
- **File:** [remove-case-studies-page.md](Docs/remove-case-studies-page.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Done

### 2026-08-17 — Removed SLYD Cloud mega-menu links (operating layer, license, orchestration & billing)
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Removed nav links to /platform/ecosystem, page kept alive (SLYD website)
- **File:** [remove-ecosystem-nav-links.md](Docs/remove-ecosystem-nav-links.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-17 — Removed case studies page and all links (SLYD website)
- **File:** [remove-case-studies-page.md](Docs/remove-case-studies-page.md)
- **Session:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Done

### 2026-08-14 23:59 — **Wrote the sales rep onboarding tutorial for CRM / Deal OS**, published as a private artifact: https://claude.ai/code/artifact/3b06f072-88e6-4e90-85d0-f6e2fef24643. Structure: five records → nav map (which 4 of ~18 sidebar sections a rep actually needs) → eight-step core loop (lead → convert → demand → match → propose → workshop → advance → close) → **the stage gate reference table** → troubleshooting → rules that bite. **Everything was read out of the code, not assumed** — the parts reps get stuck on are enforced in the service layer and invisible from the UI. Gate table came verbatim from `DealPipelineFeatures.RequirementsFor` (~line 935) split by the three deal shapes it branches on (Capacity / BOM `d.Lines.Count > 0` / Hardware+ThreeSided); match hard filters from `MatchScoringService.IsExcluded` (~line 214); propose semantics from `ProposalDraftService`. **Two findings the guide has to work around: (1) `Lead.Qualified` is a DIRECTION-OF-INTENT flag (true = outbound, we sourced them; false = inbound), NOT a quality score — the name says the opposite of what it means and is worth renaming; (2) "Claimed ≠ matchable" is the #1 'why can't I sell this', and it's deliberate — it stops us quoting phantom inventory.** Escrow gate documented as advisory-not-blocking with the bypass landing in the audit log. Palette lifted from the product's own DesignTokens so the guide looks like Deal OS. **Unreviewed by anyone who actually sells, and has no screenshots — both worth fixing before it goes to a new rep.**
- **File:** [dealos-sales-rep-tutorial.md](Docs/dealos-sales-rep-tutorial.md)
- **Session:** e503dc75-e0cf-4a94-b311-c18127000c13
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 23:55 — **Shipped the whole catalog/pricing arc to development: core v0.2.14 released, all four repos pushed, every CI green.** Sequence mattered and held: core `main` pushed (3 commits — deal docs, stage remap, catalog identity + price observation ledger) → tag `v0.2.14` → publish workflow (4m20s) produced packages + `efbundle-linux-x64.tar.gz` with FOUR migrations → pin bumps committed (admin 0.2.13→0.2.14 across 7 refs; **platform 0.2.12→0.2.14 across 6 refs — needed because its unpushed stage-translation commits read the remapped DealStage, a dependency invisible if you only look at today's diff**) → admin/platform/website pushed. **Admin commits (4 new + pin bump): catalog identity + unit pricing foundation (32 files), Demand Book create + submitter, Hardware Catalog page, inventory-as-sourcing gate — plus 4 PRE-EXISTING unpushed commits rode along (6-stage pipeline move, deal workshop rebuild, sidebar, S3 docs), so the team got ~3 days of work, not one.** CI results: admin build 1m39s (the real risk — resolving freshly-published 0.2.14 from GitHub Packages — passed), deploy-development 10m2s incl. migrations against the dev DB; platform success; website success (6m1s). **Local NuGet-path verification was impossible (feed 401s without CI's token, gh token lacks read:packages) — Mason's call: let development CI be the test. It was, and it passed.** Gotchas recorded: core releases are TAG-driven from `main` (origin/HEAD→main, origin/Development is stale) — the "never push main" rule is for the app repos; `v0.2.13` existed with unpushed commits because a tag push carries its objects. Cosmetic: core build warns on a duplicate `using SLYD.Application.Interfaces.Services` — clean up next core change. Team to-know: `/v3/pricing/catalog` needs role grants; teammates must pull core + `dotnet ef database update`; demo seed + tier2 import are LOCAL-only.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Done

### 2026-08-14 22:45 — **The Sourcing gate now counts inventory as a sourcing route.** Mason hit it live: a BOM line 100% covered by an allocated lot couldn't advance Sourcing → Quote Sent because the gate demanded a selected quote per line. **Structural, two halves: Deal OS models two sourcing routes (commercial = SelectedQuoteId, physical = DealLineFulfillment) and both the gate AND Deal.Value counted only the first** — DealPipelineFeatures had zero references to fulfillments, and value was `SUM(SelectedQuote.AmountUsd)` so an all-inventory deal was worth $0. **Mason's ruling: value > $0 derived from quotes + lot asks, every line 100% fulfilled from either route or both, "don't make a shortcut."** The proper change: **one shared definition of "sourced" — internal static `DealValues`** (same convention as PriceObservations/CatalogLinks) holding both halves. Coverage: quote-covered units (its stated Quantity, or the whole line when it states none — the pre-unit-pricing reading of AmountUsd) + committed lot units ≥ line qty; zero-qty lot-scoped lines are covered by any sourcing evidence. **Value: quote amount in full + lot units at each lot's per-unit ask, CAPPED at the units the quote didn't cover, in commit order — the cap is load-bearing: in the designed buy-then-deliver flow (quote wins, goods arrive as lots on the SAME line) the arrival adds nothing, where uncapped it would double the deal.** Evidence-never-authority carried through: an unpriced lot covers but contributes $0 — coverage passes, the value gate blocks, the fix is ops pricing the lot. **Recompute now rides every input that moves the number** (same-save overlay callback generalising the old overrideAmount trick): quote select/deselect, fulfillment commit/remove, line-quantity edits (NEW — qty bounds the lot window), and lot repricing (NEW — guarded to the fulfillment path, because recomputing a line-less proposal deal would stomp its value to $0; pinned by test). **Adjacent hole closed: RemoveLineAsync blocked sent RFQs but not fulfillments — deleting a lot-covered line would cascade the rows and strand the lot bound to the deal; now refused.** 12 new tests incl. the reported scenario end-to-end; admin **331**; Postgres probe verified the conditional-nav + nested-collection recompute projection (60,000 → 108,000 → 60,000 across commit/remove), then deleted. Old quote-only RecomputeDealValueAsync deleted.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work


### 2026-08-14 21:30 — **The price history chart rendered as a solid black wedge with no line — and it was not a colour choice, it was a real bug worth remembering.** **Blazor scoped CSS works by having the Razor COMPILER stamp a `b-xxxxx` attribute on every element it emits and rewriting the stylesheet to require it (`.area-chart[b-5cdd3xz78d]`); elements created via `RenderTreeBuilder` never get that attribute, so every rule in the .razor.css silently fails to match.** I had built the sparkline, area chart and bid/ask ruler with `builder.OpenElement(...)`, so the polygon got no fill and fell back to **SVG's default black**, the polyline's stroke came from CSS and was therefore **invisible**, sparklines lost their red/green and inherited surrounding text colour, and **the ruler was silently broken too** (position:absolute and the tick ::before both came from CSS, so marks never positioned). **Fix: rewrite them as Razor TEMPLATES (`=> @<element>…`), which are compiled markup and do get the scope attribute.** Verified by emitting the generated C# with `-p:EmitCompilerGeneratedFiles=true` and confirming `AddAttribute(345, "b-5cdd3xz78d")` now lands on the `<svg>` — the definitive check, since this failure is silent at both build AND run time. Colour, now that it can land: **the chart paints entirely from `currentColor`** (stroke + both gradient stops) so one property recolours it, set by direction on the same polarity as the 90d column (falling ask = good for us = green, rising = red); gradient fades to 2% at the baseline so it reads as a line with volume under it rather than a solid block; ruler ticks got a currentColor glow and "our ask" moved to --slyd-primary so all three marks are distinguishable. **Rule of thumb: in a .razor file, never build user-visible markup with RenderTreeBuilder if it depends on scoped CSS — use `@<…>` templates.** Admin 314 green.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work


### 2026-08-14 20:55 — **Seeded local SLYD2 with Hardware Catalog demo data** so the page can actually be viewed. Scripts in the session scratchpad: `catalog-demo-seed.sql` / `catalog-demo-teardown.sql`. **Everything is tagged for exact removal** — Accounts/CatalogPartNumbers/Lots ids start `dddddddd-`, every observation carries `Notes='demo-seed'`; teardown is four DELETEs and touches nothing else. **Deliberately creates NO Deals or Demands** — those were wiped on purpose so the new flow could be tested from scratch, and seeding fakes would muddy exactly what the wipe was for; visible consequence is that buyer ceilings read "inbound" in the DEAL column, since a ceiling's deal resolves through its source Demand. Shape: 8 part numbers across H100/H200/B200/A100, 4 lots (H100 totals **1,152 units held**, matching the mockup), 22 supplier quotes including an 8-month H100 SXM5 decline 26,100→20,400 with two lapsed, **one model-level ask with no part named** so the "counts on the model, absent from every part" rule is visible, 6 buyer ceilings, 4 paid observations off lot costs. H100 lands on the mockup's figures — range $18,600–$27,600, SXM5 spread 17.6%, NVL "no bid". **The seed caught a regression in my own rebuild: I had dropped the "N lapsed" indicator**, so A100 (every quote expired) showed a bare dash — conflating "nobody quoted" with "everything lapsed", the exact distinction the prior entry documents as load-bearing. Restored on the model band and the Whole model row. **Pre-existing junk now very visible: B200 carries a $50 ask and a $1,500 lot ask from Mason's earlier UI testing**, so its row reads range $50–$39,800, spread 87,900%, 90d −99.9% — real data, left alone, but it is the loudest row on the page. Admin 314 green.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work


### 2026-08-14 20:10 — **Hardware Catalog rebuilt against Mason's mockup.** He compared the shipped page to his design and the verdict was fair: **I had built an evidence viewer for the ledger; he had designed a trading desk** — right numbers, wrong question ("what observations exist?" vs "what do I do about this part now?"). Admin **314**, Postgres re-verified. **Three rulings from Mason settle the shape: dark theme stays (the light mockup wasn't the ask); a model with evidence but NO parts must still show that evidence; and a model row aggregates all its parts PLUS whatever is pinned to the model and to no part, while a part row is only that part.** **Structural fix: disclosure is now model band → part rows → evidence.** It was model → everything with a "scope" chip row, which is a *lens* not a drill-down — and since the nested parts table had different columns from the model table, every part-to-part comparison the mockup exists for was impossible. **A "Whole model" row now sits first in the parts table and expands to the aggregate**, auto-opening when the model has no parts — cleaner than a special case because every row in that table behaves identically. **Two whole cards were missing.** *Buyer ceilings* (ACCOUNT | DEAL | QTY | CEILING | LOGGED | BASIS) — asks and bids had been one "Observations" table with a Side column, i.e. a table half of whose columns are blank on any row; **the DEAL column needed `observation.SourceId → Demand → Deal.DisplayId`** (else "inbound"), without which a ceiling is a number with no way back to the conversation that produced it. *Bid/ask ruler* — three figures to scale on one axis plus a plain-language verdict; **the only part of the page that interprets rather than reports, which was the entire point of the mockup**, and it hedges itself when there's only one quote or one ceiling because an unqualified verdict off a single observation is false confidence. **New aggregate: the best-quote RANGE ($20,400–$27,600)** — group by `{CatalogItemId, PartNumberId}` with **the null-part bucket counting as its own bucket**, best ask per bucket, model range = min..max; a single "best ask" hid that parts under one model are quoted thousands apart. Also closed: Active/Expired badges, a `no bid` badge distinct from "no data" (asks with no interest is a worse signal than silence), spread as a coloured badge, sparkline+90d merged into one column, **absolute dates instead of "2d ago"** (relative is useless for a quote you may need to cite), lead in weeks, filled area chart with an axis instead of a month table. **Bugs the comparison exposed in my own build: the "Lots we hold" card was overflowing and clipping** (LOT-2026-0001 wrapping one char per line, margin column cut off — a 6-column table in a 1fr grid slot; now a card list), **the model subtitle read "B200 / NVIDIA B200"** (fell back to Label, which just restates the model; now composes real specs), and **manufacturer was null for every GPU** (GpuCatalogItem has no such column — now borrows the one its parts agree on, showing nothing when they disagree). **Schema gaps now SURFACED rather than hidden: BASIS renders as an amber `unset` badge with a note that these mix a signed commitment with a guess** — an invented basis would be worse than a visible gap; architecture/form-factor/cooling don't exist so the subtitle shows only the real part of "Hopper · 700W SXM"; lot location is IsoCode only. **Postgres re-verified because the rebuild added a nullable Guid inside a composite GroupBy key, a per-part DateTimeOffset.Year/.Month grouping, and the Demand→Deal projection — none provable on InMemory.** All 17 live models now render a real subtitle.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work


### 2026-08-14 18:40 — **The Hardware Catalog page is built** (`/v3/pricing/catalog`) — the market-insight surface the whole catalog identity effort was building toward. Admin **309** (was 295, +14 tests); only 2 existing files touched, both one-line registrations. **The point of the design, and the answer to Mason's question up front: the page does NOT depend on the observation sources.** Every price figure — best ask, top bid, spread, last paid, 90d, monthly history — reads `PartPriceObservation`, never the record that produced it, so wiring a new source later (closed deals → Sold, price lists, invoices) makes it appear with **zero page or service changes**; an unwired source shows as a *missing* figure, never a wrong one. First test pins exactly that using `PriceObservationSource.Manual`, which has no writer today. **Holdings are the one deliberate exception and read `Lot` directly** — units held / our ask / margin is current shelf state, and the append-only ledger structurally cannot answer "what do we have right now". **Absence renders as absence everywhere** (null, not 0 — a `$0` best ask reads as a real and very good price, the worst failure mode on a market page); spread is null unless BOTH sides exist. **The Postgres probe caught an asymmetry I hadn't stated: expired quotes leave `BestAskUsd` but STAY in the history and the 90d change** — correct, and load-bearing: a lapsed quote isn't a price you can still get, but it was true when observed, and since every quote expires eventually, filtering them from history would leave the chart erasing itself from the left. Now documented + pinned by a test; UI shows an "N lapsed" chip so ops can tell "nobody quoted" from "everything lapsed". **Probe also caught that a part-scoped price is also a price for its model** (model row = the union, so it can beat any part-blind figure) while the converse does NOT hold — `GetPartsAsync` excludes model-level observations because attributing a model-granularity quote to one sibling part invents precision. **Aggregates computed in SQL** (conditional MIN/MAX over CASE, Sum-of-1 rather than `Count(predicate)` for translation safety, on the existing `(CatalogItemId, Side, ObservedAt)` index) because the ledger only grows — except **"last paid", which is an argmax not an aggregate** and needs its own narrow pass. **Verified on real Postgres in a rolled-back transaction** (throwaway probe, deleted): InMemory proves neither the `DateTimeOffset.Year/.Month` grouping, the enum-inside-CASE, nor the conditional aggregates. All 17 live models across 8 categories project correctly, both catalog tables. **Razor gotcha: a switch expression with relational patterns (`< 1 => "today"`) fails the parse** — the tokenizer reads `<` as an opening tag and errors ~130 lines later as "unclosed tag". **Unresolved naming collision: Pricing Engine already has a "Hardware Catalog" TAB (the non-GPU row editor) and the new page carries the same name from the mockup** — left alone rather than renamed as an unrelated change, but worth a decision. **Nav note: the route is assignable immediately (AdminPageRegistry projects from NavRegistry) but existing non-wildcard roles won't have it checked, so it's hidden until granted.**
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work


### 2026-08-14 17:30 — **TODO (not started): route "Contact Us" submissions to dedicated per-use-case forms.** Go through **all form submissions on prod**, classify them by what the person actually wanted (selling hardware, buying capacity, broker intro, support, partnership, …), and work out how to redirect them off the generic Contact Us form onto a dedicated form for their use case — so the data arrives **structured instead of free text**. Free-text contact submissions can't be matched, routed, attributed or reported on. Order matters: **pull and classify the real prod submissions FIRST** — the distribution is what decides which dedicated forms are worth building. Deal OS already has structured intakes (sell submissions, broker submissions, site submissions, Deal OS access requests), so some of this traffic is likely people who couldn't find them; map buckets to existing paths before building anything new. Contact Us stays as the catch-all — the goal is to shrink it, not delete it. **Related and worth reading first: the 17:05 entry below found there is NO foreign key between `Demand` and `FormSubmission` — they're linked only by a DisplayId embedded in the subject line. Structuring intake properly should probably fix that link too.**
- **File:** [contact-form-routing-to-dedicated-forms.md](Docs/contact-form-routing-to-dedicated-forms.md)
- **Session:** e503dc75-e0cf-4a94-b311-c18127000c13
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 17:05 — **Demand Book drawer now shows who submitted a need** (Buyer read "—" for every website need). **Root cause: `Demand` carries NO name or email at all** — `SubmitNeed` writes the contact to a **parallel `FormSubmission`** and links the two only by embedding the demand's DisplayId in the submission's `Subject` (+ a `demandRef` payload key). **There is no foreign key between Demand and FormSubmission** — the intake's own comment says so. **But the drawer was also ignoring an identity it already had: `Demand.UserId` → `User` is a REAL FK**, stamped when the submitter claims the demand via the claim-token flow, and both live demands had it populated (`User` carries only `Email`, no name fields). New `ResolveSubmitterAsync` returns email/name/leadId/origin, and **looks the FormSubmission up EVEN WHEN a claimant exists** — the account says who holds the demand now, the form carries the typed name and the `LeadId`, so resolving only one would lose the single link back into CRM. Drawer gets a "Submitted by" cell with an origin label ("claimed account" vs "intake form"), a lead link, and an explicit "anonymous — no account, no contact on the intake form" instead of a bare dash. **Also had to add `[SupplyParameterFromQuery(Name="lead")]` to `LeadsInbox` — it had NO query-param support, so the lead link would have silently opened the list and done nothing.** **Data caveat: of 8 local NeedIntake submissions only 2 have a ContactName, 1 an email, 2 a LeadId — the form path is thin; the claimed-account path is what actually resolves today.** Proper fix still open: stamp a real `FormSubmissionId`/`LeadId` on Demand at intake. Admin 295 green.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 16:20 — **Demands can now be created from the Demand Book** (`/v3/crm/demand`), which was **read-only by design** — its interface doc said so, and Demands only ever came into being via platform intakes (website /need, configure, reserve, booking) or ops accepting a broker submission, so there was no way to record demand ops simply knew about. **`DemandSource.Ops` APPENDED** to the enum (values are load-bearing, never reorder); **no migration needed — the column is an int, and `has-pending-model-changes` confirms the model is unchanged.** New `DemandBookFeatures.CreateAsync`: `DMD-{year}-{seq}` DisplayId, audited `demand.created`, ctor gained IAdminUserService/IAuditEventWriter/ICatalogResolver (which forced fixing the existing read-only `DemandBookProcurementTests` construction). **Catalog rules mirror BOM lines: a picked part implies its model and a part from a different model is rejected; a picked model is AUTHORITATIVE over anything typed so the stored `WantGpuModel` can't drift from the link; with nothing picked the free text still goes through `ICatalogResolver`, so an uncatalogued demand lands with consistent casing and self-links if the model turns out to be catalogued.** **A stated `PriceCeiling` writes a Bid observation — first bid-side data the ledger gets from a UI.** Form carries the catalog model + part pickers, buyer account (via `ListAccountsAsync`), qty, urgency, ceiling, ISO, need-by, and a Term field that only appears for Compute; category disables while a model is linked because category is a fact about the hardware. 6 new tests, admin 295, core 657+311+74.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 15:30 — **Quote unit pricing + the price observation ledger** (migration `AddQuoteUnitPricingAndPriceObservations`, applied; admin 289, core 657+311+74). `SupplierQuote` gained nullable `Quantity`/`UnitPriceUsd`; **`AmountUsd` stays authoritative for deal value — untouched.** `ReconcileQuoteFigures` keeps all three consistent (unit × qty defines the total when both given; total + qty derives the unit; bare total stores as-is). **Gotcha caught mid-build: the `AmountUsd <= 0` guard ran BEFORE reconciliation, so a quote entered as qty × unit with a blank total would have been rejected — validation had to move after it.** New **`PartPriceObservation`**: append-only price facts on `CatalogItemId` (+ optional part), with Side (Ask/Bid/Paid/Sold), Source, unit price, qty, lead, counterparty, and `ObservedAt` = when the price was TRUE, not when ops typed it. Written from supplier quote → Ask, lot cost → Paid (only when the number actually moved, else every unrelated price edit spams the series), demand ceiling → Bid. `PriceObservations.Record` stages onto the CALLER's context so it can't survive a rolled-back quote, and **returns null instead of throwing when there's nothing comparable to file** — unlinked line, or no unit price; the underlying write still stands. **Rule written into the entity: evidence, never authority — nothing feeds back into `Lot.Price` or `Deal.Value`.** **Verified on real Postgres in a rolled-back transaction (InMemory proves neither the enum/DateTimeOffset mapping nor SQL translation): the rollup reproduces Mason's mockup exactly — best ask $20,400, top bid $24,000, spread $3,600/unit = 15.0% at the ceiling — plus the monthly best-ask series for the history chart.** **Depends on the same per-unit `CostBasis` assumption flagged in the 14:45 entry below — the Paid observations record CostBasis as a unit price, so if historical rows were entered as lot totals those price points are wrong by a factor of quantity.** NOT built: buyer-ceiling BASIS (Stated/Signed/Inferred), so a top bid mixes a signed commitment with a guess; platform's demand paths still write no observations.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 14:45 — **Lot pricing UI now shows the lot's ask price, not a rental rate.** Mason asked why a lot has no sale price — the field existed all along: `Lot.Price` is documented in Core as *"Sale price to the buyer"*, but every admin surface projected it as `RatePerGpuHour` and labelled it `$/GPU·hr`, so on an outright sale (B200 × 8) the one sale-price slot held a notional hourly rate. **The rest of the system already disagreed with the inventory page** — `ProposeModal` pre-fills the Propose drawer from `Lot.Price`, `ProposalDraftService` does `Value = Price × Quantity`, and `DealDetail` renders it as currency with an "unpriced" fallback. **The load-bearing discovery: `Lot.Price` is PER UNIT, and nothing says so — it is only implied by that `× lot.Quantity`.** So every new label says `$/unit` explicitly and the UI renders the derived lot total beside it; the per-unit reading is now written into the `SetLotPricingRequest` doc comment. Renamed the DTO field `RatePerGpuHour` → `PricePerUnit` across `LotListRow`/`LotDetailView`/`NewLotRequest`/`ConvertToLotRequest`, relabelled the inventory table (new derived **Lot total** column), drawer tile, pricing panel and the Submissions convert form, and added a **margin readout** ($/unit + %, red when negative) under the pricing inputs so ops sets an ask with the spread on screen. UI-only — no Core change, no migration; `CapacityListing` keeps the genuine $/GPU·hr rental concept. Admin build clean, **284/284 tests pass**. **Assumption to check: `CostBasis` was relabelled `$/unit` to make margin meaningful — if any historical rows were entered as lot totals, their margin now reads wrong.**
- **File:** [lot-ask-price-vs-rental-rate.md](Docs/lot-ask-price-vs-rental-rate.md)
- **Session:** e503dc75-e0cf-4a94-b311-c18127000c13
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-14 11:20 — **`/hardware-sales` GPU pills now derive from the GPU catalog** (platform + website). Mason spotted they were hardcoded; the page turned out to be SPLIT — the manifest autocomplete and the indicative price were already catalog-derived, but the six accelerator pills were literal HTML, because the taxonomy endpoint reads only `HardwareCatalogItems` and GPUs are deliberately excluded from that table. Drift it caused: page sold **GB200** (no catalog row), hid **B300** (in the catalog), and offered Deprecated A100 / Preview MI300X unmarked. **The constraint that shaped the fix: you can NOT render "every Active catalog row" — `ComputeBuybackAsync` prices from a catalog row only when Active AND `SecondaryBuyInUsd` is set, else constants, else THROWS 400. B300 is Active with no buy-in and not in constants, so offering it would have been a pill that 400s on click.** `LoadQuotableGpusAsync` therefore mirrors the pricer's resolution exactly and unions in constants-only models (GB200) that were never catalogued. Website got its first `@code` block on that page, server-rendering pills with a static `FallbackPills` list if the API call fails (an empty accelerator picker = dead sell page). Removed two hardcoded JS couplings: initial `accel` state now reads the server-marked pill, and `accelLabel` reads `data-label` instead of a map that would echo `undefined` for any new model. **Verified live: the six rendered pills are identical to the six hardcoded ones (zero visible change), B300 correctly withheld, and setting its buy-in in a rolled-back transaction made it appear — ops edits now reach the page.** Platform 11+166 green. **Still hardcoded and now unmoored: the "Live demand signal" cards' per-model `pricePerNode` figures in v3sell.js.**
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform
- **Status:** Follow-up Work

### 2026-08-14 09:50 — **Lots and demands now link to the catalog on write**, and the deal domain was reset for clean testing. Swapped `IAssetModelCanonicalizer` → `ICatalogResolver` across all 5 admin write paths (lot create, 2 submission conversions, broker line→lot, broker→demand); admin `src` now has ZERO references to the canonicalizer, though platform's 3 sites keep it. **Accepted behaviour change: non-GPU models now canonicalize against the hardware catalog (`xe9680` → `XE9680`) where before they stayed as typed.** Forced test churn: new `FakeCatalogResolver` with deterministic `IdFor(model)`, 6 test files swapped, dead `FakeAssetModelCanonicalizer` deleted, new `LotCatalogLinkTests`. Admin 282, core 657+311+74. **Backfill dry run surfaced real mis-categorisations, not just junk — a Server-category lot AND demand both carrying model `H100` (H100 is a GPU), and `144HGX servers` filed under Cooling.** Then wiped the deal domain per Mason (backup at `scratchpad/slyd2-before-wipe.dump`): 14 deals, 18 lots, 31 demands, 5 capacity listings, 30 submissions +12 cascaded payouts, 19 builds, 5 escrows, 91 match candidates, 38 deal activities, 3,758 deal audit rows. Kept accounts/contacts/leads/brokers/catalog/pricing and all CRM history; zero orphans verified. **Gotchas for any future wipe: `LedgerEntries → Deals` is RESTRICT so the commission ledger must be cleared FIRST or Postgres refuses; `MatchCandidates` and `AuditEvents` are stringly-typed with no FK so they survive cascades and must be named explicitly.** **Blocker: `Sites` is 0, so capacity listings can't be created until a site exists.**
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 21:35 — Mason UI-tested the BOM catalog picker and caught two bugs, both fixed with regression tests (admin 280, +4; core 657+311+74). **(1) The "LISTED LOTS MATCHING THIS LINE" panel never compared the model** — it filtered on category + subcategory only, and since a GPU line pins no subcategory, EVERY listed GPU lot matched; H200 inventory was being offered against a B300 line. Pre-existing, but only fixable now that lines carry a catalog link. `LotCoversLine` now mirrors the matching engine: equal `CatalogItemId` = pure match, model string is the fallback while either side is unlinked, no model = offer nothing rather than claim a false match. **The trap that bit me mid-fix, caught by my own test: the subcategory filter must be NON-GPU ONLY, because GPU lines carry the model IN `Subcategory` while GPU lots keep it null — comparing them rejects every lot. Same carve-out `ProcurementLineProjection` documents. So legacy GPU lines had been showing ZERO candidates all along — the opposite pre-existing bug in the same filter.** **(2) Description went stale when the catalog model changed** — the picker auto-fills it from the catalog label but `OnEditCatalogChanged` deliberately never touched it, so switching models left a line titled after a model it was no longer linked to (confirmed live: "NVIDIA H100 SXM5" linked to B300). New `IsCatalogAuthored` rule: overwrite when empty OR still verbatim the previous model's label; never clobber typed text.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 21:05 — Reviewed Mason's **Hardware Catalog page mockup** (market-insight surface: category pills → model rows → expand to parts → expand a part to *Quotes received* / *Lots we hold* / *Price history*). Assessment only, nothing built; stopping for the day. **The page validates the two-level design — it's organised model → parts → evidence, and every number on it is a join through the catalog link that this work just created** (quotes reach a part via `SupplierQuote → Rfq → DealLineItem.PartNumberId`, lots via `Lot.CatalogItemId`). Most of it needs no new tables: lots already carry cost/ask/margin, quotes already carry supplier + ReceivedAt + ValidUntil (→ the Active/Expired badge), and price history is just the quote series bucketed monthly. **But the one real schema gap: the whole page is per-unit and `SupplierQuote.AmountUsd` is a LINE TOTAL with no quantity — deriving unit price means dividing by `DealLineItem.Quantity`, which is 0 for lot-scoped/service lines. Needs a ruling (add Quantity+UnitPriceUsd to SupplierQuote, preferred) BEFORE any price column is built.** Also flagged: model subtitles need architecture/form-factor/cooling fields that don't exist; "Q1 27 allocation" encodes a quarter AND a lead *kind* we don't model; and price history only accrues (10 quotes exist in the whole DB). Proposed adding `Demand.PriceCeiling` as a third evidence source so the page shows bid vs ask, not just ask. **Tomorrow: wire the resolver into lot + demand writes — it's the next step in the plan AND unlocks four columns of this page (units held, lots we hold, our ask, margin).**
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform
- **Status:** Follow-up Work

### 2026-08-13 20:40 — Catalog identity is now UI-TESTABLE: new **Part Numbers tab** in the Pricing Engine (full CRUD, existing inline-row idiom) and a **catalog-model + part-number picker on BOM lines** in the deal workspace, with each BOM row showing a linked/`uncatalogued` chip so matchability is visible at a glance. Picking a model adopts its category+subcategory and fills an empty description with the catalog label; a typed description is left alone. `ResolveCatalogLinkAsync` enforces that a part implies its model and throws if the part belongs to a different one. Delete-part REFUSES when records reference it (the FK is SetNull, so deleting would silently unlink) and tells ops to retire instead. **Built `ICatalogResolver` as a SEPARATE core service rather than extending `AssetModelCanonicalizer` — platform has 3 call sites and `AssetModelCanonicalizerTests` pins "the GPU catalog has no opinion about server part numbers" as a deliberate decision; changing that implicitly inside a schema feature would have silently altered platform intake.** Fixed `DemoSeedJob`, which created catalog rows directly and would have produced rows with no identity. **Verification gotcha worth remembering: the admin suite runs on the InMemory provider, which CANNOT catch Postgres translation failures — and the new catalog queries use conditional navigation access plus a `PartNumbers.Count` subquery, so I ran them against real Postgres via a throwaway harness. All translated, and the resolver maps `h200` AND `H200` to one identity, leaves `RTX 6000 Ada` free, and resolves non-GPU `dgx h100` → `DGX H100` — none of which the canonicalizer could do.** Local DB seeded with 16 catalog models (6 GPU, 10 hardware), all with identities, zero part numbers. Green: core 657+311+74, admin 276. Also settled an architecture question: `SlydDbContext` in the feature layer stays, because 42 of 62 Admin.Application feature files already do it and `RecomputeDealValueAsync` in the same file has the identical signature. **Not yet wired: lots and demands still don't get `CatalogItemId` on write — the resolver is registered but uncalled; only BOM lines link today.**
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 19:35 — Catalog identity STEP 1 SHIPPED: `CatalogItem`/`CatalogPartNumber` + six nullable FK columns on Lots/Demands/DealLineItems, migration `AddCatalogItemAndPartNumbers` applied to local SLYD2 and verified in Postgres (all 17 FK delete rules correct; Cascade from catalog rows down through the identity, SetNull up from the three entities so retiring a catalog row can never delete inventory). Filtered unique indexes on both bridge pointers because the unused side is null on every row. Migration backfills one CatalogItem per existing catalog row; `PricingAdminFeatures` mints them on create going forward (via `db.CatalogItems.Add()`, dodging the client-set-Guid-PK gotcha that would make EF emit an UPDATE). Green: core 657+311+74, admin 276. **The finding that changes the plan: the catalog is effectively EMPTY — `GpuCatalogItems` has exactly ONE row (H100), `HardwareCatalogItems` has ZERO, against 18 Lots + 31 Demands referencing `H100`/`H200`/`h200`/`B200`/`ABC`/`abc`/`TTTT`/`100 GPUs`/`144HGX servers`. So populating the catalog is now a PREREQUISITE to the link backfill, not cleanup — and `H200` vs `h200` is a live demo of why `AssetModelCanonicalizer` can't help: it's a casing authority with nothing to be authoritative about.** Remaining order: link-on-write + snap → populate catalog → backfill links → FK-aware matching (+ConstantsVersion bump) → UI → part-number stage gate.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 19:00 — Deal OS hardware-identity design DECIDED (investigation only, no code): unify Lot/Demand/DealLineItem onto model-level catalog items with part numbers as children. Two codebase surveys confirmed **no PartNumber/MPN/SKU exists anywhere in Deal OS and nothing FKs to either catalog** — identity is free-text model strings compared `OrdinalIgnoreCase`, with the BOM line being the worst (GPU model stuffed in `Subcategory`, non-GPU in unvalidated `SpecJson["model"]`). Design: thin `CatalogItem` supertype now (one stable FK; the deferred Gpu/Hardware catalog-table merge later folds into it without touching entity FKs), `CatalogPartNumber` children, and a **uniform two-level identity on all three entities** — `CatalogItemId?` (model, set early, drives matching) + `PartNumberId?` (specific part, hardens toward point of sale; quotes need MPNs). FK equality = pure match; unlinked rows keep string matching (ConstantsVersion bump). Linking snaps the model string to canonical. Part number never affects scoring; "every line has a part number" becomes a stage gate. Catalog stays reference/prefill — lot price and selected quote remain price source of truth.
- **File:** [dealos-catalog-item-part-number-design.md](Docs/dealos-catalog-item-part-number-design.md)
- **Session:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 18:10 — Implemented the "Leads Inbox needs a link to the form submission" TODO (from 2026-08-13 13:09). Admin-only, no core change, no migration. **Why the existing Artifacts section didn't already cover it: it joins demands/sell/site submissions through `Lead.UserId`, and a lead captured from a public form has NO platform login — `LoadArtifactsAsync` returns `[]` immediately, so the submission that minted the lead was unreachable exactly when it was the only evidence ops had.** `FormSubmission.LeadId` (stamped by FormLeadCapture in the same transaction) is the only edge that survives an anonymous submit. **Verified against the local DB: all 5 submission↔lead links are on leads with `UserId IS NULL`, two literally named "Anonymous · HardwareSalesIntake"/"Anonymous · NeedIntake" — every linked lead was in the blind spot.** Built `LeadSubmissionItem` as a record SEPARATE from `LeadArtifactItem` (artifacts = what this login claimed; a submission = where the lead came from — folding them together would make the existing "claimed by this login" heading a lie), exposed as a LIST because a repeat submitter joins the existing lead rather than minting a second one. Drawer gets a "Source form · N" section of links; the row gets a file icon in the Source column (`×N`, opens the most recent) with `@onclick:stopPropagation`. **Link target gotcha: `/admin/forms/{id}` is the SUBMISSION detail page — the route param is named `FormId` but FormDetails.razor loads a FormSubmission by that id.** Two things fixed en route: **`AssignOwnerAsync` returned a detail with no artifacts, and the drawer swaps its whole view for that result — so taking ownership of a lead silently blanked its Artifacts section**; and `FormSubmission.SubmittedAt` is a `DateTime` (Forms predates the CRM's DateTimeOffset convention), so rows are projected raw and stamped `DateTimeKind.Utc` in memory rather than letting the provider infer an offset from server locale. Admin 276 green (9 new). Not clicked through. **Remaining TODO from today: capacity deals still can't be created from the pipeline page** — not a one-line dropdown fix, they need a listing picker + quantity because CapacityListingId/CapacityKind/GpuCount feed the close gate and CommittedRatio bump.
- **File:** [leads-inbox-form-submission-link.md](Docs/leads-inbox-form-submission-link.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 17:30 — Implemented the "deals carry zero or many reps" TODO (from 2026-08-13 12:57). **First resolved what "rep" meant**, because the codebase had two candidates: `Broker` is the EXTERNAL roster with its own commission ledger (and external counterparties are already `DealParty`), while `AccountDirectoryModels.cs:122` defines `CrmRepOption` as "the per-account CRM rep dropdown — **an admin user**" assigned via `Account.OwnerAdminUserId` — a single nullable FK, literally the "single fixed one" the TODO wanted replaced. (`Models/Sales/Rep.cs` is a different legacy module on CloudDeal/HardwareDeal; left alone.) New core `DealRep` join entity — unique `(DealId, AdminUserId)`, second index on AdminUserId for "which deals am I on", cascade from Deal but **Restrict from AdminUser so deleting an admin can't erase who worked a closed deal**. Deliberately no role and no commission split: the ask was attribution, and the Broker ledger stays the commission system of record. Migration `AddDealReps` is purely additive, applied to local SLYD2. Assign is idempotent, remove-nonexistent is a no-op, and **removing the last rep is allowed — an unstaffed deal is a real state, so the UI says "Unassigned" rather than blocking**. Audited `deal.rep.added`/`deal.rep.removed`. Surfaced on the workspace (the "Owner — coming soon" cell became a live chips+picker editor), the kanban card (`First +N`, full list in the title), and the drawer; platform gets nothing and grep confirms zero references there. **The gotcha worth remembering: adding the link through `deal.Reps.Add(...)` threw `DbUpdateConcurrencyException` on every save — a change-tracker probe showed the row entering as `Modified`, not `Added`, because a CLIENT-SET Guid PK discovered through a tracked navigation is taken for an existing row, so EF saves an UPDATE against a row never inserted. Not an in-memory quirk — it would fail identically on Postgres. `db.DealReps.Add()` forces Added; same reason AddDocumentAsync uses `db.DealDocuments`.** Green: core 657+311+74, admin 267 (12 new), platform builds. Not clicked through yet. **This is now a SECOND uncommitted core migration stacked on the stage remap** — additive and order-independent, but it ships alongside the one with the deploy-order hazard.
- **File:** [deal-reps-zero-or-many.md](Docs/deal-reps-zero-or-many.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 16:35 — Rebuilt the deal workshop (`DealDetail.razor`) to Mason's mockup layout: hero card (title, Amount/COGS/Gross margin/Your commission strip, six-stage pills) over a two-column body — specifics grid, BOM lines as a real table, documents, matching, activity on the left; Next step, Buying committee, Suggested matches in a 340px rail. Scope was explicitly **layout only, no new functionality**, so anything the data can't back renders as "coming soon" instead of being faked or dropped. Real: amount, commission (same flat 0.10 the kanban uses), stage tracker, type/power/region/site/dates, GPU model + qty (lots → demands → line quantities), longest lead time, BOM qty/net/fulfillment chips, next step (first unmet blocking gate), committee (party slots + DealParty), suggested matches (line inventory candidates deduped). Coming soon: COGS, margin, origination, close date, owner, ECCN, contract term, list price, discount slider, price floors, committee roles, match scores. **COGS/margin are structurally impossible today — `RecomputeDealValueAsync` sets `deal.Value = sum of selected supplier quotes`, so sell price and cost are literally the same number; showing a margin would mean inventing one.** Nothing was removed: the full RFQ/quote/allocation tree still expands beneath its line, now as a table detail row. Restructure done by splicing exact line ranges with a script rather than retyping; verified by diffing CSS-class usage before/after and deleting every orphaned rule. Build 0 errors, 255/255 admin tests. Not yet clicked through in a browser.
- **File:** [deal-workshop-layout-redesign.md](Docs/deal-workshop-layout-redesign.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 15:40 — Pre-production cleanup before Mason ships the stage remap. Two real customer-visible bugs found and fixed: **(1)** `Finance.razor`'s empty state still told customers "Deals appear here while they're still Configuring or Financing. Once escrowed…" — three stages that no longer exist; **(2)** the audit allowlist would have **blanked the history of every pre-remap deal**, because rows keep the kind they were written with and the DB is full of legacy `deal.financing`/`deal.escrowed`/`deal.live` — added legacy mappings (deal.live → "Deal closed", deal.financing → "Contracting started"; escrowed deliberately excluded). Plus ~12 stale doc comments across all three repos. **The thing to actually worry about at deploy time: `ci-cd.yml` runs migrations BEFORE rolling out new code, so the remap rewrites stage ints under the OLD app — production misreads every deal during that window (stage 2 shows "Escrowed" when it now means Sourcing; Closed=5 is outside the old 0–3 enum), and since admin and platform deploy independently the window stays open until BOTH finish. No backwards-compatible path exists; deploy them back-to-back in low traffic.** Version state: core uncommitted on `main` needing tag+publish, admin on core 0.2.13, platform on 0.2.12 (a two-version jump that also pulls the S3 document work). All green: core 657+311+74, admin 255, platform 166.
- **File:** [deal-stage-sales-pipeline-migration.md](Docs/deal-stage-sales-pipeline-migration.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 15:05 — Deal Room correctness pass — Mason reviewed the customer surfaces and caught four things, all now fixed (platform 166+11+5+11 green). **(1) BOM deals rendered EMPTY to their own buyer** — platform had zero `DealLineItem` references, so a quote-builder whale deal showed nothing until lots were physically allocated; added a narrow `DealRoomLineItem` carrying WHAT they're buying but deliberately NOT the selected supplier quote/amount, RFQ fan-out, or per-line sourcing state (a line reading "not yet sourced" leaks our supply position — same leverage leak as the Sourcing stage). **(2) The journey promised services SLYD doesn't provide** — step 04 claimed we rack, wire power/cooling, and bring the cluster online; we deliver hardware and that's it, so Deploy→**Deliver** with honest copy. **(3) Matching read as automatic** — it's opt-in, so step 05 now never auto-completes, shows "OPT-IN", and has a new muted `wait-optional` tier ("OPTIONAL — YOUR CALL"). **(4) The audit tab was the worst leak in the room, worse than the stage pills** — it shipped every deal AuditEvent verbatim: raw kinds (`deal.sourcing` etc., defeating the whole CustomerDealStatus layer) plus expandable before/after JSON carrying **deal Value edits = the entire negotiation and margin history, `bypassedWarnings` = ops advanced past an unmet escrow gate, and `listingCommittedRatio` = how much of a listing OTHER buyers hold**. Replaced with a 4-entry ALLOWLIST + plain-language labels; `DealRoomAuditRow` now has no field capable of holding a diff; ~5.8KB of diff-extraction code deleted rather than left lying around; tab renamed Audit→History; DiligencePackService inherits the fix. New `DealRoomLeakTests` pins every one of these boundaries.
- **File:** [deal-stage-sales-pipeline-migration.md](Docs/deal-stage-sales-pipeline-migration.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 14:20 — Platform swept onto the new 6-stage machine AND given a buyer-facing translation layer, so all three repos are green together (core 1042, admin 255, platform 161+11+5+11). Mason's question — should buyers see the new steps? — answered **no**: the new `DealStage` IS the sales funnel, so it inherits the "no CRM shows a prospect their pipeline position" rule; "Sourcing" is the worst leak because it tells a buyer we don't hold supply yet (pricing leverage). Built `CustomerDealStatus` as a SEPARATE enum (PreparingQuote/QuoteReady/Contracting/PreparingDelivery/Active/Inactive), never a relabeling — so a future internal "Stalled" stage can't flicker into customer view. **The structural win: the internal enum now stops at the service layer — platform view records carry the customer status, and grep confirms ZERO `DealStage` in any .razor file.** That auto-fixed DiligencePackService (builds the lender zip entirely from DealRoomView). Two unplanned leaks caught: CommandBar searched deals by raw stage text, BrokerDashboardController shipped raw stage strings in JSON. Migration also APPLIED and verified against Mason's local SLYD2 DB (4→Sourcing, 3+2→Negotiating, 4→Closed, all 13 rows). Everything still uncommitted.
- **File:** [deal-stage-sales-pipeline-migration.md](Docs/deal-stage-sales-pipeline-migration.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 13:09 — **TODO: Leads Inbox rows need a link to the form submission that minted the lead** — from a lead in the inbox, ops must be able to open the actual form the person submitted (the data edge already exists: form-lead capture stamps `LeadId` on the FormSubmission)
- **File:** [form-lead-capture-implementation.md](Docs/form-lead-capture-implementation.md)
- **Session:** 1e7e386d-164e-49a0-bf1f-31b72c4c1466
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 13:05 — Deal stages replaced with the 6-stage sales pipeline (New Inquiry → Qualified → Sourcing → Quote Sent → Negotiating → Closed, + terminal Lost) across core and admin; **platform deliberately NOT touched — Mason said stop, and it will not compile against local core until its 11 DealStage consumers are remapped**. Core: enum remap with load-bearing ints, `Advance`/`MarkLost` replacing the Mark* methods, raw-SQL migration `RemapDealStageToSalesPipeline` (highest-first statement order so rewritten rows can't be recaptured; Live→Closed, Financing/Escrowed→Negotiating, Configuring→Sourcing), 1042 core tests green. Admin: per-type gate matrix at every stage, capacity CommittedRatio bump moved to the Negotiating→Closed hop, MarkLostAsync (audit-only, ops signal via the audit sweep), 6-column kanban with Lost off the board, 255 tests green. Open-pipeline filters mapped `!= Live` → `!= Closed && != Lost`. Uncommitted everywhere.
- **File:** [deal-stage-sales-pipeline-migration.md](Docs/deal-stage-sales-pipeline-migration.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 12:57 — **TODO: deals need to support zero or many reps attached to them** — a deal should be able to carry no rep or several, not a single fixed one
- **File:** [pipeline-kanban-redesign.md](Docs/pipeline-kanban-redesign.md)
- **Session:** 1e7e386d-164e-49a0-bf1f-31b72c4c1466
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 12:48 — **TODO: capacity deals cannot be created from scratch on the pipeline page** (`/v3/deal-flow/pipeline`) — the new-deal flow doesn't support starting a capacity deal directly
- **File:** [pipeline-kanban-redesign.md](Docs/pipeline-kanban-redesign.md)
- **Session:** 1e7e386d-164e-49a0-bf1f-31b72c4c1466
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 12:30 — Admin left sidebar is now collapsible: a button in the sidebar's top-right corner slides it off-canvas (margin-left animation, no content reflow), a floating top-left button restores it, and the state persists in localStorage (`slyd:sidebar-collapsed`) following the existing `slyd:theme` convention. Icon-only rail mode deliberately skipped — LogoSection/AdminUserProfile/NotificationBell aren't built for a narrow layout. Only SideBarMenu.razor + its scoped CSS touched; build clean, uncommitted.
- **File:** [admin-collapsible-sidebar.md](Docs/admin-collapsible-sidebar.md)
- **Session:** 5445e395-325d-483b-ae35-02734aa6f013
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Done

### 2026-08-13 12:10 — Pipeline page redesigned from stage-filtered table to a kanban per deal type (`/v3/deal-flow/pipeline`), modeled on Mason's mockup but restricted to data we actually store. Type tabs HARDWARE / 3-SIDED / CAPACITY (Unknown legacy rows bucketed by the same FK inference the stage machine uses); same 4 stage columns on every board because the stage machine is shared across all deal types — per-type advance *requirements* already exist in `RequirementsFor`, per-type stage *names/sequences* would be a core-repo domain change. Cards: party chain, value + MW, GPU chip (new `GpuSummary` on `DealPipelineRow` — lots aggregate for lot deals, listing model × booked GpuCount for capacity), FORWARD/LIVE, region, DUE/LATE/DELIVERED, child counts + age. Mockup's weighted-% and "days in stage" deliberately NOT faked — no probability field, no stage-entry timestamp stored. Drawer + gated stage advance untouched; no drag-and-drop by design. Build clean, 74/74 DealFlow tests pass; NOT visually checked in the running app. Uncommitted.
- **File:** [pipeline-kanban-redesign.md](Docs/pipeline-kanban-redesign.md)
- **Session:** db573a0e-2c34-4a76-b41a-0676c6af891e
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-13 11:17 — Deal documents now upload to S3 with presigned retrieval + preview, across all three repos (core `50e9ab9` on **main** at the user's explicit direction after the never-push-to-main rule was raised; admin `d3abef8` and platform `3d4d9d9` on development; NONE pushed, core NOT yet tagged — deferred to the end on purpose since both consumers build via ProjectReference with `UseLocalCore=true`). Green everywhere: core 657/657, admin 250/250, platform 149/149. **The decision that mattered: reusing the existing assets bucket instead of provisioning a new documents bucket — which killed ALL Terraform work.** The user refused infra changes, and reuse turned out to be both simpler and safe because the `prod-slyd-platform-assets` policy is **prefix-scoped** (exactly two Allow statements: `provisioning_v1.sh` and `App_Icons/*`), so a new `Deal_Documents/` prefix is private by default. Nothing to provision — admin already gets `S3__AssetsBucketName`/`S3__Region`, the task role already has read+write, presigning needs NO extra IAM permission, and there's no folder to pre-create (S3 has no real folders). **Load-bearing invariant, written into `FileStorageOptions`' docstring: widening that policy to a bare `/*` silently makes every contract and invoice world-readable.** Core got `IFileStorageService` (generic — key + stream, no deal/account concepts), `S3FileStorageService` (no ACL, presigned-only, buffers non-seekable browser streams since PutObject needs a length), a dev-only `LocalFileStorageService`, and `FileStorageKeys` extracted as a **pure static** per TESTING.md so the key layout — the one thing that can't change once files exist — is pinned by 20 Tier 1 tests incl. traversal; plus `DealDocument.Visibility` (`Internal = 0 | Shared = 1`, zero value deliberate so old rows and forgetful code stay private) with an additive migration. `FileStorageOptions` binds the **existing `"S3"` section**, so zero new config. NEW core dependency: `AWSSDK.S3`, inherited by every consumer. Admin's `AddDocumentAsync` takes a request record with optional `Content`; **upload runs BEFORE SaveChanges** so a storage failure can't leave a record pointing at a file that never landed; `GetDocumentUrlAsync` is scoped by `(dealId, documentId)` so a doc id alone can't sign a URL across deals; the URL is minted per click rather than rendered into the page. Platform filters the Deal Room to `Shared` — and I also filtered the **buyer term-sheet status chip**, unplanned, because otherwise the buyer reads "term sheet awaiting signature" against an empty Documents tab, which both contradicts itself and reveals an internal term sheet exists. Three gotchas worth remembering: **Razor parses `< 1024` in a switch expression as an HTML tag** (a `FormatBytes` relational pattern threw bogus "unclosed tag" errors ~400 lines away — write it long-hand); **`char.IsLetterOrDigit('é')` is true**, so the first sanitizer let non-ASCII into storage keys; and the compiler found a second `AddDocumentAsync` call site in `Pipeline.razor:842` that grep missed. Also surfaced and NOT fixed: marketplace/Image-Library uploads return `GetPublicUrl()` for prefixes the policy doesn't cover so those URLs 403 — **latent, not live**, since the prod bucket holds exactly TWO objects and nothing has ever been uploaded that way; `dev-slyd-platform-assets` has no policy at all so app icons don't render in dev; and `appsettings.json:115` says us-east-1 while the buckets are us-west-2. Remaining to ship: tag+publish core, bump admin 0.2.13 and platform **0.2.12** (a two-version jump), verify `S3__AssetsBucketName` on the dev task def (the code has NO environment awareness — whatever the task def injects is what it writes to), and actually click through it since nothing has touched real S3 yet
- **File:** [deal-document-s3-upload-presigned.md](Docs/deal-document-s3-upload-presigned.md)
- **Session:** 02409be5-f3cc-41b0-b445-1350443804d8
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-12 17:06 — Ops now gets notified when a platform user requests Deal OS access (commit `7634cea` on development, NOT pushed; 245/245 tests, build clean). The gap: the gate at `DealOsAccountGate.razor` registers an inbound Lead via `ClaimResolution.ResolveAsync(…, "deal-os-gate", …)` and the user stays locked out of ALL SIX gated Deal-OS surfaces until ops converts the lead and adds them as a member — but **nothing announced it**. Audited all seven ops checks: `FormSubmissionCheck` sweeps FormSubmissions (gate writes none, it goes straight to Leads), `CrmActivityCheck` sweeps Activities (gate writes none either), no lead-based check existed. Requests just sat in `/v3/crm/leads` until someone looked. Proof it was an oversight not a decision: `ComplianceService.RequestVerificationAsync` writes an Activity *specifically* to fire `crm.new-activity`, commented as "the ops-facing signal" — the Deal OS gate just logs and returns. Fix is a new `DealOsSetupRequestCheck` (60s cursor sweep on `Source == "deal-os-gate"`), Severity **Warning** not Info because a pending request = a human locked out of the product. Non-obvious bit: the body reads the email from **`lead.User.Email`, not `Lead.Email`** — on an *adopted* lead (website form before signup, matched by email) the captured address can differ from the login they actually authenticate with, and the login is what ops creates the account against. **Coverage limit by design:** fires on the MINT branch only (= the new-user case). The join-existing-lead and adopt-anonymous-lead branches keep the earlier flow's `Source` and add no row, and a repeat request against a lead that already has a CompanyName skips `SaveChanges` entirely — **zero DB trace, unobservable from admin**. Completing it needs core's `DealOsSetupRequestService` to write an Activity (core release + version bumps). Also found and NOT fixed: a silent dead-end — `ConvertToContactAsync` only mints the AccountMember when `AddUserAsMember` is set (defaults false on the record; UI pre-checks it, so happy path is fine), but if ops unchecks it the lead gets `AccountId` stamped → `HasOpenRequestAsync` goes false → the gate shows the **original request form again** instead of "in progress" → resubmitting mints a DUPLICATE lead every time, with no way for the user to tell "waiting" from "dropped". Working tree also carried a concurrent session's uncommitted Demand Book changes throughout; only the 3 files for this task were staged
- **File:** [deal-os-access-request-ops-notification.md](Docs/deal-os-access-request-ops-notification.md)
- **Session:** 02409be5-f3cc-41b0-b445-1350443804d8
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-12 16:51 — TODO (investigation only, no code): make deal-workshop documents real — presigned S3 upload/preview on `/v3/deal-flow/pipeline/{id}`. Premise correction: we do NOT already store a link — `DealDocument.StorageKey` is a column nothing ever writes; `AddDocumentAsync` (`DealPipelineFeatures.cs:506`) builds a metadata row from a **typed-in filename string**, and `DealPipelineDocumentTests.cs:77` asserts `StorageKey` is null on purpose ("metadata-first"). Good news: `StorageKey`/`ContentType`/`SizeBytes` already exist on the domain model, so the upload ships **entirely from the admin repo, no core release**. Real blocker is that `S3StorageService` is public-assets-only — every method returns `GetPublicUrl()` and leans on a bucket policy allowing public read for `App_Icons/*`; MSAs/invoices/compliance certs can't go near that, so presigned GET is the decision (AWSSDK.S3 4.0.17.3 supports it; capability just doesn't exist). Two non-issues, don't re-investigate: the 512KB SignalR cap is NOT a blocker (Blazor chunks OpenReadStream; ImageLibraries already pushes 10MB through it), and `ImageLibraries.razor:184-240` is the upload template. Biggest surprise: **the platform Deal Room already renders every deal document to customers unfiltered** (`DealRoomService.cs:293`, no predicate beyond the deal) — metadata only, no bytes, but that means FILENAMES ALREADY LEAK to the counterparty, so adding an upload button makes `Acme-internal-margin-analysis.pdf` a live problem. Second surprise: compliance KYC uploads DO write real bytes (`ComplianceService.cs:92-101`) — to **local disk on Fargate**, so every deploy destroys them while `AccountDocument` rows survive pointing at dead paths, AND there is no read path anywhere (`ComplianceDocRow` has no StorageKey, no download endpoint), so ops can never open what customers upload. Two decisions blocking implementation: Admin-only service vs Core `IFileStorageService` (the latter fixes compliance too but needs a core release + Terraform to inject S3 env vars into Platform WebUI), and whether the internal/external visibility flag lands in this pass (needs core; default MUST be Internal)
- **File:** [deal-document-s3-upload-presigned.md](Docs/deal-document-s3-upload-presigned.md)
- **Session:** 02409be5-f3cc-41b0-b445-1350443804d8
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-12 16:47 — Demand Book now shows BOTH spines: website/platform intake demands + open deal BOM lines (PROCURE rows). Extracted ProcurementLineProjection so the book and the match engine share one definition of "open BOM line". Re-litigated and KEPT the projection over minting Demand rows — but found the real bug: Demand.AttachToDeal flips Open→Matched at deal formation and every matching path excludes Matched, so need goes dark mid-deal
- **File:** [match-engine-bom-line-demand-source.md](Docs/match-engine-bom-line-demand-source.md)
- **Session:** 85480ecc-e686-445b-9aa4-34f9e35bbf79
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-12 18:30 — Website: pulled the light/dark mode toggle off the V3 header (and its mobile-drawer twin) in `Components/Shared/V3/V3Nav.razor`. **This is temporary — it needs to go back in once light mode is finished.** The trigger: the SLYD logo (`SLYD-logo-300x86.webp`) is white text on transparent, so on the light background (`hsl(220,28%,96%)`) it goes white-on-white and vanishes — it appears at 7 sites (V3Nav x2, V3Footer, TopNavigation x2, Layout/Footer, DocsLayout), so an inline fix in the nav alone wouldn't have covered it. Non-obvious bit worth remembering: `Components/App.razor:26` already **hard-locks `data-mode="dark"`** on every page load, ignoring the persisted and system value (there's a long comment there about a system-light browser flipping `--slyd-bg-card` to `#ffffff` and producing white cards on V3 pages) — so this toggle was the ONLY way into light mode, and only until the next navigation. Markup preserved verbatim inside `@* ... *@` Razor comments, so restoring is uncomment-only: `.v3nav-tog` + the `:root[data-mode]` sun/moon swap rules stay untouched in V3Nav.razor.css, and `toggleMode()` in v3nav.js is already null-guarded so it no-ops with the buttons gone. Full restore also needs a dark-ink logo variant (or `filter: invert(1)`) at all 7 sites, unlocking the App.razor pre-paint script, and a light-mode audit of the V3 surfaces ("Tier C" per that comment). Build 0 errors; NOT clicked through in a running app. Uncommitted. Also surfaced this session and NOT fixed: prod deploys are impossible — deploy.yml on main gates `deploy-production` on `refs/tags/v*` (04e3f16) while `on:` only listens to `push: branches: [main, development]` with no `tags:` filter, so main pushes skip the job and tag pushes don't trigger the workflow at all (confirmed: run 31620611792, build success / deploy-production skipped)
- **File:** [website-light-mode-toggle-removed.md](Docs/website-light-mode-toggle-removed.md)
- **Session:** 7e2e587f-f459-4567-b272-155d9af40187
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-08-12 17:47 — Core: built account deletion, first pass — tombstone the User row + refuse on in-flight commitments. Triggered by a real GDPR erasure request that arrived via the public contact form; the user said they couldn't find a delete feature and was right, there was none. Two findings shaped it: (1) `UserRepository.DeleteUser` already existed with ZERO callers anywhere AND was broken — a bare `Users.Remove()` against a schema where `Notification.UserId`, `SupportTicket.CreatedById`, `BensonConversation.UserId` and `AppTags.AssignedBy` are all `DeleteBehavior.Restrict`, so it throws an FK violation for basically any real user (CustomerNotifier writes a Notification on nearly every lifecycle event); (2) there is NO Auth0 Management API client in any repo — `Auth0Service` is read-only, so a DB delete leaves a live identity. Scoped to the LOGIN (`User`), not the counterparty (`Account`/`Organization`) — one member leaving must not wind down a company others still use; `AccountMember` makes that clean. Tombstone scrubs Email → `deleted-{id:N}@deleted.invalid` (RFC 2606, undeliverable), clears AuthId/PlatformInterest/AdditionalInfo, stamps DeletedAt + DeletionReason. Deliberately NO global query filter on User despite the strong `IsDeleted`+`HasQueryFilter` precedent in this schema — it would silently alter every query and join across core/platform/admin incl. required navigations; filtered explicitly at the login path instead, and documented in the entity so nobody "fixes" it. Idempotent (retry returns AlreadyDeleted without re-stamping). 4 blockers spanning BOTH identity edges, which is the non-obvious part: v1 reaches compute+wallets via `OrganizationUser→Organization`, V3 reaches escrow via `AccountMember→Account`. Migration is 2 nullable columns, additive. FULL suite 1018/1018 passing incl. 13 new integration tests (Tier 2, per TESTING.md — DbContext-backed code must not use InMemory). Tombstone covers the User row ONLY — no data sweep, no Auth0 deletion, no UI yet. Uncommitted (not requested); core needs tag→publish→pin bump before platform/admin can use it
- **File:** [user-account-deletion-tombstone.md](Docs/user-account-deletion-tombstone.md)
- **Session:** 06f55203-7868-4979-9acc-a786e684bd7a
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-08-12 — Admin: made the buyer contact editable on a deal AFTER creation (Pipeline drawer). It previously could only be set in the new-deal dialog — `DealEditRequest` had no contact field and `UpdateDealAsync` never touched `DealParties`, so a deal created without a contact (or with the wrong one) was stuck. Attribution lives on `DealParty.ContactId`, NOT the Deal row. NO MIGRATION NEEDED — the column, index, and FK (SetNull) already shipped in `20260720190328_AddDealPartyContact`. Added `BuyerContactId`/`ClearBuyerContact` to `DealEditRequest`, `ApplyBuyerContactAsync` + `BuyerParty()` to DealPipelineFeatures, `ContactId`/`ContactName` to `DealPartyItem`, and a contact picker to the edit drawer. Non-obvious trap worth remembering: the unique index is `(DealId, AccountId, Role)` — NOT `(DealId, Role)` — so the schema permits two Buyer rows on one deal, which would double-count it in every account-involvement query; the upsert retargets the existing party instead of inserting. Contact is applied AFTER the FK mutations so it validates against the buyer the save leaves behind. Review catch: the UI now sends contact fields only when the selection actually changed, because `DealParty.cs:26-27` deliberately allows a contact to move companies mid-deal — an unchanged prefilled id would otherwise be shipped on the next unrelated save and rejected by the new validation, blocking an edit that had nothing to do with contacts. Build 0 errors; FULL suite 206/206 passing incl. 8 new tests. NOT clicked through in a running app. Uncommitted (not requested)
- **File:** [admin-deal-buyer-contact-post-creation.md](Docs/admin-deal-buyer-contact-post-creation.md)
- **Session:** c92e3c52-8093-43b7-9313-c243e44b6d5b
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-06 16:25 — Admin: made the account NAME clickable in the Accounts directory (/v3/crm/accounts), navigating to the account workspace at /v3/crm/accounts/{id}. The deep-link already existed but only as a hover-revealed external-link icon beside the name — effectively invisible. Wrapped `@row.Name` in `<a class="name-link">`, dropped the now-redundant row icon, kept `@onclick:stopPropagation="true"` so the name click doesn't also fire the row's SelectAsync (drawer-on-row-click unchanged elsewhere in the row); `.name-link` inherits row color, underline + --slyd-primary on hover. Drawer h3 keeps its ws-link icon, whose dead `opacity:0` / `.clickable-row:hover` reveal pair was simplified out. Branch gotcha worth remembering: the task targeted `development` but AccountWorkspace.razor wasn't there — PR #49 (feat/crm-accounts-quote-builder) had been PUSHED but not merged, and `git pull` reporting "Already up to date" is what surfaced it; `gh pr view 49` is the check, not the pull. Merged (be79593) then edited. Build 0 errors; NOT clicked through in a running app. Uncommitted
- **File:** [admin-account-workspace-page.md](Docs/admin-account-workspace-page.md)
- **Session:** 1da37239-f4df-4c88-a087-a94e1145a2c0
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-06 14:30 — Core: published v0.2.12 to GitHub Packages, then bumped platform's WebUI + HangFire pins 0.2.11 → 0.2.12. PR #17 was already merged to main via the GitHub UI (3d89740); verified Release build + FULL suite green (637 unit + 311 matching + 57 integration = 1005 passing, 0 failures) before tagging, since publish-packages.yml runs tests and a failure would strand the tag. Run 31110675460 all-green — Domain/Application/Infrastructure/Matching 0.2.12 all "Your package was pushed", release carries efbundle-linux-x64.tar.gz (64MB, NINE migrations). This CONFIRMS the feed-publication caveat left open by the 09:45 admin bump. Chose patch to match repo convention (62 straight v0.1.x patch bumps) but flagged v0.3.0 would better signal risk — 9 migrations, new tables AccountMember/DealLineFulfillment/Rfq/SupplierQuote/DealLineItem/ContactEngagement, AccountProvisioning.cs deleted; decision left open, v0.3.0 can still tag 3d89740. "platform-web"/"platform-hangfire" are NOT separate repos — both are projects in the single `platform` repo; the Phase 2/3 split in core's CLAUDE.md never happened. Same UseLocalCore=true gotcha as admin: the edited pins live behind `!= 'true'` so local builds never touch them; real feed restore 403s because the gh CLI token lacks read:packages (needs a PAT). Verified source-compat instead — local core main == v0.2.12 tag, both projects build 0 errors. Shipped with a HIGH-severity System.Security.Cryptography.Xml 9.0.0 advisory inside SLYD.Infrastructure that reaches consumers. Platform bump committed bd897cd on feat/crm-accounts-quote-builder, unpushed — run the TaskTracking pre-push step before pushing
- **File:** [core-v0212-release-and-platform-pin-bump.md](Docs/core-v0212-release-and-platform-pin-bump.md)
- **Session:** 77543760-4471-47c4-946a-2ab2ba6308e0
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-08-06 09:45 — Admin: bumped SLYD.Domain/Application/Infrastructure/Matching 0.2.11 → 0.2.12 in both csprojs (Components stays 0.5.0). 0.2.12 is the CRM/quote-builder release the branch already consumes — AccountMember, deal party contacts, intake contact links, lead capture from form submissions, quote builder schema, DealLineFulfillment, customer-editable demands. Build clean, 0 errors. Caveat worth remembering: UseLocalCore=true means the local build never touches the PackageReference lines edited — it's only valid evidence because local core HEAD == v0.2.12^{commit} (3d89740) with a clean tree; that the packages are actually PUBLISHED to the GitHub feed is unverified (needs NUGET_AUTH_TOKEN), CI finds out first. Bump triggers NINE migrations via the efbundle; AddDealLineFulfillment is an unguarded CreateTable so check __EFMigrationsHistory before deploying. Could NOT confirm the previously-recorded AddProcurementLoop deletion — no trace in core git log --all. Committed 11d04c5, unpushed
- **File:** [admin-core-bump-0212.md](Docs/admin-core-bump-0212.md)
- **Session:** 67e19de6-7021-4882-aa88-e24b1ab8c23b
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-06 09:19 — Admin: fixed grid overflow clipping across form/CRM detail layouts. Root cause was `1fr` tracks resolving to `minmax(auto, 1fr)` — the auto *minimum* means wide children inflate the track instead of shrinking it; switched DetailGrid (all 4 column counts + both breakpoints), LeadsInbox `.split-grid` and FormDetails `.content-grid` to `minmax(0, 1fr)`. Also renamed FormDetails' `.main-content` to `.detail-main` because the layout shell claims that class globally in custom.css (`width: calc(100% - 280px)`, `height: 100vh`) and scoped CSS doesn't shield against it, and wrapped the LeadsInbox table in a scrolling container with a min-width so it scrolls rather than stretching the grid. Build clean, committed 49479d4, unpushed
- **File:** [admin-grid-overflow-clipping-fix.md](Docs/admin-grid-overflow-clipping-fix.md)
- **Session:** 67e19de6-7021-4882-aa88-e24b1ab8c23b
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Status:** Follow-up Work

### 2026-08-05 19:20 — Hexi: notification click-through — tapping a terminal notification jumps to its tab and scrolls the scrollback to the matched line (anchored via public totalLinesTrimmed + topVisibleRow + cursor.y; nil when scrolled up or in alternate screen since Buffer.yBase isn't public), and watch-rule notifications now show the 3 preceding log lines as a monospaced context block. AppNotification widened with display-only `details`; tab/anchor targets kept reporter-side, inbox rows call a new defaulted `open` action. Tests green, app builds
- **File:** [hexi-terminal-notification-producers.md](Docs/hexi-terminal-notification-producers.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-05 18:45 — Hexi: first real notification producers — opt-in command-failure notifications (exit code ≠ 0/130, only when the tab is hidden or the command ran ≥10s; zsh shim now sends the command line via private OSC 7773 so the notification names what failed) plus user-authored watch rules (word or regex, matched against every output line via a PTY byte tap and OutputScanner with ANSI stripping and a 30s per-tab/rule cooldown). New Settings → Notifications section; rules persist in notifications.json. 105 tests green, app builds
- **File:** [hexi-terminal-notification-producers.md](Docs/hexi-terminal-notification-producers.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-05 18:05 — Merge-readiness check before pushing the lead-capture work; found one recurring deploy trap and one real conflict. Applying migrations to SLYD2 failed with 42P07 "DealLineFulfillments already exists": the 2026-07-22 reversal DELETED 20260721145707_AddProcurementLoop from the repo and regenerated it as AddDealLineFulfillment, so any DB migrated before that date has a history row pointing at an ID that no longer exists in source, and EF tries to CreateTable over a live table. Verified the live table matched the replacement exactly (6 cols + PK + 3 indexes) before recording it as applied rather than re-running — SLYD2 now fully migrated, LeadId + FK + index confirmed. Staging/prod will hit the identical failure; check __EFMigrationsHistory for %ProcurementLoop% before running the efbundle. Also confirmed nothing auto-applies migrations (no Database.Migrate anywhere; CI ships a self-contained efbundle someone runs), so schema MUST lead code or every form submission fails, not just the lead part. Branch topology after a fresh fetch: core 0 behind development but development is 6 MONTHS stale (Jan 23) while main is Jul 16 — core's real integration branch is main, contradicting the repo CLAUDE.md. No competing migration anywhere, so no snapshot conflict. Website is 10 behind and it's a full SEO/AEO + brand overhaul that touches ALL TEN files in my commit — Configure.razor +150/-80 where SEO Phase 1 reworked V3 pages for static SSR, exactly where the new contact block lives. Needs a hand rebase, not a textual merge
- **File:** [slyd-migration-drift-and-branch-topology.md](Docs/slyd-migration-drift-and-branch-topology.md)
- **Session:** d6631e24-35fd-4130-8ac9-ac2b19bfc81e
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Priority:** High
- **Status:** Follow-up Work

### 2026-08-05 12:10 — Built Hexi's notification inbox as pure structure — zero producers, shaped as the next plugin integration point. AppNotification + write-only NotificationPosting in HexiCore; capped @Observable NotificationStore in HexiPersistence (in-memory until something posts; JSONFileStore is one field away); NotificationInboxView in HexiUI; PluginContext gains notifications so plugins can post but never read. Bell with unread badge sits next to the favorites star; pressing it slides the inbox over the sidebar and forces the column visible — Mason runs sidebar-collapsed, where the slide-over would otherwise animate inside a hidden column. 107 tests green, signed universal build clean. Repeat gotcha: after adding a type to HexiCore, dependent packages' swift test fails on stale .build — rm -rf .build. Natural first producer: Claude plugin's permission-blocked state
- **File:** [hexi-notification-inbox-structure.md](Docs/hexi-notification-inbox-structure.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-05 11:45 — Hexi Claude plugin follow-up: Mason's live test showed the sessions widget working but no status dot. Bug: the polling .task hung off a Group that renders nothing until claude is detected — Group forwards modifiers to children, zero children = no task, so detection could never start. Rewrote the dot around TimelineView(.periodic by 2s), which re-evaluates on schedule even while empty. Also patched release.sh to pass ARCHS globally on the xcodebuild line (the target-level project.yml pin never reaches SwiftPM packages) — cold universal release build + signing verified. Awaiting Mason's re-test after reinstall
- **File:** [hexi-plugin-system-and-claude-plugin.md](Docs/hexi-plugin-system-and-claude-plugin.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-05 17:20 — Fixed the 6 long-standing Platform.WebUI.Tests failures; suite is 123/123 for the first time. All 6 traced to ONE commit, ce4098e "Resolve identity via AccountMember; claim flows stop provisioning accounts", which moved the identity edge off Account.OwnerUserId and deleted account auto-provisioning without touching a single test — neither test file mentioned AccountMember at all, and AccountResolverTests hadn't been edited since 8361596, several commits before the resolver was rewritten. Stale tests, not product bugs. Four just needed an AccountMember seed; two asserted deleted behaviour and were rewritten — notably PostDemand_..._provisions_a_buyer_account, whose stale assertion meant the path that ACTUALLY runs now (account-less demand + minted lead) had zero coverage while being load-bearing for the lead-capture work shipped earlier today. Two bonus catches: nothing tested the revocation path ce4098e exists for (drop the membership, access dies next request, OwnerUserId still set), and Returns_403_when_resolved_account_is_not_the_buyer was passing for the wrong reason — its "other" user had no membership, so it resolved to null and 403'd identically to the no-User-row test above it. Test-only diff, no production code touched
- **File:** [form-lead-capture-implementation.md](Docs/form-lead-capture-implementation.md)
- **Session:** d6631e24-35fd-4130-8ac9-ac2b19bfc81e
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Done

### 2026-08-05 11:15 — Built Hexi's plugin system and its first plugin. HexiPluginKit: static compiled-in plugins held to out-of-process discipline (PluginContext + contributed registrations, never the sessions/views); extension points are folder panels and tab accessories; adding a plugin is one line in AppContainer. HexiClaudePlugin: recent-sessions widget (reads only the 256KB head of ~/.claude/projects transcripts — they reach 45MB; summary line beats first user message; click copies claude --resume) and a per-tab status dot (orange working / green waiting / red permission-blocked / gray hooks-not-installed) fed by five Claude Code hooks whose sh -c $PPID is the claude pid Hexi already sees in the tab's process tree. Consent-gated, idempotent settings.json merge with backup. 46 tests green incl. hook script through real /bin/sh; widget verified in a launched build. Gotcha: target-level ARCHS in the uncommitted project.yml doesn't reach SwiftPM packages, so cold universal CLI builds fail — pass ARCHS globally on the command line, or move the setting to top-level. Mason live-tests the dot next
- **File:** [hexi-plugin-system-and-claude-plugin.md](Docs/hexi-plugin-system-and-claude-plugin.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-05 15:40 — Every form submission now mints a reachable Lead. Scope cut from the 2026-07-30 decision: Mason dropped the IP/user-agent/source-page hardening entirely ("we don't need their IP, we need the form and their contact info") — just require contact, mint on save. Choke point is FormLeadCapture called from FormSubmissionRepository BEFORE its SaveChanges, so lead + submission + LeadId commit atomically and all 11 call sites get it with zero changes; deliberately NOT best-effort, unlike the neighbouring parallel-form writes. Deny-list not allow-list, so a new form type is lead-bearing by default. ClaimResolution now adopts an anonymous email-matched lead before minting — that was the bug that would have duplicated the best leads (the ones who convert far enough to authenticate). Two corrections to the audit: /configure was worse than "persisted nowhere" — v3cfg.js sent all four contact fields as hardcoded null, the page never asked, so enforcing at the API would have broken Save outright and the capture UI had to be built; and the website proxy collapsed every non-2xx to a 502, so no validation message could ever reach the user. Mason caught a clean-architecture violation mid-build (I'd made PublicFormsController import SLYD.Infrastructure for one policy call) — moved IsLeadBearing to FormTypes in Domain. core 637/637, platform 116 pass + the same 6 pre-existing failures confirmed by stashing both repos, website 7/7
- **File:** [form-lead-capture-implementation.md](Docs/form-lead-capture-implementation.md)
- **Session:** d6631e24-35fd-4130-8ac9-ac2b19bfc81e
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Priority:** High
- **Status:** Follow-up Work

### 2026-08-05 — Surveyed plugin architecture options for Hexi: declarative script packs, static Swift package plugins, dynamic dylibs (rejected — library validation + ABI pain), out-of-process (deferred). Proposed two tiers: installable manifest+script packs for simple commands, and a compiled-in HexiPlugin protocol with a PluginContext of the existing service protocols for UI-changing plugins. Awaiting Mason's list of first real plugins before designing extension points
- **File:** [hexi-plugin-architecture-options.md](Docs/hexi-plugin-architecture-options.md)
- **Session:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-08-04 17:20 — Investigated backlog item 12 and proved EntityChangedHandler is structurally dead. First corrected my own bad call from earlier in the session: AddSlydMatching() IS wired in all three hosts (HangFire:62, WebUI:371, admin:99) — my "zero callers" claim came from grepping "AddMatching", a string that appears nowhere. Real defect: the handler hooks SavedChanges, which runs AFTER EF's AcceptAllChanges(), so every entry reads Unchanged and every IsModified reads false — its opening guard skips all entries on every save. Proved with a throwaway probe interceptor (INSERT: Added→Unchanged, UPDATE: Modified→Unchanged, IsModified=False), then deleted it. Went unnoticed because all seven EntityChangedHandlerTests assert only NotThrowAsync — zero enqueue coverage in a 311/311 green suite. Blast radius is narrower than it sounds: matching isn't broken, just never event-driven; the 15-min RefreshAll sweep is what actually picks up edits (RefreshStale's 1-min job only catches >1h-old or version-mismatched rows, so it misses fresh edits entirely). Fix is to capture in SavingChanges and enqueue in SavedChanges — with the trap that the interceptor is a singleton and can't hold the stash in a field
- **File:** [matching-engine-entitychangedhandler-dead-code.md](Docs/matching-engine-entitychangedhandler-dead-code.md)
- **Session:** 951270e3-cd9c-4187-b234-c353501d807d
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Priority:** High
- **Status:** Follow-up Work

### 2026-08-04 16:05 — Built /demands/{id}, the buy-side twin of /sell/submissions/{id}, so dashboard demand rows stop being dead ends. Core: CustomerUpdatedAt/ById on Demand + migration, and WithdrawByCustomer which deliberately bypasses Transition() — that helper stamps UpdatedById, FK'd to AdminUser, so a customer id there is a Postgres FK violation EF InMemory would swallow. Also widened EntityChangedHandler, which only fired on Added/State change and left match candidates stale for 15 min after any field edit. Two findings reversed the approved plan: ReVerify is fully editable (every matching job treats it identically to Open — it means "confirm this is still what you want", so it renders as a prompt not a lock), and Demand.Source is unusable for gating since /need never stamped it and the /configure auto-demand is also NEED-prefixed + Unknown, separated only by BuildId. Skipped the sell page's DbUpdateConcurrencyException catch — no concurrency token exists anywhere in DealOS, so it's dead code. Core 961/961 green, admin + platform build clean, 39 new tests pass; 6 platform failures confirmed pre-existing by stashing both repos and re-running at HEAD
- **File:** [demand-detail-edit-page.md](Docs/demand-detail-edit-page.md)
- **Session:** 951270e3-cd9c-4187-b234-c353501d807d
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-08-04 09:30 — Quitting Hexi left dev servers running. Two causes: terminateAll() had no caller (SwiftUI App has no termination hook), and SIGTERM to the shell alone leaves its jobs — each in its own process group — reparented to launchd. Added an AppDelegate that prompts "“node” is still running. Quitting will stop it." before quitting, and a ProcessTree that walks sysctl(KERN_PROC_ALL) from the shell pid and kills the whole tree SIGTERM-then-SIGKILL. Verified end to end against a launched build: Cancel leaves everything alone, Quit and Stop takes the shell and its background job with it
- **File:** [hexi-quit-terminates-running-commands.md](Docs/hexi-quit-terminates-running-commands.md)
- **Session:** 029dc7ac-4e16-4081-aaf6-c472d5db7b49
- **Directory:** /Users/masongill/Hexi/Packages/HexiUI
- **Status:** Done

### 2026-08-03 15:40 — Console was drowning in raw EF SQL dumps. Two compounding causes: the ~40-line Serilog block in appsettings.json is dead code (no UseSerilog() call, no package ref — so its "Microsoft": "Warning" override never applied, and the file + Seq sinks aren't running either), and the config that IS live had no EF override. Net effect was inverted — EF plumbing at Information got through while the ops-check runner's own useful per-run line sits at LogDebug and was suppressed. Silenced EF command/infrastructure logging (kept Migrations loud), raised Admin.* to Debug locally. Build clean. Serilog left as an open decision — wiring it up changes prod log format and shipping
- **File:** [admin-logging-ef-sql-noise.md](Docs/admin-logging-ef-sql-noise.md)
- **Session:** 9669b372-3dd9-4598-98b4-4c552569bf35
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Priority:** Low
- **Status:** Follow-up Work

### 2026-08-03 15:05 - Swept the unordered .First() pricing pattern: 20 display/sort sites (not ~15) now read a shared LatestPricing()/LatestPricePerHour() helper in core, with 5 unit tests pinning "newest row wins". Also fixed InstanceDetails to read the rate locked on InstanceRental rather than the server's current price - a deeper bug than ordering. Corrected two claims in the original doc. Held back RentalHistory (revenue fallback) per the no-billing constraint
- **File:** [provider-server-pricing-stale-first-row-bug.md](Docs/provider-server-pricing-stale-first-row-bug.md)
- **Session:** fdc3226f-77ce-4366-9023-007ba5ad0235
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Priority:** Medium
- **Status:** Follow-up Work

### 2026-08-03 14:20 — Deal flow: escrow account is no longer a blocker on Financing → Escrowed. Introduced advisory (warning) stage requirements — renders amber, never blocks, any admin may proceed. Bypass is stamped on the audit event + ops notification, and the counterparty notice no longer claims escrow positions exist on deals without one. 198 tests pass
- **File:** [deal-flow-escrow-gate-advisory.md](Docs/deal-flow-escrow-gate-advisory.md)
- **Session:** fdc3226f-77ce-4366-9023-007ba5ad0235
- **Directory:** /Users/masongill/Slyd-Platform/admin
- **Priority:** Medium
- **Status:** Follow-up Work

### 2026-08-03 12:10 — Built application-layer rate limiting for anonymous V3 intake, then REVERTED IT IN FULL in favour of an AWS WAF rate-based rule. Both repos verified back at their pre-change baselines. The app version needed a custom client-IP resolver, a cross-repo shared-secret handshake and Blazor circuit plumbing purely to reconstruct what the ALB already knows; WAF does the volumetric job natively with no application risk. Two real defects (spoofable XFF resolution, a cross-visitor IP leak via pooled HttpClient handlers) were caught by tests during the build and argued the same way
- **File:** [anonymous-intake-rate-limiting.md](Docs/anonymous-intake-rate-limiting.md)
- **Session:** d2a804d6-22cf-4461-98b9-3c249be2e4d6
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Priority:** High
- **Status:** Follow-up Work

### 2026-08-03 09:40 — Consolidated Slyd Platform backlog: swept every doc's "To Do Next" + the 24 open TaskTracking/Pending files, verified against live repo state (uncommitted core/admin work, unmerged website hotfix), produced 74 prioritized tasks P0→P3 with project + effort
- **File:** [slyd-platform-outstanding-work-backlog.md](Docs/slyd-platform-outstanding-work-backlog.md)
- **Session:** 6bd192ba-b6f6-4a25-8e3a-8ea00a856b7a
- **Directory:** /Users/masongill/Slyd
- **Priority:** High
- **Status:** Follow-up Work

### 2026-07-31 16:05 — Hexi Phase 1 MVP: renamed Helm→Hexi (Kubernetes collision), built the detection engine so a project's own npm scripts/make targets appear as buttons, plus filesystem package, HexiUI, and tabs; 109 tests, 5 commits
- **File:** [hexi-phase1-mvp.md](Docs/hexi-phase1-mvp.md)
- **Session:** 492f24b7-a5cd-44ef-8e0a-fbc2bb597744
- **Directory:** /Users/masongill/Hexi
- **Status:** Follow-up Work

### 2026-07-31 14:58 — Helm Phase 0 spike done: SwiftTerm-in-SwiftUI + PTY login shell working, and bidirectional cwd sync proven (shell reports via OSC 7/133, hooks injected through ZDOTDIR shims); repo scaffolded to the planned modular layout, 19 tests green
- **File:** [helm-phase0-terminal-spike.md](Docs/helm-phase0-terminal-spike.md)
- **Session:** 492f24b7-a5cd-44ef-8e0a-fbc2bb597744
- **Directory:** /Users/masongill/Helm
- **Status:** Follow-up Work

### 2026-07-30 — **[HIGH PRIORITY]** DECIDED: website form hardening — fix the server-to-server metadata hop (forward real client IP/UA/page URL), build the missing QuoteRequest + SolutionsInquiry form UIs (plumbing already exists), make email+name required first-class DTO fields validated at the API (Feedback exempt); no core changes, ships ahead of lead-minting
- **File:** [lead-capture-signal-audit.md](Docs/lead-capture-signal-audit.md)
- **Session:** a5859f81-5c32-4bc6-b1c2-375eb0494c30
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Priority:** High
- **Status:** Follow-up Work

### 2026-07-30 09:44 — Added "Coding Workflow Standards" to global ~/.claude/CLAUDE.md (production-engineer practices: read-before-write, reproduce-before-fix, incremental verified changes, non-negotiable build/test verification, git-diff self-review, re-diagnose when stuck)
- **File:** [global-claude-coding-workflow-standards.md](Docs/global-claude-coding-workflow-standards.md)
- **Session:** 8ed887bb-864d-4e00-b174-9e2b02df0f43
- **Directory:** /Users/masongill
- **Status:** Done

### 2026-07-28 21:40 — Horde Highway (playtest round 2): macOS fullscreen via SCALED, road hazards module, second boss (the Matriarch), directional zombie blocking, boost-economy fix. Found that mouse.set_pos is a no-op under SDL's dummy driver, which had invalidated every earlier aim-based measurement.
- **File:** [horde-highway-coop-zombie-driving-game.md](Docs/horde-highway-coop-zombie-driving-game.md)
- **Session:** 02e6dc52-b64e-484e-8fc0-838e3ad41055
- **Directory:** /Users/masongill/ClaudeTest/HWTH
- **Status:** Follow-up Work

### 2026-07-28 20:45 — Horde Highway: built a complete 2-player co-op zombie driving game (pygame, zero asset files — all sprites drawn procedurally, all SFX numpy-synthesized). 13 modules, flamethrower + sprite exporter added mid-build, boss arenas, 70fps at worst case.
- **File:** [horde-highway-coop-zombie-driving-game.md](Docs/horde-highway-coop-zombie-driving-game.md)
- **Session:** 02e6dc52-b64e-484e-8fc0-838e3ad41055
- **Directory:** /Users/masongill/ClaudeTest/HWTH
- **Status:** Follow-up Work

### 2026-07-28 20:05 — Links of the Hollow (opus5): APPLIED the quality-review fixes — 9 bugs (forecast seed, negative wind, alpha-less draws, stub camera, unseeded RNG, material rounding, roll-off-cliff, straight preview, OB text), 3 threading races, extracted screens.py from the Game god class, materials/difficulty dataclasses, measured perf wins. Verified by 3 auto-played rounds + all screens; pyflakes clean.

### 2026-07-28 19:20 — Links of the Hollow (opus5): full-codebase quality review (all 13 modules) — verified bugs: forecast seed mismatch, negative wind speed, RGBA on opaque draws, stubbed settle camera; plus threading races, god classes, per-frame allocation hotspots. Assessment only.
- **File:** [links-hollow-code-quality-review.md](Docs/links-hollow-code-quality-review.md)
- **Session:** 31abcef0-f1e0-4d0b-8a3d-21fcc0819e64
- **Directory:** /Users/masongill/ClaudeTest/opus5
- **Status:** Follow-up Work

### 2026-07-28 18:45 — Pulse Fairways: fixed intermittent macOS/Metal frame corruption (convert() cached surfaces, SCALED+vsync display mode, cached minimap/rain overlay)
- **File:** [pulse-fairways-golf-game.md](Docs/pulse-fairways-golf-game.md)
- **Session:** 4986f611-8ce1-41bd-b123-f7cc4ceadbd6
- **Directory:** /Users/masongill/ClaudeTest/fable5
- **Status:** Follow-up Work

### 2026-07-28 18:15 — Pulse Fairways playtest fix: aim arc now reflects live ring power + matches real physics exactly; strike grace zone (in-gate hits keep speed); per-club calibrated rollout line
- **File:** [pulse-fairways-golf-game.md](Docs/pulse-fairways-golf-game.md)
- **Session:** 4986f611-8ce1-41bd-b123-f7cc4ceadbd6
- **Directory:** /Users/masongill/ClaudeTest/fable5
- **Status:** Follow-up Work

### 2026-07-28 — **[HIGH PRIORITY]** AUDIT: lead capture signal trace — contact data collected on every intent surface but never becomes a Lead; /configure contacts persisted NOWHERE (data-loss bug); Automations engine seeds create-lead rules that never execute; recommends IOpsSubmissionNotifier as mint choke point
- **File:** [lead-capture-signal-audit.md](Docs/lead-capture-signal-audit.md)
- **Session:** a5859f81-5c32-4bc6-b1c2-375eb0494c30
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Priority:** High
- **Status:** Follow-up Work

### 2026-07-28 17:30 — Built "Pulse Fairways": complete 9-hole golf game in Python (pygame-ce), procedural everything — courses, physics, synthesized audio + soundtrack, weather forecast system, pulse-ring swing mechanic, sloped greens, tutorial
- **File:** [pulse-fairways-golf-game.md](Docs/pulse-fairways-golf-game.md)
- **Session:** 4986f611-8ce1-41bd-b123-f7cc4ceadbd6
- **Directory:** /Users/masongill/ClaudeTest/fable5
- **Status:** Follow-up Work

### 2026-07-28 — SHIPPED: Match engine procurement pass — under-covered BOM lines as demand source (synthetic-Demand projection, lot-mode section + radar + workspace deep-link w/ lot preselect); admin-only, zero core changes, 196 tests green
- **File:** [match-engine-bom-line-demand-source.md](Docs/match-engine-bom-line-demand-source.md)
- **Session:** 0f7c0174-fc17-4d62-975d-5c097ba9dbaf
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-22 12:33 — REVERSAL: stripped quote→lot creation (QuoteBacked, SourceQuoteId, SupplierAccountId, CreateLotFromQuoteAsync) — quotes stay as supplier-commitment data points; DealLineFulfillment kept; migration regenerated as AddDealLineFulfillment
- **File:** [deal-workspace-quote-builder-ui.md](Docs/deal-workspace-quote-builder-ui.md)
- **Session:** 0fe1f5b8-00f4-4b3d-81a5-492f38cfe93e
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-22 — Removed "Capital Efficient" ($500K/$55M claim) card from production /about via hotfix branch off main
- **File:** [about-page-remove-capital-efficient-card.md](Docs/about-page-remove-capital-efficient-card.md)
- **Session:** f3a6495e-7540-43cb-beb4-0285e8c4713d
- **Directory:** /Users/masongill/Slyd-Platform/website
- **Status:** Follow-up Work

### 2026-07-21 14:30 — Match engine must read under-covered BOM lines as a demand source (projection, NOT shadow Demand rows) — design decided; SHIPPED 2026-07-28 (see entry above)
- **File:** [match-engine-bom-line-demand-source.md](Docs/match-engine-bom-line-demand-source.md)
- **Session:** 0f7c0174-fc17-4d62-975d-5c097ba9dbaf
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 12:15 — Deal workspace: lead-time stat card (longest selected-quote lead time = critical path; falls back to longest received quote)
- **File:** [deal-workspace-quote-builder-ui.md](Docs/deal-workspace-quote-builder-ui.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branch f7df1e44-65a9-450d-8a99-adc7cc78930e)
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 11:45 — Contacts Deal Mode: portfolio board (contact → deals → BOM lines w/ RFQ state chips + selected-quote status), honors full filter bar
- **File:** [admin-contact-workspace-page.md](Docs/admin-contact-workspace-page.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branch f7df1e44-65a9-450d-8a99-adc7cc78930e)
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 11:00 — Contacts directory: "My Contacts" ownership toggle (OwnerAdminUserId == logged-in admin, resolved in the feature layer)
- **File:** [admin-contact-workspace-page.md](Docs/admin-contact-workspace-page.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branch f7df1e44-65a9-450d-8a99-adc7cc78930e)
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 10:15 — Procurement loop: manual deal creation, QuoteBacked lots (Claimed = not matchable), DealLineFulfillment partial coverage, supplier-party stamping, BOM-aware stage gates
- **File:** [deal-workspace-quote-builder-ui.md](Docs/deal-workspace-quote-builder-ui.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 21:00 — Deal workspace UI: quote builder at /v3/deal-flow/pipeline/{id} (expandable BOM lines, RFQ board w/ contact routing + state actions, quote intake + selection, curated Deal.Value roll-up)
- **File:** [deal-workspace-quote-builder-ui.md](Docs/deal-workspace-quote-builder-ui.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 20:15 — Quote builder data models: DealLineItem (BOM lines on Deal) + Rfq (per-supplier state machine, outreach order, contact routing) + SupplierQuote (revisions, doc link, SetNull selection)
- **File:** [deal-quote-builder-data-models.md](Docs/deal-quote-builder-data-models.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 01:45 — Leads Inbox reorg: Inbound/Outbound qualification tabs (distinct queues, per-tab columns + pill counts, login/artifact column on inbound)
- **File:** [crm-lead-pipeline-claim-rework.md](Docs/crm-lead-pipeline-claim-rework.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branch f7df1e44-65a9-450d-8a99-adc7cc78930e)
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 01:00 — Contacts directory filter bar: relationship tier pills, account dropdown, Needs/Selling intent filter with model search (person-attributed artifacts, match-engine liveness gate)
- **File:** [admin-contact-workspace-page.md](Docs/admin-contact-workspace-page.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-21 00:15 — Admin contact workspace page: /v3/crm/contacts/{id} (profile edit, relationship tier, deals via DealParty.ContactId, artifacts, login card, activity composer)
- **File:** [admin-contact-workspace-page.md](Docs/admin-contact-workspace-page.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 23:30 — Auto-mint fully dead: gate setup form → setup-request leads (CreateForUserAsync removed), MarketplaceIntakeService + SellClaim migrated to ClaimResolution, AccountProvisioning deleted
- **File:** [crm-lead-pipeline-claim-rework.md](Docs/crm-lead-pipeline-claim-rework.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 22:45 — CRM reader migration: AccountResolver/notifier/demand-staging/admin-link all resolve via AccountMember; removing a membership now actually revokes platform access
- **File:** [crm-lead-pipeline-claim-rework.md](Docs/crm-lead-pipeline-claim-rework.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 22:00 — CRM pipeline: auto-mint removed from claim paths (ClaimResolution: member→stamp, non-member→inbound lead), Lead capture fields + Qualified flag, inbox artifacts view, one-act conversion (account+contact+member+artifact attach)
- **File:** [crm-lead-pipeline-claim-rework.md](Docs/crm-lead-pipeline-claim-rework.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 21:15 — CRM: SellSubmission/LotDeposit ContactId links (intake person attribution), stub deal/contact detail pages, workspace deep-links; migrations applied to SLYD2
- **File:** [crm-account-member-table.md](Docs/crm-account-member-table.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 20:30 — Admin account workspace page: /v3/crm/accounts/{id} with edit panel, contacts (attach/detach + relationship tiers), members, deals w/ person attribution, activity composer, related counts
- **File:** [admin-account-workspace-page.md](Docs/admin-account-workspace-page.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 19:40 — CRM: Contact.RelationshipStatus closeness tier (Unknown→Champion) for marketing deal routing
- **File:** [crm-account-member-table.md](Docs/crm-account-member-table.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 19:10 — CRM: DealParty.ContactId per-role contact attribution on deals (deals stay account-held; person tagged per side)
- **File:** [crm-account-member-table.md](Docs/crm-account-member-table.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-20 18:30 — CRM multi-user accounts: AccountMember join table + OwnerUserId backfill migration + repository (Phase 1, step 1)
- **File:** [crm-account-member-table.md](Docs/crm-account-member-table.md)
- **Session:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-16 19:45 — DealOS polish: route-aware exclusive nav expansion, marketplace de-jargoning, Finance de-slop + machined metal slider
- **File:** [dealos-ui-polish-nav-finance-marketplace.md](Docs/dealos-ui-polish-nav-finance-marketplace.md)
- **Session:** 03cffc02-2e8e-447d-906d-8347231fd42b
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-07-16 18:30 — Nav edge-cast reflection system: [data-nav-cast] elements refract their color onto the sidebar glass (size/distance/brightness model, hover casts, top-rim refraction)
- **File:** [nav-edge-cast-reflection-system.md](Docs/nav-edge-cast-reflection-system.md)
- **Session:** 03cffc02-2e8e-447d-906d-8347231fd42b
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-07-16 16:00 — Moved DealOS CapacityListing + LotDeposit mutations out of the platform into core Application features (caller-owned-context staging pattern); +34 tests
- **File:** [dealos-mutations-into-core-features.md](Docs/dealos-mutations-into-core-features.md)
- **Session:** 8b33f0d9-476b-468b-a373-ed8e56d7f106
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-07-16 14:30 — DealOS nav/dashboard/deal-room UI refresh (collapsible nav, frosted active pill, lens switcher removed, readable audit fields, load fade-in)
- **File:** [dealos-nav-and-deal-room-ui-refresh.md](Docs/dealos-nav-and-deal-room-ui-refresh.md)
- **Session:** 03cffc02-2e8e-447d-906d-8347231fd42b
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-07-16 12:00 — Marketplace inset-glass mockup: listing bays (per-type sections w/ explainers), galaxies+suns background, edge roll-off
- **File:** [marketplace-mockup-inset-glass-iteration.md](Docs/marketplace-mockup-inset-glass-iteration.md)
- **Session:** faebe893-bd61-4000-a888-20fff111ccfa
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Follow-up Work

### 2026-07-16 11:30 — Grouped all uncommitted work into 11 logical commits (core/platform/admin)
- **File:** [auctions-disable-platform-admin.md](Docs/auctions-disable-platform-admin.md)
- **Session:** 297cd828-f460-49e8-8baf-7c1d74445902
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-16 10:00 — Disable auctions: Platform web (route removed) + Admin (coming-soon notice)
- **File:** [auctions-disable-platform-admin.md](Docs/auctions-disable-platform-admin.md)
- **Session:** 297cd828-f460-49e8-8baf-7c1d74445902
- **Directory:** /Users/masongill/Slyd-Platform/core
- **Status:** Follow-up Work

### 2026-07-14 15:30 — Match Engine "Link" action: bind a booking to the viewed capacity listing (audited)
- **File:** [demand-to-capacity-matching-pass.md](Docs/demand-to-capacity-matching-pass.md)
- **Session:** d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Done

### 2026-07-14 15:05 — Demand↔Capacity matching pass: bookings rank against live/forward capacity on match-engine
- **File:** [demand-to-capacity-matching-pass.md](Docs/demand-to-capacity-matching-pass.md)
- **Session:** d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Done

### 2026-07-14 14:10 — Marketplace-v3: Place Deposit → Request Booking (RSV- for hardware, BKG- for forward lots, no deposit)
- **File:** [marketplace-v3-request-booking-no-deposit.md](Docs/marketplace-v3-request-booking-no-deposit.md)
- **Session:** d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15
- **Directory:** /Users/masongill/Slyd-Platform/platform
- **Status:** Done

### 2026-07-14 12:49 — Hid counterparty identity from customer DealOS surfaces (admin unaffected)
- **File:** [hide-counterparty-identity-customer-surfaces.md](Docs/hide-counterparty-identity-customer-surfaces.md)
- **Session:** 276f1528-e953-4da9-bd82-394c87a78d93
- **Status:** Follow-up Work

### 2026-07-14 12:45 — DealOS V3 cross-repo audit (~65 findings) + 13 High/Critical task files
- **File:** [dealos-v3-cross-repo-audit.md](Docs/dealos-v3-cross-repo-audit.md)
- **Session:** 10e8aa3e-80d3-4a93-9a33-15e2c896b2de
- **Status:** Follow-up Work

### 2026-07-14 12:40 — Marketplace UI overhaul: inset-glass design ported to /marketplace-v3
- **File:** [marketplace-inset-glass-ui-port.md](Docs/marketplace-inset-glass-ui-port.md)
- **Session:** b13a711e-6622-434c-9082-fba21a5678db
- **Status:** Follow-up Work

### 2026-07-14 12:40 — Capacity deal shape + booking→deal pipeline (Operator ↔ Offtake)
- **File:** [capacity-deal-shape-booking-pipeline.md](Docs/capacity-deal-shape-booking-pipeline.md)
- **Session:** b13a711e-6622-434c-9082-fba21a5678db
- **Status:** Follow-up Work

### 2026-07-14 12:39 — Fixed detail-drawer overlapping page header on Source & Marketplace
- **File:** [dealos-drawer-header-zindex-fix.md](Docs/dealos-drawer-header-zindex-fix.md)
- **Session:** 276f1528-e953-4da9-bd82-394c87a78d93
- **Status:** Follow-up Work

### 2026-07-14 12:38 — Gated Deploy (operator) & Broker portals behind capability-request buttons
- **File:** [deploy-broker-access-gating.md](Docs/deploy-broker-access-gating.md)
- **Session:** 276f1528-e953-4da9-bd82-394c87a78d93
- **Status:** Follow-up Work

### 2026-07-14 12:36 — Auction-side gap analysis for DealOS V3 sealed-bid auctions
- **File:** [auction-side-gap-analysis-v3.md](Docs/auction-side-gap-analysis-v3.md)
- **Session:** b13a711e-6622-434c-9082-fba21a5678db
- **Status:** Follow-up Work

### 2026-07-14 12:34 — Fixed provider-server pricing card vs deploy-modal discrepancy ($1.50 vs $12.00)
- **File:** [provider-server-pricing-stale-first-row-bug.md](Docs/provider-server-pricing-stale-first-row-bug.md)
- **Session:** 6155554b-60a3-4d4e-ab5d-0d421e340c8e
- **Status:** Follow-up Work

### 2026-07-14 — Global Claude documentation workflow configured
- **File:** [global-claude-brain-workflow-setup.md](Docs/global-claude-brain-workflow-setup.md)
- **Session:** a71428d6-3667-4dc4-a155-a8398ca7269c
- **Status:** Done
