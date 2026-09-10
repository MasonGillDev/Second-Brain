# Deal OS access requests now notify ops

**Project:** SLYD Platform (admin repo)
**Date:** 2026-08-12
**Author:** 02409be5-f3cc-41b0-b445-1350443804d8
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Committed `7634cea` on `development` (not pushed). Build 0 errors, full Admin.Tests
suite **245/245** passing including 5 new tests.

### The gap

Traced what happens when a new platform user requests a Deal OS account. Six pages
(`DealOsDashboard`, `MyDeals`, `Source`, `Finance`, `Auctions`, `GatedMarketplace`) are
wrapped in `DealOsAccountGate`, which resolves the user to an `Account` via
`AccountMember`. No membership → a panel with a single **Company name** field.

There is no self-service account creation, by design — `IDealOsAccountFeatures` says so
explicitly: *"accounts are deliberate ops acts created via lead conversion — the former
self-service `CreateForUserAsync` was removed with the auto-mint pipeline."*

Submitting calls `DealOsSetupRequestService.RequestSetupAsync` →
`ClaimResolution.ResolveAsync(db, userId, "deal-os-gate", …)`, which registers an inbound
`Lead` and **never** mints an Account (asserted in the core tests).

**Nothing announced it.** All seven ops checks were audited: `FormSubmissionCheck`
sweeps `FormSubmissions` (the gate writes none — it goes straight to `Leads`),
`CrmActivityCheck` sweeps `Activities` (the gate writes none either), and there was no
lead-based check at all. So a user sat locked out of the entire product while their
request waited in `/v3/crm/leads` for someone to happen to look.

The contrast that proves it was an oversight rather than a decision:
`ComplianceService.RequestVerificationAsync` writes an `Activity` *specifically* to fire
the `crm.new-activity` ops notification, with a comment calling it "the ops-facing
signal." The Deal OS gate just logs a line and returns.

### The fix

New `DealOsSetupRequestCheck` (`src/Admin.Application/Services/Notifications/Checks/`),
registered at `DependencyInjection.cs:135`. Cursor sweep every 60s over `Leads` where
`Source == "deal-os-gate"`:

- **Title:** `Deal OS access requested by {company}`, falling back to the login email.
- **Body:** `SLYD user: founder@acme.test · Company: … · Lead: LEAD-… · Convert the lead
  and tick "add as member" to unlock their Deal OS.`
- **Href** `/v3/crm/leads`, dedupe `crm.deal-os-request:{leadId}`, `RelatedEntityType` `Lead`.

**Key decisions and why:**

- **Severity `Warning`, not `Info`** like the other CRM checks. A pending request means a
  real user is locked out of the whole product — not the same as a note landing on a
  timeline. Adjustable in the rules UI if it proves noisy.
- **Email read from `lead.User.Email`, not `Lead.Email`**, printing both when they differ.
  On an *adopted* lead the captured address is the one from the website form, which can
  differ from the address they actually sign in with — and the login is what ops needs to
  create the account against. This was the user's explicit requirement.
- **`"deal-os-gate"` mirrored as a private const.** Core has no shared constant for it;
  it's a bare string literal in `DealOsSetupRequestService`. Promote it when core is next
  touched.

### Coverage limit (deliberate, not an oversight)

`ClaimResolution` has four branches; the check fires on the **mint** branch only — which
is the new-user case, so the stated need is covered. It cannot catch:

1. **Joins an existing open lead** (they'd already claimed a demand/site) — `Source` stays
   `"need-claim"`, no new row.
2. **Adopts an anonymous lead** (website form before signup, matched on email) — `Source`
   stays whatever the form set.
3. **Repeat request where the lead already has a `CompanyName`** — `RequestSetupAsync`
   skips `SaveChanges` entirely, so there is **no database trace at all** to observe.

These are unobservable from the admin side. The complete fix is core's
`DealOsSetupRequestService` writing an `Activity`, exactly as `ComplianceService` already
does — that fires on all four branches. Deferred because it needs a core release + version
bumps in platform and admin.

### Separately found: a dead-end loop in the gate

Not fixed, not in scope, but it's real and silent. `CrmLeadFeatures.ConvertToContactAsync`
only creates the `AccountMember` when `AddUserAsMember` is set — it defaults to `false` on
the request record (`CrmModels.cs:196`), though `LeadsInbox.razor:566` pre-checks it
whenever the lead has a `UserId`, which a gate lead always does. So the happy path works.

If ops unchecks it:

- Conversion stamps `lead.AccountId`, so `HasOpenRequestAsync` (`AccountId == null`) goes
  **false**.
- The gate therefore doesn't show "in progress" — it renders the **original request form
  again**, as though they'd never asked.
- They resubmit. No membership, no open lead, and adoption can't apply (it requires
  `UserId == null`, theirs is set) → **mints a fresh duplicate lead**.
- Every retry adds another unqualified row. The user can't distinguish "still waiting"
  from "silently dropped."

Related: conversion throws if the user already belongs to a *different* account
(*"Remove that membership first."*) — one membership per user is enforced, so a genuine
multi-org person can't be handled through this path at all.

## To Do Next

1. **Core `Activity` write in `DealOsSetupRequestService`** — closes branches 1–3 above and
   makes the notification complete. Mirror `ComplianceService.RequestVerificationAsync`
   (`[VERIFICATION REQUEST]` marker + `ResolveActivityHref` mapping). Needs a core release
   and version bumps. While in there, promote `"deal-os-gate"` to a shared constant.
2. **Fix the post-conversion dead end** — either keep showing "in progress" when the user's
   lead is converted but they have no membership, or block conversion of a `UserId`-bearing
   lead without membership. Today it silently generates duplicate leads.
3. **Tell the user when they're added.** There is no email confirmation on submit and no
   notification when ops adds them — hence the manual "I've been added — refresh" button.
4. Consider whether one membership per user is the right permanent constraint for people
   who legitimately span two orgs.

## Note on the working tree

Uncommitted changes from a concurrent session were present in the tree throughout
(`DemandBookFeatures`, `MatchingEngineFeatures`, `ProcurementLineProjection.cs`,
`DemandBook.razor` — the Demand Book work). Only the three files for this task were
staged; those remain uncommitted and untouched.
