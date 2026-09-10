# DealOS V3 Cross-Repo Audit (core / platform / admin / website)

**Project:** SLYD Platform — DealOS V3
**Date:** 2026-07-14
**Author:** 10e8aa3e-80d3-4a93-9a33-15e2c896b2de

## What Was Done

Comprehensive audit of all DealOS V3 functionality across the four repos (`core`, `platform`, `admin`, `website`), run as six parallel deep passes: core domain/persistence, core services/matching/pricing, admin surfaces, platform surfaces, website V3 intake flows, and cross-repo seams (version drift, contract drift, enum drift, duplicated business logic, RSV-/BKG- prefix usage). Scope decisions made with Mason up front: core's uncommitted `AddCapacityDealShape` working tree was **in scope** (findings tagged [WIP]), and the deliverable was a findings report only — no fixes applied, no GitHub issues auto-created.

**~65 deduplicated findings, all with file:line evidence.** Full report: `/Users/masongill/Second Brain/memory/docs/2026-07-13-dealos-v3-cross-repo-audit.md` (severity-ranked, includes a verified-clean list and a prioritized execution order).

Headlines:
- **Critical release blocker:** platform and admin committed code references core symbols that exist only in core's uncommitted working tree / unpublished post-tag commits; CI pins SLYD.* 0.2.9 with `UseLocalCore=false`, so consumer CI builds cannot compile and migration bundles can't deliver the new columns. Fix is sequencing: core commit → tag/publish v0.2.10 → bump both pins in one window.
- **Wrong in production today (High):** /need intake 404s behind the `/api/match` host gate; `EntityChangedHandler` match refresh is dead code (post-save hook reads an already-accepted ChangeTracker — verified empirically); auction close has no concurrency guard (double-award); admin `/api/match` 500s on unregistered `IBackgroundJobClient`; unauthenticated Hangfire dashboard on :8082; nodes-vs-GPUs unit bug on /need (~8× demand understatement); zero rate limiting on anonymous intake POSTs at both hops; BKG- demands swallowed by hardware allocation/assembly; missing DealType/DemandSource stamps in admin formation; CommittedRatio go-Live race (capacity double-sell); client-supplied valuations persisted on single-line sell; self-declared Operators could publish bookable listings (this last one has since been fixed — see task file).
- Notable data-integrity theme: count-based DisplayId minting (`COUNT(prefix)+1`, copied at ~12 admin sites + core) deterministically breaks forever after any hard delete; `DemoSeedJob` purge does hard-delete organic demands.
- Verified clean (worth trusting): website↔platform DTO contracts match field-for-field; no consumer parses DisplayId prefixes; migration↔snapshot consistent in the WIP; admin state-machine discipline; party gating / cost-basis hiding on platform.

**Task files created** for the Critical + 12 Highs in `/Users/masongill/Slyd-Platform/TaskTracking/Pending/2026-07-13-*.md` (13 files: `core-release-train-deal-shape`, `fix-need-submit-host-gate-404`, `fix-entitychangedhandler-dead-code`, `auction-close-concurrency-guard`, `fix-admin-matchcontroller-di`, `gate-capacity-listing-publication`, `secure-hangfire-dashboard`, `fix-need-quantity-units-nodes-vs-gpus`, `rate-limit-anonymous-intake`, `protect-booking-demands-from-hardware-flows`, `stamp-dealtype-demandsource-admin-formation`, `committedratio-concurrency-token`, `server-side-single-line-valuation`). GitHub Issue fields deliberately left blank pending Mason's go-ahead (issues span four repos). Also added a memory pointer (`reference_dealos_v3_audit_2026_07.md`) in the project memory index.

Status update since filing: `gate-capacity-listing-publication` has been implemented (operator verification gate + per-listing approval state) and is marked completed in its task file pending manual verification and the coordinated v0.2.10 deploy — its Changes Made section is the detailed record.

## To Do Next
- Fix the [WIP] findings in core before committing (audit §4: booking-guard aggregate semantics vs comment, `termMonths` validation, `Deal.Type`/`CapacityKind` mutability, `CapacityKind` null-vs-Unknown, DealType.Hardware test pin, DealShapeTests round-trip, admin Unknown shape label).
- Run the release train (core commit → tag v0.2.10 + efbundle → bump platform/admin pins) — now also carries the capacity-listing approval migration.
- Work the remaining 11 High task files in `TaskTracking/Pending/` (suggested order in the audit report's Next Steps).
- Decide on GitHub issue creation for the 13 task files (which repo each issue belongs in is noted per task).
- Medium/Low tiers (data integrity, redundancy consolidation, hygiene sweeps) remain in the report — not yet filed as tasks.
