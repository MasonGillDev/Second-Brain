---
title: Compliance
route: /v3/platform/compliance
audience: compliance, support, partnership-ops
slug: compliance
surface: admin
---

# Compliance

Compliance is the **KYC review queue** that gates sealed-bid auctions on SLYD (ADR 0008 §5). Bidding and selling on **[Auctions Admin](/v3/intake/auctions)** require an account in **Verified** status — ops review on this page is the only path there. Every decision (Verify or Reject) is audited.

Open at **V3 Platform → Compliance** (`/v3/platform/compliance`).

In v1 the review covers **document metadata** — the kind of doc, file name, size, upload date — not the document bytes themselves (the files live behind a storage swap-point; identity confirmation is **out-of-band** until object storage lands).

## Page layout

- **Header** — page title + subhead: *"The verification gate for sealed-bid auctions. Verify or reject — both audited; rejection sends the account back to re-upload."*
- **Filter bar** — four pills: In review · Verified · Rejected · All non-blank
- **Queue table** — one row per account in the current filter
- **Banners** at the top — success / error feedback

Default filter on load is **In review** (so the queue lands on the work-to-do).

## The four compliance statuses

The page filters by **AccountComplianceStatus**:

- **DocsSubmitted** → labelled **In review** on the filter pill. The account uploaded documents and is waiting for ops decision. **This is the work queue.**
- **Verified** — ops approved; the account can bid and sell on auctions
- **Rejected** — ops rejected; the account must re-upload documents to come back into the queue
- (Accounts with no docs submitted yet don't appear on the **All non-blank** view — only the three statuses above)

Status pills on each row match those labels.

## Filter the list

Four pills:

- **In review** (default) — accounts with `DocsSubmitted`
- **Verified** — verified accounts (for spot-checking who passed)
- **Rejected** — rejected accounts (for follow-up or re-decision)
- **All non-blank** — every account with any compliance status

## Table columns

- **Account** — account name on top, DisplayId mono chip below (from **[CRM Accounts](/v3/crm/accounts)**)
- **Status** — status pill
- **Documents** — list of uploaded documents:
  - DisplayId · Kind · Filename · (Size in KB · upload date)
  - Empty state: `none uploaded`
- **Actions** — state-dependent action buttons

## Make a decision

The page exposes two terminal actions on every non-final row.

### Verify

1. On the row, click **Verify ✓**.
2. The account's status updates to `Verified` immediately.
3. Success banner: `<DisplayId> → Verified — logged to the Audit Log.`

The account can now bid and run sealed auctions on **[Auctions Admin](/v3/intake/auctions)**.

### Reject

1. Click **Reject**.
2. Status updates to `Rejected`.
3. Success banner: `<DisplayId> → Rejected — logged to the Audit Log.`

A rejected account is sent back to re-upload documents. The user is told via the customer-facing verification flow (in their portal **[Settings](/settings)**) that their docs were rejected.

Both buttons are visible on `DocsSubmitted` rows; on a `Verified` row only **Reject** shows; on a `Rejected` row only **Verify ✓** shows. The page never offers an action that re-applies the current status.

## What ops *cannot* do here

- Inspect the document files themselves (v1 surfaces metadata only — file bytes are out-of-band)
- Add a manual note / reason for the decision
- Request additional documents from the user (out-of-band)
- Send a templated rejection email from the page
- Bulk-verify or bulk-reject
- Re-decide an account without first stamping the new status (no "undo" — every flip is a new audited decision)

## Things to know

- **The whole point of this page is the auction gate.** No verified status, no bidding, no selling. If a user calls about auction access, this is where ops checks their status.
- **v1 is metadata-only.** The documents themselves live behind a storage swap-point ops can't access from this page. Identity confirmation is out-of-band — verify by a separate channel (call, video, secure transfer) and stamp the decision here.
- **Both decisions are audited.** Verify and Reject both write hash-chained entries to **[Platform Audit](/v3/platform/audit)**.
- **Rejection is reversible by re-upload.** A `Rejected` account stays in the queue and can be Verified later (without a new upload) — but the customer flow nudges them to re-upload, and that's the cleaner path.
- **Verified is not permanent.** Ops can flip a `Verified` account back to `Rejected` from the **Verified** tab. Use sparingly — that's an account-killer for auctions.
- **Customer-side flow.** Customers upload documents from their portal **[Settings](/settings)** — a screen ops never sees directly. After upload, the account lands in this queue with status `DocsSubmitted`. After ops's decision, the customer-side surfaces (auctions, settings) reflect the new status on next page load.
- **Status pill is the only thing customers see.** When a customer's status is `DocsSubmitted`, **[Auctions](/auctions)** shows them *"Your verification documents are in review — bidding unlocks once ops approves."* On `Rejected`, they see *"Bidding and selling require a verified account."* The exact decision-rationale isn't surfaced to them; if they need a reason, escalate out-of-band.
- **Related surface — [Auctions Admin](/v3/intake/auctions)**. The downstream of every verification — that's what the gate exists for.
- **Related surface — [CRM Accounts](/v3/crm/accounts)**. The Compliance queue is per-account; ops can cross-reference the account's broader CRM record there.
