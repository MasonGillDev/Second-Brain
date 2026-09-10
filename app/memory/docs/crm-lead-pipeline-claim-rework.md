# CRM Lead Pipeline: Claim Rework + Enhanced Conversion (auto-mint removed)

**Project:** SLYD core + admin
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branched session c91b9fc3-73e9-4d38-a31d-50775c4adf31)
**Directory:** /Users/masongill/Slyd-Platform/core (work spans ../admin)

## What Was Done

### Update (branched session f7df1e44): Leads Inbox inbound/outbound reorg
Top-level tab toggle on /v3/crm/leads: **Inbound** (Qualified=false, default —
they came to us) vs **Outbound** (Qualified=true — we sourced them). Two
distinct working queues: ListLeadsAsync gained `bool? qualified`; tab counts
always cover ALL leads, channel/type pill counts cover only the active slice
(tab = working context, pills subdivide it). Per-tab columns: Inbound shows
"Login / Artifacts" (User email + demand/sell/site count joined via
Lead.UserId, grouped queries no N+1); Outbound shows "Company". Tab switch
clears selection + pill filters; "+ New Lead" prefills the Qualified checkbox
from the active tab and lands on the created lead's tab. Both tabs keep full
conversion (the dialog already adapts: member/artifact options only when
lead.UserId exists). LeadListRow gained UserEmail/ArtifactCount; LeadListView
gained Qualified/UnqualifiedCount. 3 tests (LeadInboxQualificationTests).
Admin 184 green. NOTE: manual deal-flow-from-contact work (create
need/intake/deal) was interrupted and branched away — not implemented here.

### Tweak: convert dialog gained Name + Title fields (prefilled from the lead;
dialog wins, blank falls back to lead capture) — claim-minted leads only carry
the login email as Name, so conversion is where ops fixes the real identity.
All convert-dialog fields (name/title/email/phone) now prefill in
OpenConvertAsync. +2 tests; admin 168 green.

### Update (same session): gate setup form removed — last self-serve mint closed
After the reader migration Mason hit the platform's Deal-OS gate, which still
offered "create account" (`DealOsAccountFeatures.CreateForUserAsync`) and
granted access. Removed the self-service path entirely:
- `IDealOsAccountFeatures.CreateForUserAsync` DELETED (breaking core API;
  gate was the only caller). Interface is lookup-only now.
- New `IDealOsSetupRequestService` (core Infrastructure): the gate registers
  an inbound setup request — delegates to `ClaimResolution` so gate + claim
  paths share one-open-lead-per-user; captures company name onto the lead
  (never overwrites an existing one); returns null when the user is already
  a member (race with ops) so the gate re-resolves and reveals.
- `DealOsAccountGate.razor` rewritten: no-membership → "access is set up by
  our team" + company-name request form → pending panel with an "I've been
  added — refresh" button. `OnAccountCreated` callback removed from the gate
  and its 6 call sites (Auctions/Source/Finance/Dashboard/MyDeals/
  GatedMarketplace).
3 new integration tests (DealOsSetupRequestServiceTests).

Also migrated the LAST two auto-mint callers and deleted the helper:
- `MarketplaceIntakeService` (platform, signed-in marketplace buy + sell):
  both sites now use ClaimResolution — member → account+contact stamped;
  non-member → inbound lead, artifact account-less.
- `SellClaim.razor` (platform, direct AccountProvisioning call inside razor):
  now ClaimResolution + contact stamp.
- **`AccountProvisioning` DELETED** — zero callers remain. Auto-mint no
  longer exists anywhere.
Green: core 548 unit / 49 integration, platform 11, admin builds clean.

### Update (same session): reader migration — membership is now THE resolution edge
Mason removed his membership in admin but platform deal-OS pages still showed
the account — because AccountResolver still walked Account.OwnerUserId (which
the backfill deliberately left populated). Migrated all readers:
- **Platform `AccountResolver`**: Auth0 sub → User.AuthId → AccountMembers →
  AccountId. Removing a membership now revokes V3 surfaces on next request.
- **Core `IAccountRepository.GetForUserAsync`** (new, membership-based);
  `GetByOwnerUserIdAsync` doc-marked LEGACY. `DealOsAccountFeatures` uses it,
  and its setup-form `CreateForUserAsync` now creates the Owner AccountMember
  row alongside the account (OwnerUserId still stamped in sync until retired).
- **`Booking/ReserveDemandService`**: Demand.UserId stamped from
  `AccountMembership.ResolvePrimaryUserIdAsync` (new helper: Owner member
  first, earliest member fallback) instead of account.OwnerUserId.
- **`CustomerNotifier.NotifyAccountAsync`**: notifies the Owner member
  (earliest fallback) via IAccountMemberRepository; no members = no notice —
  revocation applies to notifications too.
- **Admin `SetAccountOwnerAsync`** ("Link customer user"): now also creates
  the Owner membership (one-account-per-user enforced, throws naming the
  other account) — without this, newly linked users would be unresolvable.
- **Platform `DevAuthBypass`**: demo-account link also adds the member row.
Tests updated (CustomerNotifierTests rewritten for membership; demand-service
tests seed member rows). Green: core 548/46, admin 166, platform 11.
Remaining OwnerUserId writers: MarketplaceIntakeService (auto-mint, flagged),
DemandClaim tests' legacy column, backfill. Column retires once those go.

### Hotfix (same session): ExecuteUpdate translation crash in configure-claim
`DeploymentBuildRepository.ClaimAsync` threw "LINQ expression 'd' could not be
translated" at runtime: the ContactId setter used a row-referencing value
lambda (`d => d.ContactId ?? resolution.ContactId`) on a query filtered
through the Build navigation — EF pushes that into a PK-join and can't
translate the entity parameter in setters. Fix: split into a second
constant-valued ExecuteUpdate with the "only when unset" condition moved into
the Where (`d.ContactId == null`). Applied to both DeploymentBuildRepository
and DemandRepository (same construct; demand's translated only by luck of a
simpler query shape). Added DeploymentBuildClaimIntegrationTests (2 tests —
the configure-claim path previously had ZERO integration coverage, which is
why this reached runtime). Core integration: 46/46 green.

Implemented Mason's full pipeline design: **accounts are never auto-minted**;
the lead is the pre-account holding pen, membership short-circuits it, and
conversion is the single act creating Account + Contact + Member + attaching
artifacts.

### The pipeline (as decided)
1. **Intake**: form → artifact (ClaimToken) + FormSubmission. Unchanged.
2. **Claim** (`ClaimResolution.ResolveAsync`, new, replaces
   `AccountProvisioning` in claim paths):
   - User is an **AccountMember** → artifact stamped with account + linked
     contact in the claim txn. No lead ("members already have a relationship").
   - **Non-member** → find the user's open lead (UserId set, AccountId null)
     or mint one: `Qualified=false` (inbound — THEY want US), Channel=Form,
     Email captured from the User row, DisplayId `LEAD-yyyyMMdd-<rand6>`
     (random, not count — runs inside concurrent claim txns). Artifact stays
     account-less. One open lead per user; second artifact joins it.
   - Converted lead (AccountId stamped) = closed; new artifact opens a fresh one.
3. **Inbox**: lead drawer shows capture fields, INBOUND/OUTBOUND chip,
   platform login email, and the user's claimed artifacts (demands/sell/site)
   joined **via UserId — no artifact→lead FK needed**.
4. **Conversion** (`CrmLeadFeatures.ConvertToContactAsync`, reworked): one act =
   resolve account (pre-linked > ops-picked existing > create from
   NewAccountName ?? lead.CompanyName; no account → throw) + create Contact
   attached + stamp lead.AccountId (closes it) + optionally add the login as
   AccountMember (contact-linked; aborts naming the other account if the user
   belongs elsewhere) + **attach artifacts**: unattached demands get
   BuyerAccountId+ContactId, site submissions OwnerAccountId, sell submissions
   ContactId. Tracked entities (not ExecuteUpdate) so it commits atomically —
   also keeps InMemory tests working.

### Lead schema (migration `20260720201336_AddLeadCaptureFields`, applied to SLYD2)
Nullable-by-design capture fields ("leads from a variety of locations — semi
fluid, capture when we can"): `Email`, `Phone`, `CompanyName`, `UserId` (FK
SetNull, the artifact join key), and `Qualified` (bool: true = outbound/we
want them; false = inbound/they want us).

### Behavior change (explicit, Mason-approved)
Old claim behavior (get-or-create account via `AccountProvisioning`) was
pinned by DemandClaimIntegrationTests — those tests were intentionally
rewritten. `AccountProvisioning` remains ONLY for Platform's
MarketplaceIntakeService (doc-marked SUPERSEDED; migrate + delete later).
Non-member demands now sit BuyerAccount-less until conversion — deal
formation correctly refuses them until ops qualifies the lead.

### Files
Core: `Lead.cs`, `ClaimResolution.cs` (new), `AccountProvisioning.cs` (doc),
`DemandRepository`/`SiteSubmissionRepository`/`DeploymentBuildRepository`
(claim rework), DbContext config, migration, `DemandClaimIntegrationTests`
(rewritten, 6 tests).
Admin: `CrmModels.cs` (LeadListRow/DetailView/NewLeadRequest/Convert request
extended + LeadArtifactItem), `CrmLeadFeatures.cs` (artifacts loader, capture
mapping, conversion rework), `LeadsInbox.razor` (+css): capture fields on
create, drawer chip/fields/artifacts, convert dialog with account
match-or-create + member checkbox. `ConvertLeadPipelineTests` (7 tests).

Green: core 549 unit / 44 integration; admin 166.

## To Do Next
- Platform: migrate MarketplaceIntakeService off AccountProvisioning, then delete it.
- Platform claim pages (NeedClaim etc.): update "account provisioned" copy to "a rep will set up your organization" messaging.
- Intake could stamp Lead.Name/Phone/CompanyName from the form's contact fields (currently only User.Email at claim).
- Commit core → tag → publish → then admin/platform.
