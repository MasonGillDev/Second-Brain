# Ops submission email — deep link to the form submission

**Project:** SLYD Platform — Platform.WebUI
**Date:** 2026-08-24
**Author:** 9556c277-fb2e-43c2-b649-cd1d0fe7dfd8
**Directory:** /Users/masongill/Slyd-Platform/admin (change touches ../platform)

## What Was Done

The ops notification email (sent to `Ops:NotificationEmail`, i.e. sales@slyd.com) ended
with `<a href="/admin/forms">Open the submissions queue →</a>`. Two defects:

1. It dropped ops on the queue, so they had to hunt for the row the email just told them
   about.
2. It was a **bare path**. A mail client has no page to resolve a relative href against,
   so the link was dead on arrival regardless of where it pointed.

Both fixed.

### `OpsSubmissionEvent` carries the FormSubmission id

New optional `Guid? FormSubmissionId` on the record. Wired at every call site that has a
FormSubmission in hand:

- `PublicFormsController` — the main website-forms path; passes `submission.Id`.
- `ConfigureController` (BuildIntake) — passes `formSubmission.Id`.
- `PublicV3IntakeController` — `/need`, `/hardware-sales` (via `WriteContactFormSubmission`,
  which now returns `Guid?` — null when the best-effort write failed), plus
  `/power-opportunities` and `/capacity` (inline `SubmitFormAsync` results).
- `MarketplaceIntakeService` — both signed-in paths, via `WriteFormSubmissionAsync`, now
  also returning `Guid?`.

Call sites with **no** form row behind them (lot deposits, capacity/forward-lot booking
requests, capacity listings, term sheet requests) pass nothing and keep the queue link —
that's correct, there's no submission page to land on.

### Notifier renders an absolute deep link

`OpsSubmissionNotifier.BuildBody` now takes the admin origin from a new config key
`Ops:AdminBaseUrl` and emits:

- `{base}/admin/forms/{id}` — "Open this submission →" when the event carries an id
- `{base}/admin/forms` — "Open the submissions queue →" otherwise

Trailing slashes on the base are trimmed. When the key is unset it degrades to the bare
path — no worse than what it replaced, and still deep-linked.

`Ops` was previously an entirely undeclared config section (set via env in deployment);
added `Ops: { NotificationEmail, AdminBaseUrl }` to `appsettings.json` as empty defaults so
the keys are discoverable.

**`Ops:AdminBaseUrl` must be set per environment for these links to work.** Admin is
VPN-only and no hostname for it appears anywhere in the repo, so I did not guess a default
— it needs to be filled in with the real admin origin.

### Verification

`dotnet build` on Platform.WebUI: 0 errors. New `OpsSubmissionNotifierLinkTests` (4 tests)
drives the real notifier with a recording `IEmailService` and asserts: deep link when an id
is present, queue fallback when it isn't, bare-path degradation with no base URL, and no
double slash when the base URL has a trailing one. Full Platform.WebUI.Tests suite: 199
passed, 0 failed.

## To Do Next

- Set `Ops:AdminBaseUrl` in each environment's config/secrets (the admin portal origin).
- Related, from the same session: existing `forms.new-submission` rows in the admin
  notification table still carry the old `/admin/forms` Href — see
  [leads-inbox-form-submission-overview.md](leads-inbox-form-submission-overview.md).
