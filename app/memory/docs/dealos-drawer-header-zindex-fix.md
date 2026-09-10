# Fix detail-drawer overlapping the page header on Source & Marketplace

**Project:** SLYD Platform (platform repo — Platform.WebUI)
**Date:** 2026-07-14
**Author:** 276f1528-e953-4da9-bd82-394c87a78d93

## What Was Done

Fixed the slide-out lot/capacity **detail drawer** on the Source (`/source`) and Marketplace (`GatedMarketplace`) pages rendering *beneath* the fixed page header — the bell / wallet / avatar cluster painted on top of the drawer's title area (see the LOT-2026-0006 screenshot the user reported).

**Root cause:** `.standard-page-header` (in `src/Platform.WebUI/Components/UI/Common/StandardPageHeader.razor.css`) is a positioned stacking context at `z-index: 200`. The two drawers were ported from HTML mockups at `z-index: 60` (scrim) / `70` (panel) and never reconciled — so the header won the stack. The app's real modals (`wwwroot/css/modals.css`) sit at `z-index: 1000`, above the 200 header.

**Fix:** Raised both drawers to the modal tier so they cover the header like a proper full-height modal:
- `src/Platform.WebUI/Components/Pages/DealOS/Source.razor.css` — `.scrim` 60→1000, `.drawer` 70→1010.
- `src/Platform.WebUI/Components/Pages/DealOS/GatedMarketplace.razor.css` — same 1000/1010.
Added comments on each explaining they must clear the 200 header.

**Scope check ("maybe others"):** Swept every fixed overlay in the component tree. The only other full-height right-side drawer is the Broker "Submit a deal" panel (`BrokerPortal.razor.css`) — it dodges the overlap a *different* way (`top: 160px`, sitting below the header rather than over it), so it's not visually broken and was left alone. Remaining `z-index: 100/90/50` elements are sticky sub-headers / dropdowns / a filter panel intentionally kept below the header.

Build passes (0 errors). Not committed/pushed.

## To Do Next

- Optional consistency cleanup: the Broker "Submit a deal" drawer's `top: 160px` is a fragile hack (its own comment admits it's pinned to the header's rendered height). Could convert it to `top: 0` + the same `1000/1010` z-index tier so all three drawers behave identically as full-height modals. Offered to the user; pending their word.
