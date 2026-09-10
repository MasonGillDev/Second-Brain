# Hide counterparty identity from customer-facing Deal surfaces

**Project:** SLYD Platform (platform repo — Platform.WebUI)
**Date:** 2026-07-14
**Author:** 276f1528-e953-4da9-bd82-394c87a78d93

## What Was Done

Counterparty identity — the **names of the other parties on a deal** (e.g. "Mason LLC", "Jim Halpert") — was being shown to customers across the DealOS surfaces. That is privileged, **admin-only** information (CLAUDE.md rule #2 auth boundary). Removed it from every customer surface and enforced the boundary at the **service layer** (rule #9 — the response is the boundary), not just by hiding UI cells.

**Admin is unaffected.** Admin is a separate app (`/Users/masongill/Slyd-Platform/admin`) with its own `IDealPipelineFeatures` / `DealPartyItem` (model `admin/src/Admin.Application/Models/DealOS/PipelineModels.cs`, page `admin/src/Admin/Components/Pages/V3/DealFlow/Pipeline.razor`). It does not consume the customer `DealRoomService` / `DealOsDashboardService`, so it keeps full party visibility. Two Explore agents confirmed the isolation before implementation.

**Product decisions (confirmed with user via AskUserQuestion):**
- Deal-room whose-move chip → show **role, not name** ("Waiting on the operator — escrow at risk").
- Dashboard activity feed → **scrub** counterparty actor names too ("A counterparty uploaded a document").

**Service layer** (`src/Platform.WebUI/Services/`):
- `DealRoomService.cs`:
  - Removed `Counterparties` from the `MyDealRow` record + its population in `ListMyDealsAsync`; deleted the now-unused `CounterpartiesOn` method.
  - `BuildParties`: `WaitingOnSummary` now uses a new `RolePhrase(DealPartyRole)` helper ("the buyer"/"the operator"/…) instead of `blocking.AccountName`.
  - `BuildParties.Add`: `DealRoomParty.AccountName` is now the **real name only when `IsYou`**; every other party is masked to its role phrase. Real names are still used *internally* by `StatusFor` (keyed on `accountId`, not name) before masking, so status derivation is unchanged. (The parties rail isn't rendered in v1, but this keeps the payload clean for when it is.)
- `DealOsDashboardService.cs`:
  - Removed `Counterparties` from `DealOsPipelineRow` + the `AddOther` derivation in `BuildRow`.
  - `LoadFeedAsync`: added `AccountId` to the projection; when the activity actor falls back to the account name, show it only if `AccountId == myId`, else `"A counterparty"` (empty → `"SLYD"`, admin-user actors unchanged — they're SLYD ops).

**UI layer:**
- `MyDeals.razor` — removed the Counterparties `<th>` + `<td>`.
- `DealOsDashboard.razor` — removed the `.d-sub` block (counterparty sub-line).
- `CommandBar.razor` — removed the `cmdk-counter` span and dropped the counterparty term from the ⌘K search predicate (deals no longer discoverable by a counterparty's name).
- `DealRoom.razor` — no markup change; its whose-move chip now renders the role-based summary from the service.
- Dead CSS removed: `.counter` (MyDeals), `.d-counter`/`.d-sub` (DealOsDashboard), `.cmdk-counter` (CommandBar — moved its `flex:1` spacer role to `margin-left:auto` on `.cmdk-val` to keep the value right-aligned).

Build passes (0 errors); grep confirms zero remaining `.Counterparties` references in Platform.WebUI. Not committed/pushed (network-operations boundary — human pushes).

Plan file: `/Users/masongill/.claude/plans/snazzy-booping-hopcroft.md`.

## To Do Next

- Manual verification not yet run. Sign in as a customer on a multi-party deal and check: `/deals` (no Counterparties column), `/deals/{id}` (chip reads "Waiting on the operator …"), dashboard (no counterparty names; feed shows "A counterparty …"), ⌘K (no counterparty text, and typing a counterparty name doesn't surface the deal). Confirm admin Pipeline still shows full party names.
