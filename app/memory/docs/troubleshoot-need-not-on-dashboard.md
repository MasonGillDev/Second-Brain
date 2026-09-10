---
title: Troubleshoot — buyer's posted need isn't on their dashboard
audience: support, deal-ops
slug: troubleshoot-need-not-on-dashboard
surface: troubleshooting
---

# Troubleshoot — buyer's posted need isn't on their dashboard

## Symptom

A buyer says: *"I submitted a need on slyd.com but it's not on my dashboard"* (or *"My Demands panel is empty after posting"*).

## Common causes

1. **They never clicked Post requirement to ops** — they only clicked **Preview matches**. The preview is anonymous and creates no record. Only the **Post requirement to ops** button triggers a real submission + sign-in flow.
2. **Sign-in failed before the claim** — they got bounced to `/Account/Login` but never completed Auth0, so the `/need/claim/{token}` step never ran.
3. **Claim link expired** — claim tokens are valid 30 days. If they posted weeks ago and only just signed in, the token is dead.
4. **Claim link consumed by a different account** — they signed in with a different Auth0 sub than the one they originally meant to use (e.g. work account vs personal), and the demand bound to the wrong account.
5. **They're looking at the wrong dashboard** — `/consumer/dashboard` is the consumer landing; the **My Demands** panel lives on `/v3/dashboard` (the Deal-OS dashboard, same route also exists on admin — confirm the buyer is on the platform domain).

The "no account linked" case from earlier guidance no longer applies on a successful claim — completing **Sign in** at `/Account/Login` and hitting `/need/claim/{token}` automatically links a CRM account to the user (creating one named from their email if they don't already own one). If a user reports a missing demand, the cause is **always** one of the five above; never "the account wasn't auto-created."

## Where to verify (admin side)

For each cause:

- **Verify the demand exists on the admin side** — open **[Demand Book](/v3/crm/demand)** and search for the customer's GPU model / quantity / region or scan recent rows. Their demand has prefix `NEED-`. If it isn't there, they likely never clicked **Post requirement to ops**.
- **If the demand exists but `Buyer` is blank** — they never completed sign-in / claim. The record is on file but unbound; the claim flow never ran (which would have stamped the buyer and auto-linked their account).
- **If the demand exists and `Buyer` is set but to a different name** — they bound it to a different account. Ask which Auth0 identity they're using now.
- **Check the buyer's account on [CRM Accounts](/v3/crm/accounts)** — search for their Buyer name. If the account exists, the drawer's **Owner** field shows which platform user is bound. After a successful claim this is populated automatically; if it's blank, the claim flow didn't run on that account.
- **Check whether they're hitting the right dashboard** — see **[Post a need (customer flow)](/need)** for what the **My Demands** panel looks like and which route it lives on.

## Resolution steps

- **If they never clicked Post:** route them back to `/need`, have them refill the form, and explicitly click **Post requirement to ops**.
- **If the claim link expired (30 days):** the demand is on file; **[Demand Book](/v3/crm/demand)** still shows it. Ops manually binds it via **[CRM Accounts](/v3/crm/accounts)** → open their account → **Link customer user** with their email. After binding, the demand appears on their dashboard.
- **If the demand bound to the wrong account:** that demand shows on the *other* account's dashboard. Either the buyer signs in with the right account to use it, or escalate to ops to re-attribute (no in-page action — needs a CRM workflow).
- **If they're on the wrong dashboard:** **[Post a need (customer flow)](/need)** explains the **My Demands** panel location is `/v3/dashboard`. Send them there.
- **If sign-in completed but the demand didn't link** (rare — usually means the claim leg failed silently): have them post a fresh need from `/need`; the new claim flow will both bind the demand and auto-link an account to their user if needed.

## Related docs

- **[Demand Book](/v3/crm/demand)** — the canonical demand record (admin)
- **[Post a need (customer flow)](/need)** — the full buyer-side walkthrough, including the four claim-link failure modes
- **[CRM Accounts](/v3/crm/accounts)** — account linking
