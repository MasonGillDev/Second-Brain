# Gate Deploy (operator) and Broker portals behind capability requests

**Project:** SLYD Platform (platform repo — Platform.WebUI)
**Date:** 2026-07-14
**Author:** 276f1528-e953-4da9-bd82-394c87a78d93

## What Was Done

Gated the `/deploy` (operator console) and `/broker` (broker portal) customer surfaces so accounts lacking the capability can't see the surface, and gave each a **request-access button** that files the request into the admin CRM feed. This mirrors the existing Settings "Request activation" flow rather than inventing a new mechanism.

**Why:** Deploy is an operator-only surface (run clusters, list capacity, revenue). It previously rendered for any linked account. The broker page already had a dead-end "contact partnerships@" notice for non-brokers. The user wanted both gated with a self-serve request that ops reviews — capabilities are ops-granted, never self-served (CLAUDE.md rule #6).

**Key decisions:**
- **Reused `ISettingsSurfaceService.RequestCapabilityAsync(capabilityLabel)`** (in `Platform.WebUI/Services/SettingsSurfaceService.cs`) instead of writing new request plumbing. It writes a `[CAPABILITY REQUEST]` `Activity` (Kind=Note) on the caller's account, which surfaces in the admin Activities feed. Validated against the known capability set; returns false when no account is linked.
- **Operator capability derivation** added to `DeploySurfaceService.GetAsync` (`Platform.WebUI/Services/DeploySurfaceService.cs`): new `IsOperator` bool on `DeploySurfaceView`. True when `Account.Type == Operator` OR the account holds the `Operator` role on any deal (`Deal.OperatorAccountId` slot or a `DealParty` row). This mirrors exactly how `SettingsSurfaceService` derives the Operator capability, so the two surfaces agree.
- **No popup.** First implementation used an auto-opening modal popup on landing; the user rejected it. Final UX is an inline `notice-card` gate ("Operator/Broker access required") with the request button right there. Clicking sends the request directly (busy → "Sending…" → "Request sent" confirmation, with inline error on failure). The whole clusters/KPIs/listings surface is hidden for non-operators.
- **Broker page made to match:** the `!_view.IsBroker` branch in `BrokerPortal.razor` changed from a dead-end notice to "Broker access required" + a "Request broker access" button calling `RequestCapabilityAsync("Broker")`. Same busy/sent/error states.

**Files touched:**
- `src/Platform.WebUI/Services/DeploySurfaceService.cs` — added `IsOperator` to `DeploySurfaceView` (+ `NotLinked()` factory), computed it in `GetAsync` (fetch `Account.Type`, query deals for Operator role).
- `src/Platform.WebUI/Components/Pages/DealOS/Deploy.razor` — injected `ISettingsSurfaceService`; added `!IsOperator` gate branch with request button; `RequestOperatorAsync` calling `SettingsSurfaceService.CapabilityLabel(DealPartyRole.Operator)`.
- `src/Platform.WebUI/Components/Pages/DealOS/Deploy.razor.css` — `.gate-sent` + notice-card button spacing (popup CSS was added then removed).
- `src/Platform.WebUI/Components/Pages/DealOS/BrokerPortal.razor` (+ `.razor.css`) — injected settings service; request button + `RequestBrokerAsync`; `.gate-sent`, `.submit-cta:disabled` styles.

Build passes (0 errors). Nothing committed/pushed (per network-operations boundary — human pushes).

## To Do Next

- Optional hardening: `DeploySurfaceService.ListSpareCapacityAsync` currently only UI-gates the operator surface. If we want a true API-layer block, reject non-operators server-side there (mirror CLAUDE.md rule #2/#9 "enforce at the API layer"). Not done yet — the user was offered this and it's pending their word.
