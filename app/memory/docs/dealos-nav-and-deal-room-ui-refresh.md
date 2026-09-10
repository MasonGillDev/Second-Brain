# DealOS Nav & Deal Room UI Refresh

**Project:** SLYD Platform (Platform.WebUI)
**Date:** 2026-07-16
**Author:** 03cffc02-2e8e-447d-906d-8347231fd42b
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

A session of UI polish across the DealOS surfaces, the shared sidebar nav, and app load. Committed to `development` as `59b7a9a` (14 files, +553/−451). **Not pushed** — per repo rules the human runs `git push` manually.

### Sidebar nav (`UnifiedNavMenu.razor` / `.razor.css`)
- Made the **Deal OS** section collapsible like the other sections (added `_dealOsExpanded`, toggle, chevron, aria-expanded). Defaults expanded.
- Removed the per-page link icons (kept the section-level icons). Done with a precise `perl` line delete matching `^\s*<i class="fa[sb] fa-[^"]*"></i>$` since duplicate icon classes made individual edits fragile.
- Removed the `<OrganizationDisplay />` "Org ID:" block from the nav.
- Made the whole nav **translucent** (`--slyd-bg-glass` + `backdrop-filter: blur(16px) saturate(140%)`).
- Active page indicator is now a **clean frosted-glass rounded rectangle** (`--slyd-card-bg-frosted-glass`, `--slyd-radius-md`, subtle border) — removed the blue left accent bar and the old glow.
- Fixed a **deactivation glitch** (lingering border on navigate) by narrowing `.nav-item` transition from `all` to `color, background-color` so the frosted pill snaps in/out as one unit.
- Hover text → white (`--slyd-text-primary`), not blue.
- Removed the `:focus` outline on section headers (kept `:focus-visible`) so clicking to expand doesn't flash a blue ring.
- **Tried and reverted**: a blue left→right (then right→left) light-source glow behind nav content, and an earlier full inset-glass card treatment. User wanted something cleaner; both were reverted.

### Deal OS dashboard (`DealOsDashboard.razor` / `.razor.css`)
- Removed the **role lens switcher** ("All / Buyer / Operator / Offtake") and the whole `page-head-actions` header (the "AccountName · viewing everything" line).
- Removed the style-changing lens code: `SetLens`, `ApplyLensAttributeAsync` (the `slydLens.set` / `data-lens` retint interop), `_lens`, `LensEcho`, `RoleTitle`. `VisiblePipeline`/`VisibleActions` now just return the full account dataset. Kept `RoleCss`/`RoleLabel` (still used by deal-row role tags). Removed the corresponding `.lens*` CSS.

### Marketplace (`GatedMarketplace.razor`, `marketplace-floor.js`)
- Removed the "EXACT PRICING · SIGNED IN" gate pill from the tab strip.
- **Left carousel arrow bug**: it showed at rest even with nothing to the left. Cause: `.mkt-carousel` has `scroll-snap-type: x mandatory` + `padding-left: 22px`, so the resting `scrollLeft` settles ~22px, above the old `< 8` gate. Fixed by gating the left arrow against the container's computed `paddingLeft` (`scrollLeft <= startPad + 8`).

### Deal room (`DealRoom.razor` / `.razor.css`)
- Removed the audit-log **"PULSE" heartbeat strip** (markup + `HbClass`/`JumpToAudit` helpers + all `.hb-*`/`.heartbeat` CSS). `_expandedAudit` kept (Audit tab still uses it).
- Removed the **hourglass glyph** (`⏳`) from the waiting chip and its `.wc-ico` CSS.
- **Right-rail alignment**: moved `.tabs` out of `.dmain` to be a direct child of `.dbody`, then used `grid-template-areas` (`"tabs ." / "main rail"`) so the rail lines up with the top of the Key facts panel, not the tab strip. Mobile breakpoint gets single-column areas.
- **Audit tab readability**: the before/after snapshots were raw JSON in `<pre>`. Now parsed into readable `Label → Value` field lists (`ReadAuditFields`, `FormatAuditValue`, `FormatAuditString` for ISO dates, `HumanizeKey` for camel/snake → Title Case). Falls back to raw text if not JSON.
- **PII filter**: added `IsIdentifierKey` to drop fields whose key is a whole-word `Id`/`Ids`/`Guid`/`Uuid` (e.g. `BuyerAccountId` GUID), including inside nested objects — avoids false positives like "Idempotency".

### App load (`PlatformLayout.razor.css`)
- Fixed a "glitchy pop-in": content (`.dashboard-layout`) revealed after the loading panel was already gone via a quick `0.15s ease-in 0.3s`. Changed to `transition: opacity 0.6s ease-out 0.1s` so it fades in **through** the loading panel's 0.3s fade-out (crossfade, no pop).

### Also in the commit (were already modified in the working tree)
- `SettingsV3.razor` / `.razor.css` — KYC upload layout restructure (`kyc-fields`, `kyc-field`, etc.).
- `LogoSection.razor`, `StandardPageHeader.razor.css` — minor UI.
- `mockups/marketplace-mockup-inset-glass.html` — design reference iteration.

## To Do Next
- `git push` to `development` (human-run; network ops are not done by Claude here).
- Marketplace: the now-unused `.tabs .gate` CSS can be stripped.
- Audit tab: numeric fields (e.g. `AmountUsd`) render raw — could add key-name-based money/kW formatting if desired.
