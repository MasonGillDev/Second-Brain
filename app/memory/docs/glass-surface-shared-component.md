# `glass-surface` / `glass-field` — New Design System Component

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

> **NEW DESIGN SYSTEM COMPONENT — REVIEW.** Flagged per Design.md §1, which requires new
> shared visuals to be proposed explicitly rather than built inline on a page.

## What Was Done

Promoted the liquid-glass card treatment from a home-page experiment into a shared pair of
utility classes, applied it to two home sections, and fixed the capabilities grid so the last
row fills the width.

### The component

Added to `wwwroot/css/shared-components.css` (globally loaded from `App.razor`), following the
precedent the concurrent session set with `hero-grid-field` in the same file — a CSS utility
rather than a Blazor component, because the two consumers have completely different internal
markup (`<a>` path cards vs `<div>` capability cards) and a component would force both to
restructure.

| class | on | does |
|---|---|---|
| `glass-surface` | the card | background, border, specular rim. Supplies **material only** — consumer keeps its own padding, radius, layout. The rim follows the consumer's `border-radius` because it's drawn with inset shadows. |
| `glass-field` | the section behind | the neutral light the material bends. |

**`glass-field` is not optional decoration.** `backdrop-filter` blurs what's behind it, and this
site's body is near-flat near-black — so blur alone returns near-flat near-black and the glass
reads as nothing. That's exactly what the first attempt did, and Mason's verdict was "Zero glass
look." The field supplies the luminance. Both facts are recorded in the CSS comment so the next
person doesn't repeat it.

Deliberately **neutral white**, never a coloured wash. The first working version used indigo +
gold radials; Mason compared them against the original and the original won. Two concrete
reasons, not taste: the website CLAUDE.md rules out "generic AI purple gradients" as the house
anti-pattern, and gold at 200% saturation behind a dark translucent fill goes muddy brown. White
keeps the palette untouched.

This complements the existing note in `Need.razor.css` — "glass tokens wash out on bg-body +
particles" — which describes the same failure from the other direction. That happens when the
*fill* is light. Here the fill stays dark and the light sits behind it.

Includes an `@supports not (backdrop-filter)` fallback to the solid surface, so older Firefox and
embedded webviews degrade to the previous look. No hover state by design (Design.md §3.2) —
consumers add their own.

### Applied to

- `/` paths section — 8 cards, replacing the bespoke rules from the experiment
- `/` capabilities section — 5 cards

### Capabilities grid — last row now fills the width

Was `repeat(3, 1fr)` with 5 cards, leaving a third of the bottom row empty. Now `repeat(6, 1fr)`
with `span 2` on each card and `span 3` on `:nth-child(n+4)`, so the top row is 3 × span-2 = 6
and the bottom is 2 × span-3 = 6. Both rows measured at exactly **1256px**; cards go 408px
(top) / 620px (bottom). Spans reset to `span 1` at the 1080px and 780px breakpoints where the
grid collapses to 2-up and 1-up.

### Removed the coloured top strips

Each capability card carried a 2px gradient strip along its top edge, a different colour per
`nth-child`. Removed, because:

- Design.md §3.1 bans gradient strips on a card edge outright
- the colour varied by position, so it encoded nothing — pure ornament
- it fought the glass rim, which now does that job on all four sides

**This was not asked for** and is trivially reversible if the strips were wanted — say so and
they go back.

Also dropped an orphaned `transition: border-color, transform` on `.v3home-cap`, left behind when
the hover sweep removed that card's hover state ([[website-hover-affordance-sweep]] follow-up 3).

### Verification

- `dotnet build --no-incremental` — succeeded, 0 errors.
- Row widths measured live: top 1256px, bottom 1256px, match confirmed.
- Responsive at 1440 / 1000 / 720 / 390px — spans collapse correctly, **no horizontal overflow at
  any width**.
- Paths section screenshotted after the refactor to shared classes: pixel-identical to before, so
  moving the material out of the page stylesheet changed nothing.
- Text contrast composited analytically (no PIL available, so the layers were alpha-composited in
  code) — worst case is the card top where the sheen is strongest: **8.15:1** for description
  text, **13.73:1** for titles, against a 4.5:1 requirement. The solid version was 10.07 / 16.96.
- `dotnet test` — **6 failed / 244 passed. Zero new failures**; the same six breadcrumb and
  byte-for-byte guards the concurrent session's in-flight sweep is breaking
  (see [[v3nav-item-state-underline]] for the evidence they aren't mine).

## To Do Next

1. **Not committed**, and the revert is no longer a single clean command:
   - `Components/Pages/Home.razor` and `Home.razor.css` — mine alone, safe to `git checkout --`
   - `wwwroot/css/shared-components.css` — **contains the concurrent session's `hero-grid-field`
     and their breadcrumb-sweep work too.** Do NOT `git checkout --` that file; remove the
     `GLASS SURFACE` block by hand instead.
2. **Adopt or reject site-wide.** Right now two home sections use glass and every other card on
   the site doesn't. Design.md §1's test is "could someone tell which page they're on by the
   styling alone?" — currently yes. Either roll `glass-surface` out to the other card surfaces or
   drop it; the half-state is the worst option.
3. **Is `backdrop-filter` earning its place?** Most of the visible effect comes from the field and
   the rim, not the blur. Worth testing with the blur removed — if indistinguishable, that's the
   same look for materially less compositing cost, which matters with 13 glass cards on one page.
4. The 6 red tests must go green before any of this is committed — the other session's to finish.
