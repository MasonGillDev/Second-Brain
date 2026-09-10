# V3 Footer Uses the Real SLYD Logo

**Project:** SLYD Website
**Date:** 2026-08-05
**Author:** 0b60bf37-8274-4925-b851-dca747b30735
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

The V3 footer's brand link rendered a placeholder mark — a `<span class="v3foot-wm">` styled as a
26px gradient square (primary → purple with a cut-out center) — next to the literal text "SLYD".
That gradient square was never the SLYD logo; it was carryover from the homepage v1 mockup.

Replaced it with the same asset the nav uses:

- `Components/Shared/V3/V3Footer.razor` — brand link now renders
  `<img src="/images/SLYD-logo-300x86.webp" alt="SLYD" width="150" height="43" />` and carries
  `aria-label="SLYD home"`, matching `V3Nav.razor`.
- `Components/Shared/V3/V3Footer.razor.css` — deleted `.v3foot-wm` / `.v3foot-wm::after`, and
  rewrote `.v3foot-brand-link` to `inline-flex` / `line-height: 0` with `img { height: 34px; width: auto }`.

The literal "SLYD" text was dropped because the 300x86 asset is a wordmark that already contains
"SLYD" — keeping both would have duplicated the name. Footer logo is 34px tall vs the nav's 44px so
the footer brand stays visually subordinate to the header.

Verified with `dotnet build` — succeeded, 0 errors (2 pre-existing AWSSDK.Core NuGet advisory warnings).
