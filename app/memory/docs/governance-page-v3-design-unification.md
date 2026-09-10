# /platform/governance — V3 Design Unification

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `/platform/governance` onto the V3 design language used by `/`, `/platform`,
`/platform/security`, `/platform/cloud` and `/platform/benson`. It was the last platform
subpage still on the old generic system (`page-section`, `page-section--alt`,
`page-section-title`, the shared `<Hero>` component, `MainLayout`).

**All content preserved** — verified mechanically, see below. Files: `Governance.razor`
765 → 723 lines, `Governance.razor.css` 1210 → 876 lines.

### What changed structurally

| | before | after |
|---|---|---|
| Layout | `MainLayout` (implicit) | `@layout BareLayout` + inline `<V3Nav />` / `<V3Footer />` |
| Wrapper | none | `<div class="v3gov">` with the standard V3 token bindings |
| Classes | global `page-section*`, `gov-*` | `v3gov-*`, scoped, 110 distinct |
| Hero | shared `<Hero>` component, Props + image | `v3gov-hero` — eyebrow, display h1 with accent span, sub, CTAs, 4 pillar cards |
| Icons | 39 `<Icon>` (Font Awesome) | 3 inline SVGs |
| Section chrome | `page-section--alt` | `v3gov-section` / `v3gov-section-alt`, matching Security exactly |

The hero, section heads (kicker → heading → lede), FAQ `details/summary`, and CTA strip are
now structurally identical to `/platform/security`, so the two read as siblings.

### Design.md compliance

Read `.claude/Design.md` partway through at Mason's prompt; it changed several decisions:

- **§3.3 gratuitous icons** — dropped all 39 `<Icon>` instances. They were ornament: a circled
  icon beside every card heading, check marks prefixing every evidence item, X marks repeating
  "cannot" that the sentence already said. The home page — the stated reference — uses **zero**
  icons, so removing them matches the reference *and* the rule. The only SVGs kept are the three
  inheritance-chain arrows, which carry cascade direction the text doesn't.
- **§3.1 colored card borders** — the CTA card does **not** get Security's
  `border-top: 2px solid var(--primary)`. Standard subtle border on all four sides.
- **§3.2 hover on non-interactive** — the finished stylesheet contains exactly two `:hover`
  rules, both on `<a class="v3gov-btn">`. Cards, pillars, chips and table rows are inert,
  consistent with [[website-hover-affordance-sweep]] earlier the same day.
- **§3.6 ad-hoc spacing** — all spacing/radii come from `--slyd-spacing-*` / `--slyd-radius-*`
  via local aliases at the top of the file, rather than eyeballed pixels.

### Reused the shared hero treatment (and fixed a latent bug doing it)

A concurrent session added a shared `hero-grid-field` class to `shared-components.css` while
this work was in progress — the masked grid + corner glow, factored out of the per-page copies.
I had hand-rolled the identical treatment as `.v3gov-hero::before/::after`.

Swapped to the shared class. **This fixed a bug I had introduced without noticing:** the shared
version carries `isolation: isolate`, and without it the `z-index: -1` layers escape the stacking
context and paint *behind* the opaque background the `.v3gov` wrapper sets — rendering as
nothing. Screenshots before/after confirm the grid and glow were invisible with my version and
render correctly with the shared one. Their comment block called this out explicitly; I'd have
shipped an invisible hero treatment otherwise.

### Content verification

Rather than eyeball 765 lines, compared old vs new mechanically:

- **192 text phrases** extracted from the old page; **0 missing** from the new one, comparing
  case- and punctuation-insensitively.
- **Both JSON-LD blocks** (TechArticle, FAQPage) byte-identical.
- **All 16 meta tags** preserved; the only delta is `&` → `&amp;` in `og:title` and
  `twitter:title`, which decode identically and are the more correct form.

Copy was restyled Title Case → sentence case ("Automated Policy Application" → "Automated policy
application") to match the V3 pages, which use sentence case throughout ("Custody model",
"Three parties. Clear lines."). No wording removed.

### Content added

Small amount, all derived from copy already on the page — no new product claims:

- **Four pillar descriptions.** The old `<HeroProp>`s were bare labels; the V3 pillar pattern
  needs a sentence each. Every one restates something already on the page (e.g. "Six report types
  compile themselves…" restates the six-row report table and the export formats).
- **CTA buttons.** The old CTA had a heading and paragraph but an *empty* `gov-cta-actions` div —
  it rendered nothing. Filled with `/contact-sales?source=governance-demo` and `/platform/security`,
  both existing routes.
- **Hero CTAs** — `/contact-sales?source=governance` and `/platform`, matching Platform's hero.

### Removed

- `/images/content-audit.png` and its markup, at Mason's request. A stock shield-and-magnifier
  illustration that read as generic clip-art next to the rest of V3 and dominated the hero.
  Confirmed nothing else in the repo referenced it before deleting; `/images/content-audit.png`
  now correctly 404s.
- The visual `<Breadcrumb>`, matching `/platform` and `/platform/security` which carry
  `BreadcrumbList` in JSON-LD only. Mason confirmed a dedicated breadcrumb-unification sweep is
  coming, so this is deliberately left for that pass.

### Verification

- `dotnet build --no-incremental` — succeeded, 0 errors.
- `dotnet test` — **250/250 passed.**
- Page returns 200; V3Nav and V3Footer render; **0 legacy `page-section` / `gov-` classes** remain.
- `sarah@acme.com` in the log sample renders correctly (`@@` Razor escape).
- Screenshots at 1440×900 and 390×844, plus per-section captures of the table, inheritance chain,
  enforcement flow, audit panel, workflows, integrations, FAQ and CTA.
- **No horizontal overflow at 390px.**
- Hero compared side by side against `/platform/security` — same skeleton.

## To Do Next

1. **Not committed.** Working tree also contains the concurrent session's `hero-grid-field`
   work across 24 hero sections — separate changeset, needs separating before commit.
2. **Tables.** The three tables are still hand-rolled `<table>` with `v3gov-table` styling.
   Design.md §3.4 wants the shared table component; Mason confirmed this needs a site-wide pass
   (35 pages hand-roll `<table>`, and the shared `SpecificationTable` is used by **zero** of them).
3. **`SpecificationTable` is unused and hardcodes hex.** When the table pass happens, note it
   hardcodes `#6366F1`/`#e6edf3` instead of tokens, so it breaks under the non-indigo themes in
   `DesignTokens.css` (there are cyan and gold variants).
4. **Design.md §6 vs `data-hero-reveal`.** §6 says "no staggered fade-in-up on page load," but the
   hero-reveal added across 34 pages today is exactly that. I kept it on governance for sibling
   consistency. **This conflict should be resolved site-wide** — either §6 is amended or the
   reveal is dropped everywhere.
5. **`PlatformStack.razor`** is now the only remaining `/platform` page on `MainLayout` rather
   than `BareLayout` + V3 chrome. Same treatment would finish the section.
6. Governance still lacks the `WebPage` + `BreadcrumbList` + `Service` JSON-LD that `/platform`
   and `/platform/cloud` carry. Left alone deliberately — that's an SEO change, not a design one.
