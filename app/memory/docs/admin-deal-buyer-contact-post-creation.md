# Attach a Buyer Contact to a Deal After Creation

**Project:** SLYD Platform — Admin
**Date:** 2026-08-12
**Author:** c92e3c52-8093-43b7-9313-c243e44b6d5b
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

### The gap

Question that started this: "can I attach a contact to a deal after the deal is created?" Answer was **no** — the buyer contact could only be set in the new-deal dialog, and there was no way to fix or add it later.

Contact attribution lives on `DealParty.ContactId` (`core/src/SLYD.Domain/Models/DealOS/DealParty.cs:29`), not on the `Deal` row. Only two places wrote a `DealParty`:

1. `DealPipelineFeatures.CreateDealAsync` — the Buyer party, at creation only.
2. `DealWorkspaceFeatures.SelectQuoteAsync` — a *Supplier* party carrying the RFQ's contact, and only via `??=` (fills a blank, never replaces).

`DealEditRequest` had no contact field and `UpdateDealAsync` never touched `DealParties`. `DealDetail.razor:68` rendered the buyer contact read-only.

### The change

**No DB migration needed.** `DealParties.ContactId` already exists as a nullable column with an index and an FK (`onDelete: SetNull`) from migration `20260720190328_AddDealPartyContact`; configured at `SlydDbContext.cs:1103`. Nothing to bump in Core, no efbundle step in CI/CD.

- **`PipelineModels.cs`** — `DealEditRequest` gains `BuyerContactId` + `ClearBuyerContact`. `DealPartyItem` gains `ContactId` + `ContactName` so the drawer can show and prefill the person.
- **`DealPipelineFeatures.cs`** — new `ApplyBuyerContactAsync` upserts the Buyer `DealParty`; new `BuyerParty(Deal)` helper; `LoadDetailAsync` includes `Parties.Contact`; `ToDetail` maps it; audit `before`/`after` carry `BuyerContactId`.
- **`Pipeline.razor`** — buyer-contact picker in the edit drawer (list follows the buyer selection), prefill, save wiring, and the attributed person shown on the party rail.
- **`DealPipelineContactTests.cs`** — 8 tests, all passing.

### Key decisions and why

**Attribution is only touched when the edit asks for it.** `ApplyBuyerContactAsync` returns immediately unless `BuyerContactId` is set or `ClearBuyerContact` is true. A contact is deal history, not form state — it must survive every unrelated field edit.

**Retarget the existing Buyer party, never insert a second one.** The unique index is `(DealId, AccountId, Role)` — *not* `(DealId, Role)` — so the schema happily permits two Buyer rows pointing at different accounts. If someone swapped the buyer account and set a contact in one save, a naive insert would leave two Buyer rows and double-count the deal in every account-involvement query (`AccountWorkspaceFeatures`, `AccountDirectoryFeatures`, `ContactWorkspaceFeatures` all read `DealParty`). `BuyerParty()` prefers the row matching the Deal's buyer FK so legacy deals that already have two rows still resolve correctly.

**Contact is applied after the FK mutations**, so it validates against the buyer account the save *leaves behind*, not the one it started with. Attaching the outgoing buyer's contact while changing buyers now throws instead of silently attributing the deal to someone at a company no longer party to it.

**Clearing the contact keeps the party row.** The company is still the buyer; only the person attribution goes away.

**The UI sends contact fields only when the selection actually changed** (`_editContactOriginal`). This was a review catch, and it matters: `DealParty.cs:26-27` documents that a contact moving companies mid-deal must not invalidate historical attribution (enforced at the service layer, not the schema). Once that happens, `ListContactsForAccountAsync` stops returning them — so an unchanged prefilled id would have been shipped on the next unrelated save and rejected by the new validation, blocking an edit that had nothing to do with contacts. Paired with `RetainAttributed()`, which keeps the already-attributed person visible in the picker labelled "no longer at this account" rather than showing an apparently-empty selection.

### Verification

`dotnet build src/Admin/Admin.csproj` → 0 errors (137 warnings, all pre-existing in unrelated files).
`dotnet test tests/Admin.Tests/Admin.Tests.csproj` → **206/206 passed**, including the 8 new ones.

Not committed — the repo convention is to ask first, and no commit was requested.

## To Do Next

- **Supplier-side contacts are still create-only in effect.** `SelectQuoteAsync` uses `party.ContactId ??= quote.Rfq.ContactId`, so once a Supplier party has a person, re-selecting a different quote never updates them. Same class of gap as the one just fixed, on the sell side.
- **Only the Buyer role is editable.** Operator, Broker, Lender, Supplier, and OfftakeBuyer parties have no contact UI at all. If ops wants "who at the operator is this deal with", that needs a party-level editor rather than the single buyer-contact field.
- **Buyer-account change without a contact edit leaves a stale party.** Pre-existing behavior, deliberately not widened here: changing the buyer account alone still leaves the old Buyer `DealParty` pointing at the old account. Only a save that also touches the contact retargets it.
