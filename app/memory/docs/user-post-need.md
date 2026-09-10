---
title: Post a need (customer flow)
route: /need
audience: support, deal-ops, revenue-ops
slug: user-post-need
surface: user
---

# Post a need — customer flow

End-to-end walkthrough of what a buyer sees when they tell SLYD what compute they need through the public demand intake. The flow runs from **slyd.com/need** → optional banded preview → sign-in on post → the buyer's **My Demands** panel on their dashboard.

The admin counterpart is **[Demand Book](/v3/crm/demand)**.

## Where the buyer starts

The buyer lands on `slyd.com/need`. The page is public — they can fill the form and click **Preview matches** as many times as they want without signing in. Sign-in is only required when they click **Post requirement to ops**.

The page has two columns:

- **Left** — the demand-intake form
- **Right** — the match-preview area + post CTAs

## Form sections (left column)

1. **What you need** — Accelerator pills (H100, H200, B100, B200, B300, MI300X, MI325X), Quantity slider (8–512 nodes), Primary workload pills (Training / Inference / Neocloud-resale / Mixed).
2. **When & where** — **Need it by** pills (ASAP · spot / This quarter / Within 6 months / Forward 6mo+), Region pills (Any region + ISO codes: ERCOT, CAISO, PJM, MISO, SPP, NYISO, ISO-NE, AESO), Consumption model pills (Own the cluster / Rent capacity / Open).
3. **Budget & financing** — Budget ceiling slider ($0.5M–$100M), Financing pills (Want SLYD financing / Cash · self-funded / Exploring).

At the bottom: **Preview matches** button (gold) and a **MATCHING · LIVE** status row.

## Match-preview area (right column)

Updates after the buyer clicks **Preview matches**. The right column always shows:

- **SLYD can likely cover** hero card — total lots across the three sourcing lanes, with the buyer's `quantity × GPU model · region` echoed back. Coverage percentage and match confidence currently render as `—` placeholders (the engine doesn't return those fields yet — do not invent values).
- **Price range** and **Delivery window** — banded numbers from the matching response (e.g. `$33.20–$35.10` and `45–60 days`).
- **Where it comes from** — three source rows with current lot counts:
  - **Recovered inventory** · READY-SHIP · GRADE A / A-
  - **Forward lots** · DEPOSIT · CONVERTS ON DELIVERY
  - **OEM partner channel** · NEW · VIA PARTNER MANUFACTURERS
- **What happens next** — 4-step process strip: POST → MATCH → STRUCTURE → DEAL ROOM. Purely explanatory, no data.

Per-row pricing in the source rows also renders as `—` until the engine returns it.

## Posting the requirement

Below the process strip is the **Post requirement to ops** card. The buyer can optionally fill **Name**, **Work email**, **Company**, and **Phone** — all marked optional. The contact fields are kept even after sign-in so ops has the right person, not just the account owner.

1. The buyer clicks **Post requirement to ops** (purple primary).
2. They are redirected to **Sign in** at `/Account/Login`. A lock note next to the button reads: *"SIGN IN · NO CREDIT PULL · OPS FOLLOW-UP."*
3. They complete sign-in (or sign-up) through Auth0.
4. After sign-in the buyer lands briefly on **Linking your demand to your account…** at `/need/claim/{token}`, then is bounced to **Deal Dashboard** at `/v3/dashboard`.
5. The dashboard URL carries a `?needClaimed=NEED-…` query param. There is **no on-dashboard success banner** that consumes the param today — the buyer's confirmation that the link worked is simply that they see the demand in the **My Demands** panel.

The demand's display ID has the prefix **NEED-** (e.g. `NEED-20260624-0042`).

## Hardware want-list (beyond GPUs)

Below the post card is a separate **Need hardware beyond GPUs?** card. It's collapsed by default — clicking **Post a hardware need** loads the hardware taxonomy and reveals:

- **Category** dropdown (everything except GPU — Server, Network, Power, etc.)
- **Subcategory** dropdown (populated from the chosen category)
- **Model** input with a datalist of catalog suggestions
- **Quantity** input
- **Post hardware need** button

This uses the same contact fields as the main post card and the same sign-in / claim flow. The resulting demand carries the chosen category + subcategory.

## What happens after sign-in — My Demands panel

On the dashboard at `/v3/dashboard`, the buyer sees a **My Demands** panel in the left column (under **Your Deals** and **My Sell Submissions**). Each row shows:

- The demand's **display ID** (e.g. `NEED-…`) as a mono chip
- A **NEED** chip (distinguishes from sell-side intake)
- A **state pill** — OPEN / REVERIFY / MATCHED / EXPIRED / WITHDRAWN
- A **CRITICAL** badge if the urgency is critical
- GPU model × quantity (e.g. `H200 · 64`)
- Region (or **Any region** if no ISO was chosen)
- Relative age (e.g. `2m ago`)

The panel only renders when the buyer has at least one demand on file. The most recent 5 demands show. **Rows are not clickable today** — there is no per-demand detail page yet. The buyer can see the demand exists and its current state; deeper inspection requires ops follow-up.

## Claim-link edge cases

If the buyer hits `/need/claim/{token}` and the token is no longer valid, the page renders one of:

- **This link can't be used.** — token doesn't match any demand (mistyped, or already consumed). Buttons: **Go to dashboard**, **Contact ops**.
- **This claim link has expired.** — links are valid for **30 days**. After expiry the demand is still on file; ops can link it manually. Buttons: **Contact ops**, **Go to dashboard**.
- **This demand is already linked to a different account.** — another account claimed it first. Buttons: **Sign out**, **Contact ops**.
- **Something went wrong linking your demand.** — anything else. The demand is still on file.

In all four cases the underlying demand is **not lost** — ops always has it in the **[Demand Book](/v3/crm/demand)**. The only thing the buyer can't do is auto-link it themselves.

## Things to know

- **Preview is free and anonymous.** The banded match preview never persists anything — buyers can iterate on the form as many times as they want without creating a record or signing in.
- **Posting requires sign-in.** Anonymous demands are no longer accepted — ops gets a real account on every demand.
- **First-time sign-in auto-creates an Account.** When the buyer completes Auth0 and lands on the claim step, the platform either finds the CRM Account they already own (matched by Auth0 identity) or **creates one in the background** named from their email. The buyer never sees a setup screen — the account exists by the time they reach **My Demands**. This is also why **[Deal Pipeline](/v3/deal-flow/pipeline)** can show a Buyer name on a configurator-sourced demand without ops touching anything.
- **The claim link is single-use and expires in 30 days.** Same constraints as the [sell flow](/hardware-sales).
- **Contact fields are still optional after sign-in.** The signed-in account is always recorded as the owner, but the buyer can still fill different contact info if a colleague should be the ops touch-point.
- **The hardware want-list shares the contact + claim flow.** It's not a separate intake — it just creates a demand with a non-GPU category.
- **Budget, financing, workload, and consumption are captured but not yet routed to the preview engine.** They are stored on the demand record so ops sees them, but they don't yet influence the banded coverage numbers shown to the buyer.
- **Demand states do not match deal stages.** OPEN means "actively matching"; MATCHED means a candidate lot has been identified; REVERIFY means ops wants the buyer to confirm specs. Withdrawn and Expired are terminal.
