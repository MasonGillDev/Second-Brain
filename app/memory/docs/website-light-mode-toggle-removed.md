# Website: Light/Dark Mode Toggle Pulled from the Header

**Project:** SLYD Website
**Date:** 2026-08-12
**Author:** 7e2e587f-f459-4567-b272-155d9af40187
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Commented out the light/dark mode toggle button in `Components/Shared/V3/V3Nav.razor` — both
the desktop header instance (`#v3nav-mode-toggle`) and its mobile-drawer twin
(`#v3nav-drawer-mode-toggle`). The markup is preserved verbatim inside Razor comments
(`@* ... *@`), not deleted.

### Why

Light mode is only half-wired on the website and the visible break is the logo. The site logo
(`wwwroot/images/SLYD-logo-300x86.webp`) is white text on transparent — on the light background
(`hsl(220, 28%, 96%)`, set by `html[data-mode="light"]` in `Components/App.razor`) it renders as
white-on-white, i.e. invisible. The logo appears in `V3Nav.razor` (x2), `V3Footer.razor`,
`Layout/TopNavigation.razor` (x2), `Layout/Footer.razor`, and `Layout/DocsLayout.razor`.

The original ask this session was "invert the SLYD logo in light mode"; the call was made to pull
the toggle instead and defer the full light-mode pass.

### How the theme system actually works here (worth remembering)

- `<html>` carries `data-slyd-theme` + `data-mode`; light styling hangs off
  `html[data-mode="light"]` / `:root[data-mode="light"]`.
- `Components/App.razor:26` — the pre-paint script **hard-locks `data-mode="dark"`** on every
  load, ignoring the persisted value and the system preference. There is a long comment there
  explaining why (a system-light browser previously flipped `--slyd-bg-card` to `#ffffff` and
  produced white cards on V3 pages).
- So light mode was only ever reachable *at runtime* by clicking this toggle, and never survived
  a page load. Removing the button closes the only remaining door into a half-styled light mode.

### What was deliberately NOT touched

- `.v3nav-tog` styling and the `:root[data-mode]` sun/moon icon-swap rules in
  `V3Nav.razor.css` (lines ~182-205, ~670) — left in place so restoring is uncomment-only.
- The `toggleMode()` handler in `wwwroot/js/v3nav.js` — it is already null-guarded
  (`if (modeBtn) ...`), so it no-ops with the buttons gone and needs no change either way.
- The `html[data-mode="light"]` critical CSS in `App.razor`.

Build: `dotnet build` → 0 errors, 2 pre-existing NU1901 warnings (AWSSDK.Core). Not clicked
through in a running app. Uncommitted — committing was not requested.

## To Do Next

**Put the mode toggle back once light mode is actually finished.** Required before restoring:

1. **Fix the logo in light mode.** Either ship a dark-ink logo variant and swap the `src` per
   mode, or apply `filter: invert(1)` under `[data-mode="light"]` — at all 7 usage sites listed
   above, not just the nav.
2. **Unlock the pre-paint script** in `Components/App.razor:26` so `data-mode` honors the
   persisted/system value again — but only after auditing the mode-aware tokens
   (`--slyd-bg-card` et al.) that caused the white-card bug called out in that comment.
3. **Audit the V3 marketing surfaces in light mode** — the App.razor note says the site is locked
   dark "until the full light-mode rollout (Tier C)," which implies more than the logo is unstyled.
4. Uncomment both `@* ... *@` blocks in `Components/Shared/V3/V3Nav.razor` (desktop header +
   mobile drawer). No CSS or JS changes needed.

**Unrelated, still open from earlier in this session:** production deploys are currently
impossible — `.github/workflows/deploy.yml` on `main` gates `deploy-production` on
`startsWith(github.ref, 'refs/tags/v')` (commit `04e3f16`) while the workflow's `on:` block only
listens to `push: branches: [main, development]` with no `tags:` filter. Pushes to main skip the
job; tag pushes don't trigger the workflow at all. Confirmed on run 31620611792 (`main`, push):
`build` success, `deploy-production` **skipped**. The workflow's own header comment still
documents the old "deploy on push to main" model, and its auto-tag/release step lives inside the
tag-gated job, which is circular. Not fixed.
