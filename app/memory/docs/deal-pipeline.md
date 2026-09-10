---
title: Deal Pipeline
route: /v3/deal-flow/pipeline
audience: deal-ops, revenue-ops, finance
slug: deal-pipeline
surface: admin
---

# Deal Pipeline

The Deal Pipeline is the admin canvas for every deal moving from configuration to live deployment. It shows the four-stage state machine (Configuring → Financing → Escrowed → Live), the deals in each stage, and the canonical record for each deal — parties, lots, escrow accounts, documents, and the deployment summary. Open it at **V3 Deal Flow → Pipeline** (`/v3/deal-flow/pipeline`).

The customer-facing counterpart is **[Deal Room (customer flow)](/deals/{DealId})** — what each party (buyer / operator / broker / lender / supplier / offtake) sees of the same deal. **Both pages display the same record**; this doc defines the stages, the pipeline summary, and the admin-only advance action.

## Page layout

- **Header** — page title + subhead describing the five-step pipeline narrative (Source → Configure → Finance → Deploy → Match)
- **Stage board** — four large stage cards across the top, each clickable as a filter, showing count + total value per stage
- **Filter bar** — pill row: `All` + one pill per stage with counts, plus the counter on the right showing `SHOWN · TOTAL`
- **Left panel** — deals table
- **Right panel** — drawer with the deal detail, mini stage tracker, parties, lots, escrow, documents, deployment, an **Edit** button to mutate the deal record, and the **Advance Stage** button
- **Banners** at the top — success / error feedback

Clicking a row opens the drawer.

## The four-stage state machine

The state machine is **linear**. Transitions are enforced by the Deal entity — you can't skip a stage and you can't go back.

1. **CONFIGURING** — initial state; the deal record exists but spec, lots, and pricing are still being shaped
2. **FINANCING** — financing terms are being arranged (advance rate, APR, escrow setup)
3. **ESCROWED** — capacity is held via deposit; deployment is underway
4. **LIVE** — terminal; the cluster is in production

The header subhead and the customer-facing **[Deal Room](/deals/{DealId})** describe a **five-step narrative** (Source → Configure → Finance → Deploy → Match), but the database / state machine has four stages. **Source** isn't a stage — it's "this deal has lots allocated" and renders as **done** on the customer tracker the moment any lot is on the deal. See "Five-step narrative vs. four-stage machine" below.

## Stage board (top of page)

Four large cards across the top, one per stage. Each card shows:

- **Label** in upper-case (e.g. **CONFIGURING**)
- **Count** of deals currently in that stage
- **Total value** of deals in that stage (e.g. `$42.5M total`)

Each card is also a **filter button** — click it to scope the list to that stage. Click again to clear the filter.

## Filter the list

- **Stage pills** in the filter bar — `All` + one pill per stage with counts. Single-select.
- **Stage cards** at the top also filter (same single-select state).
- **Counter** on the right shows: `N DEALS · $M SHOWN · $T TOTAL`
  - `N DEALS` — count in the current filter
  - `$M SHOWN` — sum of value in the current filter
  - `$T TOTAL` — sum across the whole pipeline (unaffected by the filter)

There is no free-text search, no party search, no date range.

## Table columns

- **Deal** — DisplayId (accent mono)
- **Parties** — the party chain: **Buyer → Operator → Offtake**, each rendered as a chip. Each can be `—` if not yet bound.
- **Site** — the deal's site name (or `—`)
- **Region** — ISO code (e.g. `ERCOT`)
- **Power MW** — `kW / 1000` to one decimal place (e.g. `12.5`)
- **Value** — dollar value (`$12.5M`, `$840K`)
- **Lots** — count of hardware lots allocated (or `—` if zero)
- **Escrow** — count of escrow accounts (or `—` if zero)
- **Stage** — stage pill
- **Delivery** — promised delivery date if set, plus a **LATE** badge if past the promised date with no delivery, or a **DELIVERED** badge if delivered

## Inspect a deal (the drawer)

Click any row. The drawer shows:

### Header

- **DisplayId** as the heading
- **Site · Region · Stage pill** sub-line
- **Deal value** (large) + sub-line: `DEAL VALUE · N.N MW · CREATED <date>`

### Mini stage tracker

A 4-step horizontal tracker showing **CONFIGURING → FINANCING → ESCROWED → LIVE** with connectors. Steps the deal has reached light up as **done**.

### Detail grid

- **Promised Delivery** — date or `—`
- **Delivered** — date, `LATE` badge if overdue, or dim placeholder

### Parties section (`Parties · N`)

For each attributed party: **Role** label (Buyer / Operator / Broker / Lender / Supplier / Offtake), plus the **Account name** (from **[CRM Accounts](/v3/crm/accounts)**).

If no parties have been attributed yet, shows *"No parties attributed yet."*

### Lots section (`Lots · N`)

For each hardware lot: DisplayId, `<GPU model> × <Quantity>`, lot state pill. The lot lifecycle is defined in **[Inventory Lots](/v3/supply/inventory)** — this section is read-only.

Empty state: *"No hardware lots allocated."*

### Escrow section (`Escrow · N`)

For each escrow account: DisplayId, deposit dollar amount, escrow state pill. Definitions live in **[Escrow](/v3/settlement/escrow)**.

Empty state: *"No escrow accounts."*

### Documents section (`Documents · N`)

For each document: DisplayId, filename, kind (e.g. `Loi`, `Term sheet`, `Master agreement`), and either a **SIGNED** or **PENDING** pill.

Empty state: *"No documents attached."*

### Deployment section

If the deal has a deployment (post-Escrowed), the section shows the deployment DisplayId, GPU count, MRR dollar amount, and the deployment status pill. Full deployment surface is **[Deployments](/v3/deal-flow/deployments)**.

## Edit the deal record

Every scalar field on the deal is editable from the drawer.

1. Open the deal in the drawer.
2. Click **Edit** in the top-right of the drawer header. The read-only summary swaps to a form.
3. Edit any of the fields:
   - **Buyer** — dropdown of accounts (or — none —)
   - **Operator** — dropdown of accounts
   - **Offtake buyer** — dropdown of accounts
   - **Site** — dropdown of sites
   - **Value (USD)** — number input
   - **Power (kW)** — number input
   - **Region (ISO)** — text input (e.g. `ERCOT`)
   - **Promised delivery** — date picker
   - **Delivered** — date picker
4. Click **Save**. A success banner reads `<DisplayId> updated.` and the drawer reverts to the read-only view with the new values.
5. Click **Cancel** to discard changes and return to read-only.

Every save writes a `deal.updated` entry to the **[Audit Log](/v3/platform/audit)** with the before/after diff of every changed field.

### What's editable here vs not

Editable from the drawer:

- Buyer / Operator / Offtake-buyer account bindings
- Site binding
- Value, Power (kW), Region
- Promised delivery date, Delivered date

Not editable from the drawer (lives on its own surface):

- **Stage** — use the **Advance Stage** button below; transitions are linear
- **Lots** — bind/unbind via **[Inventory Lots](/v3/supply/inventory)** (RESERVED ↔ ALLOCATED + RESERVED → LISTED via Release)
- **Escrow accounts** — managed on **[Escrow](/v3/settlement/escrow)**
- **Documents** — managed on the document store
- **Deployment** — created downstream once the deal is **ESCROWED**

## Advance a deal to the next stage

The forward-only stage transition.

1. Open the deal in the drawer.
2. At the bottom, the button shows the next-stage label: **Advance stage — Mark Financing →**, **Advance stage — Mark Escrowed →**, or **Advance stage — Mark Live →**.
3. Click once. The button text changes to **Confirm — Mark Financing →** (or whichever next stage).
4. Click again to commit.
5. The drawer updates with the new stage; a success banner reads `<DisplayId> → <STAGE> — transition logged to the Audit Log.`

Two-click confirmation pattern (same as **[Brokers](/v3/platform/brokers)**). The action note below the button reads: *"Stage transitions are linear and enforced by the Deal entity. Each writes to the Audit Log."*

When the deal is **LIVE**, no Advance button shows. Instead a green note reads: *"Deal is LIVE — the cluster is in production. See Deployments for operational metrics."*

## Five-step narrative vs. four-stage machine

The page subhead reads *"Deals across Source → Configure → Finance → Deploy → Match"* — five steps. The state machine itself is **four stages** (Configuring / Financing / Escrowed / Live).

The narrative maps to the machine like this:

- **01 · Source** — "this deal has lots allocated to it" (not a stage; rendered as done on the customer tracker the moment Lots count > 0)
- **02 · Configure** — current while `CONFIGURING`
- **03 · Finance** — current while `FINANCING`
- **04 · Deploy** — current while `ESCROWED` (capacity escrowed, deployment underway)
- **05 · Match** — done at `LIVE`

The customer-facing **[Deal Room](/deals/{DealId})** uses the five-step tracker; this admin page uses the four-stage tracker. Both reflect the same underlying machine — just two different visualisations.

## What ops *cannot* do here

- Create a deal directly — deals are created on **[Match Engine](/v3/deal-flow/match-engine)** (Propose), **[Matching · 3-sided](/v3/deal-flow/matching)** (Assemble), or when an auction closes with a third-party winner
- Bind hardware lots from this page — see **[Inventory Lots](/v3/supply/inventory)** (RESERVED → ALLOCATED transition needs a deal pick)
- Add an escrow account — see **[Escrow](/v3/settlement/escrow)**
- Sign or upload a document
- Reverse a **stage** transition (Configuring → Financing → Escrowed → Live is one-directional; the Deal entity enforces this)
- Cancel or delete a deal from this page — the deletion path is **[Inventory Lots](/v3/supply/inventory)** → open the reserved lot → **Release** (only deletes the deal if it has no remaining lots, demands, parties, escrow, documents, or deployment)

## Things to know

- **Transitions are linear and one-directional.** There is no "go back a stage." The Deal entity enforces this. If a stage was advanced in error, escalate — there is no in-UI undo.
- **Two-click confirmation.** Every Advance Stage requires two clicks (Click → "Confirm — …" → Click). Same pattern as Brokers commission-ledger transitions.
- **LIVE is terminal.** Once a deal is LIVE, the action area shows the green resolved note; jump to **[Deployments](/v3/deal-flow/deployments)** for operational metrics.
- **Edit covers the deal's scalar fields only.** The drawer's **Edit** mode mutates parties (buyer/operator/offtake), site, value, power, region, and the two delivery dates — every save writes `deal.updated` to the **[Audit Log](/v3/platform/audit)** with the before/after diff. Lots, escrow, documents, deployment, and stage are out of scope; each has its own surface.
- **Lots, escrow, and documents are read-only here.** Each row in those mini-sections links conceptually to the source-of-truth surface — Inventory Lots, Escrow, the document store — and edits happen there.
- **Deal deletion lives on Inventory Lots.** A configuring-stage deal created via **Propose** can be cleanly removed by opening the reserved lot it's bound to on **[Inventory Lots](/v3/supply/inventory)** and clicking **Release**. That detaches the demand and deletes the deal **only if** it has no other lots, parties, escrow, documents, or deployment — anything further along leaves the deal intact and just unbinds the lot.
- **Stage card and pill filter are the same control.** Clicking the stage card and clicking the pill produce the same filter; the page just gives you two affordances.
- **Counter math.** `SHOWN` reflects the current filter; `TOTAL` is the entire pipeline regardless of filter. Don't confuse one for the other.
- **Late delivery is computed.** **LATE** appears when promised delivery date has passed and the deal isn't delivered yet (or was delivered after the date). The badge is informational — there is no in-page action attached.
- **The Parties chain in the row collapses to Buyer → Operator → Offtake.** That's the canonical chain on every deal. Other roles (broker, lender, supplier) only appear in the drawer's **Parties** list.
- **Audit trail.** Every stage advance writes a hash-chained entry visible on **[Platform Audit](/v3/platform/audit)** and on the customer's **[Deal Room](/deals/{DealId})** Audit tab.
- **The same record is what the customer sees.** **[Deal Room (customer flow)](/deals/{DealId})** opens on the same DealId and shows party-gated data — Overview / Spec / Finance / Documents / Audit tabs, a what-if financing dial, the five-step tracker, and party-visible action buttons (most disabled in v1). Use that doc to answer "what does my buyer see?"
