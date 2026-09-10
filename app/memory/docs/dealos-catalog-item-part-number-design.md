# Deal OS Catalog Item / Part Number Unification — Design

**Project:** SLYD Platform — Admin (Deal OS)
**Date:** 2026-08-13
**Author:** 96c0d8c7-31e1-4a56-8cae-e7247bc649be
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

### 2026-08-14: shipped — core v0.2.14, all four repos on development, CI green

The entire arc is out. Core `main` pushed and tagged `v0.2.14` (publish
workflow produced packages + the efbundle carrying all four migrations); admin
got 4 feature commits + a pin bump (0.2.13 → 0.2.14); platform got the taxonomy
commit + a pin bump (0.2.12 → 0.2.14 — its unpushed stage-translation work
reads the remapped DealStage, so the bump was required, not optional); website
got the pills commit. **Four pre-existing unpushed admin commits and two
platform commits rode along — the team received ~3 days of work.**

CI: admin build 1m39s (proving the freshly-published packages resolve — the
step we could not verify locally because the GitHub Packages feed 401s without
CI's token), deploy-development 10m2s including migrations; platform and
website success. Core releases are tag-driven from `main`; `origin/Development`
is stale and not part of the flow.

Open cosmetic item: core build warns on a duplicate
`using SLYD.Application.Interfaces.Services` — remove on the next core change.

### 2026-08-14: the Sourcing gate learns that inventory is a sourcing route

Mason hit the disconnect live: a BOM line 100% covered by an allocated lot could
not advance Sourcing → Quote Sent, because the gate required a selected quote on
every line. Root cause was structural — **Deal OS models two sourcing routes
(commercial = `SelectedQuoteId`, physical = `DealLineFulfillment` rows) and both
the gate and `Deal.Value` counted only the first**. `DealPipelineFeatures` had
zero references to fulfillments; deal value was `SUM(SelectedQuote.AmountUsd)`,
so an all-inventory deal was worth $0. The design comment said so out loud:
lots were assumed to be the *delivery* of quote-won goods, never the sourcing
itself.

**Mason's ruling (verbatim intent):** the gate checks exactly two things —
value above $0 *derived from selected quotes and ask from lots*, and every line
*100% fulfilled from either quote or lot or both*. And "don't make a shortcut —
a proper change."

**The proper change is one shared definition of "sourced": `DealValues`**
(internal static, same convention as `PriceObservations`/`CatalogLinks`),
holding both halves:

- **Coverage** — `IsFullyCovered(line)`: quote-covered units + committed lot
  units ≥ line quantity. A quote covers the units it priced
  (`SupplierQuote.Quantity`), or the whole line when it states none (the
  pre-unit-pricing reading of AmountUsd as a line total). Zero-quantity lines
  (lot-scoped/service) can't be counted in units, so any sourcing evidence
  covers them.
- **Value** — `Total`: each line's selected-quote amount in full, **plus
  committed lot units at each lot's per-unit ask, capped at the units the quote
  didn't cover, in commit order.** The cap is the load-bearing part: in the
  DESIGNED buy-then-deliver flow (quote wins, goods arrive as lots on the same
  line), the arrival adds nothing — without it, allocating delivered goods would
  double the deal's value. Pinned by `BuyThenDeliver_DoesNotDoubleCount`.
- **Evidence, never authority:** an unpriced lot's units count toward coverage
  but contribute $0 — coverage passes, the value gate blocks, and the fix is
  ops pricing the lot, not this code inventing a number from cost basis.

**Recompute now rides every input that moves the number**, same-save via an
overlay callback (the old `overrideAmount` pattern generalised, since staged
changes aren't visible to the DB query): quote select/deselect, fulfillment
commit/remove, **line quantity edits** (the quantity bounds the lot window —
new), and **lot repricing** (`SetPricingAsync` — new, guarded to the
fulfillment path only: a lot bound to a marketplace/proposal deal has no
fulfillment rows, and recomputing such a line-less deal would stomp its
proposal-set value to $0; pinned by a test).

**Adjacent hole closed:** `RemoveLineAsync` blocked deletion on sent RFQs but
not on fulfillments — deleting a lot-covered line would cascade the fulfillment
rows and strand the lot bound to the deal with nothing explaining why. Now
refused ("remove the allocations first"), matching the RFQ rule.

Gate labels now say what they check: "Every BOM line 100% covered (selected
quote and/or committed lots)" / "Deal value above $0 (selected quotes +
committed lot asks)". `LoadDetailAsync` gained `ThenInclude(SelectedQuote)` +
`ThenInclude(Fulfillments)` for the predicate. CRM's `SelectedQuoteId is not
null` projection was left alone — it's a "has quote" display fact, not a
sourced flag.

12 new tests (`LineCoverageAndDealValueTests`) including the reported scenario
end-to-end: lot-covered line, no quote anywhere, advances to QuoteSent with
value = qty × ask. Admin **331** green. **Postgres-verified** (probe, deleted):
the recompute's conditional-nav + nested-collection projection translates;
mixed 60-quoted + 40-committed line reads 60,000 → 108,000 → 60,000 across
commit and remove.

Old `RecomputeDealValueAsync` (quote-only) deleted from DealWorkspaceFeatures.

### 2026-08-14: the price chart was a black wedge — scoped CSS never matched it

Mason asked to "add some color" to the price history chart, which rendered as a
solid black triangle with no line. **Not a colour choice — a real bug, and one
worth remembering.**

**Blazor scoped CSS works by having the Razor COMPILER stamp a `b-xxxxx`
attribute onto every element it emits, and rewriting the stylesheet's selectors
to require it (`.area-chart[b-5cdd3xz78d]`). Elements created through
`RenderTreeBuilder` never receive that attribute, so every rule in the
`.razor.css` silently fails to match.** I had built the sparkline, area chart and
bid/ask ruler with `builder.OpenElement(...)`, so:

- the polygon got no `fill` and fell back to SVG's default **black**
- the polyline had `fill="none"` inline but its `stroke` came from CSS, so it was
  **invisible** — hence a black wedge with no line
- sparklines lost their red/green (`.spark.pos` never matched; they inherited
  the surrounding text colour)
- **the ruler was silently broken too** — `position:absolute` and the tick
  `::before` both came from CSS, so the marks never positioned

**Fix: rewrite them as Razor TEMPLATES (`=> @<element>…`) instead of builder
code.** Templated delegates are compiled markup, so they get the scope attribute.
Verified by emitting the generated C# (`-p:EmitCompilerGeneratedFiles=true`) and
confirming `AddAttribute(345, "b-5cdd3xz78d")` now lands on the `<svg>` — the
definitive check, since the failure mode is silent at both build and run time.

Colour, now that it can land: the chart paints entirely from `currentColor` —
stroke plus both gradient stops — so **one CSS property recolours the whole
chart**, and it is set by direction on the same polarity as the 90d column
(falling ask = good for us = green, rising = red). Fill is a gradient fading to
2% at the baseline rather than a flat block, so it reads as a line with volume
under it instead of a solid shape. Ruler ticks got a `box-shadow` glow in their
own colour and "our ask" moved to `--slyd-primary` so all three marks are
distinguishable.

**Rule of thumb worth keeping: in a `.razor` file, never build user-visible
markup with `RenderTreeBuilder` if it depends on scoped CSS. Use `@<…>`
templates.**

### 2026-08-14: local demo data for the Hardware Catalog

Seeded SLYD2 so the page can actually be looked at. Scripts live in the session
scratchpad: **`catalog-demo-seed.sql`** and **`catalog-demo-teardown.sql`**.

**Everything is tagged so removal is exact** — Accounts / CatalogPartNumbers /
Lots get ids starting `dddddddd-`, and every observation carries
`Notes = 'demo-seed'`. Teardown is four DELETEs and touches nothing else.

**Deliberately creates no Deals or Demands.** Those were wiped on purpose so the
new flow could be tested from scratch, and seeding fakes would muddy exactly the
thing the wipe was for. The visible consequence: buyer ceilings show "inbound" in
the DEAL column, because a ceiling's deal resolves through its source Demand.

Shape: 8 part numbers across H100/H200/B200/A100; 4 lots (H100 totals 1,152 units
held, matching the mockup); 22 supplier quotes including an eight-month H100 SXM5
decline 26,100 → 20,400 with two lapsed; one **model-level** ask with no part
named (so the "counts on the model, absent from every part" rule is visible); 6
buyer ceilings; 4 paid observations off the lot costs. H100 lands on the mockup's
figures — range $18,600–$27,600, SXM5 spread 17.6%, NVL "no bid".

**Regression the seed caught in my own rebuild: I had dropped the "N lapsed"
indicator.** A100's quotes have all expired, so the page showed a bare dash —
conflating "nobody quoted" with "everything lapsed", which is the exact
distinction the previous entry documents as mattering. Restored on both the model
band and the Whole model row.

**Pre-existing junk now very visible:** B200 carries a $50 ask and a $1,500 lot
ask from earlier UI testing, so its row reads range $50–$39,800, spread 87,900%,
90d −99.9%. Real data from Mason's own testing, so left alone — but it is the
loudest row on the page.

### 2026-08-14: Hardware Catalog rebuilt against Mason's mockup

Mason compared the shipped page to his mockup and the verdict was fair: **I had
built an evidence viewer for the ledger; he had designed a trading desk.** The
numbers were right, the page answered the wrong question — "what observations
exist for this model?" instead of "what should I do about this part right now?"
Rebuilt. Admin **314**, verified again on real Postgres.

**Rulings Mason gave, which settle the shape:**
- **Dark theme stays** — the mockup was light, the cockpit is dark; theme was not
  the ask.
- **A model with evidence but no parts must still show that evidence.** This
  killed the pure model→part→evidence hierarchy from the mockup.
- **A model row aggregates all its parts PLUS whatever is pinned to the model and
  to no part. A part row is only that part.** This is the rule the existing
  aggregate already implemented, now stated and tested from both directions.

**Structural fixes:**
- **Disclosure is now model band → part rows → evidence.** Was model → everything
  with a "scope" chip filter. The chip row was a *lens*, not a drill-down, and
  because the nested part table had different columns from the model table, every
  part-to-part comparison the mockup exists for was impossible.
- **A "Whole model" row sits first in the parts table** and expands to the
  aggregate. That is how a model with no parts still shows its evidence — it
  auto-opens when `PartCount == 0`. Cleaner than a special case, because every
  row in that table now behaves identically.
- The model band is a **grid, not a table row** — it is a header for what is
  under it, with a different information shape (big stats, no per-part columns).

**Two whole cards that were missing:**
- **Buyer ceilings** — `ACCOUNT | DEAL | QTY | CEILING | LOGGED | BASIS`. Asks and
  bids had been served as one "Observations" table with a `Side` column, which
  means reading a table half of whose columns are blank on any given row. A
  supplier quote and a buyer ceiling share almost no fields. **The DEAL column
  required resolving `observation.SourceId → Demand → Deal.DisplayId`** (falling
  back to "inbound") — without it a ceiling is a number with no way back to the
  conversation that produced it.
- **Bid / ask ruler** — the three figures placed to scale on one axis plus a
  plain-language verdict ("$3,600/unit of headroom — 17.6% gross at the
  ceiling"). **This is the only part of the page that interprets rather than
  reports, and it was the whole point of the mockup.** The verdict hedges itself
  when `Quotes.Count == 1 || Ceilings.Count == 1` ("Thin evidence — one quote or
  one ceiling is not a market"), because an unqualified verdict off a single
  observation is false confidence.

**New aggregate: the best-quote RANGE** (`$20,400–$27,600`). `AskRangeByModelAsync`
groups by `{CatalogItemId, PartNumberId}` — **the null-part bucket counts as its
own bucket**, so a model with no parts still has a range of one — takes each
bucket's best ask, and the model's range is min..max across them. A single "best
ask" hid that the parts under one model are quoted thousands apart. Collapses to
one figure when the range has zero width.

**Smaller gaps closed:** `Active`/`Expired` badges (was: a muted row), `no bid`
badge distinct from "no data" (asks with no interest is a worse signal than
silence), spread as a coloured badge, sparkline + 90d merged into one `90d price`
column the way a trader scans it, absolute dates instead of "2d ago" (relative is
useless for a quote you may need to cite), lead in **weeks** over 14 days,
best active quote highlighted green, price history as a **filled area chart with
an axis** instead of a table of months, lots rendered as cards with location and
margin instead of a cramped table.

**Bugs the comparison exposed in my own build:**
- **The "Lots we hold" card was overflowing and clipping** — `LOT-2026-0001` was
  wrapping one character per line and the margin column was cut off entirely. A
  6-column table in a `1fr` grid slot. Replaced with a card list; tables that
  remain got `table-layout: fixed` + ellipsis.
- **Model subtitle read "B200 / NVIDIA B200"** — I fell back to `Label`, which
  usually just restates the model. Now composes real specs (`700W · 80GB HBM`
  for GPUs, `gpu-server · DGX` for hardware) and only uses the label when it says
  something the model name does not.
- **Manufacturer was null for every GPU** — `GpuCatalogItem` has no manufacturer
  column. Now **borrows the manufacturer its part numbers agree on**, and shows
  nothing when they disagree rather than picking one.

**Still not buildable — schema gaps, now surfaced rather than hidden:**
- **BASIS (Stated/Signed/Inferred)** renders as an amber `unset` badge with a
  note saying these mix a signed commitment with a guess. Deliberate: an invented
  basis would be worse than a visible gap.
- Architecture / form factor / cooling for the subtitle — no fields, so the
  subtitle shows the part of the mockup's "Hopper · 700W SXM" that is real.
- Lot location is `IsoCode` only; the mockup's "Ohio · DC-3 bonded" needs a site
  and a bonded flag that `Lot` does not carry.

**Postgres re-verified** (probe since deleted) — the rebuild added a **nullable
Guid inside a composite GroupBy key**, a per-part `DateTimeOffset.Year/.Month`
grouping, and the `Demand → Deal` navigation projection, none of which InMemory
can prove. All translate. Live catalog now renders a real subtitle for all 17
models across 8 categories.

### 2026-08-14: the Hardware Catalog page is built (`/v3/pricing/catalog`)

The market-insight surface the whole catalog identity effort was building
toward. New: `HardwareCatalogModels.cs`, `IHardwareCatalogFeatures` +
`HardwareCatalogFeatures`, `HardwareCatalog.razor` (+ `.css`), one DI line, one
NavRegistry line, 14 tests. Admin **309** (was 295). Only two existing files
changed, both one-line registrations.

**The architectural line, and it is the point of the whole page.** Mason asked
up front whether the page would depend on the observation *sources*. It does
not, by construction:

- **Every price figure reads `PartPriceObservation`** — best ask, top bid,
  spread, last paid, 90d change, monthly history. Never the record that produced
  the price. So wiring a new source later (closed-deal clearing price, a pasted
  price list, supplier invoices) makes it appear on this page with **zero page
  or service changes**. A source that is not wired yet shows as a *missing*
  figure, never a wrong one.
- **Holdings are the one exception and read `Lot` directly** — units held, our
  ask, margin. That is current shelf state, not an observed price; the
  append-only ledger records what we once paid and structurally cannot answer
  "what do we have right now".

The first test (`AnObservationFromAnUnwiredSource_CountsExactlyLikeAWiredOne`)
pins exactly this, using `PriceObservationSource.Manual` — a source with no
writer in the product today.

**Absence is rendered as absence.** A model nobody has quoted reports null, not
0, at every level (DTO nullables, `HasNoMarketData`, "—" in the UI). A `$0` best
ask reads as a real and very good price rather than as silence, which on a
market page is the worst possible failure mode. `SpreadUsd` is null unless BOTH
sides exist — half a spread is not a spread.

**The asymmetry the Postgres probe caught, and why it is correct.** Expired
quotes are excluded from `BestAskUsd` but **kept in the history series and the
90d change**. I had not stated this explicitly and the probe surfaced it as a
surprising -52%. It is right, and the reasoning is load-bearing: a lapsed quote
is not a price you can still get (so it must leave "best ask"), but it *was*
true when observed — and since **every quote expires eventually**, filtering
expired quotes out of the history would leave the chart erasing itself from the
left as it aged. Now documented in the query and pinned by
`AnExpiredAsk_LeavesBestAsk_ButStaysInTheHistory`. The page shows an
"N lapsed" chip when best ask is null but quotes exist, so ops can tell "nobody
quoted" from "everything lapsed".

**Second thing the probe caught: a part-scoped price is also a price for its
model.** The model row is the union of model-level and part-level observations,
so it can beat any part-blind figure. The converse does NOT hold —
`GetPartsAsync` excludes model-level observations, because attributing a
model-granularity quote to one sibling part invents precision the quote never
had. Both directions are now tested.

**Aggregates are computed in SQL, not by loading rows** — conditional
`MIN/MAX(CASE WHEN …)`, `SUM(CASE WHEN … THEN 1 ELSE 0)` for the lapsed counter
(Sum-of-1 rather than `Count(predicate)` for translation safety), leaning on the
existing `(CatalogItemId, Side, ObservedAt)` index. The ledger only grows, so a
page that pulled every observation to count them would degrade with exactly the
history that makes it useful. One deliberate exception: **"last paid" is an
argmax, not an aggregate** — the value at the latest timestamp, which no GROUP
BY column can carry — so it is a second narrow pass over Paid rows only.

**Verified on real Postgres** in a rolled-back transaction (throwaway probe,
since deleted). This is not optional here: InMemory proves neither the
`DateTimeOffset.Year/.Month` grouping, the enum-inside-CASE comparison, nor the
conditional aggregates. All translated. Live check also confirmed the flattening
projection survives **all 17 models across 8 categories** — GPU-side and
hardware-side rows both render (B200: 1 observation, 8 units held).

**Razor gotcha worth remembering:** a switch expression with relational patterns
(`< 1 => "today"`) **fails the Razor parse** — the tokenizer reads the leading
`<` as an opening tag and the error surfaces ~130 lines later as "unclosed tag".
Rewritten as if/else with a comment saying why.

**Naming collision, unresolved and deliberate:** the Pricing Engine already has
a tab called "Hardware Catalog" (the editor for non-GPU catalog rows). The new
page carries the same name from Mason's mockup. Left alone rather than renamed
as an unrelated change — but the sidebar now has two "Hardware Catalog"-ish
things: one edits rows, one reads the market. Worth a rename decision.

**Nav note:** `AdminPageRegistry` projects from `NavRegistry`, so the route is
assignable immediately — but **existing non-wildcard roles will not have it
checked**, so the page is hidden for them until someone grants it.

Not built (deliberately, per "then we will just start creating the writing
sources"): the buyer-ceiling BASIS field, and the remaining observation writers.

### 2026-08-14: Demand Book drawer now shows who submitted a need

Buyer read "—" for every website need. **Root cause: `Demand` carries no name or
email at all.** The /need intake (`PublicV3IntakeController.SubmitNeed`) writes
the contact to a **parallel `FormSubmission`**, and links the two only by
putting the demand's DisplayId in the submission's `Subject` (plus a
`demandRef` payload key). **There is no foreign key between Demand and
FormSubmission** — the code comment says so outright.

But the drawer was also ignoring an identity it already had: **`Demand.UserId` →
`User` is a real FK**, set when the submitter claims the demand through the
claim-token flow. Both live demands had it populated. `User` carries only
`Email` (no name fields).

`ResolveSubmitterAsync` now returns email / name / leadId / origin:
- claimant email from `Demand.User` (a real FK) — origin "claimed account"
- **the FormSubmission is looked up EVEN WHEN a claimant exists**, because the
  account says who holds it now while the form carries the typed name and the
  `LeadId` — resolving only one would lose the single link back into CRM.
  Origin "intake form" when there's no claimant.
- Drawer renders a "Submitted by" cell with the origin label and a lead link;
  falls back to an explicit "anonymous — no account, no contact on the intake
  form" rather than a bare dash.

Also added `[SupplyParameterFromQuery(Name = "lead")]` to `LeadsInbox` — it had
**no query-param support at all**, so the lead link would have silently opened
the list and done nothing.

**Data-quality caveat worth knowing:** of 8 local NeedIntake submissions only 2
have a ContactName, 1 has a ContactEmail, and 2 have a LeadId. So the form path
is thin — the claimed-account path is the one that actually resolves today.

**Worth fixing properly:** put a real `FormSubmissionId` (or `LeadId`) on Demand
at intake time. The string join is best-effort by construction.

### 2026-08-14: demands can be created from the Demand Book

`/v3/crm/demand` was **read-only by design** — `IDemandBookFeatures` said so in
its doc comment, and the only ways a Demand came into being were the platform
intakes (website /need, configure, reserve, booking) and ops accepting a broker
submission. Ops had no way to record demand they simply knew about.

- **Core:** `DemandSource.Ops` **appended** to the enum (values are load-bearing
  and must never be reordered). No migration — the column is an int and
  `has-pending-model-changes` confirms the model is unchanged.
- **`DemandBookFeatures.CreateAsync`** — new `DMD-{year}-{seq}` DisplayId,
  audited `demand.created`. Ctor gained IAdminUserService / IAuditEventWriter /
  ICatalogResolver (which forced a fix-up of the existing read-only
  `DemandBookProcurementTests` construction).
- **Catalog-aware, same rules as BOM lines:** a picked part implies its model
  and a part from a *different* model is rejected; a picked model is
  **authoritative over anything typed**, so the stored `WantGpuModel` can never
  drift from the link; with nothing picked, the free-text model still goes
  through `ICatalogResolver`, so an uncatalogued demand lands with consistent
  casing and links itself if the model turns out to be catalogued after all.
- **A stated `PriceCeiling` writes a Bid observation** — this is the first
  bid-side data the ledger gets from a UI (the broker path already wrote one).
- **UI:** "New demand" button + inline form on the page, with the catalog model
  and part pickers from the BOM line, buyer account (via
  `IDealPipelineFeatures.ListAccountsAsync`), quantity, urgency, ceiling, ISO
  region, need-by, and a Term field that only appears for Compute. Category
  disables while a model is linked, because category is a fact about the
  hardware. Free-text model/subcategory fields only appear when nothing is
  picked. A footnote states the consequence: uncatalogued means string-only
  matching; a ceiling means a bid gets logged.

6 new tests. Admin 295, core 657+311+74.

### 2026-08-14: quote unit pricing + the price observation ledger

Migration `20260814145357_AddQuoteUnitPricingAndPriceObservations`, applied
locally. Admin 289, core 657+311+74.

**`SupplierQuote` gained `Quantity` + `UnitPriceUsd`** (both nullable, so
existing rows stay valid). `AmountUsd` REMAINS the authoritative line total —
deal value is still `SUM(SelectedQuote.AmountUsd)` and was not touched.
`ReconcileQuoteFigures` keeps the three consistent: unit × quantity defines the
total when both are given (that's the arithmetic the supplier did), a total plus
a quantity derives the unit, and a bare total stores as-is with no unit price.
**Validation had to move after reconciliation** — it rejected `AmountUsd <= 0`
up front, which would have refused a perfectly complete quote entered as
quantity × unit price with a blank total.

UI: the quote form takes quantity, unit price and total, with a live hint saying
which figure is being derived so the arithmetic isn't a surprise after saving.
The quote list now leads with unit price (`$21,100/unit`) and shows
`512 × $10.8M total` underneath, because totals only compare between quotes for
the same volume.

**`PartPriceObservation`** — the "track all cost" primitive. Append-only price
facts hanging off `CatalogItemId` (+ optional `PartNumberId`), with `Side`
(Ask/Bid/Paid/Sold), `Source` (SupplierQuote/DemandCeiling/LotCost/Manual),
unit price, quantity, lead, counterparty, and `ObservedAt` (when the price was
true, NOT when ops typed it). **Written from three paths today:** supplier
quote → Ask, lot cost basis → Paid (on create and on pricing edit, and only
when the number actually moved so unrelated edits don't spam the series),
demand ceiling → Bid.

`PriceObservations.Record` stages onto the CALLER's DbContext so an observation
can never survive a rolled-back quote or lot, and **returns null rather than
throwing when there is nothing comparable to file** — an unlinked line has no
model to file under, and a quote with no unit price has nothing to compare.
That silence is correct: the underlying write still stands.

**Design rule stated in the entity doc: evidence, never authority.** Nothing
here feeds back into `Lot.Price` or `Deal.Value`.

**Verified on real Postgres** (round-tripped in a rolled-back transaction, since
InMemory proves neither the enum/DateTimeOffset mapping nor SQL translation).
The rollup reproduces the mockup's numbers exactly: best ask $20,400, top bid
$24,000, spread $3,600/unit = 15.0% gross at the ceiling, plus a monthly
best-ask series for the price-history chart.

**Confirmed while wiring: `Lot.CostBasis` is PER-UNIT**, despite the entity doc
saying "cost SLYD paid for this lot" — the inventory drawer renders it
`$X/unit` and computes margin against `PricePerUnit`. Recording it as a unit
price is therefore correct; the doc comment is what's wrong.

### 2026-08-14: /hardware-sales GPU pills now derive from the catalog

Mason spotted that the public sell page hardcoded its GPU list. Investigation
found the page was **split**: the manifest model autocomplete and the indicative
price were already catalog-derived (`/api/v3/hardware-sales/taxonomy` reads
`HardwareCatalogItems`; preview resolves `GpuCatalogItem.SecondaryBuyInUsd` →
`HardwareBuybackConstants` → 400), but the six accelerator pills were literal
HTML in `HardwareSales.razor`. Cause: the taxonomy endpoint reads only the
HARDWARE catalog, and GPUs are deliberately excluded from that table (the admin
upsert rejects `category=Gpu`), so there was no GPU source on that endpoint.

Drift it had caused: page offered **GB200** (no catalog row at all), hid
**B300** (in the catalog), and listed **A100** (Deprecated) and **MI300X**
(Preview) with no indication. Ops editing the GPU catalog changed nothing.

**The constraint that shaped the fix:** you cannot just render "every Active
catalog row". `ComputeBuybackAsync` prices from a catalog row only when it is
**Active AND has `SecondaryBuyInUsd`**, else from constants, else **throws →
400**. B300 is Active with no buy-in and is not in constants — offering it would
have produced a pill that 400s on click. So `LoadQuotableGpusAsync` mirrors that
resolution exactly and returns only models that can be priced, plus
constants-only models (GB200) that are not catalogued at all — dropping those
would silently stop us buying hardware we do buy.

- **platform**: `HardwareTaxonomyResponse` gains `Gpus` (`GpuBuybackModel`:
  model, label, lowConfidence). No prices cross the public boundary.
- **website**: `V3HardwareTaxonomy` gains the field; `HardwareSales.razor` got
  its first `@code` block, fetching taxonomy in `OnInitializedAsync` and
  server-rendering the pills (no flash, works without JS). **A static
  `FallbackPills` list renders if the call fails — a sell page with an empty
  accelerator picker is a dead page.**
- **v3sell.js**: two hardcoded couplings removed — the initial `accel` state now
  reads the pill the server marked on (was `'h200'`), and `accelLabel` reads
  `data-label` off the pill instead of a hardcoded map that would have echoed
  `undefined` for any newly catalogued model.

**Verified against the live catalog:** the six rendered pills are byte-identical
to the six that were hardcoded (A100, B200, GB200, H100, H200, MI300X), so this
is a zero-visible-change refactor on current data. B300 is correctly withheld,
and setting its `SecondaryBuyInUsd` in a rolled-back transaction made it appear —
proving ops edits now reach the page. Platform 11 + 166 green; both repos build.

**Still hardcoded on that page (not touched):** the "Live demand signal" cards
carry per-model `pricePerNode` figures in `v3sell.js` (h200 32000, h100 19000,
mi300x 28000, a100 11000) that no longer match anything authoritative.

### 2026-08-14: lots + demands now link, and the deal domain was reset

**Resolver wired into the write paths (full swap, Mason's call).**
`IAssetModelCanonicalizer` replaced by `ICatalogResolver` in
`InventoryLotFeatures` (lot create), `SubmissionFeatures` (single-lot + manifest
conversion) and `BrokerOpsFeatures` (broker line → lot, broker submission →
demand). All five now store `CatalogItemId` alongside the canonical model
string. **Deliberate behaviour change accepted:** the resolver handles non-GPU
categories, so a server model typed `xe9680` now snaps to `XE9680` where the
canonicalizer left it as typed. Platform's 3 call sites still use the
canonicalizer and are unaffected — the interface stays for them.

Test churn this forced: new `FakeCatalogResolver` (deterministic `IdFor(model)`
so tests can assert the exact link), 6 test files swapped over, and the now-dead
`FakeAssetModelCanonicalizer` deleted — admin `src` has **zero** references to
`IAssetModelCanonicalizer` left. New `LotCatalogLinkTests` pins the two cases
that matter: a catalogued model links + stores canonical casing, an
uncatalogued one still creates a perfectly good lot, unlinked. Admin 282, core
657+311+74.

**Backfill dry run (findings kept; the run itself was overtaken by the wipe).**
11 of 18 lots and 25 of 31 demands would have linked. The 7 + 6 that wouldn't
were **not all junk** — alongside `ABC`/`abc`/`TTTT`/`100 GPUs`, it surfaced a
**Server-category lot AND demand both carrying model `H100`** (H100 is a GPU,
not a server model) and `144HGX servers` filed under **Cooling**. Real
mis-categorisations the link exposes. Worth expecting the same class of finding
whenever a backfill is run against real data.

**Deal domain wiped for clean testing (backup:
`scratchpad/slyd2-before-wipe.dump`, restore with `pg_restore`).**
Deleted: 14 deals (cascading line items → RFQs → quotes, fulfillments,
documents, parties, reps), 18 lots, 31 demands, 5 capacity listings, 30 intake
submissions (+12 seller payouts, cascaded), 19 deployment builds, 5 escrow
accounts, 91 match candidates, 1 broker ledger entry, 38 deal-scoped activities,
3,758 deal-scoped audit events. Kept: 8 accounts, 4 contacts, 9 leads,
2 brokers, 4 admin users, all 16 catalog models, pricing configs, and 77 CRM
activities / 122 CRM audit events. Zero orphans verified afterwards.

**Order gotchas worth remembering if this is ever redone:**
`LedgerEntries → Deals` is **RESTRICT**, so the commission ledger must be
cleared before any deal delete or Postgres refuses. `MatchCandidates` and
`AuditEvents` are **stringly-typed with no FK**, so they survive a cascade and
have to be named explicitly. `Auctions → SellSubmissions` is also RESTRICT
(harmless here at 0 rows). Converted submissions SET NULL rather than cascade,
which is why keeping them would have left 17 rows reading "accepted → converted
to nothing".

**Blocker for capacity testing: `Sites` is 0** (was already empty before the
wipe). A capacity listing needs a site, so one has to be created first.

### Two bugs found in UI testing and fixed (2026-08-13, end of day)

Mason exercised the BOM picker and caught both. Admin now 280 (4 new tests).

**1. Inventory candidates ignored the model entirely.** The "LISTED LOTS
MATCHING THIS LINE" panel filtered on **category + subcategory only**, so a GPU
line (which pins no subcategory) matched EVERY listed GPU lot — H200 inventory
offered against a B300 line. Pre-existing bug, not introduced by the catalog
work, but the catalog link is what makes it fixable. `LotCoversLine` now mirrors
the matching engine: equal `CatalogItemId` on both sides is a pure match, model
string is the fallback while either side is unlinked, and a line with no model
at all offers nothing rather than claiming a false match.

**The trap that bit me mid-fix (my own test caught it):** the subcategory filter
must be **non-GPU only**. GPU lines carry their model IN `Subcategory` while GPU
lots keep `Subcategory` null, so comparing the two rejects every lot. Same
carve-out `ProcurementLineProjection` already documents. This means legacy
GPU lines with model-in-subcategory had been showing *zero* candidates all
along — a second, opposite pre-existing bug in the same filter.

**2. The description went stale when the catalog model changed.** The picker
auto-filled the description from the catalog label, but `OnEditCatalogChanged`
deliberately never touched it ("don't clobber ops' words"), so switching A100 →
B200 left a line titled "NVIDIA A100 80GB" linked to B200. Confirmed in live
data (a line reading "NVIDIA H100 SXM5" linked to B300). Rule is now
`IsCatalogAuthored`: overwrite when the description is empty OR still verbatim
the label of the model being switched away from; never touch anything typed.

New `DealLineInventoryCandidateTests` pins all four cases: wrong-model excluded,
own-model matched regardless of casing, unlinked legacy GPU line still matching
on its subcategory identity, and no-model line offering nothing.

### Steps 2 + 5 SHIPPED (2026-08-13): resolver, part-number admin, BOM picker — UI-testable

**`ICatalogResolver` (core), deliberately NOT folded into `AssetModelCanonicalizer`.**
`core/src/SLYD.Application/Interfaces/Services/ICatalogResolver.cs` +
`Infrastructure/Services/Marketplace/CatalogResolver.cs`, registered scoped.
Returns `CatalogResolution(Model, CatalogItemId?)` — canonical string plus the
identity. Resolves BOTH categories, skips Retired, looks up through the
`CatalogItem` bridge so the returned id is the one entities link to.
*Why separate:* platform (3 call sites) depends on the canonicalizer, and
`AssetModelCanonicalizerTests` pins "the GPU catalog has no opinion about server
part numbers" as a deliberate decision. Changing that implicitly, inside a
schema feature, would have been a silent behaviour change to platform intake.
Consolidation is an explicit follow-up.

**Part numbers are admin-manageable.** `PricingAdminFeatures` gained
`ListCatalogItemsAsync` (both catalogs flattened to the one list entities link
to, retired excluded), `ListPartNumbersAsync`, `UpsertPartNumberAsync`,
`DeletePartNumberAsync`. Delete REFUSES when Lots/Demands/lines reference the
part — the FK is SetNull, so deleting would silently unlink records; the message
tells ops to retire it instead. New **Part Numbers tab** in PricingEngine
following the existing inline-row idiom exactly (`_pnEditId` null/Guid.Empty/id).
Creating a catalog model on either catalog tab now also refreshes the identity
lists so the new model appears in the part picker immediately.

**BOM lines can be linked while authoring.** `AddDealLineRequest` /
`UpdateDealLineRequest` / `DealLineRow` carry `CatalogItemId?` + `PartNumberId?`
(trailing optional params, so no existing caller broke).
`ResolveCatalogLinkAsync` enforces the constraint: a part implies its model
(fills it in), a part belonging to a DIFFERENT model throws. Picking a model in
the UI adopts its category + subcategory and fills an empty description with the
catalog label — a description already typed is left alone. Each BOM row now shows
a linked/`uncatalogued` chip, so matchability is visible at a glance.

**Seed job fixed:** `DemoSeedJob` created catalog rows directly and would have
produced rows with no identity — both loops now mint the bridge row.

**Verification.** Core 657+311+74, admin 276, both build 0 errors. Critically,
the admin suite runs on the **InMemory provider, which cannot catch Postgres
translation failures**, and the new catalog queries use conditional navigation
access plus a `PartNumbers.Count` subquery — so those were run against real
Postgres via a throwaway harness. All translated; the resolver correctly maps
`h200` AND `H200` to the same identity, leaves `RTX 6000 Ada` unlinked as free
text, and resolves non-GPU `dgx h100` → `DGX H100` (which the canonicalizer
never could).

**Local DB seeded for testing:** 16 catalog models (6 GPU, 10 hardware) matching
DemoSeedJob's values, every one with its identity row. Zero part numbers — that
is the first thing to create in the new UI.

### Step 1 SHIPPED (2026-08-13): schema layer, applied and verified

Core migration `20260813204121_AddCatalogItemAndPartNumbers` — purely additive,
applied to local SLYD2 and verified against the DB.

- `CatalogItem` / `CatalogPartNumber` domain entities
  (`core/src/SLYD.Domain/Models/DealOS/`), with the reasoning for the thin-bridge
  shape written into the class doc comments.
- EF config in `SlydDbContext`: filtered unique indexes on both bridge pointers
  (the unused side is null on every row, so a plain unique index would collide),
  unique `PartNumber`, `Cascade` from the underlying catalog rows down through
  the identity, `SetNull` from Lot/Demand/DealLineItem — deleting a catalog row
  drops those entities back to string matching rather than deleting inventory.
  All 17 delete rules verified in Postgres.
- Six nullable columns live: `CatalogItemId`/`PartNumberId` on `Lots`,
  `Demands`, `DealLineItems`.
- Backfill SQL in the migration mints one `CatalogItem` per existing
  `GpuCatalogItem`/`HardwareCatalogItem`, so the "identity exists per catalog
  row" invariant holds for pre-existing data, not just new rows.
- `PricingAdminFeatures` upsert paths (GPU + hardware) mint the bridge row on
  create, which also covers CSV import since it routes through the same upserts.
  Added via `db.CatalogItems.Add()` rather than a navigation — the client-set
  Guid PK gotcha from the DealRep work would otherwise make EF emit an UPDATE.
- Green: core 657 + 311 + 74, admin 276. Both build 0 errors.

**Finding worth acting on — the catalog is effectively empty, and the local data
is a live demo of the problem this design solves.** `GpuCatalogItems` holds
exactly ONE row (`H100`) and `HardwareCatalogItems` holds ZERO, while 18 Lots +
31 Demands reference: `H100`, `H200`, `h200`, `B200`, `ABC`, `abc`, `TTTT`,
`100 GPUs`, `144HGX servers`. So (a) the linking backfill in step 3 will link
almost nothing until the catalog is populated — populating it is now a real
prerequisite, not a cleanup; (b) `H200`/`h200` and `ABC`/`abc` are casing splits
that `AssetModelCanonicalizer` CANNOT fix today precisely because those models
aren't in the catalog — it's a casing authority with nothing to be authoritative
about; (c) several strings are quantities and descriptions, not models at all.

### Design session (2026-08-13, earlier)

Investigation + design session (no code). Goal: unify demands, BOM lines, and lots onto a
single hardware identity so matching, quoting, and pricing all speak one language across
Deal OS. Two parallel codebase surveys (entity models; matching/pricing flows) established
the current state, then the design was decided with Mason.

### Current state (verified findings)

- `GpuCatalogItem` (unique `Model`) and `HardwareCatalogItem` (unique `Category+Model`)
  both exist in core with admin CRUD + CSV import (`PricingAdminFeatures.cs`), but
  **no part-number/SKU/MPN field exists anywhere in Deal OS** (zero repo-wide hits;
  the only `Sku` is the unrelated marketplace storefront).
- **No FK from any entity to either catalog.** Hardware identity is a free-text model
  string everywhere: `Lot.GpuModel`, `Demand.WantGpuModel`, and on BOM lines the model
  is a hack — `DealLineItem.Subcategory` for GPU lines, unvalidated `SpecJson["model"]`
  for non-GPU (`ProcurementLineProjection.ResolveLineModel`). `"model"` isn't even a
  legal `AssetTaxonomy.AttributeKeys` entry.
- Matching = `OrdinalIgnoreCase` string equality on `(Category, Subcategory, model)`
  (`MatchScoringService.IsExcluded`, SQL prefilter in `MatchingEngineFeatures.LoadOpenDemands`).
  GPU is strict equality by design; non-GPU gets partial credit via
  `HardwareCatalogItem.Family` (string dictionary lookup, `CatalogAssetFamilyResolver`).
- `AssetModelCanonicalizer` snaps casing to `GpuCatalogItem.Model` — GPU only,
  best-effort, cannot map aliases ("H100 SXM" ↔ "H100-SXM5-80GB"), and is never called
  on BOM-line writes.
- Pricing is per-entity manual with no derivation chain. BOM deal value = sum of selected
  `SupplierQuote.AmountUsd` (line totals). Lot `Price`/`CostBasis` manual. Catalog prices
  (`CostUsd`, `BasePriceUsd`, `SecondaryBuyInUsd`) are reference lookups only (intake
  valuation, buyback ladder). This stays true in the new design.

### Decided design

**Catalog item = MODEL-level** ("H100", "DGX H100"). Part numbers are more granular —
one model has many OEM MPNs — and live as children of the model.

New tables (core):

- **`CatalogItem` (thin supertype/bridge):** `Id`, `Category`, one-to-one pointer to the
  type-specific row (`GpuCatalogItemId` xor `HardwareCatalogItemId`). Every existing
  catalog row gets exactly one. Purpose: gives all entities ONE stable FK now, so the
  eventual merge of the two catalog tables (deferred — "wait for unification") folds
  fields into `CatalogItem` without ever touching entity FKs or part numbers.
- **`CatalogPartNumber`:** `Id`, `CatalogItemId` FK, `PartNumber` (unique),
  `Manufacturer`, `Status` — the list of MPNs falling within that model.

Entity changes — **uniform two-level identity on all three** (scope: Lot, Demand,
DealLineItem only for now; intake lines and CapacityListing later, linking belongs at
convert-to-lot where canonicalization already happens):

- `Lot`, `Demand`, `DealLineItem` each get `CatalogItemId?` (the model — set early,
  drives matching, gives the deal shape pre-quote) and `PartNumberId?` (the specific
  part — hardens toward point of sale; "by point of sale it's a part, not a model",
  and supplier quotes need MPNs).
- Constraint: `PartNumberId`'s part must belong to the entity's `CatalogItemId`;
  picking a part can auto-set the model link.
- Existing model strings stay as denormalized display + fallback matching. **On link,
  the model string is snapped to the catalog's canonical model** (decided: yes).

Matching semantics (needs `ConstantsVersion` bump):

- Both sides linked + IDs equal → pure match (full model points).
- Either side unlinked → today's string compare, unchanged ("FKs read as a pure match
  but we don't rule out the models").
- Both linked but different → excluded for GPU, family fallback for non-GPU (same as
  today's string mismatch). Part number NEVER affects scoring — matching is model-level.
- Kills the Subcategory-as-model and SpecJson["model"] hacks for linked lines;
  unlinked lines keep working with existing `UnscoreableReason` surfacing.

Flows:

- BOM line creation: pick from catalog / create catalog item inline / skip (skip =
  degraded matching, surfaced via `UnscoreableReason`). Deal has shape before any quote;
  part number chosen from the item's list when known.
- "Every line has a part number" is a natural **stage gate** (fits existing
  `DealPipelineFeatures` gate checks) at whatever stage part precision becomes mandatory.
- Price: catalog stays reference/prefill (can prefill linked lines/lots); lot price and
  selected quote remain source of truth. No change to deal-value math.
- Backfill: string-join existing rows to catalog by model (canonicalizer logic);
  unmatched rows stay unlinked and surface as catalog gaps.
- Part-number data entry: PricingEngine catalog UI + CSV import extension + inline
  create from BOM authoring (decided: yes).

Future (noted, not designed): supplier quoting an alternate equivalent MPN → override
would live on `SupplierQuote`, not the line. GpuCatalogItem gaining Manufacturer/Family
waits for unification.

## Direction: the Hardware Catalog page (mockup reviewed 2026-08-13, not built)

Mason mocked up a `Hardware catalog` page and framed it as "a great place for
market insight". Shape: category filter pills (All/GPU/Networking/Storage/Power/
Cooling) over category groups ("GPU · 5 models · 11 parts · 1,676 units held"),
then **model rows → expand to parts → expand a part to evidence**. Model row
carries manufacturer, part count, units held, a best-quote/unit range, and a 90d
% change. Part table: PART | MODEL NUMBER | LEAD | BEST QUOTE | HELD | OUR ASK |
90D PRICE + sparkline. Expanded part shows three cards — *Quotes received*
(supplier, received, qty, unit, lead, Active/Expired), *Lots we hold* (LOT-259,
state, qty, cost vs ask, margin %), and *Price history* (best quoted unit price,
monthly, with HIGH/LOW/NOW).

**The page validates the two-level design** — it is organised exactly as
model → parts → evidence, and every number on it is a join through the catalog
link. Quotes reach a part via `SupplierQuote → Rfq → DealLineItem.PartNumberId`;
lots via `Lot.CatalogItemId`/`PartNumberId`. Both paths exist only because of
this work; before it, none of this page was expressible without free-text
matching.

**Free today (no new tables):** models/parts/counts from `CatalogItem` +
`CatalogPartNumber`; "Lots we hold" from `Lot` (DisplayId, State, Quantity,
`CostBasis` = cost, `Price` = ask, margin from those two); "Quotes received"
from `SupplierQuote` (+ supplier via Rfq, `ReceivedAt`, `LeadTimeDays`, and
`ValidUntil` giving the Active/Expired badge); best quote = min over that set;
price history + 90d delta = the same quote series bucketed monthly.

**Blocked on already-queued work:** nothing is linked yet — 0/18 lots and 0/6
BOM lines. Today the page would render models and parts with every evidence
column empty. Wiring the resolver into lot writes unlocks four columns at once
(units held, lots we hold, our ask, margin). Note the data is thin regardless:
only 3 lots have a CostBasis and exactly 1 has a Price.

**The one real schema gap — the page is per-unit and quotes are not.**
`SupplierQuote.AmountUsd` is a LINE TOTAL with no quantity of its own. A unit
price would mean dividing by `DealLineItem.Quantity`, which breaks exactly where
it matters: `Quantity = 0` is legal and meaningful for lot-scoped/service lines.
**Decision needed before any price column is built:** give `SupplierQuote` its
own `Quantity` + `UnitPriceUsd` (additive, preferred) vs derive-with-a-guard.

**Smaller gaps:** model subtitles are only partly derivable — "700W" is
`TdpWatts` and "48GB" is `HbmGb`, but architecture (Hopper/Blackwell/Ada/CDNA3),
form factor, and cooling are not fields. "Q1 27 allocation" encodes both a
delivery quarter and a *kind* of lead (allocation vs stock vs build-to-order);
we store lead as a day count only.

**Addition proposed (Mason hasn't ruled on it):** the mockup has two evidence
sources — supplier quotes (the ask) and lots we hold. The third is
`Demand.PriceCeiling` (the bid), reachable by the same join now that demands can
link. Bid vs ask on one row is what makes it market insight rather than a
procurement reference. Currently 0 demands carry a ceiling.

**Honest caveat:** price history accrues. There are 10 supplier quotes in the
entire database. The chart is real but earns its keep after months of quoting.

## To Do Next

Schema (1), resolver (2) and the BOM/part-number UI (5) are done and testable.

**Pick up here tomorrow:** wire the resolver into lot + demand writes (first item
below). It is both the next step in this plan AND the highest-leverage step for
the Hardware Catalog page above, since it unlocks four of that page's columns.
Get Mason's ruling on the `SupplierQuote` unit-price question before building any
price column on top of a division that can't always be done.

Remaining, in dependency order:

- ~~Build the Hardware Catalog page~~ — **DONE 2026-08-14**, see the top entry.
- **Remaining observation sources** (the agreed next step — the page reads the
  ledger, so each of these lights up columns without touching the page):
  closed-deal clearing price (→ Sold), manual
  price-list entry, supplier invoices. Platform's demand paths (public intake,
  DemandEditService) also set `PriceCeiling` and don't write observations yet —
  only admin's broker path does.
- **Buyer-ceiling BASIS (Stated / Signed / Inferred)** from the mockup is NOT
  built — `Demand.PriceCeiling` has no basis field, so a top-bid figure
  currently mixes a signed commitment with a guess.
- **Create a Site** — `Sites` is 0 and a capacity listing requires one, so
  capacity flows can't be tested until one exists.
- **Lot/demand link UI** — display the linked model + a part picker in the
  inventory and demand drawers (BOM lines have this; lots and demands don't).
  This is now the main gap: lots/demands link on WRITE but ops can't see or
  correct the link anywhere.
- **Matching goes FK-aware + `ConstantsVersion` bump.** No longer blocked on a
  backfill — the DB is empty of lots/demands, so everything created from here
  links on write. Flip the comparison and bump the version.
- **Backfill is moot locally** (nothing left to backfill) but the code path is
  still needed before this ships anywhere with existing rows.
- **Stage gate**: "every line has a part number". Still to decide which stage.
- **Consolidate `IAssetModelCanonicalizer` into `ICatalogResolver`** — decide
  whether non-GPU models should canonicalize (today they don't, deliberately),
  then migrate platform's 3 call sites and delete the narrower service.
- **Part-number CSV import**, matching the two catalog CSV paths.

Later: unify GpuCatalogItem/HardwareCatalogItem into CatalogItem; extend links to
intake lines and CapacityListing.

Note: this migration now stacks on the two uncommitted core migrations (stage
remap + deal reps) that were still unpushed when this work started.
