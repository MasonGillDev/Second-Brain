# Power Opportunities Page Commercial Truth Rebuild (/marketplace/power-opportunities)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `https://slyd.com/marketplace/power-opportunities` per the three-file package at `/Users/masongill/Slyd/power-opportunities-claude-package-2026-08-17`. Content, SEO, AEO, metadata, schema, internal links, and presentation only. The site intake form and its submit handoff are functionally untouched.

Third in the series after [[broker-page-program-governance-rebuild]] and [[hardware-sales-page-commercial-truth-rebuild]], and the hardest of the three: the driving JavaScript is **inline in the .razor file**, so the file being edited for content is the same file holding the operational script.

### Files changed (three)

- `Components/Pages/Marketplace/PowerOpportunities.razor`
- `Components/Pages/Marketplace/PowerOpportunities.razor.css`
- `tests/Website.Tests/Pages/PowerOpportunitiesPageContentTests.cs` (new, 29 tests)

No controller, service, model, migration, admin screen, CRM mapping, analytics event, or notification changed. All three API calls are unchanged.

### The scope conflict, and how it was resolved

The package documents pointed opposite ways and the conflict was material, so it was escalated rather than guessed.

Spec 02 orders removal of "Fit scores" and "Operator match counts". But those two values reach the page from a live endpoint (`/api/v3/power-opportunity/preview`, running `PowerFitScorer` against real operator Accounts), and prompt 03, which declares itself the winner on conflicts, forbids rewiring any output or component.

**Mason chose: remove the whole match display.** The operator-match card and the fit score, operators-matched, and time-to-deal tiles are gone. The revenue estimate stays, reframed as unverified. The reasoning that carried it: the audit's second critical risk is that matching is presented *before* SLYD has verified site control, interconnection, deliverability, permits, or authority, and that objection does not care whether the number is live.

Worth recording: the probe showed the "live" fit score rendering as `7.0 / 10` and operator count as `3` even with the platform running. Those are the hard-coded client defaults in `calc()` (`fit: 7.0, ops: 3`); the fit endpoint had not overridden them. So the supposedly live values were themselves showing fabricated defaults.

### Claims removed

- **The demand rail.** Four cards with MW ranges and revenue-per-MW-year figures, driven by a hard-coded table in the inline script that a twelve-second timer walked with `Math.random()`. A "DEMO TICK" label did not make them safe.
- **The whole match display.** Three operator rows with invented archetypes ("Tier 1 hyperscaler", "Mid-market neocloud", "Inference-only"), invented forward books ("FORWARD BOOK 8.4 MW"), and invented fit percentages ("FIT 92%"), plus the fit score, operators-matched, and `6-10 wk` time-to-deal tiles.
- `data-spec="heroLbl"`, because the script writes the literal `INDICATIVE SITE REVENUE · BANDED ±10%` into it and that precision has no governed basis. A truthful static label replaces it.
- The 48-hour feasibility promise, the hard-coded `DRAFT · E-Q2-0089` identifier, "operators with capital and offtake waiting", and the `Indicative match · banded` badge.

Retained and reframed: `revLo`, `revHi`, `heroSubHtml`, `lifetime` (backend values from `/api/v3/power-opportunities/preview`) plus `heroBand` and `ft1Lbl`, the two labels that switch between the lease and sale branches. They now sit under an "Indicative only. Not a valuation or an offer." notice and a caveat that self-reported inputs produce a self-reported estimate.

### Key decisions

**The inline script was reproduced byte for byte, not retyped.** It was extracted to a file, the new page was written with a placeholder, and the script was substituted back in programmatically. SHA-256 `0bf91db3…df9f9e4f`, 24,510 chars, verified identical before and after, and now pinned by a test that fails on any edit.

**Every removal was proven null-guarded first.** `set()` returns early on a missing `data-spec` target, `refreshFitScore()` guards `fitEl`, `opCntEl`, and `opCnt2El` individually, the `data-live` loop returns early, and the demand-rail lookup is wrapped in `if (rail)`. The removed blocks degrade to no-ops. Confirmed empirically: zero console errors and zero JS exceptions at all four viewports.

**Retired strings survive inside the script.** `6–10 wk`, `FORWARD BOOK …`, `OPERATORS MATCHED`, and `±10%` are still literals in the preserved script, and two dollar figures appear in one of its code comments. They are in the shipped page source but **cannot render**, because the elements they target no longer exist. Verified by span analysis against the served HTML: zero occurrences outside the script block. Removing them means editing operational code, so it is flagged rather than done.

**Heading promotion.** The five intake section headings were `h3` directly under the `h1`. Styling is class-based (`.v3energy-fsh`) with no tag-qualified CSS and no script reference, so promoting them to `h2` is semantic only.

### Verification

Two harnesses, both in the session scratchpad, run before and after:

- `energycontract.py` extracts the markup-only DOM contract plus a hash of the inline script.
- `energyprobe.mjs` drives the real page over CDP with the platform API running, exercises both commercial branches (`sell-site` and `ground-lease`, which take different code paths), and captures the submit payload by stubbing **only** the submit fetch so no `FormSubmission` is written.

Markup contract diff, exactly as intended and nothing more:

| Section | Result |
|---|---|
| pills, selects, inputs, form element, contact fields | identical |
| inline script SHA-256 | identical |
| `data-spec` removed | `fitScore`, `ft3Lbl`, `op1-3Prefix`, `op1-3Sub`, `opCount`, `opCount2`, `opmatchLbl`, `opmatchTail`, `ttd`, `heroLbl` |
| `data-spec` retained | `revLo`, `revHi`, `heroSubHtml`, `lifetime`, `heroBand`, `ft1Lbl` |
| `data-live` / demand cards | 16 → 0, 4 → 0 |
| ids | `v3energy-d-grid` removed; `submit-site`, `qualification-requirements` added |

Runtime probe, identical before and after: submit payload, form state across both branches, all six retained bindings, all three endpoints, zero console errors. The reference element still receives the real ref on submit.

Build succeeded, 0 errors, 2 pre-existing NuGet advisory warnings. Tests 142/142 (23 pre-existing, plus broker, hardware-sales, and power suites). Served HTML: one title, description, canonical, robots tag, h1; three valid JSON-LD blocks; FAQ byte-identical to the FAQPage JSON-LD across all 8 questions; zero static currency or percentages in rendered content. All 8 internal links return 200. `scrollWidth == clientWidth` at 1440x900, 1024x768, 390x844, 360x800; no unlabeled controls, no empty link text, no positive tabindex, all 8 FAQ summaries keyboard focusable.

## To Do Next

1. **The `$0` degradation bug (worth fixing soon).** When the valuation backend is unavailable, `calc()` returns zeros and `fmt(0)` renders `$0`, so the page shows **"$0 to $0"** and "$0 / MW·yr" as an apparent valuation. The script's own comment says it intends "—" placeholders. This was captured accidentally when the platform died mid-QA; the screenshot is kept at `shots/energy-1440x900-BACKEND-DOWN.png`. It is pre-existing operational-code behaviour, outside a content pass, but it is exactly the class of false economic claim this package exists to remove.
2. **Script cleanup pass.** Now dead or unreachable in the inline script: the entire demand IIFE (hard-coded table, `Math.random()` walk, twelve-second `setInterval`), the `refreshFitScore()` fetch and its debounce, the `ttd` and `op*Sub` literals, and the `heroLbl` writes carrying `±10%`. Removing them clears the retired strings from the shipped source.
3. **Legal sign-off** on the qualification, role-boundary, and confidentiality copy, and on the retained revenue-estimate framing.
4. **og:image asset.** `og-power-opportunities.png` reads "Operators with offtake waiting" over an abstract lightning-bolt illustration; the claim is retired and the spec requires a real power or data center site photograph. A test asserts it stays out until replaced.
5. **Governed public opportunity module.** Spec 02 section 6 defines the future approved public projection (`publicOpportunityId`, capacity bands, `publicationExpiresAt`, `verifiedAt`, fail-closed rules). Not built in this phase by instruction; it is the sanctioned way to show real demand later.
