# Slyd Platform — Outstanding Work Backlog

**Project:** Slyd Platform (core / admin / platform / website / component-library)
**Date:** 2026-08-03
**Author:** 6bd192ba-b6f6-4a25-8e3a-8ea00a856b7a
**Directory:** /Users/masongill/Slyd

## What Was Done

Swept every `## To Do Next` section across `~/Brain/Docs/`, cross-referenced against
`~/Slyd-Platform/TaskTracking/Pending/` (24 open task files), and verified live repo
state (`git status` / branches / tags) so the list reflects what is *actually* still
outstanding rather than what was outstanding when each doc was written.

**Repo state at time of writing (2026-08-03):**

| Repo | Branch | Uncommitted | Notes |
|---|---|---|---|
| core | `feat/crm-accounts-quote-builder` | 8 files (DealLineFulfillment + migration) | 1 commit ahead of `origin/main`; local tags stop at `v0.2.9` |
| admin | `feat/crm-accounts-quote-builder` | 22 files (CRM workspaces, match engine, quote builder UI) | pinned to core `0.2.11` |
| platform | `feat/crm-accounts-quote-builder` | clean | pinned to core `0.2.11` |
| website | `development` | 1 file (`Configure.razor`) | `hotfix/remove-capital-efficient-card` pushed but **NOT merged to main** |
| component-library | `main` | clean | — |

Nothing is unpushed on any branch — the outstanding risk is *uncommitted*, not unpushed.

**Effort key:** XS ≈ under 1h · S ≈ 1–3h · M ≈ half-day to 2 days · L ≈ 3–5 days · XL ≈ 1–2 weeks

---

## P0 — Critical (data loss, security, or blocking everything downstream)

| # | Task | Project | Effort | Why now |
|---|---|---|---|---|
| 1 | **Commit + tag + publish the core release train.** 8 uncommitted core files (`DealLineFulfillment`, `AddDealLineFulfillment` migration) and 22 uncommitted admin files sitting on `feat/crm-accounts-quote-builder`. Core must be committed → tagged → published before admin/platform CI can consume it. | core → admin | S | Blocks items 2, and every CRM/quote-builder item below. Largest single pile of unversioned work. |
| 2 | **Run the SLYD2 rollback + new-migration apply.** Two permission-gated commands documented in `deal-workspace-quote-builder-ui.md` (2026-07-22 update). Mason must run these personally. | core / DB | XS | Migration was regenerated after the quote→lot reversal; the DB is out of sync with the branch. |
| 3 | **Fix the `BuildIntake` data-loss bug.** `/configure` contacts are persisted **nowhere** — add contact columns to `DeploymentBuild` or write a parallel `FormSubmission` in `ConfigureController`. | core | M | Actively losing real contacts every day it ships later. Standalone value regardless of the lead-minting work. |
| 4 | **Secure the Hangfire dashboard** — currently unauthenticated on `ListenAnyIP(8082)`. (`2026-07-13-secure-hangfire-dashboard.md`, complexity 3) | platform | S | Open admin surface on a public port. |
| 5 | **Gate capacity-listing publication** — any authenticated user can self-declare Operator and publish bookable capacity. (complexity 4) | core / platform | M | Unauthorized supply can enter the marketplace and be booked. |
| 6 | **Server-side single-line valuation** — hardware-sales intake persists client-supplied valuations verbatim. (complexity 4) | core / platform | M | Client controls a number that drives deal value. |
| 7 | **Rate-limit anonymous V3 intake POSTs.** **Still open** — approach changed 2026-08-03 to an AWS WAF rate-based rule on the website ALB; an application-layer build was completed then reverted in full. Now an infra task, not a code one. Spec in `Slyd-Platform/docs/waf-rate-limiting.md`; reasoning in [anonymous-intake-rate-limiting.md](anonymous-intake-rate-limiting.md). | **infra (AWS)** | S | No protection on any anonymous intake endpoint. |
| 8 | **Website form hardening — DECIDED 2026-07-30, ships ahead of lead-minting, no core changes.** Three parts: (a) fix the server-to-server metadata hop so the website forwards real client IP / UA / originating page URL (Blazor Server — capture from the circuit's `HttpContext` at circuit start); (b) promote `ContactEmail`/`ContactName` to required first-class `PublicFormRequest` DTO fields validated at the API for lead-bearing form types (`Feedback` exempt); (c) build the missing **QuoteRequest** and **SolutionsInquiry** form UIs — endpoints and service methods already exist, nothing calls them. | website (+ platform API validation) | L | Already decided and scoped. Platform currently records the *website server's* identity, not the visitor's. |

---

## P1 — High (correctness bugs affecting money, matching, or production availability)

### Matching / deal-flow correctness

| # | Task | Project | Effort |
|---|---|---|---|
| 9 | **`/need` submissions 404 in production** — intake route trapped behind the matching host gate. (complexity 3) | platform | S |
| 10 | **`/need` quantity unit bug** — collected as NODES, stored and matched as GPUs. (complexity 4) | core / platform | M |
| 11 | **Admin `/api/match` 500s** — `IBackgroundJobClient` injected but never registered. (complexity 2) | admin | XS |
| 12 | **`EntityChangedHandler` never fires** — event-driven match refresh is dead code. (complexity 5) | core | M |
| 13 | **BKG- booking demands silently consumed** by hardware allocation and assembly flows. (complexity 4) | core | M |
| 14 | **Admin formation paths don't stamp `DealType`/`DemandSource`** — deals and demands persist as `Unknown`. (complexity 3) | admin | S |
| 15 | **`CommittedRatio` go-live bump races** — capacity can be double-sold. Needs a concurrency token. (complexity 6) | core | M |
| 16 | **Auction close has no concurrency protection** — overlapping runs double-award. Needs `[DisableConcurrentExecution]` on the close job + rowversion/xmin token on `Auction`, per-auction try/catch with audit-before-transition ordering, and an interleaved-close test. (complexity 6) | core | M |

### Infrastructure / Cloudflare

| # | Task | Project | Effort |
|---|---|---|---|
| 17 | **DNS deletion uses the wrong record ID** — passes instance GUID instead of `instance.DNSId`; Cloudflare returns 1001 `method_not_allowed`. One-line fix in `DeleteLxdInstance.cs:167`. (complexity 3) | platform | XS |
| 18 | **ASN JSON deserialization error** in Server Location Map. (complexity 2) | platform | XS |
| 19 | **Handle Cloudflare tunnel active-connections error** on deletion. (complexity 4) | platform | M |
| 20 | **Update Cloudflare Access application + policies cleanup logic.** | platform | M |

### Pricing display integrity

| # | Task | Project | Effort |
|---|---|---|---|
| 21 | **Sweep the unordered `.First()`/`.FirstOrDefault()` pricing pattern** — ~15 remaining display/sort sites can show a stale price inconsistent with the card. Start with the two **possibly billing-relevant** core sites: `CustomerInstanceFeatures.cs:1242` and `CustomerView/InstanceDetails.razor:1622`. Then customer-facing displays, sorts, provider-side displays (full list in `provider-server-pricing-stale-first-row-bug.md`). Skip `ServerCardBak.razor` (dead). Optional systemic alternative: add `OrderByDescending(p => p.CreatedAt)` to the `ProviderServerPricing` includes in `ProviderServerRepository` — note this does **not** cover `ServerMatchingService`-loaded servers. | platform + core | M |

### Website

| # | Task | Project | Effort |
|---|---|---|---|
| 22 | **Open + merge the `hotfix/remove-capital-efficient-card` PR.** Branch is pushed but unmerged — the $500K/$55M "Capital Efficient" claim is **still live on production `/about`**. PR URL in the doc; merging triggers the prod deploy. Verify at slyd.com/about, then delete the local branch. | website | XS |

---

## P2 — Medium (the lead-minting spine)

This is the biggest coherent body of work and has a hard dependency order. Item 24
blocks 25–30.

| # | Task | Project | Effort |
|---|---|---|---|
| 23 | *(P0 item 3 — `BuildIntake` fix — is step 1 of this chain; listed above because it stands alone.)* | — | — |
| 24 | **Decide the identity spine: `Lead` vs `Contact`.** Blocks everything below it. | core | M (decision + design) |
| 25 | **Add an intent tier to `Lead`** (deposit pledge ≫ need intake ≫ waitlist) so the inbox stays workable once anonymous surfaces start minting. | core + admin | M |
| 26 | **Add lead→artifact linkage** (`LeadId` on artifacts, or a join table). Anonymous leads are useless in the inbox without it. | core + admin | M |
| 27 | **Teach `ClaimResolution` email-matching** before minting, and stamp `UserId` onto matched anonymous leads — prevents the best leads from doubling. | core | M |
| 28 | **Reconcile `DisplayId` minting** — pick the race-safe random scheme. Overlaps with the auction-side ask for a shared `MAX(suffix)+1` + retry-on-unique-violation helper in core, consumed by auction + admin call sites. Do it once, for both. | core | M |
| 29 | **Build the notifier lead sink** for the six anonymous surfaces. Recommended choke point is `IOpsSubmissionNotifier`. Decide core-vs-web placement first. | core | L |
| 30 | **Backfill** from `FormSubmission` + `SellSubmission` + `LotDeposit` — **last**, once dedupe is proven. Alias mapping (`name`, `companyName`) only matters here, for interpreting historical rows. | core | M |

**Open questions parked on this chain:** Automations runtime (actually execute
`TriggerJson`/`ActionJson`) vs. hardcoded mapping — the engine currently seeds
create-lead rules that never execute. And soft identity capture on preview endpoints,
which is a product decision, not just engineering.

---

## P2 — Medium (CRM / quote builder / DealOS feature work)

| # | Task | Project | Effort |
|---|---|---|---|
| 31 | **Supplier capability tags on `Account` + "blast out" bulk RFQ creation.** Explicit sales ask, deferred until workspace v1 landed — which it now has. | core + admin | L |
| 32 | **Manual deal creation entry point** — the workspace currently opens existing deals only. | admin | M |
| 33 | **Quote document upload UI** — `SupplierQuote.DealDocumentId` exists with no UI behind it. | admin | M |
| 34 | **Cross-deal quote price-book page** (`/v3/deal-flow/quotes`) — filter by hardware, $/unit normalization, price-over-time chart, won/lost dimension. | admin | L |
| 35 | **On-Listed alert fast-follow** — when a lot publishes, evaluate open BOM lines via the procurement projection and write Activity rows on covered deals. Touches core `MatchAlertJob`, so it carries the commit→tag→publish chain. | core + admin | M |
| 36 | **Post demands & sell hardware from the DealOS Marketplace** (`2026-07-13-marketplace-demand-sell-intake.md`, **In Progress**, complexity 5). | platform | M |
| 37 | **Migrate `MarketplaceIntakeService` off `AccountProvisioning`, then delete `AccountProvisioning`.** | platform | S |
| 38 | **Update platform claim-page copy** (`NeedClaim` etc.) from "account provisioned" to "a rep will set up your organization". | platform | XS |
| 39 | **Stamp `Lead.Name`/`Phone`/`CompanyName` from the intake form's contact fields** — currently only `User.Email` is captured at claim. | platform + core | S |
| 40 | **Wire "attach unclaimed submissions" preview into `AddMember`** (the backfill from the phase plan) — now unblocked, since claim paths no longer auto-mint. | admin | M |
| 41 | **Route `PublicMarketplaceLotController.PlaceDeposit` through `ILotDepositService.AddDepositAsync`** — the last inline `LotDeposit` construction, and the last rule-drift risk on deposits. The service was deliberately designed for it (nullable accountId + contact, `allowSpotListed: false`). | platform | S |
| 42 | **Contact merge/dedup tooling** — email uniqueness is still unenforced. Build when real duplicates appear. | admin | M |
| 43 | **Invite flow** (claim-token pattern) — prevents account fragmentation. | core + platform | L |
| 44 | **Retire `OwnerUserId`** now that readers resolve via `AccountMember`. | core | M |
| 45 | **Retire the Accounts drawer** once the workspace page is proven. | admin | S |
| 46 | **Manual verification of counterparty hiding** — never run. Sign in as a customer on a multi-party deal and check `/deals` (no Counterparties column), `/deals/{id}` (chip reads "Waiting on the operator…"), dashboard (no counterparty names; feed reads "A counterparty…"), ⌘K (no counterparty text, and typing a counterparty name doesn't surface the deal). Confirm admin Pipeline still shows full party names. | platform | S |

---

## P2 — Medium (auctions — currently disabled in prod)

Auctions are switched off (platform route removed, admin shows a coming-soon notice).
To re-enable: uncomment the `@page` directives + nav link + disposition radio in
platform, and set `_auctionsEnabled = true` in admin. Items 15–16 above are the
blocking correctness work; the rest is only worth doing if auctions come back.

| # | Task | Project | Effort |
|---|---|---|---|
| 47 | **Canonicalize `AuctionCommitment.Compute`** (InvariantCulture, fixed scale) with a migration/verification story — must land *before* any `HasPrecision` sweep. | core | M |
| 48 | **Add `Deal.AuctionId`**, replacing the `(BuyerAccountId, Value)` heuristic. | core | S |
| 49 | **Decide broker-commission policy for auctioned submissions**; wire `BrokerAttributionService` into award if commissions should accrue. | core | M (decision + wiring) |
| 50 | **Admin auction follow-ups:** Draft state handling, timezone marker, two-click confirm on Cancel, doc-presence check before Verified. | admin | M |

---

## P2 — Medium (audit debt / architectural cleanup)

| # | Task | Project | Effort |
|---|---|---|---|
| 51 | **Fix the `[WIP]` findings from the DealOS V3 cross-repo audit** (§4): booking-guard aggregate semantics vs. comment, `termMonths` validation, `Deal.Type`/`CapacityKind` mutability, `CapacityKind` null-vs-Unknown, `DealType.Hardware` test pin, `DealShapeTests` round-trip, admin Unknown shape label. | core + admin | M |
| 52 | **Work the remaining High task files in `TaskTracking/Pending/`** in the audit report's suggested order. *(Most are itemized individually above — this line covers the tracking hygiene: reconciling which are genuinely still open.)* | all | S |
| 53 | **Decide on GitHub issue creation** for the 13 audit task files — the target repo for each is noted per task. | all | S |
| 54 | **File the Medium/Low audit tiers as tasks** — data integrity, redundancy consolidation, hygiene sweeps still live only in the report. | all | S |
| 55 | **Remaining audit offenders (High) not yet touched:** `ProviderRevenueController` → `IProviderFinancialsFeatures`/`IUnifiedBillingService`; `LxdServerStatsJob`; `ServerLocationMap.razor.cs` (DbContext in a Razor component); `AuctionSellerService` → route through the existing `IAuctionService`. Plus DealOS feature gaps for compliance status + intake (`ComplianceService`, `MarketplaceIntakeService`). | platform + core | L |
| 56 | **Verify the `2026-07-13-core-release-train-deal-shape.md` task (v0.2.10) is genuinely complete** and move it to `Complete/`. Admin and platform are both pinned to `0.2.11`, so it almost certainly shipped — but local core tags stop at `v0.2.9`, so confirm before closing. | core | XS |
| 57 | **Decide branch strategy for core:** stay on `feat/capacity-matching-pass` lineage or fast-forward onto `main`. Core is 1 commit ahead of `origin/main` with more uncommitted on top. | core | XS (decision) |

---

## P3 — Low (UI polish, hygiene, offered-but-unclaimed)

| # | Task | Project | Effort |
|---|---|---|---|
| 58 | **Marketplace mockup: square corners in the user's browser.** Blocked on info — need the browser name and what the reverted fix broke before another attempt. | platform | S |
| 59 | **Port the inset-glass "bay" design into `GatedMarketplace.razor`** if approved. Note the earlier port deliberately cut galaxies/suns; decide whether bays carry those over. | platform | M |
| 60 | **Nav edge-cast guardrails:** full `prefers-reduced-motion` suppression (currently only kills transitions) and a global kill switch (`slydNavCast.disable()`). | platform + component-library | S |
| 61 | **Strip the now-unused `.tabs .gate` CSS** from marketplace. | platform | XS |
| 62 | **Audit tab numeric formatting** — `AmountUsd` and friends render raw; could add key-name-based money/kW formatting. | platform | S |
| 63 | **Broker "Submit a deal" drawer `top: 160px` hack** — its own comment admits it's pinned to the header's rendered height. Convert to `top: 0` + the `1000/1010` z-index tier so all three drawers behave identically. Offered to Mason, never answered. | platform | XS |
| 64 | **API-layer gate on `DeploySurfaceService.ListSpareCapacityAsync`** — currently UI-gated only. CLAUDE.md rules #2/#9 say enforce at the API layer. Offered, never answered. | platform | S |
| 65 | **Sweep "demand" out of service-layer result messages** (user-facing jargon). | platform | S |
| 66 | **Move the component-library commit off local `main`** to a branch/PR, per repo rules. | component-library | XS |
| 67 | **Enhance main dashboard provider tab with reusable panels** (In Progress). | platform | M |
| 68 | **Fix usage history table data collection** (complexity 5). | platform | M |
| 69 | **Improve compute marketplace navigation responsiveness** (complexity 3). | platform | S |
| 70 | **Fix instance details scroll jump during status polling** (In Progress). | platform | S |
| 71 | **Keep endpoint manager visible on instance details** (complexity 3). | platform | S |
| 72 | **Implement or permanently remove the missing `PlatformLayout` JS functions** — `initializeOrganizations()` and `initializeSidebarCollapse()` are commented out at lines 225–226 to stop a crash. Decide which. (complexity 3) | platform | S |
| 73 | **Finance seed data** — the $2.5K deal / $28 fee toy values are a data problem, not a UI one. Replace with realistic seeds. | platform | XS |
| 74 | **Commit the uncommitted `website/Components/Pages/Configure.razor` change** (or discard it) — it's been sitting on `development` unexplained, and it's the same file the `BuildIntake` data-loss fix touches. | website | XS |

---

## Suggested order of attack

1. **Unblock the pipeline** (items 1, 2, 57) — nothing else in core/admin can ship until the release train runs. Half a day.
2. **Stop the bleeding** (items 3, 22) — the data-loss bug and the live false claim on `/about`. Both small, both compounding.
3. **Close the security holes** (items 4, 5, 6, 7) — all four are P0 and none exceed M.
4. **Website form hardening** (item 8) — already decided, no core dependency, ships in parallel with anything.
5. **The cheap High-priority bug batch** (items 9, 11, 14, 17, 18) — five bugs, all XS/S, high production impact per hour spent.
6. **Then pick a lane:** the lead-minting spine (24–30, gated on the item 24 decision) or the CRM/quote-builder feature set (31–35, which sales is asking for).

## To Do Next

- Mason to confirm the P0 ordering and whether the lead-minting spine or the sales-facing
  quote-builder work takes the next big block of time.
- Item 24 (`Lead` vs `Contact` identity spine) is a decision, not an implementation — it
  needs an hour of thought before seven downstream tasks can start.
- Items 58 (browser name for the square-corners bug), 63, and 64 are blocked on Mason's
  answer, not on engineering time.
