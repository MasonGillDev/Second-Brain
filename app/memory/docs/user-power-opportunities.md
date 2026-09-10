---
title: Bring energy to SLYD (customer flow)
route: /marketplace/power-opportunities
audience: supply-ops, deal-ops, support
slug: user-power-opportunities
surface: user
---

# Bring energy to SLYD — customer flow

End-to-end walkthrough of what a public visitor sees on `slyd.com/marketplace/power-opportunities`. This is the **public Bring-Energy intake** — a marketing page + banded match preview that a site owner uses to surface a power-rich location to SLYD. Submitting **requires sign-in via a claim flow** (same shape as `/need`, `/hardware-sales`, and `/configure`); the structured submission lands on the admin **[Site Submissions](/v3/intake/site-submissions)** page as a `SiteSubmission` row.

## The page in one line

*"Power-rich sites need AI buyers. Bring stranded gas, surplus hydro, refinery tail, or a retired BTC site to SLYD — we'll match it to an operator with capital and offtake waiting."*

The page itself is public — tuning the match preview is anonymous and free. The visitor only needs to sign in when they click **Submit** to commit the submission to their SLYD account.

## Page layout

- **Hero** — *"Bring energy to SLYD."* + lede paragraph + two badges (**No login required**, **Indicative match · banded**)
- **Demand rail** — *"Operators are actively looking for sites"* — four cards showing live-ish demand signals from operators by region/type (Permian / Eagle Ford stranded gas, Canada West hydro, TX/LA refinery tail, WA/OR/MT retired BTC)
- **Intake form** (left column)
- **Match preview** area (right column, fills in after the visitor submits the form)

## The demand rail

Four cards above the form show what operators are looking for right now. Each shows:

- A priority tag — **URGENT · CLOSE Q3** (red), **PRIORITY · CLOSE Q4** (amber), **STANDING · CONTINUOUS** (neutral)
- The MW band (e.g. `3–5 MW`)
- Where + type (e.g. `PERMIAN / EAGLE FORD · STRANDED GAS`)
- A **REV RANGE** line (e.g. `$1.6M–$2.4M/MW·yr`)

The header strip says `DEMAND SIGNAL · HOURLY · DEMO TICK` — the cards refresh on the demo cycle, not real demand. Treat the rail as marketing copy, not as authoritative numbers ops should quote.

## The intake form

Three sections, all on one column:

### 1 · Site & energy

- **Energy source** — pill row: Stranded gas (default) / Refinery tail / Hydro / Retired BTC / Grid · industrial / Solar / wind / Other
- **Site capacity available** — slider + number input in MW (range 0.2–30 MW typical, max 500 MW). Hint: *"Net to compute."*
- **Region** — dropdown: `US · Permian / Eagle Ford`, `US · Bakken`, `US · Appalachia`, `US · Southeast`, `US · Pacific NW`, `Canada · West`, `Canada · East`, `Nordics`, `Middle East`, `Other`

### 2 · Timing & contract

(The page has additional sections; full field list is not in scope of this v1 doc — refresh on a re-author pass.)

### 3 · Contact (optional)

Like the **[Post a need](/need)** form, contact info is optional on the page itself — but submitting now requires sign-in, so the SLYD account email is always known to ops post-claim. The optional contact fields let the submitter name a different person as the ops touch-point.

## What the visitor gets back

After tuning the form, the page shows an **indicative banded match preview** — the demand-side equivalent of the buyer-side preview on **[Post a need](/need)**. The preview shows:

- A coverage indication (banded)
- A revenue range (banded, in `$M/MW·yr`)
- A timeline-to-deal indication

The exact numbers are **indicative only** — same convention as the buyer side, no fabricated precision.

## Submitting (the claim flow)

When the visitor clicks **Submit**, the page commits the submission to a real account:

1. The button shows *"Submitting…"*.
2. The page POSTs the form payload to the platform's submit endpoint. The platform persists a **`SiteSubmission`** row with all stated fields (source, available kW, region, availability, cost, term, structure / water / fiber / commercial / move-in / notes) and mints a single-use 30-day claim token.
3. The browser redirects to **Sign in** at `/Account/Login` with `redirectUri=/site/claim/{token}`.
4. The visitor completes sign-in (or sign-up) through Auth0. New users get a SLYD account auto-created at this step; no extra forms.
5. After sign-in the visitor lands briefly on **Linking your site submission to your account…** at `/site/claim/{token}`, then is bounced to **Deal Dashboard** at `/v3/dashboard?siteClaimed=SITESUB-…`.

The submission's display ID has the prefix **SITESUB-** (e.g. `SITESUB-20260629-0042`).

A dashboard "**My Sites**" panel for buyers to see their submissions on `/v3/dashboard` is **not yet wired** — deferred to a follow-up. Submissions exist on the buyer's account but don't currently surface in their own portal.

## Claim-link edge cases

If the visitor hits `/site/claim/{token}` and the token is no longer valid, the page renders one of:

- **This link can't be used.** — token doesn't match any submission (mistyped, or already consumed). Buttons: **Go to dashboard**, **Contact ops**.
- **This claim link has expired.** — links are valid for **30 days**. After expiry the submission is still on file; ops can link it manually. Buttons: **Contact ops**, **Go to dashboard**.
- **This submission is already linked to a different account.** — another account claimed it first. Buttons: **Sign out**, **Contact ops**.
- **Something went wrong linking your site submission.** — anything else; the submission is still on file.

In all four cases the underlying submission is **not lost** — ops sees it in **[Site Submissions](/v3/intake/site-submissions)**.

## What happens on the admin side

Every submitted site lands on **[Site Submissions](/v3/intake/site-submissions)** as a structured `SiteSubmission` row:

- Status starts at **Submitted**; ops moves it to **In Review** via the drawer's **Begin Review →** action
- If the submitter completed the claim flow, the row's **Owner** column shows their Account name + email; otherwise it shows **Unclaimed**
- Ops can **Mark Declined** or **Mark Withdrawn**; conversion into a real Site on **[Sites Registry](/v3/sites)** is a separate workflow that's still being built
- A parallel `FormSubmission` is also written for backward compatibility on `/admin/forms` — same data, two surfaces during the migration window

## Things to know

- **Sign-in required to submit.** The visitor can tune the preview anonymously, but committing the submission redirects through Auth0. The SLYD account is auto-created behind the scenes for new users — no extra signup forms.
- **The demand rail is marketing.** The four operator-demand cards refresh on a demo tick, not real-time. Don't quote those revenue ranges to a real seller as authoritative.
- **Banded preview only.** Exact numbers are deliberately not shown — same convention as **[Post a need](/need)**. The visitor gets a coverage band, a revenue range, and a timeline; nothing exact.
- **The claim link is single-use and expires in 30 days.** Same constraint as `/need`, `/hardware-sales`, and `/configure`.
- **Submissions land in [Site Submissions](/v3/intake/site-submissions).** The downstream feed for the three-sided matcher is on **[Sites Registry](/v3/sites)** + **[Matching · 3-sided](/v3/deal-flow/matching)** — but only after ops promotes the submission into a real Site row.
- **Origin channel is preserved.** When ops follows up, the **Origin** field on the converted Site row indicates this surface as the source.
- **"Net to compute" capacity.** The capacity slider is labelled "Net to compute" — meaning the kW actually available for compute load after the site's own draw and losses, not gross nameplate. Sellers entering gross numbers will produce inflated PowerFit scores until ops corrects **Available kW** at site-promotion time.
- **No "My Sites" panel on the dashboard yet.** A buyer-facing panel that surfaces a user's own SiteSubmissions on `/v3/dashboard` is on the deferred list. Until it lands, the buyer's only confirmation is the dashboard landing URL's `?siteClaimed=…` query param.
