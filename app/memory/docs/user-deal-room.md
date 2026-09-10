---
title: Deal Room (customer flow)
route: /deals/{DealId}
audience: deal-ops, support, customer-success
slug: user-deal-room
surface: user
---

# Deal Room — customer flow

End-to-end walkthrough of what a signed-in deal **party** sees when they open `/deals/{DealId}` — the shared record every buyer, operator, broker, lender, supplier, and offtake counterparty reads against the same deal. The page is **party-gated**: a viewer who isn't on the deal sees a "Not a party" notice with no record visible.

The admin counterpart is **[Deal Pipeline](/v3/deal-flow/pipeline)**, which owns the canonical definitions of the deal stages, lots, escrow, parties, and the linear state machine. This doc only describes what a party themselves sees.

## Where the party starts — the index

Before the room itself, every signed-in party has a deal index at **`/deals`** (rendered as the **Deal Room** in their nav, *"The shared record every party reads and writes — one deal, one truth, across all of your roles."*).

The index shows one row per deal the signed-in account is a party to (FK or DealParty tag):

- **Deal** — DisplayId chip
- **Stage** — pill (Configuring / Financing / Escrowed / Live — see **[Deal Pipeline](/v3/deal-flow/pipeline)** for definitions)
- **Your role** — one or more role tags (Buyer / Operator / Broker / Lender / Supplier / Offtake) — a single account can hold multiple roles
- **Counterparties** — the other parties on the deal, joined with `·`
- **Value** — dollar value
- **Region** — ISO code
- **Updated** — relative timestamp

Clicking a row opens the deal room at `/deals/{DealId}`.

If the account isn't bound, the index shows: *"No account linked — No SLYD account is linked to your login yet — contact ops or your broker to claim your account."* This is the same "not bound" state surfaced on the **[Broker portal](/broker)** — the cause and fix are admin-side on **[CRM Accounts](/v3/crm/accounts)** → **Link customer user**.

If the account is bound but has no deals, the page shows: *"No deals yet — you're not a party to any deals. When a deal names your account — as buyer, operator, broker, lender, supplier, or offtake — it appears here."*

## Opening a deal — the access gate

When a party clicks into `/deals/{DealId}`:

- **If the viewer is a party to the deal** — the full room loads.
- **If not** — a single notice card appears: *"Not a party to this deal — This deal room is only visible to its parties — buyer, operator, broker, lender, supplier, or offtake. If you believe you should have access, contact ops or your broker."* No record data leaks; the same notice is shown whether the deal exists or not (so a stranger can't discover deal IDs by probing).

A **← Back to your deals** link returns them to `/deals`.

## Page layout (when access is granted)

- **Page header** — *Deal Room* title
- **Deal header strip** — breadcrumb (`Deals / <DisplayId>`), DisplayId + stage pill, deal value, MW, region, "updated <ago>", your role tags, and the **Export diligence pack** button (right side)
- **5-step pipeline tracker** — Source · Configure · Finance · Deploy · Match
- **PULSE heartbeat strip** — one tick per audit event (see "Pulse" below)
- **Tabs** — Overview / Spec / Finance / Documents / Audit
- **Right rail** — Parties card + Actions card

## Deal header strip

- Breadcrumb shows **Deals / <DisplayId>**
- Big DisplayId headline next to a **stage pill** (CONFIGURING / FINANCING / ESCROWED / LIVE — same labels as **[Deal Pipeline](/v3/deal-flow/pipeline)**)
- Meta row: `<deal value> · <MW> · <region> · updated <relative time>`
- A **YOUR ROLE** strip with one role pill per role the viewer holds on this deal
- Right side: **Deal value** (large) + sub-line `OPENED <date>`
- Right side action: **Export diligence pack** — a `.zip` link to `/api/deals/<id>/diligence-pack` containing the hash-chained audit log, deal summary, and document manifest. Designed for handing to a lender. The button's tooltip reads: *"Hash-chained audit log, deal summary, and document manifest — packaged for a lender."*

## The 5-step tracker

Five steps across the top:

1. **01 · Source** — done when the deal has any lots; sub-line shows `N LOT(S) · N GPUS` or `NO LOTS ALLOCATED`
2. **02 · Configure** — current while `CONFIGURING`
3. **03 · Finance** — current while `FINANCING`
4. **04 · Deploy** — current while `ESCROWED`
5. **05 · Match** — done at `LIVE`

This is the customer-side framing. **[Deal Pipeline](/v3/deal-flow/pipeline)** uses a 4-stage tracker; same underlying state machine, different visualisation.

## PULSE — the heartbeat strip

Below the tracker, a small horizontal strip of ticks reads **PULSE · N EVENTS**. Each tick is one audit event, colour-coded by actor class:

- **OPS** — SLYD operations
- **PARTY** — one of the parties (the viewer or a counterparty)
- **SYSTEM** — automation / state machine

Hovering shows `<Kind> · <Who> · <When>`. Clicking a tick **time-jumps** the room to the Audit tab with that event expanded.

The legend at the right reads `OPS PARTY SYSTEM` with colour swatches.

## Tabs

### Overview

- **Key facts** — Deal value, Power (MW), Region, Promised delivery (with **LATE** badge if overdue), Delivered date (with **DELIVERED** badge if delivered), Stage pill
- **Escrow summary** — three sub-cards: **Deposits held**, **Contract value secured**, **Offtake secured** (as a percentage). Hidden if no escrow exists; shows *"No escrow accounts on this deal yet."*
- **Deployment** — present once a deployment exists; shows DisplayId, GPU count, MW, deployment status pill

### Spec

The hardware lots allocated to the deal. Table columns: **Lot · GPU · Qty · Grade · State · Rate**.

Lot states are defined on **[Inventory Lots](/v3/supply/inventory)**.

Empty state: *"No hardware lots allocated to this deal yet."*

### Finance

The signature tab — three sub-sections:

**Offtake lever** — visual lever showing the deal's escrowed-offtake fraction against the threshold:
- Big **APR** number on the right
- **ADVANCE RATE** below it
- Sub-line below the bar: `<deal value> · BEST <best APR> @ <threshold> THRESHOLD`
- A path note explaining the current state

**What-if dial** — a draggable percentage slider letting the party explore what would happen to APR, advance rate, and estimated monthly cost if escrowed offtake reached a different percentage:
- Heading: **WHAT IF ESCROWED OFFTAKE REACHED <N>%**
- Outputs: **APR · <%>**, **ADVANCE · <%>**, **EST. MONTHLY · <$X>/36 mo**
- Delta chips: **−N bps** (save) / **+N bps** (cost), and the dollar-per-month delta
- Note: *"Simple-interest estimate over a 36-month term on `<deal value>` × advance rate — versus your current `<%>` escrowed offtake. The marketplace Forward board is where offtake gets escrowed."*

The math is the **same formula the public configurator uses** (so every surface agrees). See **[Pricing Engine](/v3/pricing/engine)** for the published config that drives the numbers, and **[Financing Curve](/v3/pricing/financing-curve)** for the APR / advance-rate curve specifically.

**Escrow accounts** — table: **Escrow · Deposit · Contract · Term · Window · State**. The escrow state and window definitions live on **[Escrow](/v3/settlement/escrow)**.

### Documents

List of documents on the deal. Each row shows the document **Kind** chip (Loi / Term Sheet / Master Agreement / etc.), filename, byte size, upload date, and either a **SIGNED** badge (with the signing date in the tooltip) or a **PENDING** badge.

Heading: `Documents · N · M signed`.

### Audit

The append-only, content-hashed deal history. Each event shows:
- Timestamp
- **Who** (e.g. *SLYD Ops*, the party name, or a system component)
- **Kind** chip (e.g. `stage.advanced`, `lot.allocated`, `escrow.placed`)
- Short hash chip (`#<8 chars>`) for events with a hash
- A **+** / **−** expander for events that have a before/after diff — expanding shows a two-column **Before** / **After** JSON view

When the viewer time-jumps from the PULSE strip, that event is auto-expanded.

The Audit log doc on **[Platform Audit](/v3/platform/audit)** describes the broader hash-chained ledger this tab is a per-deal slice of.

## Right rail — Parties + Actions

### Parties card

`Parties · N on record`.

If a **critical-path** condition has been derived from live state (escrow / wire / docs / delivery), a **waiting chip** appears at the top of the card with the most-blocking line — e.g. *"Waiting on lender wire confirmation."* Severity is colour-coded. The tooltip reads: *"Derived from live deal state — escrow, deposits, documents, delivery dates."* This is the only "what's the next thing?" hint on the page.

Each party row shows:

- Avatar (initials, colour-coded by role)
- Account name
- Role title
- Status line (with severity colour) — or `—` if no status
- **YOU** badge if this party is the viewer's account

### Actions card

A list of buttons. **In v1 these are intentionally inert** — they render as a preview of what's coming. Each button shows its text, a **COMING SOON** sub-label, and a role pin indicating which role can take that action.

Examples:
- **Request term sheet** — Buyer
- **Update delivery status** — Operator
- **Contact ops** — everyone

A note below the action list reads: *"v1 renders the action surface — these go live with deal-room mutations in the next release."*

## Things to know

- **Party-gated, not visibility-gated.** A non-party can't read any deal data, can't probe for the deal's existence — the "Not a party" notice is the same whether the deal exists or not. There's no "request access" workflow visible on the page.
- **Stage is read-only here.** The party sees the stage but cannot advance it. Stage transitions are an admin action on **[Deal Pipeline](/v3/deal-flow/pipeline)**. When the admin advances, the change appears in this room's PULSE strip and Audit tab on the next page load.
- **The Finance tab math matches the public configurator.** Same APR / advance / monthly formula. If a party's What-if estimate doesn't match what they got from `/configure`, the published Pricing Engine config has changed since the configurator session. See **[Pricing Engine](/v3/pricing/engine)**.
- **The What-if dial is fully exploratory.** Moving the slider doesn't change the deal — it only updates the on-screen estimate. Escrowing actual offtake happens on the **marketplace Forward board**.
- **Diligence pack export.** The button generates a `.zip` of the hash-chained audit log, deal summary, and document manifest. Aimed at lenders.
- **Heartbeat clicking is the fastest navigation.** Clicking any PULSE tick time-jumps to the Audit tab with that event expanded. Useful for "what happened on the 12th?" questions.
- **Waiting-on chip is derived live.** It reflects real state — escrow / wire / docs / delivery — not a manual workflow flag. If it says nothing, nothing's blocking.
- **Actions in v1 are inert.** Every button on the Actions card is disabled and labelled **COMING SOON**. If a party tells you they clicked something and "nothing happened" — confirm they're talking about an Actions button; that's expected behaviour, not a bug.
- **Audit events have full before/after diffs for the ones that mutate state.** Click the **+** chevron next to the event row to see the JSON delta. Useful when a party asks "what changed?"
- **Same record both sides see.** Anything visible in the admin **[Deal Pipeline](/v3/deal-flow/pipeline)** drawer is also here (with party-safe redactions). When an admin and a party are on the phone, they're looking at the same deal — the views differ in framing but not in data.
