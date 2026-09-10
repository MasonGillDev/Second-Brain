# Energy Intake Rejected Every Valid Email (Razor `@@` escape leak)

**Project:** SLYD Platform (website)
**Date:** 2026-08-20
**Author:** dc64a138-6016-4577-ba7f-ab2dee6b72bf
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done

The site-intake form at `/marketplace/power-opportunities` refused every email
address, showing "That email doesn't look right" on the submit button. Found
while trying to seed a `SiteSubmission` for capacity-conversion testing.

**Root cause:** `wwwroot/js/v3energy.js:351` had

```js
if (!/^[^\s@@]+@@[^\s@@]+\.[^\s@@]+$/.test(email)) ...
```

`@@` is Razor's escape for a literal `@`. That was correct while the code lived
inline in `PowerOpportunities.razor`. Commit `4990290` (2026-08-19) —
*"Move the power-opportunities estimator out of an inline script"* — moved it
to a standalone `wwwroot/js` file, which gets **no Razor processing**, so the
escape survived into the served output as two literal `@` characters.

Net effect, verified in node:

| input | old regex | fixed |
|---|---|---|
| `masongill@gmail.com` | reject | accept |
| `ops@slyd.com` | reject | accept |
| `a@b.co` | reject | accept |
| `not-an-email` | reject | reject |
| `two@@at.com` | **accept** | reject |

Exactly inverted — the only thing it accepted was the malformed double-at form.

The stale comment directly above it still read *"this is a .razor file, so a
single one reads as a code transition"*, which is what made the bug survive
review: the justification looked correct in isolation.

**Fix:** single `@`, matching `v3sell.js:511`, which has the correct form
because it never moved. Swept the rest of `wwwroot/js` — this was the only
leak.

Server-side validation was never wrong (`PublicContactValidation` uses
`EmailAddressAttribute`), so this blocked people only at the form. Nothing bad
reached the database; the cost was silent lost submissions.

## Related

The same commit `4990290` also broke `PowerOpportunitiesPageContentTests` by
removing the inline `<script>` block the test class extracts — see the TODO in
[public-capacity-intake.md](public-capacity-intake.md). One refactor, two
casualties, both undetected because that test class fails at static-constructor
time and its 55 failures were being read as pre-existing noise.

**Worth checking:** whether any other `.razor` → `wwwroot/js` extraction in that
series carried Razor constructs (`@@`, `@(...)`, `@Model`) into a static file.
`v3nav.js` and `v3sell.js` both carry "lives outside the .razor file" headers,
so the pattern was applied more than once. Only `v3energy.js` had a leak at the
time of writing.

## To Do Next

None for this fix — committed as `f07ffc7` on website `development`, not pushed.
