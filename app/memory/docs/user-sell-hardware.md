---
title: Sell hardware to SLYD (customer flow)
route: /hardware-sales
audience: support, deal-ops, supply-ops
slug: user-sell-hardware
surface: user
---

# Sell hardware to SLYD — customer flow

End-to-end walkthrough of what a seller sees when they bring hardware to SLYD through the public sell intake. The flow runs from **slyd.com/hardware-sales** → sign-in → the seller's **My Sell Submissions** panel on their dashboard → the per-submission edit page.

The admin counterpart for everything below is **[Submissions](/v3/intake/submissions)**.

## Where the seller starts

The seller lands on `slyd.com/hardware-sales`. The page is public — no sign-in is required to fill the form or see the indicative valuation. Sign-in happens only after they click **Submit lot for valuation**.

The page has two columns:

- **Left** — the intake form
- **Right** — a live indicative-valuation card that updates as they fill the form

## Form sections (left column)

The seller fills these in order. Each section's choices drive the valuation panel on the right in real time.

1. **What you have** — Accelerator family pills (GPU model), GPUs per node, Quantity slider, OEM dropdown.
2. **Condition** — Self-graded condition pills (A / A- / B / C), Age slider, Warranty pills, Burn-in hours pills.
3. **Logistics** — Current location dropdown, **Ready to ship** pills, Packaging pills.
4. **More than GPUs?** — Optional manifest section for sellers bringing mixed inventory. They can download the **CSV template**, upload a filled one, or click **Add line** to enter rows manually. The manifest table appears below once any lines exist.
5. **Contact** — Company, Name, Email, Phone, and a **Notes** textarea for anything ops should know.

## Indicative valuation panel (right column)

This panel updates live as the form is filled. It shows:

- **Indicative Buyback band** — banded range, ±5%
- **Per-node estimate**
- **Payout options** — Pay on Inspect / Resale / Buy-out (these are the three paths SLYD ops can issue an offer against)
- **Time to Pay** per path
- **Valuation Breakdown** — Base market value, then Condition / Age / Warranty / Volume / Logistics adjustments stacked to the indicative offer per node
- **How SLYD Buys** — 3-step explainer (Submit → Inspect → Pay/Resale)

The valuation is **indicative only**. The firm offer is issued by ops on the admin **[Submissions](/v3/intake/submissions)** queue after they review the submission.

## Submitting the lot

1. The seller clicks **Submit lot for valuation** at the bottom of the form.
2. They are redirected to **Sign in** at `/Account/Login`. The page tells them sign-in is required so the submission can be linked to their account.
3. They complete sign-in (or sign-up) through Auth0. If they don't already have a SLYD account, they create one inline.
4. After sign-in the seller lands briefly on **Linking your submission to your account…** at `/sell/claim/{token}`, then is bounced to **Deal Dashboard** at `/v3/dashboard`.
5. The dashboard URL carries a `?sellClaimed=INTAKE-…` query param, which the dashboard can use to surface a "your submission is linked" cue.

The submission's display ID has the prefix **INTAKE-** (e.g. `INTAKE-20260624-0042`).

## What happens after sign-in — My Sell Submissions panel

On the dashboard at `/v3/dashboard`, the seller sees a **My Sell Submissions** panel in the left column (under **Your Deals**). Each row shows:

- The submission's **display ID** (e.g. `INTAKE-…`) as a mono chip
- A **SELL** chip (distinguishes from need-side intake)
- A **status pill** — NEW / REVIEW / OFFERED / CLOSED / REJECTED / LOST
- Hardware type × quantity (e.g. `H100 · 2000`)
- The indicative valuation band (or **Pending valuation** if no band yet)
- Relative age (e.g. `10m ago`)

The panel only renders when the seller has at least one submission on file. The most recent 5 submissions show.

Clicking a row opens **[Sell submission detail](/sell/submissions/{id})**.

## Editing a submission — /sell/submissions/{id}

The seller can self-serve edit certain fields on their submission while it's still in early states. The page mirrors the form sections from intake plus a status / valuation panel on the right.

### What's editable when

| Section | New | In Review | Offered | Closed / Rejected / Lost |
|---|---|---|---|---|
| What you have (Type, Quantity) | editable | locked | locked | locked |
| Disposition (Buy/Sell vs Auction) | editable | editable | locked | locked |
| Manifest rows | editable | locked | locked | locked |
| Contact (Name, Email, Phone) | editable | editable | locked | locked |
| Notes for ops | editable | editable | editable | locked |

When a field is locked, it shows as read-only with the value the seller submitted.

### Page layout
- **Left** — the editable form (same sections as intake)
- **Right** — Indicative valuation band · Status timeline (Submitted → Claimed → Review → Offered) · Submitter on file (visible once any field has locked)

### Saving
- The page tracks dirty state. The **Save changes** button is disabled until something changes; **Discard** reverts to last-saved values.
- Saves update the customer-edit timestamp separately from ops edits — admins viewing the same submission in **[Submissions](/v3/intake/submissions)** can tell which side made the last change.

## Claim-link edge cases

If the seller hits `/sell/claim/{token}` and the token is no longer valid, the page renders one of:

- **This link can't be used.** — token doesn't match any submission (mistyped, or already consumed once and dropped from the database). Buttons: **Go to dashboard**, **Contact ops**.
- **This claim link has expired.** — links are valid for **30 days**. After expiry the submission is still on file; ops can link it to the account manually. Buttons: **Contact ops**, **Go to dashboard**.
- **This submission is already linked to a different account.** — another account claimed it first. Buttons: **Sign out**, **Contact ops**.
- **Something went wrong linking your submission.** — anything else. The submission is still on file; ops can see it.

In all four cases the underlying submission is **not lost** — ops always has it in the admin queue. The only thing the seller can't do is auto-link it themselves.

## Things to know

- **Sign-in is required to submit.** Anonymous valuations are not persisted — only submitted-and-signed-in intakes are kept.
- **The claim link is single-use and expires in 30 days.** If a seller forwards the link to someone else, the first person to open it after signing in owns the submission. Recovery requires ops linking by hand.
- **Indicative ≠ firm.** Everything the seller sees on the website is indicative. The firm offer is issued by ops via the admin **Submissions** queue and surfaces back on `/sell/submissions/{id}` once issued.
- **The Notes field stays editable longer than other fields.** Sellers can add context (shipping window changes, new info on condition) all the way until the submission reaches a terminal state.
- **Status pill terminology matches the admin side** — same six states (New / Review / Offered / Closed / Rejected / Lost) appear in both portals.
