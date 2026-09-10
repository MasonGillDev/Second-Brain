# Build Intake SQL Injection Attack — Triage (2026-08-17)

**Project:** SLYD Platform
**Date:** 2026-08-17
**Author:** c762ad9e-daa3-4d99-99bb-7a7a483d3be8
**Directory:** /Users/masongill/Slyd-Platform/core

## What Was Done

**Update (same day): app-level rate-limit hotfix built and verified.** Added .NET built-in rate limiting to the **website** app (not the platform — the platform only sees the website's server IP, so a per-IP limit there would throttle everyone). New `website/ExtensionMethods/RateLimitingExtensions.cs`: fixed-window limiter, 10 submits / 5 min per client IP, keyed on the **rightmost** X-Forwarded-For entry (the one the ALB appends — the only unforgeable one with a single trusted hop; falls back to socket IP locally). Applied via `[EnableRateLimiting("anon-submit")]` to the 7 submit endpoints: configure/submit, need/submit, hardware-sales/submit, power-opportunities/submit, waitlist/benson, financing/apply, marketplace forward-deposit. Previews/catalog deliberately unlimited (fire on every configurator tweak). Gotcha found in testing: an empty 429 gets re-executed by `UseStatusCodePagesWithReExecute("/not-found")` into a 400, so OnRejected writes a JSON body (`{"error":"Too many submissions..."}`). Verified live: 10×200 then 429s; limiter log line records offending IP. Build clean; changes uncommitted pending Mason's review (22 lines + 1 new file in website repo).

Triaged a burst of ~200 BuildIntake form submissions in 6 minutes containing sqlmap-style time-based blind SQLi probes (PG_SLEEP, DBMS_PIPE.RECEIVE_MESSAGE, MySQL sleep/XOR variants) hitting the public `POST /api/v3/configure/submit` (website proxy → `platform/src/Platform.WebUI/Controllers/ConfigureController.cs:381`, `[AllowAnonymous]`).

**Verdict: injection failed — no breach.** Entire write path is EF Core parameterized SQL; no FromSqlRaw/ExecuteSqlRaw/Dapper anywhere in the submission or read-back path (admin search is LINQ `.Contains` → parameterized LIKE). Admin UI (Blazor auto-encoding) and ops emails (`OpsSubmissionNotifier.cs` HtmlEncode) escape values — no stored XSS, no email header injection.

**Real damage was amplification.** Each submission creates: DeploymentBuild + Demand (Open, feeds matching engine → up to 20 MatchCandidates each), FormSubmission + ~10 fields, Lead minted in same transaction (`FormLeadCapture`, deduped by email — attacker used sample@email.tst so likely 1 lead enriched 200×), SendGrid ops email, SignalR admin alert, hash-chained AuditEvent, and (unless marked Spam first) a SalesLead via `SalesServices.cs:534-575`. Also burned ~200 of the 9,000 daily DisplayId values.

**Why it was possible:** no rate limiting (RateLimitingMiddleware deliberately removed 2026-08-03, `Program.cs:431-438`; compensating ALB/WAF rule in `docs/waf-rate-limiting.md` never applied — task `TaskTracking/Pending/2026-07-13-rate-limit-anonymous-intake.md` still Not Started). No captcha, no honeypot, no length caps on unbounded text columns (`FormSubmissionField.Value`, `DeploymentBuild.Notes`/`RegionDetail`). 9 sibling `[AllowAnonymous]` intake endpoints share the exposure.

**Forensic gap:** `ConfigureController.cs:557-559` passes `ipAddress: null, userAgent: null` despite FormSubmission having those columns — no attacker IP in DB; only Serilog logs under `platform/src/Platform.WebUI/logs/` and ALB access logs.

**Cleanup gap:** only per-row Spam button in admin; `DeleteOldSubmissionsAsync` has zero callers and no time-window/id filter; Spam status doesn't remove derived Lead/DeploymentBuild/Demand/audit rows; Open demands keep the matching engine churning.

## To Do Next
- Commit + deploy the website rate-limit hotfix (Mason to approve commit).
- Apply the ALB/WAF rate-limit rule from `docs/waf-rate-limiting.md` (Mason — infra change).
- Pull Serilog/ALB logs for attacker IP before rotation.
- Targeted cleanup script: delete burst FormSubmissions + derived DeploymentBuild/Demand/Lead/SalesLead rows by time window + sample@email.tst; close demands.
- Harden intake: honeypot field, length caps, capture IpAddress/UserAgent (columns exist), consider Turnstile on all anonymous intakes.
