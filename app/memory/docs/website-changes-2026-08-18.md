# Website Changes — 2026-08-18 (Full Day Summary)

**Project:** SLYD Platform website
**Date:** 2026-08-18
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

A consolidated record of everything that changed on `slyd.com` today. Four
parallel sessions worked the same repo and landed as four commits on branch
`content-governance-2026-08-18` (pushed, working tree clean):

| Commit | Time | Scope |
|---|---|---|
| `318bd5f` | 14:00 | Rebuild the 18 `/hardware` subpages against primary manufacturer sources |
| `d3e9519` | 14:01 | Govern the Resources cluster: source every claim or remove it |
| `90af22b` | 14:02 | Rebuild the commercial pages for claim truth: broker, sell, power, compute, need |
| `bbed059` | 14:03 | Add `/financing/lenders` capital-partner page |

Aggregate: **101 files changed, 21,808 insertions, 33,597 deletions**. The
net deletion is the point — the day removed far more published claim surface
than it added.

The single unifying theme across all four workstreams: **the site was
publishing precise-looking commercial and technical information with nothing
behind it.** Every page below was rewritten so that a claim either has a
recorded source, is operational output from a live endpoint, or does not
appear. Content, SEO, AEO, metadata, schema, internal links, and presentation
only — no controller, service, model, migration, admin screen, CRM mapping,
auth path, or form contract was changed anywhere in the day's work.

---

### 1. Commercial pages rebuilt for claim truth (5 pages)

Per five separate spec packages under `/Users/masongill/Slyd/*-claude-package-2026-08-17`.
Detail docs: [[broker-page-program-governance-rebuild]],
[[hardware-sales-page-commercial-truth-rebuild]],
[[power-opportunities-page-commercial-truth-rebuild]],
[[compute-marketplace-page-listing-truth-rebuild]],
[[need-intake-page-requirement-truth-rebuild]].

**`/broker`** — rewritten as a partner recruitment and governance surface.
Removed the unconditional "you earn a clearing fee on every deal that closes",
"SLYD originates, finances, and closes" as a universal claim, "sourcing is the
entire role", and the no-execution-responsibility claim. Compensation is now
governed by the applicable written agreement; no percentages, ranges, or timing
in copy or schema, and the `Service` block publishes no `Offer`. Modeled
structurally on `/financing/lenders`.

**`/hardware-sales`** — removed the "SLYD is actively buying right now" demand
rail: four cards (H200/H100/MI300X/A100) with per-node prices and quantities
wanted, driven by a hard-coded JS table random-walked every twelve seconds. Also
removed static seed prices ($1.5M–$1.7M, $32,000/node, $760K/$1.4M payments)
that JS overwrote on first paint — invisible to users, fully visible to
crawlers. Plus ±5% valuation precision, the universal 50/50 payment structure,
5–8 week timing, one-business-day quote and firm-offer promises, "no auction
discount", and universal inspection/burn-in/grading claims. Four disposition
paths now each read "Available when approved for the specific transaction".

**`/marketplace/power-opportunities`** — removed the fabricated demand rail and,
after escalation to Mason, **the entire operator-match display**: fit score,
operators-matched, forward books, invented operator archetypes, and the 6–10 wk
time-to-deal tile. The reasoning: the audit's second critical risk is matching
presented *before* SLYD has verified site control, interconnection,
deliverability, permits, or authority — and that objection holds whether or not
the number is live. Notably the "live" fit score was rendering the hard-coded
client defaults (7.0 / 3 operators) even with the platform running, so the
supposedly live values were themselves fabricated. Revenue estimate retained,
reframed as "Indicative only. Not a valuation or an offer."

**`/marketplace/compute`** — removed the universal platform promises with no
listing record behind them: instant deployment, 2–5 minute deploy time, scale
1 to 1,000+, "Live Inventory", real-time availability, universal CUDA/driver/ML
framework inclusion, per-second billing, preinstalled PyTorch/TensorFlow/vLLM/
TensorRT, autoscaling, load balancing, private networking, encryption at rest,
24/7 support, "50+ one-click AI tools", and the "under 5 minutes, no credit card
required" close. Replaced with listing-specific framing: software, support,
networking, tenancy, billing, fees, and deployment path belong to the individual
listing and never carry across.

**`/need`** — the odd one out: the job was editorial weight, not deletion. The
form already supported own / rent / advise equally, but the page read as a
compute rental preview. All three paths now carry equal weight without touching
the selector or its values. Retired "Live Match Preview", "No commitment, no
signup", "NO CREDIT PULL", and the universal "READY-SHIP · GRADE A/A-"
condition claim. Match vocabulary corrected throughout — a candidate is never
called a match before the responsible verification.

Also fixed in this batch: a broken query string (`&amp;` re-encoding produced a
parameter literally named `amp;source`), duplicate `BreadcrumbList` schema on
`/marketplace/compute`, and a mobile horizontal overflow from an inline
`grid-template-columns` out-specifying the responsive breakpoints.

### 2. The 18 `/hardware` subpages rebuilt (`318bd5f`)

Detail doc: [[hardware-subpage-cluster-rebuild]]. Every `.razor` page rewritten;
all 18 per-page scoped stylesheets deleted and replaced by one shared
`wwwroot/css/v3hwsub.css` with four family accents (accelerator / OEM / infra /
service). Removed across the cluster: static pricing, lead times, availability
and stock language, OEM partner/authorized/factory-direct claims, universal
warranty/support/SLA claims, 24/7 monitoring, certification claims, fabricated
case studies and project counts, and unsourced efficiency percentages.

Two P0 spec corrections verified against AMD's own current pages:
**MI355X FP4** claimed 20 PFLOPS against AMD's published **10.1 PFLOPs peak
MXFP4**; and the claim that all Instinct accelerators require liquid cooling,
when AMD publishes Passive OAM for MI300X/MI325X/MI350X. Nav gained four
previously orphaned routes. `/configure` had a hard-coded `source=configure`
that killed CTA attribution — it now reads and forwards an incoming `source`.

### 3. The Resources cluster governed (`d3e9519`)

Detail doc: [[resources-nav-cluster-governance]]. 16 routes. Two findings that
were not in the audit and matter most:

- **Fabricated structured data.** Both calculators emitted `aggregateRating` in
  JSON-LD (4.7 from 124 ratings on TCO, 4.7 from 89 on power). There is no
  rating system on those pages. Invented review data, eligible for rich results.
- **Electricity rates understated by a third.** Nine unsourced rates against EIA
  Electric Power Monthly for May 2026: Texas 6.5¢ published vs 8.26 actual, US
  average 10 vs 13.54, California 18 vs 24.10. Understating electricity biases
  every owned-versus-rented comparison toward owning.

Structurally: accelerator specs became a dataset (`Data/AcceleratorDatabase.cs`,
18 records each with source page and read date) so pages can't disagree with
each other; same pattern for server models. FAQ parity became structural — one
`FaqSection` component generates both the visible list and the `FAQPage`
JSON-LD, after four of six TCO answers and all six power answers had drifted out
of sync, and the OEM comparison's JSON-LD was offset by one. New governance
components: `SourceRegister`, `MethodologyNote`, `AnswerCapsule`. The
fail-closed rule removed ~120 currency figures, all per-OEM lead times, market
share, revenue, PUE, and every unsubmitted MLPerf figure. Cooling guide stopped
reproducing ASHRAE tables it was citing from superseded editions.

### 4. New page: `/financing/lenders` (`bbed059`)

Detail doc: [[financing-lenders-network-page]]. The capital-side counterpart to
the borrower financing pages — 12 sections, no new form. Every lender CTA goes
to `/contact-sales?source=financing-lenders`, with a new
`"Lender or Capital Partner"` interest option that the existing preselect logic
picks up, so inquiries carry both a distinct Interest value and the source tag.
Schema is WebPage + BreadcrumbList + Service + FAQPage with no numbers anywhere.
Seven analytics events via the `v3events.js` bridge, no PII.

---

## Cross-cutting patterns from the day

**Every removal was proven safe before it shipped.** The reusable method, built
independently in three sessions and worth keeping: a Python *contract extractor*
that hashes the `@code` block and enumerates every binding, handler, `data-spec`,
select option, input bound, and form element from the Razor source, plus a
Node *CDP probe* that drives the real page against the running platform API,
exercises both commercial branches, and captures the exact submit payload by
stubbing only the submit fetch so no record is written. Run before and after,
then diff. On `/need` this went further — the original file was restored,
rebuilt, and scanned across four accelerators, then the new one restored and
scanned identically; every preview data value matched.

**Inline and external operational JavaScript was preserved, not edited.**
`v3sell.js` untouched; the `PowerOpportunities.razor` inline script reproduced
byte-for-byte (SHA-256 pinned by a test) by extracting it to a file and
substituting it back programmatically. Removed markup degrades to no-ops
because every access is null-guarded — verified empirically, zero console
errors at four viewports. The cost: retired strings survive inside preserved
scripts where they cannot render. Flagged for a separate JS cleanup pass.

**og:image was removed from four pages, not replaced.** `og-broker.png`,
`og-hardware-sales.png`, `og-power-opportunities.png`, and `og-need.png` all
render claims retired today. Tests now assert each stays out. This is a blocking
approval dependency, not an oversight.

**Gotchas worth remembering.** Incremental `dotnet build` silently serves stale
Razor when the DLL timestamp is newer — use `--no-incremental` and grep the
served HTML. The executable is `bin/Debug/net10.0/Website`, not `Website.dll`,
so `pkill -f "Website.dll"` misses it; kill by port. Chrome headless
`--window-size` crops a desktop render rather than emulating mobile — use CDP
`Emulation.setDeviceMetricsOverride` with `mobile: true`. Razor `@* *@` comments
are stripped by the compiler, so tests scanning raw source produce false
positives; HTML comments do ship and must stay in scope.

## Verification across the day

- Build clean, 0 errors (2 pre-existing NuGet advisory warnings throughout)
- Tests: 250/250 at the end of the day, from a 23-test baseline — 174 new
  page-content tests plus 21 GPU database tests
- All routes 200; 0 broken internal links across ~900 link instances in the
  Resources cluster alone
- 0 invalid JSON-LD blocks; two fabricated `aggregateRating` nodes and two
  duplicate `Organization` nodes removed
- FAQ visible text byte-identical to `FAQPage` JSON-LD on every rebuilt page
- No horizontal overflow within page content at four to six viewports;
  ~156 screenshots captured
- No form submitted, no email sent, no auth or Docs behavior touched

## Related, not on the website

The admin app also shipped today: [[admin-intake-cleanup-form-spam]] — bulk
delete of form-spam intake across the derived graph, closing the cleanup gap
from the 08-17 SQLi triage. Different repo (`/Users/masongill/Slyd-Platform/admin`).

## To Do Next

Consolidated open items. The full detail sits in each linked doc and in
`documentation/resources-cluster/source-register.md` and
`documentation/hardware-cluster/source-register.md`.

**Blocking publication:**
1. **Sign off both source registers.** Reviewer is explicitly unassigned in
   both; no page may claim a reviewer until that changes.
2. **Legal sign-off** on: broker compensation/protection/conduct copy;
   hardware-sales payment, inspection and title language; power qualification
   and confidentiality copy; the `/need` credit-inquiry and draft-vs-submission
   wording; the `/financing/lenders` entity, licensing, participant types and
   compensation disclosure; and the reworded principal-risk statement on
   `/about`.
3. **Five og:image assets** — broker, hardware-sales, power-opportunities, need,
   financing-lenders. Approved 1200x630 real-infrastructure photography, no
   prices, counts, timelines or offer language. Tests assert the retired assets
   stay out.
4. **Confirm the four hardware disposition paths** are actually offered before
   they stay published; the spec says not to show unsupported paths.

**Bugs and defects, prioritized:**
5. **The `$0` degradation bug on power-opportunities.** With the valuation
   backend down, `calc()` returns zeros and the page renders "**$0 to $0**" and
   "$0 / MW·yr" as an apparent valuation. The script's own comment says it
   intends "—" placeholders. Screenshot kept at
   `shots/energy-1440x900-BACKEND-DOWN.png`. Pre-existing operational-code
   behaviour, but exactly the class of false economic claim this work exists to
   remove.
6. **MainLayout horizontal overflow.** The 340px off-canvas `v3nav-drawer` has
   no `overflow-x` clip on MainLayout, so every MainLayout page scrolls sideways
   on mobile. Confirmed on `/legal`, `/privacy-policy`, `/need`,
   `/ai-development`. One line in a shared layout; reported, not applied.
7. **Featured blog post data.** `/blog` renders the literal word "title" as its
   headline — the platform API returns `title` as the title field with the real
   headline in the body. Not fixable from this repo.
8. **JavaScript cleanup pass.** Now-dead code in `v3sell.js` (~lines 29-95) and
   the `PowerOpportunities` inline script: hard-coded demand tables,
   `Math.random()` walks, twelve-second `setInterval`s that update nothing, and
   the retired string literals they carry. JS-scoped change with its own
   verification.
9. **`V3Footer` uses `h5` for column headings**, producing an `h2 → h5` step
   site-wide including already-approved pages. Own pass.
10. **`v3nav-drawer` keeps ~46 focusable links inside an `aria-hidden`
    container when closed.** Site-wide accessibility fix.

**Content and data follow-ups:**
11. **Re-verify HPE, Supermicro and GIGABYTE** hardware facts directly — those
    sites time out or 403 from the build environment, so facts came from
    vendor pages surfaced via search.
12. **Dell XE9685L and XE9785L** omitted from the model table; add once their
    accelerator column is confirmed from Dell's spec sheets.
13. **`/about` evidence record** for 300+ MW, 150,000+ GPUs, 26 years.
    Attribution is corrected (the team's cumulative history, not SLYD's) but the
    record itself does not exist.
14. **Confirm the six careers roles** are approved and recruiting before
    `JobPosting` markup is added.
15. **Contact-sales attribution decision** for `/marketplace/compute`
    (`?source=compute-marketplace` changes admin-queue attribution, needs ops
    approval). Related: `/need` does not read query parameters at all today, so
    `?type=compute&source=...` is currently decorative.
16. **`/need` preview backend gap.** `TODO(need-preview-backend)` — coverage
    percentage, confidence, and per-source pricing render as em-dash
    placeholders. The content pass made the placeholders honest; it did not
    close the gap.
17. **Expose a pricing-config version and effective date** from the platform API
    so `/configure` can state which revision produced a result.
18. **Shared nav labels** still say "Become a broker" / "For brokers" in four
    places; realigning is a site-wide chrome change.
19. **Broker analytics events** deliberately not added; mirror the Lenders
    `data-analytics-event` pattern if funnel measurement is wanted.
20. **Add lender-network links** from `/financing/gpu` and
    `/financing/infrastructure` once those pages get their rebuilds.
21. **Governed public opportunity / listings module** remains absent by design
    (fail-closed) across both the power and hardware clusters. It is the
    sanctioned way to show real demand later.

**Release:** the branch `content-governance-2026-08-18` is pushed but this is a
coordinated gated release — `/financing/lenders` in particular is explicitly not
to be deployed separately, and the legal gates above precede publication.
