# Deal OS sales rep tutorial

**Project:** SLYD Admin (Deal OS / CRM)
**Date:** 2026-08-14
**Author:** e503dc75-e0cf-4a94-b311-c18127000c13
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Wrote an onboarding tutorial for a sales rep using the CRM / Deal OS, published as
a private artifact:

**https://claude.ai/code/artifact/3b06f072-88e6-4e90-85d0-f6e2fef24643**

### Approach

Everything in it was read out of the code rather than assumed, because the parts a
rep gets stuck on are exactly the parts that are enforced in the service layer and
invisible from the UI. The tutorial is structured as: the five records → where
things live in the nav → the eight-step core loop → **the stage gate reference** →
troubleshooting → rules that bite.

### Sources it was written from

| Claim in the guide | Where it came from |
|---|---|
| Six stages + Lost terminal from any open stage | `Deal.cs` `DealStage` enum, `Deal.Advance` / `MarkLost` |
| The full gate table, per deal shape | `DealPipelineFeatures.RequirementsFor` (~line 935) — Capacity, BOM (`d.Lines.Count > 0`), Hardware/ThreeSided branches |
| Escrow row is advisory, bypass is audited | `EscrowWarning` + `BypassedWarnings` in the same file |
| Match hard filters (category, subcategory, exact GPU model, lot state) | `MatchScoringService.IsExcluded` (~line 214) |
| Region distance bands 500 / 1,500 / 3,000 mi | `MatchingConstants` |
| Propose creates deal, reserves lot, binds demand; `Value = Price × Quantity` | `ProposalDraftService.CreateDraftAsync` |
| Lead conversion is one-time and always lands on an account | `CrmLeadFeatures.ConvertToContactAsync` |
| Demand states Open / ReVerify / Matched / Expired / Withdrawn | `Demand.cs` |
| Reserved lot can't be re-pointed — Release first | `InventoryLotFeatures.AdvanceAsync`, Reserved branch |
| Nav sections and routes | `NavRegistry.cs` |

### Two things worth knowing that the guide calls out explicitly

1. **`Lead.Qualified` is a direction-of-intent flag, not a quality score.** True =
   outbound (we sourced them), false = inbound (they came to us). The name reads as
   "this lead is qualified" and it does not mean that. Documented in `Lead.cs:34-40`.
   Worth renaming at some point — the guide works around it instead.
2. **Claimed ≠ matchable** is the single most common "why can't I sell this" and it
   is deliberate: it stops us quoting against phantom inventory. The guide teaches it
   as a rule rather than a bug.

### Design

Palette and semantics lifted from the product's own `DesignTokens.css` (SLYD indigo
accent, the same teal/amber/red for met/advisory/blocked) so the guide reads as part
of Deal OS. Light and dark both handled at token level.

## To Do Next

- **Get it reviewed by someone who actually sells** before it goes to a new rep —
  it is accurate to the code but unproven against how the job really runs.
- The guide has no screenshots. The gate table and Match Engine sections would be
  much stronger with them; worth adding once someone can grab clean captures.
- If the Deal OS UI changes, this needs a pass — republish the same file path (or
  pass the artifact URL) to keep the link stable.
