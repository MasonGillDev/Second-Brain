---
title: Audit Log
route: /v3/platform/audit
audience: support, finance, exec, compliance
slug: audit-log
surface: admin
---

# Audit Log

The Audit Log is the **append-only, attributed, content-hashed** record of every state mutation on the V3 platform. It's the source-of-truth ledger that nearly every other doc in this knowledge base references when they say *"logged to the Audit Log"* — broker commission transitions, lot lifecycle moves, automation toggles, alert acknowledgements, account-type changes, pricing edits, and many more all land here.

Open at **V3 Platform → Audit** (`/v3/platform/audit`).

Every event chains to the previous one — each event's **AfterHash** covers the prior event's content, so tampering with or removing any historical row is **detectable**. The chain is what makes the log auditable, not just appendable.

## Page layout

- **Header** — page title + subhead emphasizing the append-only / hash-chained property + an **Export CSV** button (top right) and a download link after export
- **Filter bar** — Kind dropdown · Subject type dropdown · Search box · counter
- **Events table** — chronological list; click a row to expand the before/after diff
- **Banners** at the top — error feedback

## Hash-chain integrity

Each row has an **AfterHash** — a SHA-256 hash computed over the previous event's AfterHash plus this event's after-state JSON. That chain is what makes the log auditable:

- Tampering with any row breaks the chain forward from that row
- Removing any row makes the next row's hash recompute incorrectly
- The chain can be re-verified by any external party with the row data — no SLYD privileges needed

The **Hash** column shows the first 12 chars of the AfterHash as a chip with a link icon (and a `chained` tooltip).

## Filter the list

Three filters, all server-side, applied as you change them:

- **Kind** dropdown — `All kinds` + every distinct event Kind in the system (e.g. `lot.created`, `lot.advanced`, `broker.commission.earned`, `automation.enabled`, `alert.acknowledged`, etc.). The list is computed from existing events, so new kinds appear as they're emitted.
- **Subject type** dropdown — `All subjects` + every distinct subject entity type (e.g. `Lot`, `Broker`, `Deal`, `Demand`, `Account`, etc.).
- **Search** — free-text. Matches against **Subject ID** or **Actor** display.
- **Counter** on the right: `SHOWING N OF M` for the current filter.

## Table columns

- **When** — full timestamp to millisecond precision with timezone offset (`yyyy-MM-dd HH:mm:ss.fff zzz`)
- **Actor** — the human or system actor that caused the mutation (e.g. an admin name, *SLYD Ops*, *system:match-refresh-worker*)
- **Kind** — event kind chip (e.g. `lot.advanced`)
- **Subject** — subject entity type + DisplayId (e.g. `Lot LOT-2026-0042`)
- **Hash** — first 12 chars of the AfterHash, or `—` if no hash

## Inspect the before/after diff

Click any row to expand it. The page lazily loads the event's full body and renders a two-column **Before** / **After** view:

- **Before** — the JSON state of the subject before the mutation
  - Shows `— (created)` if this event created the subject (no prior state)
- **After** — the JSON state after the mutation
  - Shows `—` if this event was a deletion (no resulting state)

If the event has no body payload (some lightweight events don't carry one), the expanded row shows `no diff payload`.

Click the row again to collapse.

## Export CSV

The **Export CSV** button packages the **current filter** (Kind + Subject type, not Search) into a CSV:

1. Click **Export CSV** in the header.
2. The button is disabled while the export runs.
3. When ready, a **Download `audit-log-YYYYMMDD-HHmmss.csv`** link appears next to the export button.
4. Click the link to download.

The export uses an inline `data:` URL — no separate fetch needed.

## What ops *cannot* do here

This is the **strictest read-only** page in the admin. Every action is reading the chain:

- Edit, redact, or remove an event — by design
- Re-attribute an event to a different actor
- Add a manual note to an event
- Re-emit a missed event
- Trigger a chain verification scan from the page

Tampering would break the chain forward; the page deliberately exposes nothing that would let ops do that.

## Things to know

- **The chain is the contract.** Each event's AfterHash covers the prior event. Editing or removing any row breaks the chain forward, which any auditor can detect by recomputing hashes externally. This is the whole point of the log.
- **Every "logged to the Audit Log" reference in other docs lands here.** Brokers, Inventory Lots, Demand Book, Automations, Match Alerts, Compliance, Pricing Engine, and the rest — all of their audited mutations show up on this page with the relevant Subject type and Kind.
- **Actor naming convention.** A row's Actor is either an admin's display name (real human), `SLYD Ops` (a generic ops attribution), or a system component (e.g. `system:match-refresh-worker`). The pattern matters for filtering — humans, ops, and systems each surface differently.
- **Timestamps are to the millisecond with timezone.** Useful for forensic work — two events emitted in the same second are still orderable.
- **Lazy diff load.** Expanding a row fetches the before/after body — collapsed rows don't carry the JSON. If a diff doesn't appear immediately, the page is loading it.
- **Empty diff is normal for some kinds.** Lightweight kinds (e.g. an acknowledgement) don't carry before/after JSON. `no diff payload` isn't a bug.
- **CSV export ignores Search.** Only the Kind and Subject type filters scope the export. Use Kind / Subject type to narrow before exporting if you need a focused CSV.
- **Customer-side, the same chain feeds the Deal Room.** The **[Deal Room (customer flow)](/deals/{DealId})** Audit tab is a deal-scoped slice of this log — same events, same hashes, same chain. Customers can verify their own deal's chain just as ops can verify the global one.
- **Diligence pack on the deal room is derived from this log.** When a deal party clicks **Export diligence pack** on **[Deal Room](/deals/{DealId})**, the package includes the deal's audit chain — same data as appears here filtered to that deal.
