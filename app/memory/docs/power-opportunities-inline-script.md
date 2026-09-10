# Power Opportunities: "Pending" Estimate Card (inline script + enhanced nav)

**Project:** SLYD Website
**Date:** 2026-08-19
**Author:** e37b45cb-f2c9-4157-ab82-6508f53c3fa2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

### The bug

`/marketplace/power-opportunities` showed an estimate card reading "Pending to Pending",
"Pending", "Pending" where the indicative site revenue estimate should be.

The card is populated by JS from `data-spec` hooks. That JS was a 474-line **inline
`<script>`** at the foot of `PowerOpportunities.razor`. Blazor's enhanced navigation does
not execute inline scripts on internal-link arrivals, so the calculator only ever ran on a
hard page load. Confirmed both paths in headless Chromium:

| entry path | result |
|---|---|
| direct load / refresh | `$5.26M` to `$6.43M`, `PER YEAR · LEVELIZED` — works |
| clicked in-site link | `Pending` everywhere — never runs |

So it was invisible to anyone testing with a refresh, and broken for every real visitor
arriving from another page.

### Why inline scripts at all

No good reason — the repo already knows about this and had migrated away from it
everywhere else. `App.razor` carries five deferred globals (`v3sell.js`, `v3cfg.js`,
`v3events.js`, `v3faq.js`, `v3nav.js`), each with a comment saying exactly this: inline
`<script>` doesn't fire on enhanced-nav arrivals, so the code lives in a global that
no-ops when its markup is absent. The energy page simply never got migrated — its own
header comment even defers the script as "operational code" for a separate cleanup.

### The fix

1. Extracted the inline block to `wwwroot/js/v3energy.js`, wrapped in the standard
   `init()` that bails without `.v3energy`, guards re-entry with a dataset flag, and runs
   on both `DOMContentLoaded` and a debounced `MutationObserver` for enhanced nav.
2. Registered it deferred in `App.razor` alongside its siblings.
3. **The card now ships `hidden` and is revealed by the script only after the estimate is
   calculated.** Per Mason: if it isn't going to render anything useful, don't render it.
   Any future failure of this script shows nothing rather than a wall of "Pending".

Verified: both entry paths populate identically, and with JavaScript disabled the card
stays out of view rather than showing placeholders.

## To Do Next

Five pages still carry inline `<script>` blocks with the same latent failure — they will
work on refresh and silently do nothing on in-site navigation. Worth auditing the same way:

| file | inline JS |
|---|---|
| `Resources/GpuDatabase.razor` | 121 lines |
| `Marketplace/Marketplace.razor` | 97 lines |
| `Docs/Features/Instances.razor` | 23 lines |
| `Platform/Benson.razor` | 10 lines |
| `Blog/BlogPost.razor` | 7 lines |

(`App.razor` and `TopNavigation.razor` also match the grep but are chrome, not page code.)
