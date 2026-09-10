# Hardware Sales Page Commercial Truth Rebuild (/hardware-sales)

**Project:** SLYD Website
**Date:** 2026-08-18
**Author:** 88fa5f51-4797-4c3e-b7cf-044dd4d21bb4
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Rebuilt `https://slyd.com/hardware-sales` per the three-file package at `/Users/masongill/Slyd/hardware-sales-claude-package-2026-08-17`. Content, SEO, AEO, metadata, schema, internal links, and presentation only. The seller intake, manifest editor, CSV upload, valuation panel, and submit handoff are functionally untouched.

This is the harder sibling of [[broker-page-program-governance-rebuild]]. The broker page was static. This one is wired: `wwwroot/js/v3sell.js` reads and writes the page by element id, by pill `data-key`/`data-val`, and by `data-spec` binding, then posts to `/api/v3/hardware-sales/submit`. A careless content edit here would not fail the build, it would silently change what a seller submits.

### Files changed (three)

- `Components/Pages/HardwareSales.razor` (rewritten, operational DOM preserved)
- `Components/Pages/HardwareSales.razor.css` (demand-rail rules replaced with new section styles)
- `tests/Website.Tests/Pages/HardwareSalesPageContentTests.cs` (new, 29 tests)

`wwwroot/js/v3sell.js` was **not** modified. No controller, service, model, migration, admin screen, CRM mapping, analytics event, or notification changed.

### Claims removed and why

The page was publishing fabricated commercial information as if it were live:

- **The "SLYD is actively buying right now" demand rail.** The four cards (H200, H100, MI300X, A100) with per-node prices and quantities wanted were a hard-coded JS table (`demand = {h200: {wanted: 200, pricePerNode: 32000}, ...}`) random-walked every twelve seconds by `Math.random()`. A small "DEMO TICK" label did not make them safe. They read as active bids.
- **Static prices in the result panel.** The seed markup published `$1.5M — $1.7M`, `$32,000/node`, `$38,000` base market value, and fixed `$760K`/`$1.4M` payment amounts. JS overwrote them on first paint, so nobody with JavaScript saw them, but every crawler did.
- Plus or minus five percent valuation precision; the universal 50/50 payment structure; five-to-eight-week timing; the one-business-day quote promise; the firm-letter-offer promise; "no auction discount"; universal inspection, burn-in, grading, and "SLYD's recovery facility" claims; and the hard-coded `DRAFT · S-Q2-0143` identifier.

Replaced with: SLYD does not purchase every lot as principal, four disposition paths each marked "Available when approved for the specific transaction", seller-reported condition explicitly separated from verified findings, and payment/timing/inspection responsibility deferred to the transaction documents.

### Key decisions

**Preserve the result panel, neutralise its seed text.** The specification says to remove pay-on-inspection, pay-on-resale, and buyout amounts. Those amounts are live backend output (`r.inspectionClear.amountTotal * 0.50`), and the implementation prompt forbids rewiring the result panel. Resolution, per the package's own precedence rule: keep every element and `data-spec` attribute exactly, change only the static seed text to `Pending`, relabel the tiles as illustrative, and add a caveat paragraph stating that payment structure, settlement timing, inspection responsibility, and title transfer are set per transaction. The operational output is untouched; the framing around it is now truthful, and a JS-off client sees no figure at all.

**Remove the demand rail markup, do not touch its JavaScript.** Every `v3sell.js` access to the rail is null-guarded (`if (!el) return`, `if (rail)`, and a `forEach` over zero elements), so deleting the markup degrades the demand block to a no-op. Editing `v3sell.js` to delete the dead code would have meant touching operational script for a content fix. The now-idle twelve-second timer is left in place and flagged for a separate JavaScript cleanup. A test pins the null-guards so this reasoning stays checkable.

**Heading promotion.** The five intake section headings were `h3` directly under the `h1`, a heading-level skip. All styling is class-based (`.v3sell-fsh`), with no tag-qualified selectors, so promoting them to `h2` is semantic only and renders identically.

**og:image removed.** `og-hardware-sales.png` carries "Sourced, financed, deployed" over a mock inventory list with a "Request pricing" action. That is the buy-side proposition on a page about selling *to* SLYD, so it cannot share the proposition the spec requires Open Graph to carry. It has no prices or payment terms, so it was not unsafe, only wrong-facing. Omitted pending approved photography, consistent with the broker and lenders pages.

### Verification method worth reusing

Two harnesses were built, both in the session scratchpad:

- `domcontract.py` extracts the operational DOM contract from the razor: element ids, pill key/value pairs, `data-spec` keys, select options, input bounds, the form element, and CTA hrefs. Run before and after, then diff.
- `sellprobe.mjs` drives the real page over the Chrome DevTools Protocol with the platform API running, exercises an identical eight-step input sequence, adds a manifest line through the real `preview-line` endpoint, and captures the exact submit payload by stubbing **only** the submit fetch so the probe never writes a `SellSubmission`.

The DOM contract diff showed exactly three intended deltas and nothing else: `data_card_keys`, `data_live`, and `v3sell-buy-grid` removed (the demand rail), plus two new anchor ids and six internal links. `data_spec`, `pills`, `selects`, `inputs`, `form`, `accepts`, and `datalists` were byte-identical.

The runtime probe was identical before and after: same submit payload including `indicativeLow: 4620000` / `indicativeHigh: 5880000` parsed back out of the result panel, same values across all 21 `data-spec` bindings, same manifest rows and summary, same endpoints, zero console errors.

Running the platform API on :5080 matters here. Without it the valuation degrades to `$0` and the probe proves much less.

### Verification results

- Build: succeeded, 0 errors, 2 pre-existing NuGet advisory warnings.
- Tests: 96/96 pass (23 pre-existing, 29 broker, 29 hardware-sales, plus theory cases). Baseline before both pages was 23/23.
- Served HTML: one title, description, canonical, robots tag, and h1. Three JSON-LD blocks, all valid. FAQ visible text byte-identical to the FAQPage JSON-LD across all 10 questions. Zero static currency figures outside CSS colour values. All twelve retired claim strings absent. 21 `data-spec` bindings, 37 `v3sell-*` ids, and the form element all present.
- Links: all 7 internal targets return 200.
- Layout: `scrollWidth == clientWidth` at 1440x900, 1024x768, 390x844, 360x800. No JS exceptions at any viewport.
- Accessibility: one h1, no heading skips within page content, no unlabeled form controls, no images without alt, no empty link text, no positive tabindex, all 10 FAQ summaries keyboard focusable.

One real visual bug was found and fixed during QA: `.v3sell-val-hero` and `.v3sell-brk-card` both set `padding: 0` and carry padding on inner children, so the new caveat paragraphs rendered flush to the card edge.

## To Do Next

1. **Confirm which disposition paths are actually supported.** All four are published because the approved specification defines all four, but the spec also says "Do not show unsupported paths". Ops and legal must confirm that direct purchase, brokered sale, consignment or managed disposition, and trade-in/buyback/asset recovery are all currently offered, and remove any that are not.
2. **Legal and finance sign-off** on the compensation, payment, inspection, and title language, and on the disposition-path descriptions.
3. **og:image asset.** Produce an approved 1200x630 image of real, inspectable enterprise hardware with no prices, quantities, offer language, or payment terms, then restore `og:image` and `twitter:image`. A test asserts `og-hardware-sales.png` stays out.
4. **JavaScript cleanup pass.** The demand IIFE in `v3sell.js` (roughly lines 29-95) is now dead: a hard-coded table, a `Math.random()` walk, and a twelve-second `setInterval` that updates nothing. Removing it is a separate, JS-scoped change with its own verification.
5. **Runtime em dashes.** `v3sell.js` emits `'$—'` and `'—'` from `fmt()` and the empty-cache path, and `1–4 wk` uses an en dash. The no-em-dash rule was applied to authored content; operational script output was out of scope.
6. **Pre-existing, not introduced.** The shared `v3nav` mega-menu emits `h3`/`h4` headings before the page `h1` and keeps focusable links inside an `aria-hidden` container when closed. Site-wide, worth its own accessibility pass.
