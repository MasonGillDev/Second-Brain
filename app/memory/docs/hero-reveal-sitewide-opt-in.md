# Hero Reveal Animation — Site-Wide Opt-In

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

### Follow-up: scroll-triggered section fades

`scroll-reveal.js` and a `.scroll-reveal` CSS block already existed and were loaded on every
page — with zero consumers. Dead code. Rather than hand-tagging hundreds of sections, the
script now auto-tags: every outermost `<section>` that starts below the fold gets the class
and fades up on entry. No markup changes anywhere.

Design decisions that matter:

- **The class is only ever added by JS, and only to elements below the viewport.** Since
  `.scroll-reveal` sets `opacity: 0`, putting it in markup would mean a blank page if the
  script ever failed, and a visible flash-out-then-in for anything already on screen.
  Tagging only below-fold elements avoids both.
- **`threshold: 0` + a bottom `rootMargin`, not a visibility ratio.** The original used
  `threshold: 0.15`. A section taller than ~6x the viewport can never show 15% of itself at
  once, so it would have stayed invisible permanently. Nothing used the old code, so this
  was latent rather than a live bug.
- **Revealed state is `transform: none`, not `translateY(0)`.** Any transform value keeps a
  stacking context alive, which would trap the `z-index: -1` decoration layers that sections
  paint (the same class of bug as the hero grid). Interpolates identically.
- Heroes are excluded (they animate on load via `hero-reveal.js`), nested sections are
  excluded (they'd double-fade), `prefers-reduced-motion` skips the whole thing, and
  `data-no-reveal` opts any subtree out.
- Pages built as one long `<section>` (`/need`, `/marketplace`) get nothing from the section
  rule. Added `data-reveal-children` as an explicit opt-in that animates a container's direct
  children — not applied anywhere yet, since fading form blocks and live listing grids is a
  judgment call.

Verified in headless Chromium by scrolling each page end to end: every tagged section
reaches `revealed`, none stays invisible, no lingering transforms, and nothing on screen at
load starts hidden. Docs pages have no `<section>` elements and legal pages nest theirs, so
both are untouched.

## Original Work

### Follow-up: one breadcrumb for the site

Breadcrumbs had drifted into two implementations plus three markup shapes:

- The shared `<Breadcrumb>` component — a centered pill with a home icon and chevrons,
  used by 33 pages.
- Bespoke v3 trails — quiet monospace `Home / Section / Page`, 25 pages, each with its own
  `X-crumb` CSS. `/broker` is one of these, and it's the look Mason wants everywhere.

Restyled the shared component to the /broker trail (monospace 12px, muted, slash-separated)
and converted the 23 bespoke v3 trails onto it. Placement was unified too: the trail now
sits as the first child of the hero copy container, where /broker has it. The 18 `v3hs`
pages had theirs in a separate band *above* the hero — that band is gone, the crumb moved
inside. Deleted the six now-dead bespoke CSS blocks.

Three things worth remembering:

- **Duplicate structured data.** The component has always emitted BreadcrumbList JSON-LD,
  and 27 pages hand-write their own inside a richer `@graph` (with `@id`, cross-referenced
  by the page's other nodes). Converting those pages would have put two BreadcrumbLists on
  one page. Added an `EmitStructuredData` parameter and set it false on the 24 pages that
  already declare one, so the page's `@graph` stays authoritative. This also fixed a
  pre-existing duplicate on /marketplace/compute.
- **The JSON-LD `<script>` is a hero child now.** `hero-reveal.js` staggers the hero's
  direct children, so a non-rendered node would eat a slot — and worse, `pending()` would
  never see it as processed, re-triggering `init()` on every mutation. Both paths now skip
  SCRIPT/STYLE/TEMPLATE/LINK/META.
- Legacy (non-v3) pages keep their current placement and wrapper bands. Mason is doing a
  separate legacy-page pass, so relocating those was explicitly out of scope.

Verified: one trail and exactly one BreadcrumbList per converted page, hero reveal still
correct, build clean.

## Original Work

### Follow-up: shared hero grid field

Mason liked the masked grid + corner glow on the /broker hero and wanted it on every page
header. Audit found the treatment was already hand-copied into 12 page stylesheets (Home,
About, Broker, Hardware hub, Financing, Lenders, Platform, Cloud, Security, Benson, …) and
missing from 23 heroes.

Added `.hero-grid-field` to `wwwroot/css/shared-components.css` — one copy of the glow
`::before` + masked grid `::after` — and put the class on the 23 heroes that lacked it:
`.v3hs-hero` (18 hardware / GPU / OEM pages), plus Configure, Need, HardwareSales,
Marketplace, and PowerOpportunities. Pages that already had their own copy were left alone;
consolidating those onto the shared class is still available if uniform geometry is wanted.

Two things that cost real debugging time:

1. **`isolation: isolate` is load-bearing.** The layers sit at `z-index: -1` so content
   stays above them without a per-page stacking fix. But without a stacking context on the
   hero itself, `z-index: -1` escapes to the nearest one and paints *behind* whatever opaque
   background an ancestor carries — and the v3 page wrappers (`.v3hs`, `.v3hw`) all set
   `background: rgb(2,5,19)`. The grid computed correctly in devtools and rendered as
   nothing. `isolation: isolate` on `.hero-grid-field` confines it. Costs nothing, since the
   `overflow: hidden` in the same rule already stops hero content escaping.
2. **Editing CSS under `wwwroot` after a build breaks the page entirely.** Blazor's
   `@Assets[...]` emits fingerprinted URLs with integrity hashes, so a post-build edit makes
   the browser reject the stylesheet and the page renders unstyled. Rebuild before
   re-testing, or you will "verify" a page with no CSS at all.

Verified in headless Chromium: on each updated page the `::after` layer resolves to a 64px
grid with the radial mask applied, and screenshots confirm the header now matches /broker.

## Original Work

### Follow-up: gradient-text headlines (homepage bug)

After the rollout the homepage h1 animated but rendered invisible — the space was
reserved, and the text only appeared when selected. Cause: `Home.razor.css:1655` paints
that headline's text through its own background:

```css
.v3home .v3home-hero-h1 {
    background: linear-gradient(180deg, ...);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
```

`hero-reveal.js` moves the headline text down into `.hero-line-inner` spans. Those spans
inherit the transparent text-fill but *not* the background, so nothing paints them —
transparent text on a transparent background.

Homepage-only because it is the one page that puts the gradient on the `h1` itself.
Every other hero puts it on a child `.accent` / `v3xxx-a` span, and child elements are
moved into the line wrapper intact, so their background travels with them.

Fixed generically in `carryGradientText()` in `hero-reveal.js`: if the computed style of a
headline shows a background image plus a transparent text fill, the gradient is copied onto
each line with `background-size: 100% <headline height>` and `background-position: 0
-<line offset>`. That keeps the headline reading as one continuous gradient instead of
restarting it per line (which is what a plain `background: inherit` would have done).
Offsets are measured from the `.hero-line` wrapper, not the inner span — the inner is
mid-slide under a `translateY`, so its own rect would be shifted. Offsets are re-measured
on `document.fonts.ready` and on debounced resize, since both change line metrics.

Confirmed working by Mason in the browser.

## Original Work

The headline slide-up-on-load animation that ran only on `/platform/governance` (and the
other pages using the shared `<Hero>` component) now runs on the v3 pages too, without
copying any CSS into page-scoped stylesheets.

### Why it only worked on some pages

The animation was never part of the `Hero` Blazor component. It lives in two global files:

- `wwwroot/js/hero-reveal.js` — splits the headline on `<br>` into masked `.hero-line`
  spans that slide up, then staggers a fade-up over the headline's siblings.
- `wwwroot/css/shared-components.css` — the `hero-line-reveal` / `hero-fade-up` keyframes
  plus the `opacity: 0` initial state.

The JS matched a hard-coded pair of selectors: `.hero-headline` inside `.hero-content`,
which only the shared `<Hero>` component emits. Every v3 page hand-rolls its hero with a
page-specific prefix (`v3hs-h1`, `v3plat-hero-h1`, `need-headline`, …), so nothing matched.

### The change

Rather than a new component (which would have meant restructuring 34 pages' hero markup and
risking their existing layout CSS), the reveal became **attribute-driven**. Put
`data-hero-reveal` on the element whose direct children are the eyebrow / h1 / lede / CTAs,
and it animates. Nothing else — no per-page CSS, no wrapper div, no markup moved.

- `hero-reveal.js` — generalized to collect hero blocks from both `[data-hero-reveal]` and
  the legacy `.hero-content`/`.hero-headline` pair. Headline resolution is
  `[data-hero-reveal-headline]` → direct-child `.hero-headline` → direct-child `h1` → any
  `h1`. Also added: `prefers-reduced-motion` handling (reveals instantly, no animation) and
  a `load + 1.5s` safety net so a hero can never stay stuck at `opacity: 0` if the animation
  path fails.
- `shared-components.css` — added `[data-hero-reveal] > * { opacity: 0 }` and a
  reduced-motion block that un-hides everything.
- Added `data-hero-reveal` to 34 page heroes: Home, About, Configure, HardwareSales, Broker,
  Need, all `/hardware` pages (hub, subpages, GPU families, all 5 OEMs), Financing +
  Lenders, Platform/Cloud/Security/Benson, Marketplace, PowerOpportunities.

Docs and Legal pages were deliberately left alone — the animation is a marketing-page
gesture and delays reading on reference content.

### Verification

- `dotnet build` — succeeded, 0 errors.
- Ran the app and drove `hero-reveal.js` against the real server-rendered HTML of all 34
  pages under jsdom, asserting the masked line wrappers get built with the right stagger
  delays and every hero sibling picks up `hero-fade-up`. All 34 pass; `/platform/governance`
  still behaves identically (2 lines, 0s/0.18s delays), confirming no regression on the
  pages that already had it.

Not verified: actual visual playback in a browser. Worth an eye on headlines whose accent
span has unusual descenders or padding — `.hero-line` sets `overflow: hidden`, so heavy
glyph overhang could clip.

### Note on unrelated working-tree changes

While this work was in progress, ~60 CSS files in the working tree had their `:hover`
rule blocks stripped (`.gov-integrity-card:hover`, `.btn-brand-primary:hover`, etc.) by
something outside this session — a concurrent process or another session. Those deletions
are not part of this change and were left untouched for Mason to decide on.

## To Do Next

- Eyeball a few pages in a browser to confirm playback and check for glyph clipping in the
  masked lines.
- Decide what to do about the site-wide `:hover` rule deletions sitting in the working tree.
- Optional: extend `data-hero-reveal` to Resources/Services/Guides pages if the same gesture
  is wanted there.
