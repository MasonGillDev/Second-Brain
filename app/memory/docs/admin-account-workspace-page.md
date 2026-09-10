# Admin Account Workspace Page (/v3/crm/accounts/{id})

**Project:** SLYD admin (V3 console)
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branched session c91b9fc3-73e9-4d38-a31d-50775c4adf31)
**Directory:** /Users/masongill/Slyd-Platform/core (work spans ../admin; UseLocalCore=true picks up uncommitted core changes)

## What Was Done

### 2026-08-06 — account name is now the entry point to the workspace

Clicking the account **name** in the Accounts directory table now navigates to
`/v3/crm/accounts/{id}`. Previously the only way in from a row was a hover-only
external-link icon sitting next to the name — discoverable only if you knew to
hover, which is why it went unnoticed.

Change is confined to `Accounts.razor` + its scoped CSS:
- Row name wrapped in `<a class="name-link" href="/v3/crm/accounts/@row.Id">`;
  the redundant per-row `ws-link` icon removed (the name replaces it exactly).
- `@onclick:stopPropagation="true"` on the anchor so the name click does **not**
  also fire the row's `SelectAsync` — row-click-opens-drawer is unchanged for
  every other part of the row. Same guard the removed icon used, and the same
  pattern the CRM-rep `<td>` already uses.
- `.name-link` inherits row text color, underlines + shifts to `--slyd-primary`
  on hover. The drawer `h3` keeps its `ws-link` icon; that rule's now-dead
  `opacity: 0` / `.clickable-row:hover` reveal pair was simplified out since the
  h3 was the only remaining consumer and it was always visible anyway.

Note on branch history: this work targeted `development`, but the workspace page
had not landed there yet — PR #49 (`feat/crm-accounts-quote-builder`) was still
open despite being pushed. Merged first (be79593), then made the change. Worth
checking `gh pr view` rather than trusting "I merged it" when a pull reports
already-up-to-date.

Build clean (0 errors). Not clicked through in a running app.

### 2026-07-20 — initial build

Built the full-page account workspace — the "one place to manage a counterparty"
from the CRM robustness plan. Route `/v3/crm/accounts/{AccountId:guid}`, linked
from the Accounts directory (row hover icon + drawer header icon).

Clean architecture per Mason's instruction: **no DbContext in razor**. The page
DIs three feature interfaces:
- `IAccountWorkspaceFeatures` (new) — workspace read model + all new mutations
- `IAccountDirectoryFeatures` (existing) — activity composer reuses LogActivityAsync
- `IComplianceAdminFeatures` (existing) — compliance changes ride the dedicated
  KYC mutation path (ADR 0008 §5) so verification stays one audited act

### New files (admin repo)
- `src/Admin.Application/Models/DealOS/AccountWorkspaceModels.cs`
- `src/Admin.Application/Interfaces/Features/DealOS/IAccountWorkspaceFeatures.cs`
- `src/Admin.Application/Features/DealOS/AccountWorkspaceFeatures.cs`
- `src/Admin/Components/Pages/V3/Crm/AccountWorkspace.razor` + `.razor.css`
- `tests/Admin.Tests/Features/V3/Crm/AccountWorkspaceFeaturesTests.cs` (17 tests)
- DI registration in Admin.Application/DependencyInjection.cs; ws-link styles
  appended to Accounts.razor.css; links added in Accounts.razor.

### Page composition (all four extras Mason approved)
- Header: name, pills (type/stage/tier/compliance), CRM rep, created; Edit Info
  panel (name/displayId/type/tier/stage + compliance select) — diff-based save,
  audit `account.info.updated` + Activity row; no-op saves write nothing.
- KPI strip: LTV, deal count, delivery rate, contacts/members counts.
- Deals table: direct FK + DealParty attributions deduped per deal, role set
  joined ("Buyer, Broker"), person attribution via DealParty.ContactId.
- Activity: composer (Note/Call/Email/Meeting) + 30-item feed.
- Contacts panel: closest-first ordering (RelationshipStatus desc), inline
  relationship-tier select (audit `contact.relationship.changed`), detach
  button, "Attach" picker searching UNATTACHED contacts only. Attach of a
  contact on another account throws naming that account (moves = two audited
  acts: detach there, attach here).
- Members panel: AccountMember logins with role + linked contact name; add by
  email (case-insensitive, ambiguity surfaced — same precedent as
  SetAccountOwnerAsync); one-account-per-user invariant enforced (throws naming
  the current account); remove scoped to (accountId, memberId).
- Related strip: counts linking to demand/listings/sites/site-intake/auctions/
  escrow/compliance surfaces.

All mutations require an authenticated admin actor and write AuditEvents;
membership and contact changes also write Activity rows to the account timeline.

Tests: 17 new (in-memory DbContext pattern per Admin.Tests conventions), full
admin suite 159/159 green. Admin solution builds clean against local core.

## To Do Next
- Commit core changes (AccountMember, DealParty.ContactId, RelationshipStatus)
  → tag/publish → then commit admin (its CI needs the published core version).
- Wire "attach unclaimed submissions" preview into AddMember (the backfill from
  the phase plan) once claim paths stop auto-minting accounts.
- Reader migration: AccountResolver / AccountProvisioning / CustomerNotifier /
  Booking+ReserveDemandService onto membership; then remove auto-mint.
- Consider retiring the Accounts drawer once the workspace page is proven.
