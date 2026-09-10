# Nav Edge-Cast Reflection System

**Project:** SLYD Platform (Platform.WebUI + component-library)
**Date:** 2026-07-16
**Author:** 03cffc02-2e8e-447d-906d-8347231fd42b
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Built `slydNavCast` — a platform-wide UI primitive where any element tagged `data-nav-cast` throws a soft colored reflection onto the sidebar's inner edge at the element's height: a blurred bloom refracting into the glass plus a 1px peaked rim glint. Committed as platform `a7fdeef` and component-library `f4f2369` (**not pushed**; note the component-library commit is on its local `main`, and platform depends on it — push together).

### Architecture (`wwwroot/js/nav-cast.js` + `wwwroot/css/nav-cast.css`)
- **Overlay on `<body>`, not inside the Blazor nav** — avoids Blazor diffing removing nodes AND the scoped-CSS trap (`.razor.css` selectors get `[b-xxxx]` attributes that JS-created nodes lack; this was why v1 rendered nothing).
- **Renders UNDER the glass** (`z-index: 19` vs sidebar 20): the nav's translucent `--slyd-bg-glass` + `backdrop-filter` dims/blurs the light — real refraction; nav content is never tinted. (User chose under after seeing over.)
- **Keyed glows, not index-pooled** — a `Map(casterEl → glowNode)`; each caster owns its glow for life. Index pooling caused visible pops: hover-casts entering the list shifted indices and teleported lit glows. Also: force reflow (`void glow.offsetWidth`) after creating a node or the opacity 0→1 transition coalesces and skips (pop-in).
- **Strength model**: size (`height/80`, clamp .35–1) × distance falloff (full ≤120px from nav edge, linear to 0.2 by ~1300px) × `data-nav-cast-brightness` (0.1–2.5), capped 1.6. Strength drives bloom opacity, refraction depth (`width: calc(12% + 22%×s)`), and rim-line opacity. Strength >1 reaches deeper (opacity clamps at 1).
- **Color resolution** (`resolveColor`): bare tag → element's computed `color`; `"background"` → live `backgroundColor` (follows `:hover`; falls back to color if transparent); semantic names (`danger/warning/success/primary/info`) → `:root` tokens via `var()`; other `var(--x)` → resolved against the **caster element** so element-scoped tokens like `--role-c` work (glow node is outside that scope).
- **`data-nav-cast-on="hover"`** — casts only while `el.matches(':hover')`; eases in/out 0.5s to match card glow transitions.
- **Top-edge mode**: when a caster's center scrolls above the nav top, the glow switches to a `top-edge` class — a horizontal band catching the TOP rim, refracting right→left, decaying to nothing by 600px above.
- **Updates**: rAF-coalesced on scroll (capture — app scrolls `.main-content`), resize, MutationObserver (childList + `class`/`data-nav-cast` attrs — deliberately NOT `style`, our own writes would loop), and mouseover/out on casters (+350ms follow-up for CSS transitions).
- **Rim glint tuning journey**: flat plateau mask read as a "painted stripe" — fixed with a pure peaked mask (transparent→peak@50%→transparent), 62% color, 0.5px blur, 1px wide. Bloom stops 42/17/6% over 12–34% width.

### Tagged elements
- Dashboard payment alert (`@_alertSeverity` — semantic)
- StandardPageHeader title (`var(--slyd-primary-light)`, brightness 2 — the "laser")
- DealOS marketplace: status chips (bare — self-colored), cards (hover, primary, 0.8), CTA buttons (hover, white glass, 1.5)
- Compute marketplace: cards (hover, primary, 0.6), Deploy buttons (`"background"` — follows hover), status chip UNtagged by request
- SettingsV3 capability cards (`var(--role-c)`, 0.7 active / 0.4 available) + matching box-shadow glow in role color

### Component-library dependency
`ActionButtonPurple` got `CaptureUnmatchedValues` splatting (`f4f2369` on **local main**) — platform's Deploy-button tag would throw at runtime without it.

## To Do Next
- **Push both repos together** (platform `development` ahead 9; component-library commit is on local `main` — may want to move to a branch/PR per repo rules).
- Guardrails discussed but not built: full `prefers-reduced-motion` suppression (currently only kills transitions) and a global kill switch (`slydNavCast.disable()`).
- Uncommitted in platform: backend/test files from the core-mutations session, mockup, Finance.razor whitespace.
