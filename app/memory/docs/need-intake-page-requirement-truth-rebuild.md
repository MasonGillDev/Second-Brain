# Need Intake Page Requirement Truth Rebuild (/need)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `https://slyd.com/need` per the three-file package at `/Users/masongill/Slyd/need-intake-claude-package-2026-08-17`. Content, SEO, AEO, metadata, schema, internal links, and presentation only. The requirement form, match preview, post-requirement flow, and hardware want-list are functionally untouched.

Fifth and last of the series, after [[broker-page-program-governance-rebuild]], [[hardware-sales-page-commercial-truth-rebuild]], [[power-opportunities-page-commercial-truth-rebuild]], and [[compute-marketplace-page-listing-truth-rebuild]].

### Files changed (three)

- `Components/Pages/Need.razor`
- `Components/Pages/Need.razor.css` (236 lines appended, nothing modified)
- `tests/Website.Tests/Pages/NeedIntakePageContentTests.cs` (new, 41 tests)

No controller, service, model, migration, admin screen, HubSpot mapping, analytics event, notification, or route changed. `NeedPreviewService`, `V3IntakeService`, and `Models/NeedPreview` are untouched.

### The commercial point of this one

Unlike the other four, the main job was not deleting claims. The `/need` form already supported three equal access paths through its existing consumption-model selector, but the page read as a compute rental preview with hardware as an afterthought. The content pass gives ownership, rental, and advice equal editorial weight without touching the selector, its option values, or its behaviour.

`Own the cluster` now reads as purchasing physical GPU hardware, `Rent capacity` as renting cloud compute, and `Open / advise me` as asking SLYD which fits. Each gets its own card with the specification's definition and its own onward links.

### Claims corrected

- **"Live Match Preview"** in the title, description, Open Graph, and visible copy. The preview is a preliminary candidate check over records that may fit the entered fields.
- **"No commitment, no signup"** replaced with an explicit draft-versus-submission explanation: nothing is stored while you adjust the form, and a private record is created only at the post step.
- **"NO CREDIT PULL"** replaced with the specification's exact wording: initial requirement intake does not authorize a credit inquiry, and any later financing review requires its own disclosures and consent.
- **"READY-SHIP · GRADE A / A-"** on the recovered-inventory lane, a universal condition-grade claim, now "RECOVERED SUPPLY · CONDITION VARIES BY LOT".
- **Match vocabulary.** "SLYD can likely cover" became "Candidate records"; "N sources cover this need" became "N sources hold candidate records"; "Coverage across three lanes" became "Candidate records by source"; "Match confidence" became "Confidence". Per the audit, a candidate is never called a match before the responsible verification.
- The preview notice now leads with "Preliminary candidate check. Not an offer." and states plainly that counts are not confirmation that capacity exists, is held, or can be delivered on your timeline.

### What was deliberately kept

**Every operational CTA label.** "Preview matches", "Post requirement to ops", and "Post hardware need" are unchanged, as the specification requires.

**The preview's placeholder dashes.** The response carries no coverage percentage, confidence, or per-source pricing, and the existing code renders those slots as em-dash placeholders with a `TODO(need-preview-backend)` note not to fabricate them. That was already the right call and is left alone.

**The em dash as a no-data glyph.** The no-em-dash rule was applied to prose. `—` survives only inside `need-stat-pending` and `need-hero-coverage-pending` render branches, where it is a UI marker rather than punctuation. A test encodes that exception explicitly.

**og:image removed.** `og-need.png` reads "Banded results. No signup.", and both framings were retired here.

### Verification

`needcontract.py` extracts a SHA-256 of the `@code` block plus every Razor binding, handler, `@bind`, model read, response read, loop, validation element, input attribute, select, datalist, and ARIA role. All 22 tracked sections identical; the only delta is added internal links and two anchors.

`needprobe.mjs` drives the real page over CDP with the platform API running, reads the pill groups and their `aria-checked` state, drives six selections through the live Blazor circuit, and submits the preview against the real `/api/match/need/preview` endpoint.

**The strongest check was a restore-and-compare.** The original file was put back, rebuilt, and scanned across four accelerators, then mine was restored and scanned identically. Both the populated branch and the empty branch were exercised:

| Accelerator | Result | Data values |
|---|---|---|
| H100 | 4 lots across 2 sources | identical |
| H200 | 2 lots across 2 sources | identical |
| MI300X | no matching lots | identical |
| B100 | no matching lots | identical |

Every preview data value matched the original exactly. The only differences were the two static labels changed on purpose.

One limitation to state plainly: the post-requirement submit runs server-side through `IV3IntakeService`, so its payload cannot be intercepted from the browser the way the hardware-sales and power-opportunities posts were. Clicking it would create a real Demand record, so it was not exercised. The `@code` hash covers `HandlePost` and `HandleHwPost` byte for byte instead.

### Verification results

- Build: succeeded, 0 errors, 2 pre-existing NuGet advisory warnings.
- Tests: 250/250. 41 are this page's; 206 across the five page suites; 23 pre-existing. A `GpuDatabaseTests.cs` (21 tests) in the same folder came from other work in parallel and is not part of this change.
- Served HTML: one title, description, canonical, robots tag, and h1; no `meta keywords`; three JSON-LD blocks all valid; FAQ byte-identical to the FAQPage JSON-LD across all 14 questions; zero retired-framing hits.
- Links: all 8 targets return 200.
- Layout: no overflow inside `.need-page` at any of the four viewports. The residual page-level overflow at mobile widths is entirely the shared `v3nav-drawer`, identical to every other page.
- Accessibility: one h1, no heading skips, 6 labelled radiogroups with 30 radios all exposing `aria-checked`, all 14 FAQ summaries and all pills keyboard focusable, no empty link text, no positive tabindex. The single "unlabeled" control the probe flagged is Blazor's hidden EditForm field.

Two of my own mistakes were caught by the tests and fixed: an HTML comment that quoted the retired "Banded results. No signup." copy and named the withdrawn asset, which would have shipped to crawlers; and an h1-to-h3 heading skip, resolved by promoting seven class-styled card headings to h2 after confirming no tag-qualified CSS or code reference.

## To Do Next

1. **Withdrawal and update path.** The FAQ now says to contact the SLYD team with the submission reference to update or withdraw a requirement, because there is no self-service control. The specification's validation list expects "privacy, consent, update, and withdrawal paths work". Confirm the manual path is real and staffed, or build the self-service control as a separate product change.
2. **og:image asset.** Needs an approved 1200x630 visual representing an AI infrastructure requirement or operating environment, with no match counts, prices, timelines, or supply claims. A test asserts `og-need.png` stays out.
3. **Legal sign-off** on the credit-inquiry wording, the draft-versus-submission explanation, and the privacy answer.
4. **The preview backend TODO still stands.** `TODO(need-preview-backend)` at the top of the file lists coverage percentage, confidence, and per-source pricing as fields the mockup shows but the response does not carry. They render as placeholders. The content pass makes the placeholders honest; it does not close the gap.
5. **Requirement-record language.** The FAQ states a submitted requirement is private and not published to public marketplace pages. That reflects the intended design; someone with access to the demand pipeline should confirm it matches actual retention and visibility behaviour.
