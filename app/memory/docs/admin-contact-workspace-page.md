# Admin Contact Workspace Page (/v3/crm/contacts/{id})

**Project:** SLYD admin (V3 console)
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24 (branched session c91b9fc3-73e9-4d38-a31d-50775c4adf31)
**Directory:** /Users/masongill/Slyd-Platform/core (work in ../admin)

## What Was Done

### Update: Deal Mode on the Contacts directory
Directory/Deal-Mode toggle in the page head. Deal mode keeps the entire
filter bar (type/search/relationship/account/intent/my-book — filter logic
extracted into shared `BuildContactsQueryAsync`) and renders the filtered
contacts as a portfolio board: contact header (name link, rel chip, account)
→ deal cards (SLY id → deal workspace, stage chip, type, party role, curated
Value) → BOM line rows with per-state RFQ chips (D/S/Q/✕ counts) and a line
status: "Selected $X · Supplier" / "Quotes in — pick one" / "Waiting on
quotes" / "RFQs drafted" / "Not sourced". Contacts without attributed deals
omitted; same-deal-multiple-roles deduped. One projection query (party →
deal → lines w/ counts + selected quote + winning supplier), no N+1. New
`GetContactDealBoardAsync` on ICrmLeadFeatures + board view records.
+3 tests (rollup, omission, filter honor); admin 187 green.

### Update: "My Contacts" ownership toggle
Toggle pill at the start of the Contacts filter row scoping to
Contact.OwnerAdminUserId == the authenticated admin ("my book" — unowned
contacts excluded). Identity resolved inside ListContactsAsync (new
`mineOnly` param, throws without an actor) so the page never touches
identity; composes with all other filters. +1 test; admin 185 green.

### Update: Contacts directory filter bar
Second filter row on /v3/crm/contacts: **Relationship pills** (Champion→
Unknown, tinted), **Account dropdown** (options via
IAccountDirectoryFeatures.ListAccountsAsync, same reuse as LeadsInbox), and
**Intent** (Needs / Selling) with a model text input. Intent is
person-attributed only (Mason's call): Needs = open (Open/ReVerify) Demands
with ContactId — same liveness gate as the match-engine's LoadOpenDemands;
Selling = SellSubmissions with ContactId (any status), matching headline Type
OR manifest Lines.Model. Model term is loose case-insensitive Contains
("h100" surfaces "DGX H100" lines) — deliberately NOT the match-engine's
canonical equality; MatchScoringService (pair-based 7-dim scoring) evaluated
and not reused. ListContactsAsync extended (relationship/accountId/intent/
model params; ContactListRow gained RelationshipStatus); relationship chip
column added to the table. New ContactIntent enum. 6 tests
(ContactDirectoryFilterTests). Admin 181 green.

### Update: reach line + live engagement
- Header now shows email (mailto:) and phone (tel:) as a mono "reach line"
  under the name — previously only visible in the edit panel.
- **EngagementScore is live**: it was dormant (only demo seed wrote it).
  New core domain policy `ContactEngagement` (Meeting 15 / Call 10 / Email 5
  / Note 3, system kinds 0, clamp 0–100, stamps LastEngagementAt) applied in
  `AccountDirectoryFeatures.LogActivityAsync` — the single human logging path
  both workspaces + activities page use. So "adding an engagement" = logging
  an activity on the contact via any composer. Decay = future nightly job.
  Tests: ContactEngagementTests (core, 7) + ActivityEngagementTests (admin, 2).
  Core 559 / admin 175 green.

Replaced the ContactDetail.razor "under construction" stub with the full
contact workspace — the person-side counterpart to the account workspace,
surfacing every attribution edge built this session:

- **Header + KPIs**: name/title, ContactType pill, RelationshipStatus pill
  (tinted), account deep-link, CRM rep; KPI strip = relationship tier,
  engagement score, deal count, artifact count.
- **Edit panel** (diff-based, audit `contact.info.updated` + Activity row;
  no-op saves write nothing): name/title/email/phone/type/relationship.
- **Deals table**: via DealParty.ContactId — role, stage, value, account,
  deep-linked to /v3/deal-flow/pipeline/{id}.
- **Artifacts card**: Demands + SellSubmissions with ContactId == this person.
- **Platform Login card**: the AccountMember row with ContactId == this
  person (email, role, link to account workspace to manage). Explains how to
  link when absent.
- **Activity composer + feed** (reuses IAccountDirectoryFeatures
  .LogActivityAsync with ContactId + AccountId).
- **Deliberately absent**: account attach/detach — that stays on the account
  workspace so moves remain deliberate audited acts there.

Files: `ContactWorkspaceModels.cs`, `IContactWorkspaceFeatures.cs`,
`ContactWorkspaceFeatures.cs` (Admin.Application, registered in DI),
`ContactDetail.razor` + scoped css (generated from AccountWorkspace css base),
Contacts.razor directory rows now link by name (`nm-link`).
Tests: `ContactWorkspaceFeaturesTests` (5). Admin suite 173/173 green.

## To Do Next
- Same as pipeline doc: commit core → tag/publish → admin/platform; retire OwnerUserId; invites; merge tool.
- Contact merge/dedup tooling (email uniqueness still unenforced) once real duplicates appear.
