# Deal Quote Builder — Data Models (DealLineItem / Rfq / SupplierQuote)

**Project:** SLYD core libraries
**Date:** 2026-07-20
**Author:** 4dc3e1b6-5bbc-4993-81e5-861e58f31a24
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

Schema layer for the whale-deal quote builder (requirements source: NorthVault
RFQ sheet — see Second Brain `2026-07-20-northvault-rfq-strategy-crm-reference.md`).
Data models only, per Mason — the dedicated deal workspace UI comes later.

### Context confirmed before building

Mason had already completed (verified via Brain timeline + working tree):
reader migration onto AccountMember, auto-mint fully dead (`AccountProvisioning`
deleted → `ClaimResolution` member/lead branching), Admin account + contact
workspace pages, Leads inbox inbound/outbound tabs, `ContactEngagement`
scoring, intake ContactId links, Lead capture fields. All uncommitted on
`feat/capacity-matching-pass`.

### The model (flow: lines → RFQs → quotes → curated selection)

- `DealLineItem` — BOM line on a Deal (`Deal.Lines` collection added).
  LineNumber, `AssetCategory` + Subcategory + SpecJson (mirrors
  SellSubmissionLine), Description, headline Quantity (0 = lot-scoped),
  `DealLinePriority` (Unset=0, Immediate=1, High=2, Standard=3 — sheet tiers),
  and `SelectedQuoteId` (SetNull) = "attach the supplier to the line" moment;
  losing quotes survive as supplier history.
- `Rfq` — one supplier account asked to quote one line. Unique
  (DealLineItemId, SupplierAccountId); revisions are quote rows, not new RFQs.
  ContactId (who at the supplier — default routing by
  Contact.RelationshipStatus descending, ops-overridable), OutreachOrder,
  IsPrimary. State machine (BrokerSubmission pattern, private setter +
  transition methods): Draft=0 → Sent → Quoted/Declined; Withdrawn from
  Draft/Sent only; MarkQuoted allowed from Quoted (revisions); Quoted RFQs
  can't be withdrawn. Supplier FK is Restrict (accounts with sourcing history
  can't be hard-deleted).
- `SupplierQuote` — AmountUsd, LeadTimeDays, ValidUntil, Notes,
  DealDocumentId (quote PDF as DealDocument, SetNull), ReceivedAt vs CreatedAt.
  Append-only revisions; latest ReceivedAt is current.

Migration `20260720…_AddDealQuoteBuilder`. Cycle (line→quote→rfq→line) is fine
on Postgres; EF adds the SelectedQuoteId FK after both tables exist.

### Tests

- `RfqStateMachineTests` (unit): all transitions + blocked paths + enum pins.
- `QuoteBuilderSchemaTests` (integration): full-graph round trip with selection,
  unique-index rejection, line-delete cascade (supplier account untouched),
  selected-quote delete → SetNull reopens line, supplier-delete Restrict.
  Note: `ExecuteDeleteAsync` bypasses SaveChanges, so Restrict surfaces as
  `PostgresException` 23503, not `DbUpdateException`.
- Green: 578 unit / 54 integration.

### Deliberately deferred (keep in mind)

1. **Deal workspace UI**: manual deal creation — pick end-buyer account/contact
   ("whatever the term" — likely the Buyer DealParty + primary contact), add
   lines, run RFQ → quote → curated quote. Data model supports it now.
2. **Supplier capability tagging** (sales: "sort suppliers by what they provide
   — OEM for GPU / naddod for optics — fill in requirements and blast it out;
   would cut quote time in half"): future `Account` supplier-category tags
   (OperatorCapabilities list pattern) → auto-suggest RFQ fan-out per line
   category → bulk MarkSent. Rfq model needs no change for this.
3. Deal.Value roll-up from selected quotes (service-layer, when workspace lands).
4. RFQ DisplayId ("RFQ-" prefix) stamping — service layer.

## To Do Next

- Commit everything (branch decision: suggest fresh feat branch off main), tag, publish core.
- Deal workspace UI in admin (create deal, lines, RFQ board) when Mason says go.
- Supplier capability tags + blast-out flow (sales' ask) after workspace v1.
