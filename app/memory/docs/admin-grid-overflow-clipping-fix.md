# Admin: Grid Overflow Clipping in Form & CRM Detail Layouts

**Project:** SLYD Admin
**Date:** 2026-08-06
**Author:** 67e19de6-7021-4882-aa88-e24b1ab8c23b
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Committed as `49479d4` on `feat/crm-accounts-quote-builder` (not pushed).

Wide content — the LeadsInbox table, long monospace values in DetailGrid —
was pushing its grid column past the track and overflowing the page.

**Root cause:** a CSS grid track declared `1fr` resolves to `minmax(auto, 1fr)`,
and `auto` as a *minimum* means "at least the content's min-content width". So a
wide child never shrinks the track; it inflates it. The fix is to state the
minimum explicitly as `minmax(0, 1fr)` everywhere a track holds content that can
exceed it.

Applied to:
- `DetailGrid.razor.css` — all four column counts plus both responsive breakpoints
- `LeadsInbox.razor.css` — `.split-grid` and its 1200px breakpoint
- `FormDetails.razor.css` — `.content-grid`

Three supporting changes:

1. **`.main-content` → `.detail-main` in FormDetails.** The layout shell claims
   `.main-content` globally in `custom.css` with `width: calc(100% - 280px)` and
   `height: 100vh`. Blazor scoped CSS doesn't shield a component from a global
   rule matching the same class name, so the page's inner column inherited the
   shell's dimensions and collapsed/clipped. Left a comment in the stylesheet
   explaining why the name must not go back — this is easy to "fix" wrong later.
2. **Removed the `forms-styles.css` `<link>`** from FormDetails; the scoped
   stylesheet already covers it.
3. **`.table-scroll` wrapper on the LeadsInbox table**, with `min-width: 1080px`
   on `.data-table` and `white-space: nowrap` on the mono cells. The table now
   scrolls horizontally inside its card rather than stretching the split grid.
   Styled webkit scrollbar to match the theme (`--slyd-border-color` thumb).

Verified with `dotnet build src/Admin/Admin.csproj` — succeeded, 0 errors, and
the 10 warnings are all pre-existing package warnings (NU1510 pruning,
NU1903 on `System.Security.Cryptography.Xml` 9.0.0 from Core).

## To Do Next

- Branch is unpushed. Per repo rules push to `development`, never `main`.
- The `.main-content` global-vs-scoped collision likely affects other detail
  pages that copied the same markup — worth a grep for `class="main-content"`
  inside `Components/Pages/`.
- `System.Security.Cryptography.Xml` 9.0.0 in Core carries two known high
  severity advisories; unrelated to this change but surfaced by the build.
