# Form Lead Capture — every form submission now mints a reachable Lead

**Project:** SLYD core + platform + website
**Date:** 2026-08-05
**Author:** d6631e24-35fd-4130-8ac9-ac2b19bfc81e
**Directory:** /Users/masongill/Slyd-Platform/platform

Implements the lead-minting half of [lead-capture-signal-audit.md](lead-capture-signal-audit.md).

## Scope decision (Mason, this session)

The audit's "website form hardening" package was **explicitly dropped**. Mason:
*"Website form hardening is not what we are doing. We don't need their IP, we
need the form and their contact info. So for all form submissions require those
fields. Then right after saving, create a lead with them. Then if the user
doesn't create a slyd account, we can still reach out."*

So: no X-Forwarded-For work, no user-agent forwarding, no source-page
attribution. Contact fields required + lead minted on save. Two forks settled by
Mason before build:

1. **Feedback exempt** — anonymous page-pulse widget, requiring contact kills
   the response rate and it isn't sales signal. Mints no lead.
2. **/configure included** — its contacts were persisted nowhere at all.

## What Was Done

### The choke point (core)

`FormLeadCapture.CaptureAsync(db, submission, at, ct)` —
`SLYD.Infrastructure/Data/FormLeadCapture.cs`. Same shape as `ClaimResolution`:
static, operates on the caller's `SlydDbContext`, never calls SaveChanges.

Called from `FormSubmissionRepository.CreateSubmissionAsync` **before** its
SaveChanges, so lead + submission + the `LeadId` link commit in one transaction.
That covers all 11 production call sites — website marketing forms, the V3
/need, /sell, /site intakes, marketplace intake, and the in-app modals — **with
zero call-site changes**.

**Deliberately not best-effort.** The /need and /sell parallel FormSubmission
writes swallow exceptions; this doesn't. Silently dropping a lead is worse than
dropping an ops email — the whole point is not losing the ability to reach
someone. A lead that can't be written fails the submission loudly.

### Decisions inside the capture

- **Deny-list, not allow-list.** `FormTypes.IsLeadBearing()` — a NEW form type
  is lead-bearing unless deliberately excluded. Excluded: Feedback, the two
  `*Edit` types (existing customers editing their own artifacts — Tier 2 noise),
  SupportRequest/BugReport/FeatureRequest/UserApproval/JobApplication.
- **Lives in Domain, not Infrastructure.** First cut put `IsLeadBearing` on
  `FormLeadCapture`, which forced `PublicFormsController` to
  `using SLYD.Infrastructure.Data`. Mason caught it — that's a clean-architecture
  violation the controller didn't need (unlike the pre-existing
  `IDbContextFactory<SlydDbContext>` injections in 38 WebUI files). Moved the
  policy to `FormTypes` so both layers read one list.
- **Dedupe is UserId-first, then email** (lowercased both sides). Matches only
  *open* leads (`AccountId == null`) — a converted lead is closed history and a
  later submission is new intent.
- **Mints with no contact info at all.** A nameless lead on a 5,000-GPU
  configurator run is still worth chasing.
- **Enrichment only fills blanks** — ops may have hand-corrected a field; a later
  form must not stomp it. Exception: an email-shaped `Name` (what
  `ClaimResolution` mints, since a claim only carries the email) is upgraded to
  a real name.
- **DisplayId uses the random scheme** `LEAD-yyyyMMdd-XXXXXX`, not admin's
  `CountAsync`-based `LEAD-<year>-<0001>`. Public intake is concurrent and
  unthrottled — a count-based sequence races under exactly the flood this
  feature creates.
- **Account members mint nothing.** If `SubmittedById` has an `AccountMember`
  row they're a customer, not a lead.

### The anonymous→authenticated double (core)

`ClaimResolution.ResolveAsync` now adopts before minting: if no lead matches on
UserId, look for an *anonymous* open lead with the user's email and stamp the
login onto it. Without this every anonymous form lead duplicates the moment its
owner signs up and claims — i.e. the **best** leads in the system, the ones who
converted furthest, duplicate reliably.

### Lead↔artifact linkage (core)

`FormSubmission.LeadId` (nullable FK, `SetNull`) + migration
`20260805152204_20260805_AddFormSubmissionLeadLink`. Purely additive.

This is the only lead↔artifact link that works for anonymous submitters — the
leads inbox otherwise joins artifacts by shared `UserId`, which a form lead has
no way to carry. Without it an anonymous lead shows in the inbox as "someone
wants something" with nothing attached.

### Required contact (platform)

`PublicFormsController` validates email (format-checked) + name on every
lead-bearing type, 400 otherwise. Enforced at the API because these endpoints
are called server-to-server from the website — browser validation is not a
boundary.

Also widened contact extraction to aliases and added `ContactPhone`/`Company` to
`PublicFormRequest`. The old extractor matched the fields bag by exact key name,
so two of three contact-bearing website forms silently stored nulls:
`BensonWaitlistModal` sent `name` (→ ContactName null on every signup),
`FinancingApplication` sent `companyName` (→ OrganizationName null on every
application).

### /configure — the actual data-loss bug (platform + website)

`ConfigureController` now writes a `BuildIntake` FormSubmission (new
`FormTypes` constant) alongside the DeploymentBuild, and requires contact.
`DeploymentBuild` has no contact columns, so before this the configurator's
contact info reached the ops notification email and **nothing else** — not the
database, unrecoverable.

**Bigger than the audit described:** the audit said /configure contacts were
persisted nowhere. In fact `wwwroot/js/v3cfg.js` sent all four contact fields as
hardcoded `null` — *"contact aren't captured on the page yet (deferred to the UX
redesign phase)"*. The page never asked. So enforcing at the API would have
broken the Save button outright. Had to build the capture UI: a 4-field block
(name + email required, company + phone optional) on the save card, matching
tokens, plus client-side validation and inline error rendering.

Also fixed the website proxy: `V3ConfigureService.SubmitAsync` collapsed every
non-2xx to `null`, and `V3ConfigureController` turned that into
`502 Upstream submit unavailable`. A validation message would never have reached
the person typing. It now returns a `V3ConfigureSubmitOutcome` distinguishing
validation rejection (400, message passed through) from transport failure.

### Website contact is now compiler-enforced

`IFormSubmissionService` methods take a non-optional
`FormContact(Email, Name, Phone?, Company?)`. Email and name are non-nullable —
a required field is better enforced by the compiler than by a runtime 400.
Feedback keeps its own contact-free signature. The 3 form components pass
explicit contact and no longer stuff it into the fields bag.

## Verification

- core: **637/637 green** (593 at HEAD + 44 new — 37 `FormLeadCaptureTests`,
  7 `ClaimResolutionLeadAdoptionTests`)
- platform: **123/123 green** after the stale-test fix below. Initially 116
  passed / 6 failed; the 6 were pre-existing, confirmed by stashing both repos
  and re-running at HEAD. 13 of the passes are `PublicFormsContactRequiredTests`.
- website: 7/7 green, `node --check` clean on v3cfg.js

## Follow-up: fixed the 6 stale platform tests

All 6 traced to one commit — `ce4098e "Resolve identity via AccountMember;
claim flows stop provisioning accounts"` — which moved the identity edge from
`Account.OwnerUserId` to `AccountMember` and removed account auto-provisioning,
without updating any test. Neither test file mentioned `AccountMember` at all;
`AccountResolverTests` hadn't been touched since `8361596`, several commits
before the resolver was rewritten. **Stale tests, not product bugs** — the
production behaviour matches `ClaimResolution`'s own docblock ("Accounts are no
longer auto-minted; they are deliberate ops acts created via lead conversion").

Fix was test-only, no production code touched:

- **Seeded `AccountMember`** where the intent was still valid —
  `AccountResolverTests` ×2, `AuthPipelineTests.Returns_200…`, and the
  marketplace "reuses the existing account" test.
- **Rewrote the two asserting deleted behaviour.**
  `PostDemand_creates_an_owned_open_demand_and_provisions_a_buyer_account`
  asserted *"a Buyer account is auto-provisioned when none exists"*; renamed to
  `…_and_mints_a_lead_for_a_non_member` and now asserts what actually happens —
  zero accounts, null `BuyerAccountId`, and a `marketplace-buy` lead. That path
  had **no coverage at all** while the old assertion stood, and it's
  load-bearing for the lead capture in this change.
  `PostDemand_supports_non_gpu_hardware_with_taxonomy_validation` lost one
  trailing `BuyerAccountId` assertion incidental to what it tests.

Two coverage gains beyond the repair:

- New `GetCurrentAccountIdAsync_returns_null_when_owner_column_is_set_but_membership_is_not`
  pins the revocation path — dropping a membership cuts access on the next
  request even though `OwnerUserId` still points at the user. That's the entire
  point of `ce4098e` and nothing tested it.
- `Returns_403_when_resolved_account_is_not_the_buyer_of_the_demand` was passing
  for the wrong reason: its second user had no membership, so it resolved to
  null and 403'd identically to the no-User-row test above it. It now seeds a
  real but *different* account, so it tests what its name claims.
- All three repos build with 0 errors. Migration reviewed: additive only, and
  the model snapshot diff contains nothing but the new column/index/FK.

## To Do Next

Straight from the audit's remaining list, none of it blocked by this work:

1. **Decide the identity spine — `Lead` vs `Contact`.** Still unresolved and now
   more urgent: leads are arriving at volume while `Contact` is nominally the
   "deduplicated person record" with `EngagementScore`/`RelationshipStatus`.
   Two competing person tables.
2. **Add an intent tier to `Lead`.** A deposit pledge and a Benson waitlist
   signup still land as identical rows with no scoring or ranking. This is the
   thing that makes ops abandon a flooded inbox — and the inbox is now flooded.
3. **Surface artifacts for anonymous leads in the inbox.** `LeadId` on
   FormSubmission exists now, but `CrmLeadFeatures.LoadArtifactsAsync` still
   joins by `UserId` only — it needs to read the FormSubmission link too, or
   anonymous leads keep rendering with nothing attached.
4. **Backfill** from historical `FormSubmission` + `SellSubmission` +
   `LotDeposit`. Dedupe rules are now proven by tests, so this is unblocked.
   BuildIntake contacts remain unrecoverable — they only ever existed in email.
5. **`LotDepositPledged` still mints no lead** — it writes a `LotDeposit` with
   contact fields but no FormSubmission, so the choke point misses it. Hottest
   signal in the system (someone pledging money against a lot). Same fix shape
   as /configure.
6. Automations runtime (`TriggerJson`/`ActionJson` are still never parsed) vs.
   leaving the mapping hardcoded in `FormLeadCapture`.
