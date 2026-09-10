# CRM AccountMember Table — Multi-User Accounts (Phase 1, Step 1)

**Project:** SLYD core libraries
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

### Update (branched session c91b9fc3): intake ContactId links + workspace deep-links

Decision: transactional records link to Contact where sales works them —
`Demand.ContactId` already existed but has NO writers (dormant; wire it at
claim time from `AccountMember.ContactId` during the reader-migration phase).
Lots stay person-free; attribution lives on intake artifacts:
- `SellSubmission.ContactId` (mirrors Demand.ContactId, sell side)
- `LotDeposit.ContactId` (inline ContactName/Email strings stay as raw
  pre-claim capture; FK is the resolved identity)
Migration `20260720194138_AddIntakeContactLinks` (applied to local SLYD2).
3 integration tests (SetNull preserves intake records + inline capture).
Green: 549 unit / 42 integration.

Also: stub pages `/v3/deal-flow/pipeline/{dealId}` (DealDetail.razor) and
`/v3/crm/contacts/{contactId}` (ContactDetail.razor) — "under construction";
workspace deal DisplayIds and contact names now deep-link to them. All three
earlier migrations applied to SLYD2; backfill created 3 Owner memberships and
exposed a real dup: jim.halpert@gmail.com owns two accounts (auto-mint
fragmentation in dev data).

### Update (same session): Contact.RelationshipStatus — closeness tier for marketing

Marketing needs to push the best deals to the closest contacts. Added
`ContactRelationshipStatus` enum (Unknown=0, Cold, Warm, Strong, Champion=4)
on `Contact` — ordered coldest→closest so `OrderByDescending` ranks closest
first; append-only since it persists as int. Deliberately distinct from
`EngagementScore` (recomputed from activity): this is a human judgment set by
ops/sales. Indexed for marketing filters. Migration
`20260720…_AddContactRelationshipStatus` (existing rows default Unknown).
Enum pins + ordering + default tests in `ContactRelationshipStatusTests.cs`.
Green: 549 unit / 39 integration. Not committed yet.

### Update (same session): DealParty.ContactId — per-role contact attribution on deals

Sales wanted deals "held per contact." Decision: deals stay held by Accounts
(legal/economic counterparty — LTV, compliance, delivery-rate all account-scoped),
but each deal-role gains optional person attribution via `DealParty.ContactId`
(nullable, SetNull). Per-party rather than a flat `Deal.ContactId` because deals
are multi-party (buyer-side person ≠ operator-side person), and DealParty is
already the deal↔account↔role attribution join. Consistency rule (contact
belongs to the party's account) is service-layer, not schema, so a contact
moving companies doesn't invalidate historical attribution. With
`AccountMember.ContactId` this completes the identity triangle: login↔person
and deal-role↔person.

- `src/SLYD.Domain/Models/DealOS/DealParty.cs` — ContactId + navigation.
- `SlydDbContext` DealParty config — Contact FK, SetNull.
- Migration `20260720190328_AddDealPartyContact`.
- `tests/SLYD.Core.IntegrationTests/DealOS/DealPartyContactTests.cs` — 3 tests:
  persist per-role attribution, same account different contacts across deals,
  contact-delete nulls attribution but preserves the party.
- Green: 542 unit / 39 integration. Not committed yet.

First implementation step of the CRM robustness plan: the `AccountMember` join
table so one Account (company/counterparty) can have many platform User logins,
superseding the single-login `Account.OwnerUserId` binding.

### Context / decisions from this session (design discussion preceded the code)

- **Account = company**, not a person or login. Contact = person at the company,
  AdminUser = SLYD internal owner, User = customer login, Organization = v1
  billing bridge. The disjointedness came from `OwnerUserId` conflating company
  with a single login, plus auto-minting an Account for every user who touched a
  gated deal-OS flow (fragmenting one company into N accounts).
- **Chosen direction:** kill auto-mint → admin-manual account creation first,
  invite flow later, merge tool only as a rare ops escape hatch (merge across
  15+ FK tables with sealed-auction commitment hashes is dangerous; prevent
  duplicates instead of curing them).
- **Form-submission provenance is unaffected** by removing auto-mint: website
  intake (Demand/SellSubmission/SiteSubmission) already binds to the User via
  single-use ClaimTokens. Account attach becomes a deterministic backfill at
  member-add time: attach all unattached User-bound records, with an ops preview
  UI (checkbox per item) to guard against wrong-person mistakes. Removing a
  member must NOT un-attach records.
- **Phase 1 invariant: one account per user**, enforced in the repository
  (`AddAsync` throws), NOT the schema — the unique index is on
  `(AccountId, UserId)` so relaxing to many-accounts-per-user later needs no
  migration.
- Contact creation currently only happens via lead conversion in Admin
  (`CrmLeadFeatures.ConvertToContactAsync`); no direct create, no dedup, no
  attach/move. That's the next Admin-side work.

### Files changed (all in core, branch `feat/capacity-matching-pass`)

- `src/SLYD.Domain/Models/DealOS/AccountMember.cs` — new entity + `AccountMemberRole`
  enum (Member=0, Owner=1, Admin=2, Viewer=3; append-only, backfill hardcodes 1).
  Optional `ContactId` links login identity ↔ CRM person.
- `src/SLYD.Infrastructure/Data/SlydDbContext.cs` — DbSet + config: unique index
  (AccountId, UserId), Account/User FKs Cascade, Contact + audit FKs SetNull.
- `src/SLYD.Infrastructure/Migrations/20260720181431_AddAccountMembers.cs` —
  generated migration + hand-added backfill: every non-null `OwnerUserId`
  becomes an Owner membership row. `OwnerUserId` stays until all readers move.
- `src/SLYD.Application/Interfaces/Repositories/DealOS/IAccountMemberRepository.cs`
  + `src/SLYD.Infrastructure/Repositories/DealOS/AccountMemberRepository.cs` —
  GetForUserAsync (auth-resolution lookup), GetByAccountAsync, AddAsync (invariant
  guard), RemoveAsync. Registered in DependencyInjection.cs.
- Tests: `tests/SLYD.Core.IntegrationTests/DealOS/AccountMemberRepositoryTests.cs`
  (7 tests: persist/resolve, invariant throw, unique-index backstop, list,
  remove, account-delete cascade, contact-delete set-null) and
  `tests/SLYD.Core.Tests/Domain/DealOS/AccountMemberRoleTests.cs` (enum pins).
- All green: 542 unit, 36 integration. Not committed — user must approve commits.

## To Do Next

1. Commit (ask user first, per repo rules), tag + publish core so admin/platform can consume.
2. Move readers off `OwnerUserId`: `AccountResolver` (platform), `AccountProvisioning.EnsureAccountForUserAsync`, `DealOsAccountFeatures`, `CustomerNotifier` (notify all members), `Booking/ReserveDemandService` (stamp acting user, not owner).
3. Remove auto-mint from claim paths; unbound users get "pending setup" gate; intake surfaces as Lead in Admin.
4. Admin: Account detail page — add member (with unattached-submission preview/backfill), add/attach Contact directly, contact dedup check.
5. Later: invite flow (claim-token pattern, prevents fragmentation); minimal ops merge tool only when real duplicates exist; eventually deprecate `OwnerUserId`.
