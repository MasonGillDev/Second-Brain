# GitHub Deployment Security Audit (Token + Environment Variables)

**Date:** 2026-04-02
**Branch:** `feature-GitHubOAuth`
**Repo:** `SLYD-Platform/core`

---

## Overview

Performed a full end-to-end security audit of both the `EncryptedAccessToken` field on `UserGitHubConnection` and the user-supplied **environment variables** flow. Traced both through their entire lifecycle — from input through storage and usage in deployment scripts — identifying all attack surfaces.

---

## Token Lifecycle

| Stage | Location | State |
|-------|----------|-------|
| OAuth Exchange | `GitHubService.ExchangeCodeForTokenAsync()` | Plaintext in memory |
| Encryption | `GitHubTokenEncryptor.Protect()` | Encrypted via ASP.NET Data Protection |
| Database Storage | `UserGitHubConnections.EncryptedAccessToken` (PostgreSQL, `varchar(1000)`) | Encrypted at rest |
| Decryption | `GitHubTokenEncryptor.Unprotect()` | Plaintext in memory |
| Usage | GitHub API calls, clone URLs, shell scripts | Plaintext in transit/on disk |

## Encryption Mechanism

- Uses `Microsoft.AspNetCore.DataProtection` with purpose string `"SLYD.GitHub.AccessToken"`
- Registered in `DependencyInjection.cs` with `SetApplicationName("slyd-platform")`
- **No `PersistKeysTo*` configured** — keys stored in default location (filesystem)
- **No key encryption at rest** — no `ProtectKeysWithCertificate` or similar
- **No key rotation policy** configured

## Files That Consume the Token (Decryption Points)

- `GitHubDeploymentProcessor.cs` — initial deployment, embeds token in cloud-init
- `GitHubRedeployProcessor.cs` — redeploy, writes token into shell script on instance
- `GitHubDeploymentFeatures.cs` — deploy, enable/disable auto-deploy, terminate deployment
- `GitHubTokenRotationJob.cs` — token rotation (30-day expiry), revoke + delete
- `GitHubService.cs` — all GitHub API calls (list repos, get repo, create/delete webhooks, revoke token)

---

## Vulnerabilities Identified (Ranked by Severity)

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | HIGH | Plaintext token embedded in cloud-init config, persisted in LXD instance metadata on host | **Fixed** (scrub userdata) |
| 2 | HIGH | Plaintext token written to `/tmp/redeploy.sh` on instances with no cleanup | **Fixed** (self-delete script) |
| 3 | HIGH | No `PersistKeysTo*` configured — Data Protection keys can be lost on redeployment | **TODO** |
| 4 | MEDIUM | No key encryption at rest — Data Protection XML key files stored unencrypted on disk | **TODO** |
| 5 | MEDIUM | Token briefly visible in `/proc/*/cmdline` during `git clone` and `git fetch` | **TODO** (requires `git credential fill`) |
| 6 | MEDIUM | Token in `.git/config` between `remote set-url` calls (race window) | **TODO** (requires `git credential fill`) |
| 7 | LOW | No DPAPI/certificate protection on key ring — DB + key ring theft = full decryption | **TODO** |
| 8 | LOW | Failed rotation leaves potentially valid unrevoked tokens on GitHub | **TODO** |

---

## Environment Variables Security Audit

### Env Var Lifecycle

| Stage | Location | State |
|-------|----------|-------|
| User Input | `GitHubDeploymentRequest.EnvironmentVariables` (API request body) | **Plaintext** |
| Serialization | `GitHubDeploymentFeatures.cs:187` — `JsonSerializer.Serialize()` | **Plaintext JSON** |
| Hangfire Queue | `HangfireJobScheduler.cs:174` — passed as `environmentVariablesJson` job argument | **Plaintext in Hangfire DB** |
| Cloud-Init | `GitHubDeploymentProcessor.cs:454` — written as shell `echo` commands | **Plaintext in LXD instance config** |
| Instance Disk | `/app/.env` on the container | **Plaintext file** |
| Docker Runtime | `--env-file /app/.env` passed to `docker run`/`docker compose` | **Plaintext in container env** |

**Key difference from GitHub token:** Environment variables are **never encrypted at any stage**. The GitHub token at least goes through `IGitHubTokenEncryptor` before DB storage. Env vars containing database passwords, Stripe keys, etc. travel as plaintext end-to-end.

### Env Var Vulnerabilities (Ranked by Severity)

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | HIGH | **Plaintext in Hangfire database** — Hangfire serializes all job arguments (including `environmentVariablesJson`) to its DB tables. Anyone with DB read access sees every user's secrets. Hangfire dashboard also exposes job arguments. Completed jobs may persist indefinitely depending on config. | **TODO** |
| 2 | HIGH | **Plaintext in cloud-init / LXD instance metadata** — env vars are embedded in the cloud-init YAML stored in LXD instance config. `lxc config show <instance>` exposes all of them. Unlike the GitHub token, **env vars are not scrubbed** from cloud-init userdata. | **TODO** |
| 3 | HIGH | **No encryption at rest anywhere** — unlike the GitHub token, env vars have zero encryption at any point in the pipeline. | **TODO** |
| 4 | MEDIUM | **Shell injection via env var values** — escaping in `GitHubDeploymentProcessor.cs:450-454` only handles `\` and `'`. Values containing `$(command)` or backticks inside double quotes could execute arbitrary commands. The **key name is not escaped at all** — a key like `; rm -rf /` injects directly into the shell command. | **TODO** |
| 5 | MEDIUM | **`.env` backup has default permissions** — during redeploy, `/tmp/.env.backup` is created without `chmod 600`, readable by any user on the instance during the redeploy window. | **TODO** |
| 6 | LOW | **Env vars visible in `docker inspect`** — when passed via `--env-file`, variables are readable via `docker inspect <container>`. Standard Docker behavior but relevant for untrusted hosts. | **TODO** |

### Env Var Recommendations (Prioritized)

1. **Encrypt env vars before passing to Hangfire** — use `IGitHubTokenEncryptor` or store them in a separate encrypted column and pass only a reference ID to Hangfire
2. **Scrub env vars from cloud-init userdata** the same way we now scrub the GitHub token
3. **Sanitize/validate env var keys** — reject keys containing shell metacharacters (`;`, `$`, `` ` ``, `|`, `&`, etc.)
4. **Set permissions on the backup** — add `chmod 600 /tmp/.env.backup` during redeploy
5. **For untrusted hosts**: env vars need the same treatment as the token — don't embed in cloud-init, fetch at runtime from platform API

---

## Changes Made (2026-04-02)

### 1. Redeploy Script Self-Deletion (`GitHubRedeployProcessor.cs`)

- Added `rm -f /tmp/redeploy.sh` immediately after variable declarations — script deletes itself from disk as soon as bash reads it into memory
- Added `unset TOKEN` after git operations complete — clears the token from the shell environment

### 2. Cloud-Init Userdata Scrubbing (`GitHubDeploymentProcessor.cs`)

- Added `sed` scrub of `/var/lib/cloud/instance/user-data.txt` — removes token from persisted cloud-init config
- Added `sed` scrub of `/var/lib/cloud/instance/scripts/runcmd` — removes token from generated runcmd script
- Existing scrub of `/var/log/cloud-init-output.log` was already in place

---

## Remaining Work (Prioritized)

### Priority 1: Shell Injection Fix (Env Vars)

**Effort: Small | Impact: HIGH**

Sanitize/validate env var key names — reject keys containing shell metacharacters (`;`, `$`, `` ` ``, `|`, `&`, etc.). Also fix value escaping to handle `$(command)` and backtick injection inside the double-quoted context. One-file change in `GitHubDeploymentProcessor.cs`.

### Priority 2: Encrypt Env Vars Before Hangfire

**Effort: Medium | Impact: HIGH**

Env vars sit as plaintext JSON in Hangfire's DB tables indefinitely. Either:
- Encrypt the JSON blob with `IGitHubTokenEncryptor.Protect()` before passing to Hangfire, decrypt on the other side
- Or store env vars in an encrypted column and pass only a reference ID as the Hangfire job argument

### Priority 3: One-Time Token + Secrets Endpoint (Option B)

**Effort: Medium | Impact: HIGH**

Removes **both** the GitHub token and env vars from cloud-init and deploy scripts entirely:

1. Before provisioning, generate a one-time-use secret (random UUID), store in DB with deployment ID and a 10-minute TTL
2. Pass only the OTP to cloud-init/redeploy script
3. Script calls: `curl https://your-api/api/internal/deploy-secrets/{otp}`
4. API validates OTP (exists, not expired, not used), returns the clone URL with real token **and** the env vars
5. API marks OTP as consumed immediately
6. Script writes env vars to `/app/.env` and uses clone URL — nothing persisted in cloud-init metadata

Uses existing infrastructure — platform API + Cloudflare Tunnel. No AWS needed. Solves the cloud-init metadata exposure for both tokens and env vars in one shot.

### Priority 4: GitHub App Installation Tokens

**Effort: Large | Impact: HIGH (required for untrusted hosts)**

Replace long-lived OAuth tokens with short-lived (1 hour) GitHub App installation tokens:

- Register a GitHub App
- Change the OAuth flow to use App installation tokens
- Tokens are scoped and auto-expire — biggest security win for untrusted hosts
- Required before supporting user-owned/third-party hardware

### Priority 5: Data Protection Key Persistence

**Effort: Small | Impact: MEDIUM**

- Configure `PersistKeysToDbColumn` or `PersistKeysToAzureBlobStorage`
- Add `ProtectKeysWithCertificate` for key encryption at rest
- Prevents token loss on redeployment and protects keys on disk

### Priority 6: `git credential fill` via stdin

**Effort: Small | Impact: MEDIUM (required for untrusted hosts)**

- Eliminates token from `/proc/*/cmdline` (process arguments)
- Eliminates token from `.git/config` (no URL-embedded tokens)
- Needed if platform expands to untrusted hardware

### Priority 7: Redeploy `.env` Backup Permissions

**Effort: Trivial | Impact: LOW**

Add `chmod 600 /tmp/.env.backup` in `GitHubRedeployProcessor.cs` during the backup step so the file isn't world-readable during the redeploy window.

---

## Architecture Decision: Untrusted Hosts

If the platform moves toward users deploying to their own hardware or third-party providers, the security model changes fundamentally:

- **Asymmetric token exchange** — instance generates a keypair, sends public key to platform, platform encrypts token with it, instance decrypts locally. Plaintext never crosses the wire.
- **GitHub App installation tokens** become mandatory (short TTL)
- **Cloud-init cannot contain secrets at all** — host operator can read instance metadata
- **Token proxy via Cloudflare Tunnel** — instance authenticates via tunnel identity, fetches secrets at runtime

This is **not over-engineering** in the untrusted host scenario — it's baseline. But for the current model (SLYD-controlled LXD hosts), Priorities 1-3 above are sufficient.

---

## Key Design Insight

The Cloudflare Tunnel already solves the "how does the instance authenticate" problem. The tunnel identity is the credential. The instance calls home to the platform API, which decrypts and serves the token. No AWS, no new secret distribution mechanism needed. The platform API **is** the secrets manager.
