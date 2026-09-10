---
title: Configurator (customer flow)
route: /configure
audience: support, deal-ops, revenue-ops
slug: user-configurator
surface: user
---

# Configurator — customer flow

End-to-end walkthrough of what a public, anonymous visitor sees on `slyd.com/configure` — the **energy-backwards configurator**. It lets a visitor size a buildable, financable AI deployment by starting from **whichever number they actually know**: power envelope, GPU count, budget, or IT load. Then SLYD's live pricing engine sizes the rest and quotes a banded build cost + financing terms + revenue estimate.

The admin counterpart that owns every number on this page is **[Pricing Engine](/v3/pricing/engine)** (catalogs, curves, multipliers) and **[Financing Curve](/v3/pricing/financing-curve)** (APR + advance rate). Configurator output is **published-config-only** — drafts in the Pricing Engine are invisible to this page.

## Where the visitor starts

The configurator preview is public — **no login required to tune the sizing inputs and see banded output**. Sign-in is only required when the visitor clicks **Save this build · sign in** to persist the build to their account. The visitor lands at `slyd.com/configure` and sees:

- **Hero head** — *"Configure a deployment. Energy in, compute out. Start from whichever number you actually know — power envelope, GPU count, budget, or IT load — and SLYD sizes a buildable, financable package against its live pricing engine."*
- Two badges: **No login required**, **Live pricing engine · banded $**

## The four input modes

Above the form, four large mode-selector cards. The visitor picks the one matching the number they have:

- **Power envelope** — *"My site has X MW at the meter. What fits?"* (default)
- **GPU count** — *"I need N accelerators. What power and cost?"*
- **Budget ceiling** — *"My build budget is $X. What does it buy?"*
- **IT load** — *"I already know my post-PUE IT load in kW."*

Picking a mode switches the form's primary input control. The other inputs (workload, region, etc.) remain.

## The form (section 1 · Your input)

Depending on mode, one of four primary inputs:

- **Site power at the meter** — slider + number input in MW (0.2–500 MW)
- **Accelerators** — slider + number input in GPUs (1–100,000)
- **Build budget** — slider + number input in $M (0.5–2000 $M)
- **IT load · post-PUE** — slider + number input in MW (0.05–400 MW)

Sliders carry visible scale labels (e.g. `200 kW · 10 MW · 20 MW+`).

## Sections 2–N (form continues)

Further sections gather:

- **Accelerator** — preferred GPU model (driven by **Pricing Engine** GPU Catalog)
- **Workload** — training / inference / mixed
- **Region** — ISO codes
- **Cooling** — air / liquid / immersion (drives PUE)
- **Financing interest** — preferences

(Exact field list mirrors the published Pricing Engine config — adding a new GPU to the catalog adds it here.)

## The output (right column, banded)

After the visitor's form changes, a fetch hits the same-origin proxy that calls the platform configurator endpoint. The output renders **banded** — exact-to-the-cent pricing is **sign-in-only** (tied to a real lot per the published auth boundary). Before the first response lands, every value shows `—` placeholders.

Outputs include:

- **Build cost band** (e.g. `$8.4M–$9.2M`)
- **GPU count + power envelope** at the sized configuration
- **PUE assumption**
- **APR + advance rate** from the **[Financing Curve](/v3/pricing/financing-curve)** (published version)
- **Revenue estimate** from compute-rental rate × utilization assumption
- **Indicative monthly** for a financed build

**No numbers are hardcoded.** Every value comes from the published `PricingConfig` via the live pricing engine. If the live API hasn't responded yet, the page shows `—` rather than a fabricated number.

## Section IDs

The headline sections are numbered (`1 · Your input`, `2 · …`, etc.) so the visitor can navigate the form like a wizard without committing to a multi-step flow.

## Saving the build (the claim flow)

Below the output column is a **Save this build · sign in** primary button (gold) alongside a **Talk to us** ghost button. Saving turns the configured spec into a durable record:

1. The visitor clicks **Save this build · sign in**. The button changes to *"Saving build…"*.
2. The page POSTs the current form state to the platform's submit endpoint. The platform persists a **`DeploymentBuild`** row — the binding constraint the visitor typed (Power Envelope / GPU Count / Budget / IT Load) plus the full calculator snapshot — and mints a single-use 30-day claim token.
3. The browser redirects to **Sign in** at `/Account/Login` with `redirectUri=/configure/claim/{token}`.
4. The visitor completes sign-in (or sign-up) through Auth0. New users get a SLYD account auto-created at this step; no extra forms.
5. After sign-in the visitor lands briefly on **Linking your build to your account…** at `/configure/claim/{token}`, then is bounced to **Deal Dashboard** at `/v3/dashboard`. The dashboard URL carries a `?buildClaimed=BUILD-…` query param.
6. On the dashboard the visitor sees their build in the **My Builds** panel — DisplayId `BUILD-YYYYMMDD-XXXX`, entry-mode chip (`POWER · 5 MW` / `GPUS · 320` / `BUDGET · $5M` / `LOAD · 350 kW`), GPU model × count, region, age.

A child **Demand** is also created automatically at intake time — the GPU-side slice that enters the matching engine. After claim, that demand also appears in the **My Demands** panel on the dashboard.

## Claim-link edge cases

If the visitor hits `/configure/claim/{token}` and the token is no longer valid, the page renders one of:

- **This link can't be used.** — token doesn't match any build (already consumed, or mistyped). Buttons: **Go to dashboard**, **Contact ops**.
- **This claim link has expired.** — links are valid for **30 days**. After expiry the build is still on file; ops can link it manually. Buttons: **Contact ops**, **Go to dashboard**.
- **This build is already linked to a different account.** — another account claimed it first. Buttons: **Sign out**, **Contact ops**.
- **Something went wrong linking your build.** — anything else; the build is still on file.

In all four cases the underlying build is **not lost** — ops always has it.

## Things to know

- **Public, anonymous. No login.** Every visitor can use it. The page intentionally doesn't capture identity.
- **Live pricing engine.** Every number comes from the published Pricing Engine config — APR, advance rate, GPU prices, cooling, PUE, electrical cost. There is no fabricated number anywhere on the page; before the first API response, fields show `—`.
- **Banded output, not exact.** The visitor sees a band (e.g. `$8.4M–$9.2M`), not a precise figure. The band width is set by the **PublicBandFraction** in the published config (the **Configurator** tab on **[Pricing Engine](/v3/pricing/engine)**). Exact pricing comes only after sign-in tied to a real lot.
- **Draft Pricing Engine values are invisible here.** This page reads **published only**. If ops wants to test a config change before exposing it, they Save Draft on Pricing Engine and verify in the admin worked example; only Publish makes it visible here.
- **Same math as [Deal Room](/deals/{DealId})'s What-if dial.** The `FinancingMath` calculator that drives APR + advance rate on this page is the same one the buyer's What-if slider uses on the deal room. Customers should get consistent answers across both surfaces.
- **Configurator save → Operator lead** is the automation pathway. See **[Automations](/v3/crm/automations)** and **[Leads Inbox](/v3/crm/leads)**.
- **Save persists a `DeploymentBuild`.** Once the visitor signs in via the claim flow, the build is a durable record on their dashboard — they can come back and see it under **My Builds**. The auto-Demand attached to the build also enters the matching engine immediately, so even before ops touches it the engine is ranking lots against it.
- **The claim link is single-use and expires in 30 days.** Same constraint as `/need` and `/hardware-sales`. If a visitor forwards their post-submit URL to someone else, the first person to complete sign-in claims it.
- **The mode picker matters.** Power-envelope mode sizes around a fixed power limit; GPU mode sizes around a fixed accelerator count; Budget mode sizes around a fixed dollar cap; IT-load mode skips the PUE calculation. Visitors choosing the wrong mode get a different banded answer for the same intent — confirm which mode they used.
- **Customer-facing peers.** **[Marketplace · Spot tab](/marketplace)** is for off-the-shelf live capacity; **[Configure](/configure)** is the custom-sizing path; **[Post a need](/need)** is the structured-intake path; **[Contact sales](/contact-sales)** is the catch-all human path.
