# Deal Flow: Escrow Gate Downgraded from Blocker to Warning

**Project:** SLYD Admin Portal
**Date:** 2026-08-03
**Author:** fdc3226f-77ce-4366-9023-007ba5ad0235
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

The Financing → Escrowed transition required "At least one HELD escrow on the deal" as a hard gate. Not every deal settles through escrow (direct wire, existing MSA terms, intra-group transfers), so this blocked legitimate deals and pressured ops into opening sham escrow records purely to clear the check. The Financing stage itself was kept — only the blocker was removed.

### Design decision: advisory requirements, not deletion

Rather than deleting the escrow row (which loses the signal entirely), `StageRequirement` gained a third member:

```csharp
public sealed record StageRequirement(string Label, bool Met, bool Advisory = false);
```

A positional param with a default kept every existing construction site compiling untouched. `Met` still evaluates the real `EscrowState.Held` check, so the row renders as a green tick on deals that *do* use escrow — nothing is lost for the normal path.

Enforcement changed in exactly two places, and both had to change together or the button would unlock while the server still threw:

1. **Server** — `AdvanceStageAsync` filters the throw to `!r.Met && !r.Advisory` (`DealPipelineFeatures.cs:221`).
2. **UI** — `AllGatesMet` on both `Pipeline.razor` and `DealDetail.razor` became `.All(r => r.Met || r.Advisory)`.

The escrow row was identical across all three deal-shape branches (capacity, BOM, hardware/three-sided), so it was extracted to a single `EscrowWarning(Deal)` helper — one place to change if the policy shifts again.

### Two consequences that had to be handled, not just the gate itself

**The counterparty notice became a lie.** Advancing to Escrowed sends *"Escrow positions are visible in your Deal Room"* to the buyer, operator, and offtake accounts. On a no-escrow deal there are no positions. Added a `when !deal.EscrowAccounts.Any()` arm that falls back to *"Settlement terms are available in your Deal Room."* Skipping this would have shipped a customer-facing falsehood.

**The bypass had to be auditable.** Removing a hard gate without a record makes "who moved this deal to Escrowed with no money held" unanswerable. The audit `after` payload now carries `bypassedWarnings` (a list of the skipped labels), and the ops notification body appends *"Advanced past unmet warning(s): …"*. The payload moved from branching anonymous objects to a `Dictionary<string, object?>` — with two optional members (committed ratio, bypassed warnings) the anonymous-object approach needed four shapes.

**Ordering subtlety:** `BypassedWarnings(deal)` is read *before* the stage transition. `RequirementsFor` keys off the deal's *current* stage, so calling it after the flip describes the next hop instead of the one just taken.

### Access policy

Any admin can bypass — confirmed with the user. No role or permission check. Both pages already had a two-click `_pendingConfirm` on Advance, so the deliberate-action step came for free.

### UI

A third visual state: `warn` (amber `fa-triangle-exclamation`) sits between `met` (green check) and `unmet` (red X). `Pipeline.razor.css` had been using `--slyd-warning` for *unmet* while `DealDetail.razor.css` used `--slyd-danger`; both now use danger for blocking-unmet and warning for advisory, so the two states are visually distinguishable and the two pages agree. The action-note copy gained a third branch explaining that advancing records the bypass.

### Verification

Build clean (0 errors; 137 warnings all pre-existing in unrelated files). Full suite **198 passed, 0 failed**.

Test changes in `DealStageGateTests.cs`:
- `Advance_FromFinancing_RequiresAHeldEscrow` asserted the throw and was replaced by `Advance_FromFinancing_WarnsAboutMissingEscrow_ButDoesNotBlock` — checks the advisory row is visible pre-advance, the advance succeeds, the audit carries `bypassedWarnings`, and the notice says "Settlement terms" not "Escrow positions".
- Added `Advance_FromFinancing_WithHeldEscrow_MeetsTheRow_AndRecordsNoBypass` — the normal path still ticks green and records no bypass.
- Added `Advance_BlockingGate_IsStillHard_WhenAnAdvisoryRowIsAlsoUnmet` — guards the real risk of this change: an advisory gap must not soften the genuine Escrowed → Live gates.
- The file-local `FakeAuditWriter` gained an `Events` list and `AfterOf(kind)` so the payload can be asserted; it previously recorded only event kinds.

`CapacityDealGateTests` and the Escrowed → Live tests already seed a held escrow, so they were unaffected. The Live gate *"No escrow at-risk, late, or partial"* passes vacuously with zero escrows — correct as-is, deliberately unchanged.

### Files touched

- `src/Admin.Application/Models/DealOS/PipelineModels.cs` — `Advisory` member
- `src/Admin.Application/Features/DealOS/DealPipelineFeatures.cs` — enforcement, `EscrowWarning`, `BypassedWarnings`, audit payload, notice copy
- `src/Admin/Components/Pages/V3/DealFlow/Pipeline.razor` + `.css`
- `src/Admin/Components/Pages/V3/DealFlow/DealDetail.razor` + `.css`
- `tests/Admin.Tests/Features/V3/DealFlow/DealStageGateTests.cs`

Note: these files carried unrelated uncommitted branch work (quote builder, CRM accounts, matching engine) on `feat/crm-accounts-quote-builder`. The escrow change is separable from it.

## To Do Next

- Not committed — the user has not asked for a commit, and the branch holds unrelated in-progress work that would be swept in.
- Consider whether the `Advisory` mechanism should be reused elsewhere. It is currently a single-use flag; if a second advisory gate appears, the pattern is already in place.
- If ops ever needs to know *why* a deal skipped escrow, the natural next step is a required reason string on bypass rather than a silent proceed. Deliberately not built — the user asked for a warning, not a prompt.
