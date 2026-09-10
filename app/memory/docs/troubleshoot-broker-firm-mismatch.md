---
title: Troubleshoot — broker signs in but can't see / use their portal
audience: partnership-ops, support
slug: troubleshoot-broker-firm-mismatch
surface: troubleshooting
---

# Troubleshoot — broker signs in but can't see / use their portal

## Symptom

A broker calls in with one of these:
- *"I signed in at /broker but it says I'm not a broker."*
- *"I don't see my submissions / commission ledger."*
- *"The page says my profile is pending approval — what does that mean?"*
- *"It says my access is paused / suspended."*
- *"I see the portal but my submit button doesn't work."*

The broker portal at `/broker` always renders **one** of seven things: the full active portal, or one of six notice cards. The card's wording is exact — ask the broker to read it verbatim, then use the matching row below to land on the fix.

## What the broker sees → what's wrong → what to fix

| Notice text | Cause | Fix |
|---|---|---|
| **"No SLYD account is linked to your login yet — contact ops or your broker to claim your account."** | The broker's auth identity isn't bound to any V3 Account. | [CRM Accounts](/v3/crm/accounts) → find/create the broker's Account → **Link customer user** with their email. They reload `/broker`. |
| **"This account isn't flagged as a broker — contact partnerships@slyd.com."** | The Account exists but its **Type** isn't **Broker**. | [CRM Accounts](/v3/crm/accounts) → open the Account drawer → change Type to **Broker** → save. Then add a roster row (next row). |
| **"Your account is flagged as a broker but ops hasn't created your roster row yet."** | Account.Type is Broker but no matching roster row exists on the Brokers page. | [Brokers](/v3/platform/brokers) → **+ Add broker** → in **Link to Account**, select this user's V3 Account → **Add broker**. The roster row lands in **PENDINGREVIEW**, so the broker's next reload shows the **Pending approval** notice. |
| **"Your broker profile is in review. Ops is verifying your application — once approved you'll see your portal and be able to submit deals."** | Roster row exists but is in **PENDINGREVIEW**. This is the default state for every newly added broker. | [Brokers](/v3/platform/brokers) → click **Approve** on the broker's roster row (twice for confirm). The roster pill flips to **ACTIVE** and the broker's next reload shows the full portal. |
| **"Your broker access is paused. New submissions are blocked until ops reinstates you."** | Ops paused the broker (status = **PAUSED**). | [Brokers](/v3/platform/brokers) → **Reinstate** on the roster row. |
| **"Your broker access has been suspended. Contact partnerships@slyd.com to discuss reinstatement."** | Ops suspended the broker (status = **SUSPENDED**). | [Brokers](/v3/platform/brokers) → **Reinstate** on the roster row. (Reinstate works from both Paused and Suspended.) |

Two other failure modes don't show a notice but have the same observable effect:

| Symptom | Cause | Fix |
|---|---|---|
| Broker sees **"No broker profile"** notice even though ops thinks they're set up. | The broker's roster row was **TERMINATED** — terminated rows are filtered out at the resolver, so the portal can't see them. | [Brokers](/v3/platform/brokers) → if the broker should be reinstated, create a new row (Terminated is terminal — can't be un-terminated). |
| Broker sees **"No broker profile"** with an Account that IS typed Broker. | The roster row exists but the **Firm** field doesn't match the V3 Account name exactly (legacy firm-name match path). Account-linked rows aren't affected. | [Brokers](/v3/platform/brokers) → fix the Firm spelling (or terminate the row and recreate with **Link to Account** so the FK takes precedence over the string match). |

## Verifying which case applies

Always ask the broker for the **exact wording** of the notice card on their screen. If they can't read it for you:

1. Find the broker on [Brokers](/v3/platform/brokers) roster.
2. Read the **Status** pill: `PENDINGREVIEW` / `ACTIVE` / `PAUSED` / `SUSPENDED` / `TERMINATED`.
3. If status is **ACTIVE** but the broker still says the portal is empty, check the Account link:
   - Open the broker's V3 Account on [CRM Accounts](/v3/crm/accounts).
   - Confirm Type is **Broker**.
   - If the roster row was added via **+ Add broker** with the Account dropdown selected, the FK binds them — no firm-name match needed.
   - If the roster row was added with **— unlinked (firm-name fallback) —**, compare the **Firm** field on the roster to the Account **Name** — they must match exactly. Mismatch = silent failure.

## "I see the portal but my submit button is rejecting / hidden"

The portal renders the **Submit a deal +** button only when the broker is **ACTIVE**. If they're in PENDINGREVIEW / PAUSED / SUSPENDED the entire portal is replaced by the matching notice card.

If a broker reports clicking Submit and getting a server-side error message instead of a success banner, the error text will be one of these (the gate enforces it server-side too):
- *"Your broker profile is pending ops approval — you can't submit yet."* → PENDINGREVIEW
- *"Your broker access is paused — contact ops to reinstate before submitting."* → PAUSED
- *"Your broker access is suspended — contact ops."* → SUSPENDED
- *"No broker profile is linked to this account — contact ops."* → roster row missing/terminated
- *"This account is not flagged as a broker."* → Account.Type changed away from Broker
- *"Subcategory 'foo' is not valid for category Server."* → taxonomy validation on their submitted fields (not a gate issue — they should fix their submission)

All of these are admin-fixable on [Brokers](/v3/platform/brokers) or [CRM Accounts](/v3/crm/accounts).

## Related docs

- [Brokers](/v3/platform/brokers) — the admin roster page, owns admission gate transitions (Approve / Pause / Suspend / Reinstate / Terminate)
- [Broker portal (broker flow)](/broker) — full walkthrough of what the broker sees at every state
- [CRM Accounts](/v3/crm/accounts) — Account directory + Type change action + customer-user link
