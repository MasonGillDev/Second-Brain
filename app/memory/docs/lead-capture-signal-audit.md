# Lead Capture Signal Audit — flooding the Leads inbox from intent-bearing surfaces

**Project:** SLYD core + platform + admin + website
**Date:** 2026-07-28
**Author:** a5859f81-5c32-4bc6-b1c2-375eb0494c30
**Directory:** /Users/masongill/Slyd-Platform/core (audit spans ../platform, ../admin, ../website)
**Priority:** HIGH
**Status:** Audit only — no code written

Follows on from [crm-lead-pipeline-claim-rework.md](crm-lead-pipeline-claim-rework.md)
(the auto-mint removal + inbound/outbound reorg) and
[crm-account-member-table.md](crm-account-member-table.md).

## Goal

Mason: "flood the leads with more data — anyone interacting with SLYD in a way
that indicates they're trying to buy/sell hardware or offtake." Best-effort
capture of name + any contact info. This doc is the audit that precedes that
work.

## What Was Done

### Update 2026-07-30: website form trace + hardening decisions

Traced the website repo's form path (website → server-to-server → platform
`PublicFormsController`). Findings:

- The website's `FormSubmissionService` posts only a `Fields` dictionary +
  `Subject` — it never sets the DTO's top-level `ContactEmail`/`ContactName`.
  The platform extracts contact info from the bag by **exact key name**
  (`email`, `firstName`+`lastName`, `phone`, `company`,
  `PublicFormsController.cs:134-145`). Two of three contact-bearing forms
  mismatch:
  - `BensonWaitlistModal.razor` sends `name` → `ContactName` stored **null**
  - `FinancingApplication.razor` sends `companyName` → `OrganizationName`
    stored **null**
  - `ContactSales.razor` matches all aliases — the one clean channel
  - Data isn't destroyed (still in `FormSubmissionField` rows) but never
    reaches the promoted columns a backfill would read.
- **Metadata is junk on the website hop.** The website's `HttpClient`
  (`website/Program.cs:162-167`) forwards no headers, so
  `GetClientIpAddress()` records the **website server's** IP for every
  visitor; `UserAgent` is .NET's; `SourceUrl`/referer is empty. Looks like
  real data, isn't. Forms posted browser→platform directly are unaffected.
- `submit-quote` / `submit-solutions` endpoints + website service methods
  (`SubmitQuoteFormAsync`/`SubmitSolutionsFormAsync`) exist end-to-end but
  **no website UI calls them** — the missing piece is purely the form pages.

**Decisions (Mason, 2026-07-30):**

1. **Fix the hop, don't kill the metadata** — website forwards real client
   IP (`X-Forwarded-For`), browser user-agent, and page URL per submission.
   Website is exactly where source-page attribution matters most.
2. **Build the QuoteRequest + SolutionsInquiry website forms** (plumbing
   exists; UI missing). Open sub-questions: SolutionsInquiry as its own page
   vs. a `ContactSales` variant with a `sourceTag`; QuoteRequest should
   funnel toward the structured V3 intakes (`/need`, `/sell`, `/configure`)
   rather than siphon from them.
3. **Contact info becomes required first-class fields** — a small set
   (email + name) required and stored with every form, sent as explicit DTO
   properties (`PublicFormRequest.ContactEmail/ContactName` already exist,
   website just never sets them), **validated at the API**, not inferred
   from the fields bag by alias. Fields bag returns to form-specific payload
   only. Exempt `Feedback` (anonymous pulse widget; requiring contact kills
   the rate and it isn't lead signal). Email is the truly-required key
   (lead dedupe is email-first); name required; phone/company optional.

Sequencing note: decision 3 mostly obsoletes the "widen extractor aliases"
fix for live traffic — the alias mapping only matters for interpreting
historical rows during backfill. None of this touches core (no NuGet
republish) — it's a standalone website+platform package that can ship ahead
of the lead-minting work.

### Original audit (2026-07-28)

Full cross-repo trace of every intent-bearing surface, what contact data each
collects on the wire, and where that data actually lands.

### Headline finding

**This is a routing problem, not a data-collection problem.** Every high-intent
surface already asks for name/email/phone/company. That data lands in
`FormSubmission` (an ops email queue) or — in one case — nowhere at all.
Nothing on any of those paths ever touches the `Leads` table.

Leads are minted in exactly two places today:

1. `ClaimResolution.ResolveAsync` (`core/src/SLYD.Infrastructure/Data/ClaimResolution.cs:40`)
   — fires only when an **already-authenticated** user claims an artifact
   *and* has no `AccountMember` row. Four callers: `DemandRepository`
   (`need-claim`), `SiteSubmissionRepository` (`site-claim`),
   `DeploymentBuildRepository` (`configure-claim`), `DealOsSetupRequestService`
   (`deal-os-gate`).
2. `CrmLeadFeatures.CreateLeadAsync` (`admin/src/Admin.Application/Features/DealOS/CrmLeadFeatures.cs:169`)
   — manual ops entry, requires an authenticated admin actor.

So the only inbound leads that exist are from people who submitted, went
through Auth0, then came back and claimed. Everyone who filled a form and
walked away is invisible.

`FormSubmissionService` (`core/src/SLYD.Application/Features/Forms/FormSubmissionService.cs`)
writes a `FormSubmission` row with status `New` and nothing else. `FormSubmission`
has **no `LeadId` column**. No form submission has ever produced a lead.

### Signal inventory

**Tier 1 — anonymous, high intent, full contact captured, zero leads:**

| Signal (`OpsSubmissionEvent.Kind`) | Entity written | Contact lands in | Intent |
|---|---|---|---|
| `LotDepositPledged` | `LotDeposit` (has `ContactName/Email/Phone`) | entity + notifier | **Pledging money against a lot — hottest signal in the system** |
| `NeedIntake` (`/need`) | `Demand` + `FormSubmission` | FormSubmission only — `Demand` has NO contact fields | Buy-side |
| `HardwareSalesIntake` (`/sell`) | `SellSubmission` (has `SubmitterName/Email/Phone`) + `FormSubmission` | both | Sell-side |
| `EnergySiteIntake` | `SiteSubmission` + `FormSubmission` | FormSubmission only — `SiteSubmission` has NO contact fields | Offtake/energy |
| `BuildIntake` (`/configure`) | `DeploymentBuild` + `Demand` | **notifier email ONLY — persisted nowhere** | Operator |
| `ContactUs`, `SolutionsInquiry`, `FinancingApplication`, `QuoteRequest`, `BensonWaitlist` | `FormSubmission` | FormSubmission (+ IpAddress, UserAgent, SourceUrl/referer) | Mixed |

**The `BuildIntake` data-loss bug.** `ConfigureController.cs:499-502` passes
`ContactName/ContactEmail/ContactPhone/Company` straight into the notifier
email. `DeploymentBuild` has zero contact columns. No `FormSubmission` is
written on that path (`WriteContactFormSubmission` exists only in
`PublicV3IntakeController`). Someone configures a 5,000-GPU build, types their
email, and the only record is an email in an ops inbox. **That data is not in
the database at all** and is unrecoverable retroactively.

**Tier 2 — authenticated, already account members. Leave alone.**
`CapacityBookingRequested`, `ForwardLotBookingRequested`, `TermSheetRequest`,
`CapacityListingSubmitted`, `HardwareSalesEdit`. These carry an `AccountId`;
`ClaimResolution` correctly returns the account and skips the lead. Minting
leads here would be pure noise.

### Recommended choke point: `IOpsSubmissionNotifier`

`platform/src/Platform.WebUI/Services/IOpsSubmissionNotifier.cs`. Every
intent-bearing event already flows through it — 14 call sites — and
`OpsSubmissionEvent` already carries the exact normalized tuple needed:

```csharp
Kind, Ref, Summary, ContactEmail, ContactName, ContactPhone, Company, ExtraFields
```

A lead-minting sink alongside the email fanout captures all six anonymous
surfaces at once with **zero changes to any call site**. `Kind` maps cleanly
to `LeadType` (`NeedIntake`→Offtake/Operator, `HardwareSalesIntake`→Supply,
`EnergySiteIntake`→Energy, `BuildIntake`→Operator); `Ref` gives the artifact
backlink for free.

Two caveats:
- The notifier deliberately lives in `Platform.WebUI` (not `SLYD.Application`)
  to avoid a core/NuGet republish "for this pure transport concern". Minting
  leads is **not** transport — either the interface moves to core, or the sink
  lives in the web layer and writes through a core service.
- It is contractually best-effort with swallowed exceptions. Silently dropping
  a lead is worse than silently dropping an email — failures must be loud.

**Alternative:** mint at each persistence site. More code, but puts the lead in
the same transaction as the artifact and lets you set `Demand`/`SiteSubmission`
contact linkage at the same time.

### The hard part: dedupe

Most likely thing to make ops abandon the feature.

`ClaimResolution` dedupes on `UserId` (one open lead per user). Anonymous
submitters have no `UserId`, so email-based matching is required.
`IX_Leads_Email` exists (non-unique, `SlydDbContext.cs:1471`) so lookups are
cheap. Problems:

- **Email is dirty and optional.** Every contact field on every intake DTO is
  `string?`. A submission with no email and no phone can't be deduped against
  anything. Recommendation: mint anyway — a nameless lead attached to a $2M
  deposit pledge is still worth a call.
- **Anonymous-then-authenticated doubles.** Submit `/need` anonymously (email
  lead minted) → claim via Auth0 → `ClaimResolution` finds no `UserId` match
  and mints a **second** lead. `ClaimResolution` must try email-match against
  the user's email before minting, and stamp `UserId` onto the matched
  anonymous lead. Without this, your *best* leads (the ones who converted far
  enough to authenticate) reliably duplicate.
- **Repeat submitters.** A serious buyer hits `/configure`, `/need`, and a
  deposit pledge in one session. One lead with three artifacts, not three leads.
- **`DisplayId` minting is already inconsistent.** `ClaimResolution` uses
  `LEAD-yyyyMMdd-<random6>` (deliberately random — it runs inside concurrent
  claim transactions where a count would race). Admin uses `LEAD-<year>-<0001>`
  via `CountAsync`. A third site must pick one; under flood volume the
  count-based one *will* race.

**No artifact→lead FK exists anywhere.** The leads inbox joins artifacts purely
via shared `UserId` (`CrmLeadFeatures.LoadArtifactsAsync`, lines 137-167).
Anonymous leads have no `UserId`, so they would appear in the inbox **with no
artifacts attached** — "someone wants something" with no way to see what.
Needs either a `LeadId` on artifacts or a lead↔artifact join table. Decide
before flooding, not after.

### The Automations engine describes this and does not run

`Automation` carries `TriggerJson`/`ActionJson`. `DemoSeedJob.cs:739-750` seeds
literally the rules Mason is asking for:

```json
{"event":"configurator.save"} → {"type":"create-lead","leadType":"operator"}
{"event":"sell.submit"}       → {"type":"create-lead","leadType":"supply"}
```

But `AutomationAlertFeatures` only **lists and toggles** them —
`TriggerJson`/`ActionJson` are never parsed or executed in any repo (verified
by grep across core/platform/admin). The admin Automations page renders rules
that do nothing. The `Lead` class docblock ("App events auto-create leads via
the Automations engine") describes intent, not behavior.

Fork: hardcode the mapping at the notifier sink (ships fast), or build the
automations runtime the schema is already shaped for (ops-configurable, no
redeploy per trigger). Recommendation: hardcode first, but write the sink so
it's swappable later.

### Backfill opportunity

Every historical `FormSubmission` already holds `ContactName`, `ContactEmail`,
`ContactPhone`, `OrganizationName`, `SourceUrl`, `IpAddress`, `UserAgent`,
`SubmittedAt`. Plus `SellSubmission.SubmitterName/Email/Phone` and
`LotDeposit.ContactName/Email/Phone`. A one-time backfill lights up the inbox
immediately from data already held — and is the cheapest way to pressure-test
dedupe rules before they run live. `BuildIntake` contacts are the exception:
unrecoverable, they only ever existed in email.

### Other gaps found

- `Demand` and `SiteSubmission` have no contact columns; both rely on the
  parallel `FormSubmission` for identity, linked only by `DisplayId` embedded
  in a subject string. Fragile.
- `DeploymentBuild` has no contact columns and no parallel `FormSubmission` —
  the one true data-loss bug.
- **Anonymous preview endpoints are uncaptured behavioral signal:**
  `hardware-sales/preview`, `hardware-sales/preview-line`,
  `power-opportunities/preview`, `configure/preview`, `need/preview`. Someone
  pricing a 10,000-GPU build who never submits is real signal, but there's no
  contact info and no session identity. Only useful with a soft identity
  capture (email-gate on results, or a cookie tying previews to eventual submit).
- **`Contact` vs `Lead` overlap unresolved.** `Contact` is the "deduplicated
  person record" with `EngagementScore`/`RelationshipStatus`; `Lead` now
  duplicates name/email/phone/company. Flooding leads without deciding which is
  the identity spine produces two competing person tables.

### Risk

The thing that kills this feature is ops abandoning the inbox. Filtering exists
on `Channel`/`Type`/`Qualified` (`LeadsInbox.razor`) but there is **no scoring
or ranking**. A deposit pledge and a Benson waitlist signup land as identical
rows. Flooding without a priority signal — deal size, intent tier, or reusing
`EngagementScore` — buries the leads that matter.

## To Do Next

> **STATUS 2026-08-05 — lead minting SHIPPED, see
> [form-lead-capture-implementation.md](form-lead-capture-implementation.md).**
>
> The website-form-hardening package below was **dropped by Mason**: the IP /
> user-agent / source-page metadata work is not wanted ("we don't need their IP,
> we need the form and their contact info"). Item 2 (contact as required
> first-class fields) shipped; items 1 and 3 did not and are not planned. The
> alias mapping in item 4 was widened anyway, since it was ~6 lines.
>
> Of the lead-minting list: items 1 (BuildIntake data loss), 4 (lead→artifact
> linkage), 5 (ClaimResolution email matching), 6 (DisplayId scheme) and 7 (the
> capture sink) are done. Items 2 (identity spine), 3 (intent tier) and 8
> (backfill) remain — carried forward in the new doc.

**Website form hardening (DECIDED 2026-07-30 — ships first, no core changes):**

1. Fix the metadata hop: website forwards real client IP
   (`X-Forwarded-For`), browser user-agent, and originating page URL on
   every form POST; platform records visitor identity, not the website
   server's. (Website is Blazor Server — the "browser" values come from the
   circuit's HttpContext, captured at circuit start.)
2. Promote contact to required first-class DTO fields: website sets
   `PublicFormRequest.ContactEmail/ContactName` (+ phone/company optional)
   explicitly; platform validates email+name at the API for lead-bearing
   form types; `Feedback` exempt; fields bag returns to form-specific
   payload only. Kills the alias-extraction fragility for live traffic.
3. Build QuoteRequest + SolutionsInquiry website form UIs (endpoints and
   service methods already exist, nothing calls them). Settle first:
   SolutionsInquiry standalone vs. ContactSales variant; QuoteRequest
   funnels toward structured V3 intakes rather than competing with them.
4. Alias mapping (`name`, `companyName`) then only matters for interpreting
   historical rows during the lead backfill — not live code.

**Lead-minting work, recommended order:**

1. **Fix the `BuildIntake` data-loss bug** — add contact columns to
   `DeploymentBuild` or write a parallel `FormSubmission` in
   `ConfigureController`. Standalone value regardless of the lead work; every
   day it ships later is contacts permanently lost.
2. **Decide the identity spine** — `Lead` vs `Contact`. Blocks everything else.
3. **Add an intent tier to `Lead`** (deposit pledge ≫ need intake ≫ waitlist)
   so the flooded inbox stays workable.
4. **Add lead→artifact linkage** (`LeadId` on artifacts, or a join table) —
   anonymous leads are useless in the inbox without it.
5. **Teach `ClaimResolution` email-matching** before minting, and stamp `UserId`
   onto matched anonymous leads. Prevents the best leads from doubling.
6. **Reconcile `DisplayId` minting** — pick the race-safe random scheme.
7. **Build the notifier lead sink** for the six anonymous surfaces (decide
   core-vs-web placement first).
8. **Backfill** from `FormSubmission` + `SellSubmission` + `LotDeposit` — last,
   once dedupe is proven.

Deferred / open questions:
- Automations runtime (execute `TriggerJson`/`ActionJson`) vs hardcoded mapping.
- Soft identity capture on preview endpoints — product decision, not just eng.
