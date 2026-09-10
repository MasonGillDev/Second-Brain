# V3Nav — Nav Item State Restyle (pill → underline)

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** da01a02d-ae5d-49a8-ab48-50a4007bdff9
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

Mason flagged the highlighted nav item as looking "strange" and asked for something cleaner but
still minimal. Replaced the filled-pill hover/open treatment with an underline rule, and fixed
two pre-existing bugs found while doing it.

Chosen from three options (underline / softer pill / text-only); Mason picked the underline.
A current-page indicator was offered and deliberately deferred — this nav has none at all.

### The visible change

| state | before | after |
|---|---|---|
| rest | `--text-primary` | `--text-secondary` (11.01:1 contrast, passes) |
| hover | `background: var(--bg-elevated)` — solid grey pill | text → `--text-primary`, 1.5px rule at 50% opacity |
| open | `background: var(--primary-soft)` — indigo pill | text → `--text-primary`, 1.5px rule in `--primary` at full opacity |
| focus | **nothing** | `outline: 2px solid var(--primary)` |

The open-state rule takes the accent colour so it reads as connected to the mega-menu panel
directly beneath it — the filled block used to compete with that panel.

### Pre-existing bug 1 — `.v3nav-item` padding never applied

The root cause of the "strange" look. `.v3nav-top button` (line 58) sets `padding: 0`:

```
.v3nav-top button[b-scope]   →  (0,2,1)   wins
.v3nav-item[b-scope]         →  (0,2,0)
```

Class + type beats class, so `.v3nav-item { padding: 12px 18px }` has **never** taken effect.
Measured on the live page: computed `padding: 0px`, item height 26.3px = exactly the 26.35px
line-height. The pill was therefore drawn tight around the raw text box with no breathing room,
which is precisely why it looked cramped and off.

This also broke my first attempt: I inset the underline by `--nav-pad-x: 18px` on each side,
assuming the padding existed. On a box only as wide as the word, that made the rule *narrower
than the label*. Caught it by measuring the DOM rather than trusting the stylesheet.

**Decision: did not restore the padding.** Making it apply would grow the header by ~24px —
a layout change well beyond what was asked. The rule now spans the full item box (= the word)
and sits at `bottom: -6px`. The dead `padding` declaration was removed and the reason recorded
in a comment so the next person doesn't re-add it.

### Pre-existing bug 2 — labels ran together at ≤1140px

Direct consequence of bug 1. The `@media (max-width: 1140px)` block sets
`.v3nav-items { gap: 4px }`, which only makes sense if each item contributed its own 12px of
horizontal padding. With that padding inert, 4px was the *entire* separation between labels —
at 1100px the nav read as "The Fabric Hardware Marketplace Financing Resources Docs" nearly
touching. Raised to `gap: 16px`, restoring a tightened but readable rhythm from gap alone.
Screenshot at 1100px confirms the fix.

### Verification

- `dotnet build --no-incremental` — succeeded, 0 errors.
- Contrast computed from the actual tokens against `--slyd-bg-body` hsl(229,84%,4%):
  rest **11.01:1**, hover **18.54:1**. Both pass WCAG AA for 17px/600 text (needs 4.5:1).
- Screenshots at 1440px (rest, hover, open) and 1100px (hover). Open state verified by applying
  `.v3nav-item-open` directly — synthetic CDP clicks don't trigger the mega-menu JS.
- Computed `::after` on the open item: `opacity=1, rgb(100,103,242), h=1.5px, bottom=-6px`.
- `prefers-reduced-motion` block extended to cover `.v3nav-item::after`, which the new
  opacity/colour transitions live on.

### ⚠️ Test suite is red — not from this change

`dotnet test` reports **6 failures / 244 passing**. All six are the concurrent session's, not
mine:

```
BrokerPageContentTests.Breadcrumb_and_decorative_markers_carry_correct_semantics
ComputeMarketplacePageContentTests.Structured_data_is_page_level_only
HardwareSalesPageContentTests.Breadcrumb_and_decorative_markers_carry_correct_semantics
NeedIntakePageContentTests.Breadcrumb_carries_correct_semantics
NeedIntakePageContentTests.Code_block_is_byte_for_byte_unchanged
PowerOpportunitiesPageContentTests.Breadcrumb_carries_correct_semantics
```

Evidence it isn't this work:

- **No test in the suite references `V3Nav` or `Governance`** (grepped).
- Each failing test reads only its own page file — Broker, Compute, HardwareSales, Need,
  PowerOpportunities. None of those are files I touched.
- Those five pages were written at **11:40:30**; my V3Nav edit was **11:57:13**.
- The suite passed **250/250 at ~11:05**, after my governance work and before their 11:40 edits.
- The diffs show the breadcrumb-unification sweep in progress: hand-rolled
  `<nav class="need-crumb">` being replaced with `<Breadcrumb Items="..." EmitStructuredData="false" />`.
  The failures are exactly the breadcrumb-semantics and byte-for-byte `@code` guards those pages
  carry.

**Those six need to go green before anything here is committed** — they're the other session's
to finish, not a regression to chase.

## To Do Next

1. **Not committed.** Tree holds three interleaved changesets now: the governance rebuild
   ([[governance-page-v3-design-unification]]), this nav restyle, and the concurrent session's
   in-flight breadcrumb sweep with its 6 red tests.
2. **No current-page indicator.** This nav still shows nothing for the section you're in —
   `/platform/governance` doesn't highlight "The Fabric". Offered and deferred; would need route
   matching wired into V3Nav. Worth doing.
3. **The `.v3nav-top button` specificity trap is still armed.** Any future rule on `.v3nav-item`
   that sets a property the button reset also sets (padding, background, border, color) will be
   silently ignored. Consider scoping the reset to `:where(.v3nav-top) button` so it carries zero
   specificity, which would let `.v3nav-item` win naturally — and would restore the intended
   padding, so pair it with a deliberate decision about header height.
4. Check whether other V3 pages' local button resets have the same trap.
