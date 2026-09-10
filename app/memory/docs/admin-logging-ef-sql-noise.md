# Admin Portal: EF SQL Log Noise & Dead Serilog Config

**Project:** SLYD Platform — Admin
**Date:** 2026-08-03
**Author:** 9669b372-3dd9-4598-98b4-4c552569bf35
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Console output during `dotnet run` was dominated by raw EF Core SQL dumps — every
`SELECT`/`UPDATE` issued by the background ops-check loop, printed in full at
Information level every 15 seconds. Investigated why, found two compounding causes.

### Cause 1: The Serilog config block is dead code

`src/Admin/appsettings.json` contains a complete ~40-line `Serilog` section —
Console/File/Seq sinks, enrichers, and a `MinimumLevel.Override` of
`"Microsoft": "Warning"` that would have suppressed exactly this noise.

**None of it is in effect.** `Program.cs` never calls `builder.Host.UseSerilog(...)`,
and `Admin.csproj` has no Serilog `PackageReference`. `Serilog.AspNetCore` 9.0.0 is
only present transitively via `SLYD.Application` / `SLYD.Infrastructure` from core.

Proof is in the log output format itself: `info: Microsoft.EntityFrameworkCore.Database.Command[20101]`
with the bracketed event ID and two-line indent is the **default ASP.NET Core
`SimpleConsoleFormatter`**. Serilog's console sink emits `[HH:mm:ss LVL] message`.
So the file sink (`logs/admin-.log`) and Seq shipping are also silently not running,
despite `launchSettings.json` setting `Serilog__WriteTo__3__Args__serverUrl`.

This was NOT fixed — wiring Serilog up changes prod log format and log shipping,
which is a deployment-affecting decision, not a local noise cleanup. Left as an open
decision (see To Do Next).

### Cause 2: The config that IS live had no EF override

The active `Logging.LogLevel` section only overrode `Microsoft.AspNetCore`.
`Microsoft.EntityFrameworkCore.*` fell through to `Default: Information`, and EF's
command logger writes every executed statement at Information.

The net effect was **inverted from what's useful**: `OpsCheckHostedService.cs:137`
already writes a genuinely informative per-run line
(`"Ops check {RuleKey} ran in {ElapsedMs}ms"`) — but at `LogDebug`, which
`Default: Information` suppresses. So the plumbing was visible and the narrative was not.

### Changes made

`src/Admin/appsettings.json` — added to `Logging.LogLevel`:
- `Microsoft.EntityFrameworkCore.Database.Command: Warning` — kills the SQL dumps.
  Warning still surfaces command *failures*, which is what you actually want.
- `Microsoft.EntityFrameworkCore.Infrastructure: Warning` — kills context-init spam.
- `Microsoft.EntityFrameworkCore.Migrations: Information` — deliberately kept loud;
  migration application is worth seeing on boot.

Comments were deliberately NOT added to the JSON. The .NET config provider tolerates
them (`JsonCommentHandling.Skip`), but no other JSON in this repo uses them and any
`jq`-based tooling would break.

`src/Admin/Properties/launchSettings.json` — added `Logging__LogLevel__Admin: "Debug"`
to both the `http` and `https` profiles, so the app's own `Admin.*` category lines
(including the ops-check per-run line) surface locally. This file is **gitignored**
(`.gitignore:16` `appsettings.*.json` plus launchSettings being untracked — it holds
live API keys), so this is a local-machine-only change and will not reach teammates.

### Verification

- Both JSON files re-parsed clean via `python3 -c "json.load(...)"`.
- `dotnet build src/Admin/Admin.csproj` → **0 errors**, 137 warnings, all pre-existing
  and unrelated (nullable-ref warnings in `AdminScripts.razor`, `ASP0014` in `Program.cs`).

## To Do Next

- **Decide on Serilog.** Either wire it up (`builder.Host.UseSerilog((ctx, cfg) =>
  cfg.ReadFrom.Configuration(ctx.Configuration))` + add the `Serilog.AspNetCore`
  package explicitly to `Admin.csproj` rather than relying on the transitive ref from
  core), which activates the intended file + Seq sinks — or delete the dead ~40-line
  block from `appsettings.json` so it stops implying behavior that doesn't exist.
  Leaving it as-is is the worst option: it reads as configured observability that
  isn't there. Note that wiring it up means the `"Microsoft": "Warning"` override
  becomes live and would independently silence the EF noise.
- **Consider a shared dev default.** The `Admin: Debug` level currently lives only in
  the untracked `launchSettings.json`. Since `.gitignore:16` excludes
  `appsettings.*.json`, a tracked `appsettings.Development.json` is not an option
  without amending the ignore rules — worth a team decision if others hit the same noise.
- **Optional: make the ops-check line carry a result count.** `IOpsCheck.ExecuteAsync`
  returns `Task` (void), so the log line can only report elapsed time, not what the
  check actually found. Changing the interface to return a count would make
  `"Ops check {RuleKey} found {N} in {ElapsedMs}ms"` possible — a real signal rather
  than a heartbeat. Deliberately not done here; it's an interface change across all
  `IOpsCheck` implementations.
