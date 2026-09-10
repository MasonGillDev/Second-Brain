# Disable Auctions on Platform Web UI + Admin Portal

**Project:** SLYD Platform (platform web + admin)
**Date:** 2026-07-16
**Author:** 297cd828-f460-49e8-8baf-7c1d74445902
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

Took auctions offline in two repos without deleting any auction logic — only the code that *exposes* the pages was disabled, so it's trivially reversible.

### Platform web UI (`/Users/masongill/Slyd-Platform/platform`) — users can't reach auctions
Goal: users shouldn't even be able to get to the page. Chosen approach: remove the route (direct URL → Blazor 404), not a redirect.
- `Components/Pages/DealOS/Auctions.razor` — commented out `@page "/auctions"`.
- `Components/Pages/DealOS/AuctionRoom.razor` — commented out `@page "/auctions/{AuctionId:guid}"`.
- `Components/Pages/DealOS/AuctionNew.razor` — commented out `@page "/auctions/new"`.
- `Components/Layout/Nav/UnifiedNavMenu.razor` — commented out the "Auctions" nav link.
- `Components/Pages/DealOS/SellSubmissionDetail.razor` — commented out the "Put to auction" disposition radio (user asked to hide it too, so inventory can't be routed into auctions).

All component `@code`, services (`IAuctionService`, `AuctionSellerService`, `IComplianceService`), and `.razor.css` left intact.

### Admin portal (`/Users/masongill/Slyd-Platform/admin`) — "coming soon" notice
- `Components/Pages/V3/Intake/AuctionsAdmin.razor` — added a "Auctions are coming soon" notice; wrapped the entire ops console in `@if (_auctionsEnabled)` with a new `private bool _auctionsEnabled = false;` field; `OnInitializedAsync` now early-returns (skips `LoadAsync()`) while disabled to avoid needless service calls.
- Nav link kept visible per user's choice (NavRegistry.cs line 41 unchanged) — clicking "Auctions" shows the notice.

### Decisions (confirmed with user)
- Platform direct-URL behavior: **remove route → 404** (most literal "remove the code that exposes the page").
- Admin nav link: **keep visible**, page shows notice.
- Platform "Put to auction" seller disposition: **hide it too**.

### Verification
- `dotnet build src/Platform.WebUI/Platform.WebUI.csproj` → Build succeeded, 0 errors.
- `dotnet build src/Admin/Admin.csproj` → Build succeeded, 0 errors.

### Committed (2026-07-16)
All uncommitted work across the three repos was grouped into 11 logical commits (the auction changes were only part of a larger matching/deal-flow batch that was also sitting uncommitted):
- **core** — new branch `feat/capacity-matching-pass` off `main`: (1) MessagePack 2.5.302 security pin, (2) forward-lot booking demand staging, (3) capacity matching pass (6 scorers + service + worker). No auction changes in core.
- **platform** — on `development`: (1) *Take auctions offline on the customer surface* `6629b04`, (2) mask counterparty identity, (3) forward-lot booking replaces deposit/wire, (4) newest ProviderServerPricing fix, (5) MatchController test wiring.
- **admin** — on `development`: (1) *Show 'coming soon' notice on the auctions console* `b0390c5`, (2) Match Engine capacity mode + booking Link action, (3) matching test wiring.

Nothing pushed. core landed on a branch (was on default `main`; library-repo convention = branch from `main`).

## To Do Next
- Decide whether core commits should stay on `feat/capacity-matching-pass` or fast-forward onto `main`.
- Push when ready: core (new branch), platform + admin (`development`).
- Update TaskTracking (if a matching task exists) and close any related GitHub issue.
- To re-enable auctions: uncomment `@page` directives + nav link + disposition radio (platform); set `_auctionsEnabled = true` (admin).
