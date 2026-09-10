# Website Hover Affordance Sweep — Non-Interactive Elements

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

First pass of a broader styling cleanup. The rule applied: **if an element is not clickable or
interactive, it gets zero hover animation.** Cards that lift, glow, and shift borders on hover
promise a click target that doesn't exist — the user reads it as a bug, clicks, and nothing happens.

Removed **247 hover selectors across 58 stylesheets** (−1,076 lines). CSS only; no markup changed.

### Scope decisions (confirmed with Mason before editing)

| Question | Decision |
|---|---|
| Table row hovers (`tr:hover`, row tints) | **Left alone** — 42 selectors skipped. Row highlight is a readability aid on wide spec tables. |
| Shared `component-library` (SLYD.Components) | **Out of scope** — website only, to avoid blast radius on admin/platform. |
| Dead CSS found along the way | **Dead hover rules removed**; other dead CSS reported, not touched. |

### Method

Hand-auditing 627 grep hits was not viable, so I built a classifier
(`scratchpad/classify3.py`) that parses every first-party stylesheet and cross-references each
hover selector against actual markup. Key correctness requirements, each of which produced wrong
answers until handled:

1. **Ancestor tracking.** A `<div class="card">` wrapped in an `<a>` *is* hoverable. The parser
   maintains a tag stack so an element inherits interactivity from any ancestor. Without this,
   every link-wrapped card is a false positive.
2. **Blazor scoped CSS.** `X.razor.css` only applies inside `X.razor`. Lookups are scoped to the
   sibling component, not global. Without this, a class name reused elsewhere resolves against
   the wrong markup.
3. **Compound selectors.** In `.showcase-card.dell`, `.showcase-card` is the element and `.dell`
   a modifier — take the *first* class, not the last.
4. **Functional pseudo-classes.** `.share-row:not(.header):hover` was resolving its subject to
   `.header`, stolen from inside the `:not()`. Strip those before tokenizing.
5. **Scrollbar pseudo-elements.** `::-webkit-scrollbar-thumb:hover` looks static but a scrollbar
   thumb is draggable. Excluded explicitly.

Interactive = tag in `a/button/input/select/textarea/summary/label/details`, or `NavLink`, or
carrying `@onclick`/`href`/`role="button"`/`tabindex="0"` — on the element **or any ancestor**.

Final tally: 324 KEEP_INTERACTIVE, 247 removed, 42 table rows skipped, 2 scrollbars kept.
The 26 genuinely ambiguous cases were resolved by reading markup individually.

### What was removed

Declarations stripped: `border-color` (114), `transform` (77), `box-shadow` (47),
`background` (27), `opacity` (5), plus a few `filter`/`color`/`animation`.

Two categories:

- **Static elements with hover effects (~139):** `.careers-benefit-card`, `.feature-card`,
  `.tco-card`, `.thermal-card`, `.docs-*-card` family, `.mp-product-card`, `.equipment-card`,
  `.category-card`, and the OEM `.showcase-card.dell|hpe|lenovo|supermicro|gigabyte` variants.
  All plain `<div>`s containing text, sometimes with a link *inside* — the inner link keeps its
  own hover, the container no longer pretends to be one.
- **Dead rules (~108):** hover rules for classes that exist in no markup the stylesheet can
  reach — `.component-card`, `.menu-item`, `.toc-link`, `.code-action`, `.mobile-search-btn`,
  `.in-development`, `.btn-brand-primary/-secondary`, `.btn-outline-cyan`, bare `.card`.
  Each was confirmed absent from `.razor`/`.cs`/`.js` before deletion.

Also removed `cursor: pointer` from `Components/Shared/Cards/CategoryCard.razor.css`. That card
is a static `<div>` whose only link is a child element — the pointer cursor was the same false
promise as the hover, so it went with it. This is the only non-hover declaration touched.

### Verification

- `dotnet build --no-incremental` — succeeded, 0 errors (9 warnings, all pre-existing in
  `component-library`).
- `dotnet test` — **250/250 passed.**
- **Automated integrity check** on all 58 generated files before writing: brace balance and
  zero empty rule bodies. This caught a real bug — the first applier computed match offsets
  against comment-stripped source but applied them to the original, and the stripper wasn't
  length-preserving, so it shredded files mid-declaration (`border-radius: 1e-info strong {`).
  Fixed by blanking comment characters in place. **Always dry-run and validate before writing.**
- **Live CDP probe** (`scratchpad/probe2.mjs`) against `localhost:5000`: drives a real mouse
  over each element and diffs computed style before/after, with an `elementFromPoint` hit-test
  guard so an element hidden behind a sticky nav isn't misreported as "hover removed."
  Result **10 pass / 1 explained / 1 absent**:
  - inert as intended: `.careers-benefit-card`, `.careers-job-card`, `.careers-culture-stat`,
    `.benefit-card`, `.process-card`, `.equipment-card`, `.tco-card`, `.thermal-card`
  - still reacts, as intended: `.v3nav-btn-ghost`, `.need-door`
  - the one "failure" was a generic `a[href]` on `/careers` with no hover styling of its own —
    pre-existing, and that file's diff only removed card rules.
- **Probe control test:** injected an element with a known hover rule and confirmed the probe
  detects the change. Without this, "no change detected" is indistinguishable from a broken
  probe — and two earlier readings *were* probe artifacts, not regressions.

### ⚠️ Concurrent session in this repo

While working, **another Claude Code session was editing the same working tree.** 34 `.razor`
files plus `wwwroot/js/hero-reveal.js` (a hero slide-up reveal feature) appeared in `git diff`
that I did not write — timestamps 10:02–10:03, minutes after my CSS landed at 09:59:32, with
three `claude` processes live. Verified before finishing:

- My footprint is exactly the 58 CSS files I intended; no CSS was changed by anyone else.
- One overlap — `wwwroot/css/shared-components.css`. My three hover removals survived intact,
  and their additions (`[data-hero-reveal]` opacity + a `prefers-reduced-motion` block)
  introduce **no new hover rules**.

**Nothing of theirs was reverted.** Anyone committing this branch must separate the two changesets.

## To Do Next

**Directly related to this rule (natural next passes):**
1. `cursor: pointer` audit — 181 rules use it. `.docs-phase-header` and
   `.instances-phase .phase-header` are static `<div>`s with pointer cursors; confirm whether a
   JS accordion makes them clickable, and if not, remove. (I scanned but only fixed
   `.category-card`, where it paired with a hover I was already removing.)
2. **The inverse defect:** interactive elements with *no* hover feedback. The `/careers` anchor
   the probe caught is one. A link that looks inert is the same class of bug in reverse, and
   the design system explicitly requires hover states on interactive elements.
3. Orphaned `transition` declarations left on elements whose hover is now gone. Harmless
   (dead weight, no visual effect) but worth a tidy pass.

**Dead code found, deliberately not actioned:**
4. `Components/Pages/Resources/ServerComparison.razor.css` contains a large block of rules for
   classes absent from its component (`.showcase-card`, `.position-card`, `.share-row`,
   `.use-case-row`) — the file was copied from the standalone `Docs/enterprise-ai-servers-comparison.html`
   artifact. Same pattern in `OEMComparison.razor.css`.
5. **14 stylesheets in `wwwroot/css/` are referenced nowhere** — not in any `.razor`, and no
   `@import` chain reaches them: `animations.css`, `api-docs.css`, `brand-colors.css`,
   `coming-soon.css`, `cta-section.css`, `generic-buttons.css`, `generic-hero.css`,
   `generic-sections.css`, `partners-grid.css`, `partnership-cards.css`, `services-strip.css`,
   `stats-strip.css`, `use-case-cards.css`, `variant-cards.css`. Confirm nothing loads them
   dynamically before deleting.

**Process:**
6. Reconcile with the concurrent session's hero-reveal work before committing.
7. Committed as `133ea96` on `content-governance-2026-08-18` (2026-08-19). Not pushed.
