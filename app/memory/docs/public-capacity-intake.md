# Public Capacity Intake (CapacitySubmission)

**Project:** SLYD Platform (core + platform + website + admin)
**Date:** 2026-08-20
**Author:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Phases 1–3 (plus 5) of the public compute-capacity intake. Posting spare GPUs
used to require signing up, requesting an account, requesting operator status,
sending documents, and waiting for ops to clear all of it before you could
submit anything — none of it documented publicly. This replaces that with a
public form.

Phase 0 (`SiteSubmission` → `Site` conversion) shipped first and is documented
separately in [site-submission-to-site-conversion.md](site-submission-to-site-conversion.md).

### Why a separate entity instead of writing CapacityListing directly

Mason initially proposed writing `CapacityListing` rows straight from the form
in `PendingReview`. The decisive argument against it was not spam, it was that
**a listing structurally cannot hold a public submission**:

- `CapacityListing` has no region, notes, or contact fields. Its location comes
  only through `SiteId`, an FK to an ops-managed `Site`. An anonymous submitter
  has nowhere to say where their capacity even is.
- `CapacityRegionScorer` scores a siteless listing **0 forever** (its own doc
  comment says so), so ops must create a `Site` during review regardless — the
  conversion step is unavoidable either way. The only question was whether the
  pre-conversion data got a structured home or lived in a `FormSubmission`
  string dictionary that ops hand-copies from.
- It preserves stated-vs-verified. `AskRatePerGpuHour` is deliberately NOT
  named `RatePerGpuHour`: the listed rate is an ops decision, and merging the
  two would lose the difference between what they asked and what we list. Same
  stance as `Lot.BrokerEstimateUsd`.

A useful side effect: this killed the `Reviewed` state we were about to add to
`CapacityListingState`. "Vetted but not public" is just
`CapacitySubmission.Converted` + the resulting listing sitting in
`PendingReview`.

### Phase 1 — data structures (core)

`CapacitySubmission` mirroring `SiteSubmission` in four blocks: stated fields,
`Status` + conversion link, audit/customer-edit tracking, and the claim-token
block verbatim.

**Twelve stated fields** (first pass — Mason approved proceeding without
finalising the list, since no data exists and columns are cheap to change):
`GpuModel`, `GpuCount`, `PowerKw?`, `Region?`, `Availability?`, `OnlineAt?`,
`AskRatePerGpuHour?`, `TermMonths?`, `CommittedRatio?`, `Hosting?`,
`NetworkFabric?`, `Notes?`. Only the first two are non-nullable.

`CapacitySubmissionStatus`: `Submitted → InReview → Converted`, with
`Declined`/`Withdrawn` terminal. Private setter, `Transition()` guard.

`ICapacitySubmissionRepository` + implementation including `ClaimAsync` with
the execution-strategy-wrapped transaction and compound race guard, calling
`ClaimResolution.ResolveAsync(..., "capacity-claim", ...)`. Non-members mint an
inbound **Lead** rather than auto-minting an account — that lead conversion IS
the "we create the account for them" step Mason described.

Migration `20260820160642_CapacitySubmission` — new table, six SetNull FKs,
filtered unique `ClaimToken` index.

### Phase 2 — public endpoint (platform)

`POST api/marketplace/capacity/submit`, `[AllowAnonymous]`, in
`PublicV3IntakeController` alongside the other four V3 intakes. Mints the
submission + claim token, writes the parallel `FormSubmission` under new
`FormTypes.CapacityIntake` with a `capacitySubmissionRef` field, notifies ops,
writes a `capacity-submission.submitted` audit event.

`CommittedRatio` is bounded to 0–1 because **80 means someone typed a
percentage**, and there is no way to detect that later — it would become a
listing stamped 8000% sold at conversion. GPU model goes through
`_modelCanonicalizer` so `"h100"` and `"H100 SXM"` don't land as distinct
supply.

### Phase 3 — website form + claim page

`/marketplace/list-capacity` — interactive Blazor following the `ContactSales`
pattern (`EditForm`, component-library `TextInput`/`SimpleDropdown`, per-field
validation). Linked from `/marketplace`'s CTA strip next to "Bring energy" and
added to the sitemap.

- The form **says "everything below is optional"** above the optional block. The
  premise is that an operator can stop after two fields; a long form implies
  otherwise unless you say it.
- Numeric fields are **strings**, so an empty optional input stays empty rather
  than rendering a `0` to clear.
- Committed capacity is asked as a **percentage** (how operators think) and
  converted to the API's 0–1 ratio client-side, keeping the endpoint's contract
  single-meaning.
- Only `WebPage` schema, no `Offer`/`Product` — marking it up as an offer would
  claim availability SLYD has not verified.

`/capacity/claim/{token}` on platform mirrors `SiteClaim`, including two-tab
race handling. Claiming is optional by design and every failure state says the
capacity is on file regardless.

### Phase 5 — spam cleanup (admin)

`IntakeCleanupFeatures` keys off `<entity>Ref` fields on `FormSubmission`; added
`capacitySubmissionRef`, a `CapacitySubmissionIds` set, the `RemoveRange`, and
those ids to `AlertTargetIds`. Converted rows stay deletable on purpose —
`ConvertedCapacityListingId` is SetNull, not Cascade, so a spam purge can never
reach through into a live marketplace listing. Tested.

New test class rather than extending `IntakeCleanupFeaturesTests`, whose shared
flood fixture asserts exact per-table counts.

### Verification

core 688 · admin 380 · platform 174 · all builds green.

Website suite: **55 pre-existing failures, none from this work** (verified
against a stashed baseline). See To Do Next.

### Commits (all local, nothing pushed)

- core `feat/capacity-submission` (stacked on `feat/capacity-listing-archive`):
  `daa37c2` entity + repo + migration, `564470d` FormType
- platform `development`: `9c64841` endpoint, `ab4d92a` claim page
- website `development`: `6e997c6` intake form
- admin `development`: `134d91a` cleanup wiring

## To Do Next

### Fix PowerOpportunitiesPageContentTests (55 failing tests)

`tests/Website.Tests/Pages/PowerOpportunitiesPageContentTests.cs` throws in its
**static constructor**, so all 55 tests in the class fail with
`TypeInitializationException`. Root cause at line ~31–40:

```csharp
private static readonly string InlineScript =
    Regex.Match(PageRazor, @"<script>(?<body>.*)</script>", RegexOptions.Singleline).Groups["body"].Value;

private static readonly string PageMarkup =
    Regex.Replace(PageRazor.Replace(InlineScript, string.Empty), ...);
```

`PowerOpportunities.razor` has had **no inline `<script>` block since commit
`6b0fa86 "remove buttons"`**, so `InlineScript` is `""` and
`String.Replace("")` throws `ArgumentException: The value cannot be an empty
string. (Parameter 'oldValue')`.

Fix is a guard — only strip when the match is non-empty:

```csharp
private static readonly string PageMarkup =
    Regex.Replace(
        string.IsNullOrEmpty(InlineScript) ? PageRazor : PageRazor.Replace(InlineScript, string.Empty),
        @"@\*.*?\*@", string.Empty, RegexOptions.Singleline);
```

Then re-run and check whether the individual content assertions still hold —
the page has changed since those tests were written, so some may legitimately
need updating rather than the guard alone making them pass. Deliberately NOT
fixed in this session: there was in-flight uncommitted work on that page at the
time, and touching it looked likely to collide.

### Remaining capacity-intake work

**Phase 4 — admin queue + conversion.** `ICapacitySubmissionBookFeatures`
mirroring `ISiteSubmissionBookFeatures` (list/get + MarkInReview/MarkDeclined/
Withdraw), plus `ConvertAsync`. Reuses the Site creation from Phase 0 — the
convert form needs a Site picker with "create new", since a capacity listing
without a Site scores 0 on region forever. **Conversion must mint the
CapacityListing as `PendingReview`, NOT Approved** (unlike `CreateListingAsync`,
where ops-creation is self-approval). That is what gives "reviewed but not
public" with no new enum value.

**Confirm the STATED field list** before this hardens — twelve fields shipped
as a first pass.

### Then: Need Compute (separate work stream)

- `/need` gets a HARDWARE/COMPUTE toggle; the `own`/`rent`/`open` consumption
  selector is **dropped entirely** (Mason's call), requiring a rewrite of the
  FAQ, structured data, and "three consumption paths" section on `Need.razor`.
- `PublicV3IntakeController.SubmitNeed` hardcodes `Type = DemandType.Hardware`.
  **Live bug:** every "Rent capacity" submission to date is a Hardware demand,
  and `MatchRefreshJob` only ranks `DemandType.Compute` against capacity
  listings, so they structurally cannot match.
- `GatedMarketplace.razor:99` "Request hardware" is tab-independent
  (`OpenPostNeed` sets `_needHardware = false`, never reads `_tab`), and
  `MarketplaceIntakeService.cs:222` hardcodes Hardware. Make both follow the tab.

### Ship order

core is consumed as NuGet. core PR → release → bump `SLYD.Infrastructure` in
`admin/src/Admin/Admin.csproj` and platform's csproj → deploy. Two migrations
pending: `CapacityListingArchive` and `CapacitySubmission`. Both additive.
