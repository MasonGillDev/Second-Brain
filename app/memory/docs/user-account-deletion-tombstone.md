# User Account Deletion — Tombstone + Blockers (first pass)

**Project:** SLYD Core (SLYDV3/core)
**Date:** 2026-08-12
**Author:** 06f55203-7868-4979-9acc-a786e684bd7a
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

Triggered by a GDPR erasure request that arrived through the public contact form: a
user asked to delete their account, couldn't find any feature for it, and was right —
there was none.

### Findings that shaped the build

- `UserRepository.DeleteUser` (core) existed but had **zero callers** anywhere in
  platform, admin, or website. It was also **broken**: a bare `Users.Remove()` against
  a schema where several FKs into `User` are `DeleteBehavior.Restrict`
  (`Notification.UserId`, `SupportTicket.CreatedById`, `BensonConversation.UserId`,
  `AppTags.AssignedBy`). Since `CustomerNotifier` writes a Notification for nearly
  every lifecycle event, most real users have one — that call throws an FK violation.
- **No Auth0 Management API client exists** in any repo. `Auth0Service` is read-only
  (token → user). Deleting a DB row leaves a live Auth0 identity.
- The published privacy policy (`website/.../PrivacyPolicy.razor:319`) affirmatively
  promises right-to-erasure, and directs users to `privacy@slyd.com` — a channel not
  discoverable from inside the product.

### What was built

Scoped deliberately to the **login** (`User`), not the counterparty (`Account` /
`Organization`) — deleting one member must not wind down a company others still use.
`AccountMember` makes that separation clean.

- `User.DeletedAt` + `User.DeletionReason` (`SLYD.Domain/Models/User/User.cs`)
- `IUserDeletionService` (`SLYD.Application/Interfaces/Services/`) — eligibility check
  + tombstone, with `DeletionBlocker` codes for UI to switch on
- `UserDeletionService` (`SLYD.Infrastructure/Services/Users/`)
- Migration `20260812174716_AddUserDeletionTombstone` — two nullable columns, additive
- `UserRepository.GetUserWithAuthToken` now filters `DeletedAt == null`
- DI registration in `AddInfrastructure`
- 13 integration tests (`tests/SLYD.Core.IntegrationTests/Services/Users/`)

### Key decisions and why

**Tombstone, not hard delete.** Hard delete is impossible without migrating the
`Restrict` FKs, and undesirable regardless — financial lineage must survive an erasure
request, which the privacy policy itself carves out (`:183`, `:319`). The tombstone
scrubs `Email` → `deleted-{id:N}@deleted.invalid` (RFC 2606 reserved, undeliverable),
clears `AuthId`, `PlatformInterest`, `AdditionalInfo`, and stamps `DeletedAt` /
`DeletionReason`. PII leaves the row; the row stays.

**No global query filter on `User`.** The schema has a strong `IsDeleted` +
`HasQueryFilter` precedent, but applying it to `User` would silently change every
existing query and join across core, platform, and admin — including required
navigations. Chose explicit filtering at the login path instead. Documented in the
entity so the next person doesn't "fix" it.

**Deletion is idempotent.** A retry returns `AlreadyDeleted` without re-stamping the
timestamp or overwriting the original reason.

**Blockers refuse rather than partially delete.** Four, spanning both identity edges —
v1 (`OrganizationUser → Organization`) reaches compute and wallets, V3
(`AccountMember → Account`) reaches escrow:
`active_instances`, `wallet_balance` (non-zero either direction), `pending_payout`
(Scheduled/PartiallyPaid), `open_escrow` (any non-terminal state).

### Verification

`dotnet test SLYD.Core.sln` — 1018 passed, 0 failed (637 unit + 311 matching + 70
integration, incl. the 13 new).

## To Do Next

Not built in this pass, in rough priority order:

1. **Admin UI** — ops-initiated deletion. This is the shortest path to answering the
   outstanding GDPR request; nothing else is required for it.
2. **Auth0 Management API client** — without it the identity survives and the person
   gets a fresh empty `User` row on next sign-in. Needs a new M2M app + SSM secret.
3. **The data sweep** — the tombstone covers the `User` row only. Still carrying the
   person's details: `Contact`, `Lead`, `FormSubmission` (+ fields), `SellSubmission`,
   `LotDeposit`, `SupportTicket`/`TicketMessage`, Benson conversations, `Activity`,
   `ContactEngagement`. Plus external: S3/R2 attachment blobs, Stripe, SendGrid.
4. **Platform self-serve** in `SettingsV3.razor`, ideally with a cancellable grace
   period rather than immediate execution.
5. **Remove or fix the dead `DeleteUser`** on `IUserRepostiory` / `IUserFeatures` —
   unreachable and would throw. Left in place because removing an interface member is
   a breaking change for NuGet consumers; needs a deliberate call.
6. **Unrelated but found alongside:** `/legal` link 404s from the wallet terms gate
   (`platform/.../WalletElements/TermsAcceptanceModal.razor:30` points at a route that
   only exists on the website). And `ContactUs` is lead-bearing, so the GDPR request
   itself minted a sales Lead — a `PrivacyRequest` form type in `NonLeadBearing`
   (`FormTypes.cs:77`) would stop that.

**Release note:** this is core, so it needs commit → tag → NuGet publish → pin bump in
platform and admin before either can consume it.
