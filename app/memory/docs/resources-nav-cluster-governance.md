# Resources Navigation Cluster: Content and Truth Governance Pass

**Project:** SLYD Platform website
**Date:** 2026-08-18
**Author:** 3d03f149-0de7-49d6-975d-45f036b6bf58
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Implemented the `slyd-resources-nav-audit-2026-08-17` package across the 16
routes in the Resources navigation. Content, SEO, AEO, metadata, schema,
source governance, and internal links. No calculator formula, form field,
validation rule, backend call, or auth path was changed.

### The shape of the problem

The audit framed this as stale counts and broken links. The larger issue was
that the cluster published a great deal of precise-looking information with
nothing behind it, and in several cases the numbers were not merely stale but
wrong in a direction that flattered SLYD.

Two findings stand out and were not in the audit:

- **Fabricated structured data.** Both calculators emitted `aggregateRating`
  in JSON-LD: 4.7 from 124 ratings on the TCO calculator, 4.7 from 89 on the
  power calculator. There is no rating system on those pages. This is invented
  review data eligible for rich results.
- **Electricity rates understated by a third.** The power calculator published
  nine unsourced rates. Against EIA Electric Power Monthly for May 2026: Texas
  6.5 cents published against 8.26 actual, US average 10 against 13.54,
  California 18 against 24.10. Understating electricity biases every
  owned-versus-rented comparison toward owning.

Also corrected: the training guide's cloud table listed Lambda H100 at
$2.10-2.99/hr when Lambda publishes $3.99 per GPU-hour.

### Structural decisions

**Accelerator specs became a dataset.** `Data/AcceleratorDatabase.cs` holds 18
records, each with the manufacturer page it came from and the date it was read.
`/resources/gpu-database` renders cards and its comparison table from that one
list, so the two cannot disagree, and every other page links to it rather than
carrying a second copy. This is what let the guides stop being duplicate spec
sheets, which the audit asked for. Same pattern for server models in
`Data/ServerModelCatalog.cs`.

Note on naming: `Data/` and `AcceleratorDatabase` read like data access and
caused a "why are you accessing my db" question mid-session. They are static
in-memory arrays with no DbContext, connection string, or network call. Mason
chose to keep the names; both files carry a header comment saying what they are.

**FAQ parity became structural.** `FaqSection` generates the visible `<details>`
list and the `FAQPage` JSON-LD from one `List<FaqItem>`. Before this, four of
six answers on the TCO calculator and all six on the power calculator had
drifted out of sync with the markup claiming to reproduce them, and the OEM
comparison's JSON-LD was offset by one so two answers were attached to the
wrong questions.

**Governance components.** `SourceRegister`, `MethodologyNote`, `AnswerCapsule`,
plus `SourceEntry`/`ClaimBasis`. Deliberately lightweight so pages keep their
own layout rather than collapsing into one template.

**Server versus OEM comparison separated.** Both pages previously covered market
share, lead times, support tiers, and server specs, so they competed. Server
comparison is now named models with a vendor source per entry. OEM comparison is
the relationship: geography, procurement path, support model, lifecycle, and
what to get in writing. It names no vendor in its fit guidance, because which
vendor satisfies a criterion depends on the buyer's countries and channel.

### The fail-closed rule did most of the work

The package says dynamic commercial claims fail closed when the record is
missing. Applied honestly that removed a lot: ~120 currency figures, all
per-OEM lead times, market share, revenue, price positions, efficiency
percentages, universal rack-density thresholds, per-technology PUE, and every
throughput and MLPerf figure that lacked a submission.

The guides got shorter and considerably more useful. The training guide now
resolves its own contradiction (it said 18 bytes/parameter beside a table built
on 6) by showing the per-component budget so the arithmetic is checkable. The
inference guide gained the KV cache formula, which is what actually decides
serving capacity and was entirely absent.

### The ASHRAE finding

The cooling guide attributed specific temperature envelopes and coolant
chemistry limits to ASHRAE. ASHRAE TC 9.9's own site records that in 2024 that
content moved into the subscription Datacom Encyclopedia, that the liquid
cooling guidance was "almost entirely rewritten", and that it introduces new S
Classes for Technology Cooling System supply temperature. A TC 9.9 white paper
exists specifically to correct misunderstandings in the last printed edition.

So the page was citing superseded editions. The Encyclopedia is paywalled and
could not be read. The guide now names the authority precisely and reproduces
none of its tables, which is the only honest option.

### Two audit findings did not reproduce

The live site is behind the repo. The `/guides` breadcrumb is already
`/resources#guides` in all three guides, and Docs has no breadcrumb parent links
and no BreadcrumbList at all. Reported rather than "fixed".

## Results

- 16/16 routes HTTP 200, **0 broken internal links** across ~900 link instances
- 15/16 clean on content, metadata, canonical, single-H1, and FAQ parity
- **0 invalid JSON-LD blocks**; added AboutPage, ContactPage, CollectionPage;
  removed two fabricated aggregateRatings and two duplicate Organization nodes
- 13/16 clean on accessibility and responsive at six viewports; the three
  remaining are pre-existing interactive markup the boundary protects
- 250 tests pass, 48 screenshots captured
- No form submitted, no email sent, no auth or Docs behavior touched

## Gotchas worth remembering

**Incremental build silently skips Razor changes.** Mid-session `dotnet build`
reported success while serving stale content, because the DLL timestamp was
newer than the `.razor` files. Cost real debugging time chasing "FAQ mismatch"
errors that were actually stale output. Use `dotnet build --no-incremental`
after Razor edits, and verify with a grep against the served HTML.

**Validators need to know about governed omissions.** `/broker` deliberately
ships without an `og:image`, documented in the component, because the previous
asset rendered retired claims. A validator that flags it as a defect pushes
someone to re-add the withdrawn image. The exemption is now in `resvalidate.py`.

**Audit hidden elements out of a11y checks.** The Blazor reconnect overlay sits
`display:none` in every page's DOM and produced 36 false heading-order failures
before the auditor learned to skip non-rendered elements.

## To Do Next

Everything below needs a human, and is itemised with detail in
`documentation/resources-cluster/source-register.md`.

- **Sign off the source register.** Reviewer unassigned; no page may claim one.
- **`/about` evidence record** for 300+ MW, 150,000+ GPUs, 26 years. Attribution
  is now corrected everywhere (team's cumulative history, not SLYD's), but the
  record itself does not exist.
- **Legal review** of the reworded principal-risk statement on `/about`.
- **Confirm the six careers roles** are approved and recruiting before
  `JobPosting` markup and per-role routes are added.
- **Re-check HPE, Supermicro, GIGABYTE** server details directly. Those three
  sites time out or 403 from the build environment.
- **Expose a pricing-config version and effective date** from the platform API
  so `/configure` can state which revision produced a result.
- **Fix the featured blog post data.** `/blog` renders the literal word "title"
  as its headline: the platform API returns `title` as the title field, with the
  real headline in the body. Not fixable from this repo.
- **MainLayout horizontal overflow.** The off-canvas `v3nav-drawer` is 340px
  wide with no `overflow-x` clip on MainLayout, so every MainLayout page scrolls
  sideways on mobile. Confirmed on `/legal`, `/privacy-policy`, `/need`,
  `/ai-development`, none touched by this work. One line in a shared layout,
  reported rather than applied.
- **Not committed and not deployed.** The working tree also holds a concurrent
  Financing workstream (`ContactSales.razor` interest option,
  `SitemapController.cs` entry, `Financing/Lenders.razor`) and the previous
  session's hardware cluster. Separate before committing.
