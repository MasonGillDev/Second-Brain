# Deal document upload to S3 (presigned)

**Project:** SLYD Platform (core + admin + platform)
**Date:** 2026-08-13 (built) · 2026-08-12 (investigation)
**Author:** 02409be5-f3cc-41b0-b445-1350443804d8
**Directory:** /Users/masongill/Slyd-Platform/admin

## Status

**BUILT — committed, not pushed, core not yet tagged.** All three repos green:
core 657/657, admin 250/250, platform 149/149.

| Repo | Commit | Branch |
|---|---|---|
| core | `50e9ab9` | `main` (user explicitly directed, after the never-push-to-main rule was raised) |
| admin | `d3abef8` | `development` |
| platform | `3d4d9d9` | `development` |

**Remaining: tag + publish core, bump the pins in admin and platform.** Deliberately
deferred to the end — both consumers build against core by ProjectReference
(`UseLocalCore=true`), so everything works locally without a release. Nothing deploys
until that tag exists.

### Decisions taken (all three confirmed by the user)

1. **Core `IFileStorageService`**, not an Admin-only extension — right long-term home,
   and the only route that later fixes the compliance KYC data loss.
2. **Visibility flag in this pass**, not deferred.
3. **Deal documents only** in this milestone; compliance repoint tracked separately.
4. **Reuse the existing assets bucket** rather than provisioning a new documents
   bucket — see "No infrastructure work was needed" below. This one reversed an
   earlier plan.

## Goal

Let ops actually attach files to deals in the deal workshop
(`/v3/deal-flow/pipeline/{DealId}` → `DealDetail.razor`), upload them to the S3 assets
bucket, and retrieve/preview them. **Decided: presigned URLs**, not an authenticated
streaming controller.

## What Was Built

### No infrastructure work was needed — and that was the key finding

The plan originally had a new `{env}-slyd-platform-documents-{account}` bucket on the
critical path. The user pushed back: no Terraform, no new secrets. Reuse turned out to be
both simpler **and** safe, because of one fact — **the assets bucket's public-read policy
is prefix-scoped**. The actual `prod-slyd-platform-assets` policy is exactly two
statements:

```
provisioning_v1.sh          (single object)
App_Icons/*                 (prefix)
```

So a new `Deal_Documents/` prefix is **private by default**. Nothing to provision: admin
already receives `S3__AssetsBucketName` / `S3__Region`, the task role already has
read+write, and presigning needs no extra IAM permission (the URL carries the signer's
existing access). No folder to pre-create either — S3 has no real folders; `PutObject`
with a slash in the key makes the prefix.

**The load-bearing invariant: widening that policy to a bare `/*` would silently make
every contract and invoice world-readable.** That is written into `FileStorageOptions`'
docstring so it isn't lost.

`dev-slyd-platform-assets` has **no bucket policy at all**, which is even safer for us —
though it means app icons don't render in dev.

### Core (`50e9ab9`)

- `IFileStorageService` (`SLYD.Application/Interfaces/Infrastructure/Services/Storage/`) —
  generic: a key and a stream, no deal/account concepts. `GetPresignedUrlAsync` returns
  `string?` so callers degrade to "no preview" instead of throwing.
- `S3FileStorageService` — no ACL, presigned reads only. Buffers non-seekable streams,
  because browser upload streams aren't seekable and `PutObject` needs a length up front.
- `LocalFileStorageService` — dev fallback, with the ephemeral-container warning in its
  docstring so it doesn't become another KYC.
- `FileStorageKeys` — **pure static**, extracted per core's `TESTING.md` "default to
  extraction". Keys are the one thing that can't change once files exist, and the
  sanitizer is a security boundary (a browser filename becomes a filesystem path under
  the local provider). 20 Tier 1 tests including traversal cases.
- `FileStorageOptions` bound to the **existing `"S3"` section** — no new config anywhere.
- `DealDocument.Visibility` (`Internal = 0 | Shared = 1`) + composite `(DealId, Visibility)`
  index + additive migration `20260813154555_AddDealDocumentVisibility` with
  `defaultValue: 0`.
- `AddFileStorage(configuration, localRootPath?, localBaseUrl?)` using
  `TryAddSingleton<IAmazonS3>` so admin's existing client registration isn't disturbed.
- `AWSSDK.S3 4.0.17.3` — **a brand-new dependency on `SLYD.Infrastructure`**, inherited by
  every consumer.

### Admin (`d3abef8`)

- `AddDocumentAsync` now takes `AddDealDocumentRequest` with an optional `Content` stream.
  **Upload runs before `SaveChanges`** — a storage failure must not leave a record
  pointing at a file that never landed. Without `Content` it stays metadata-only, still
  correct for a contract executed offline.
- `GetDocumentUrlAsync` — scoped by `(dealId, documentId)` so a document id alone can't
  sign a URL for a file on another deal. Tested.
- `DealDetail.razor` — `InputFile` + extension allowlist + 20 MB check, Internal/Shared
  selector, size display, per-document **Open**. URL minted per click rather than rendered
  into the page, so nothing long-lived sits in the DOM or history.
- `storageOptions` is an **optional** ctor param on purpose: making it required forced
  churn through three test files unrelated to documents.

### Platform (`3d4d9d9`)

- `DealRoomService.cs:293` filters to `Shared`.
- **Also filtered the buyer term-sheet status chip** (`:519`), which wasn't in the plan.
  Without it the buyer sees "term sheet awaiting signature" against an empty Documents
  tab — self-contradictory, and it reveals an internal term sheet exists.

### Gotchas hit while building

- **Razor parses `< 1024` in a switch expression as an HTML tag.** A `FormatBytes` switch
  with relational patterns produced a cascade of bogus "unclosed tag" errors ~400 lines
  away. Written long-hand with a comment.
- **`char.IsLetterOrDigit('é')` is true** — the first sanitizer let non-ASCII into storage
  keys. Now explicit ASCII ranges; the original filename is preserved in the DB for
  display, so nothing user-visible is lost.
- The compiler found a **second `AddDocumentAsync` call site** in `Pipeline.razor:842`
  that grep hadn't surfaced.
- **Locally, documents are served from `wwwroot/uploads/documents` with no auth.** Same as
  the existing local image storage, and admin is VPN-only, but dev has no access control
  on document bytes. Production is presigned-only.

## What Was Found

### The starting premise was wrong in a useful way

We do **not** already store a link to the file. The *column* exists but nothing in the
solution ever writes it. `DealDocument.StorageKey` is nullable and untouched
everywhere. `DealPipelineFeatures.AddDocumentAsync` (`:506`) builds a metadata row from
a **typed-in filename string** and stops. The test locks this in deliberately —
`admin/tests/Admin.Tests/Features/V3/DealFlow/DealPipelineDocumentTests.cs:77`:

```csharp
persisted.StorageKey.Should().BeNull("metadata-first: the record is a placeholder until upload lands");
```

So it is a placeholder feature, not a half-wired one.

**The upside:** the schema was designed for this. `StorageKey` (nvarchar 1000,
`SlydDbContext.cs:1420`), `ContentType`, and `SizeBytes` all already exist on
`DealDocument`. **No core domain change is required** for the upload itself — this can
ship entirely from the `admin` repo with no core release or `Admin.csproj` bump. (The
visibility flag, if chosen, is the one thing that *would* need core.)

### Where the UI lives

`src/Admin/Components/Pages/V3/DealFlow/DealDetail.razor`, "Documents & settlement"
panel, lines 238–291. Today: a `<select>` for `DealDocumentKind`, a **text input** for
the filename, a note field, and a list rendering `DisplayId · FileName (Kind)` with a
"Mark signed" button. No `InputFile`, no anchor, no preview.

Note the document path goes through `IDealPipelineFeatures`, **not**
`IDealWorkspaceFeatures` — the latter owns BOM lines / RFQs / quotes on the same page.
Easy to grab the wrong interface.

### The real design problem: S3StorageService is public-assets-only

`S3StorageService` is built exclusively around *publicly readable* assets. Every method
returns `GetPublicUrl()` — a raw `https://{bucket}.s3.{region}.amazonaws.com/{key}` —
and the upload comment (`:53`) states the mechanism:

```
// The bucket policy already allows public read for App_Icons/*
// No need to set ACL since we're using bucket policy
```

Deal documents are MSAs, LOIs, invoices and compliance certs. Public URLs are not
acceptable and **extending the bucket policy to a `Deal_Documents/*` prefix would be the
wrong fix**. Presigned GET (short TTL) is the decision. `AWSSDK.S3` is at `4.0.17.3`,
which supports presigning fine — the capability simply doesn't exist in the service yet.

Three implementations move together: `S3StorageService`, `LocalFileStorageService`
(writes under `wwwroot/uploads/`, so local dev serves statically), and
`NullS3StorageService`.

### Infrastructure is ready

- Bucket exists per env: `{env}-slyd-platform-assets-{account_id}`, private.
- ECS task role already has S3 read+write incl. multipart.
- **Admin already has `S3__AssetsBucketName` + `S3__Region` injected.** Platform WebUI
  and HangFire do **not** — relevant only if this ever needs to serve customers.
- Env vars come from Terraform in a separate infra repo; `.github/workflows/ci-cd.yml:229`
  pulls the live task definition via `describe-task-definition` and only swaps the image,
  so nothing in this repo defines them.
- Source: `platform/docs/implementation/TICKET-IMAGE-UPLOAD-S3.md`.

### Non-issues (checked, don't re-investigate)

- **The 512 KB SignalR cap** (`Program.cs:296`) is *not* a blocker. Blazor chunks
  `OpenReadStream` below it; `ImageLibraries.razor` already pushes 10 MB files through
  this exact path.
- **Upload UI pattern already exists**: `ImageLibraries.razor:184-240` is the cleanest
  template — extension allowlist → size check → buffer to `MemoryStream` → call service
  → per-file error collection. Size precedent: 10 MB in admin, 20 MB for compliance docs
  in platform.

### Platform visibility: already decided against us

The Deal Room **already renders every deal document to customers**, unfiltered —
`platform/src/Platform.WebUI/Services/DealRoomService.cs:293` selects `deal.Documents`
with no predicate beyond the deal, and `DealRoom.razor:322-350` renders a full Documents
tab (kind chip, filename, size, upload date, SIGNED/PENDING badge, live count in the tab
header).

What is *not* exposed is the bytes — `DealRoomDocumentRow` carries no `StorageKey` and
there is no download action. The record comment says so: *"Documents tab — metadata only,
read-only v1."*

**So the question is not "let platform users see these or not" — metadata is already
live.** The risk that makes this urgent: **filenames leak**. `_view.Documents` will
happily render `Acme-internal-margin-analysis.pdf` to the counterparty today. Adding a
real upload button to a surface that already mirrors filenames turns that from
theoretical into real the moment it ships.

Precedent for how to fix it, if chosen: `hide-counterparty-identity-customer-surfaces.md`
(2026-07-14) established that this boundary is enforced at the **service layer** — "the
response is the boundary" (platform CLAUDE.md rule #9) — not by hiding UI cells. A
visibility filter therefore belongs in `DealRoomService`, not in `DealRoom.razor`.

### Compliance uploads write real files that nobody can read

Asked as a side question; the answer matters more than expected.

`ComplianceService.UploadDocumentAsync` (`platform/.../Services/ComplianceService.cs:92-101`)
**does** persist real bytes — `File.Create(fullPath)` + `content.CopyToAsync(fs)`, real
`SizeBytes` from `FileInfo`, real `StorageKey`. It's a working upload pointed at local
disk (`ContentRoot/App_Data/kyc/{accountId}/`) instead of S3. Its own docstring flags
itself as a `SWAP-POINT`.

Three consequences, worst first:

1. **On Fargate those files are already gone.** The container filesystem is ephemeral —
   every deploy/restart/task replacement destroys uploaded KYC docs while the
   `AccountDocument` rows survive pointing at dead paths. With >1 task behind the LB, an
   upload lands on one task and is invisible to the others. **If customers have uploaded
   KYC docs in a deployed environment, that data is not recoverable.**
2. **There is no read path at all.** Admin's `ComplianceDocRow`
   (`admin/src/Admin.Application/Features/DealOS/ComplianceAdminFeatures.cs:25`) is
   `(DisplayId, Kind, FileName, SizeBytes, UploadedAt)` — no `StorageKey`, no download
   endpoint anywhere. Ops can see a document exists and never open it. The interface
   docstring concedes this: verification works by *"ops reaching out to the account
   email"*. The upload is decorative.
3. **Minor: orphaned partials.** The 20 MB guard is enforced twice —
   `OpenReadStream(maxAllowedSize: 20MB)` at `SettingsV3.razor:445` (throws mid-copy) and
   a post-write `fs.Length` check. The post-write branch deletes the file, but the
   `OpenReadStream` throw propagates out of `CopyToAsync` with no `try/finally`, leaving a
   partial file on disk with no DB row.

`AccountDocument` is explicitly documented as *"the DealDocument storage pattern,
re-instanced at the account level"* — so it is the same problem twice, and it is the one
with real data at risk right now.

## To Do Next

### To ship this

1. **Tag + publish core, then bump the pins.** Admin is on `SLYD.Infrastructure` 0.2.13,
   platform on **0.2.12** — so platform takes a two-version jump and will carry unrelated
   diff. Confirm the release's `efbundle` artifact contains
   `20260813154555_AddDealDocumentVisibility`; admin's CI applies it before deploy.
2. **Push all three branches.** Nothing is pushed. Core is committed on `main` at the
   user's explicit direction — decide whether that should move before it goes anywhere.
3. **Check what `S3__AssetsBucketName` is set to on the dev task definition.** The code has
   no environment awareness; whatever the task def injects is the bucket it writes to.
   `aws ecs describe-task-definition --task-definition slyd-platform-dev-admin-family
   --query "taskDefinition.containerDefinitions[0].environment"`. If it's unset, uploads
   are simply unavailable in dev (the DI registers nothing) rather than misdirected.
4. **Click through it in a running app.** Everything so far is build + tests; the upload,
   presign and preview have never been exercised against real S3.

### Adjacent, found along the way

5. **Marketplace and Image Library uploads are latently broken.** Both return
   `GetPublicUrl()` while the bucket policy covers only `App_Icons/*` and
   `provisioning_v1.sh`, so those URLs 403. **Not currently live** — the prod bucket holds
   exactly two objects, so nothing has ever been uploaded through those paths. The first
   upload will be broken. No backfill needed; cheap to fix.
6. **App icons don't render in dev** — `dev-slyd-platform-assets` has no bucket policy.
7. **`appsettings.json:115` says `"Region": "us-east-1"`** but the buckets are in
   **us-west-2**. Deployment overrides it, so prod is fine; local dev with a bucket set
   would build wrong-region URLs.
8. **`TICKET-IMAGE-UPLOAD-S3.md:18` is stale in two ways** — the real name is
   `{env}-slyd-platform-assets` (no account-id suffix), and admin's env vars are as
   described but the doc's bucket naming is wrong.

### Deferred by decision

9. **Repoint `ComplianceService` at `IFileStorageService`.** Still writing KYC files to
   local disk on Fargate, so **every deploy destroys them** while `AccountDocument` rows
   survive pointing at dead paths — and there is no read path at all, so ops can never
   open what customers upload. Now a ~10-line swap plus adding `StorageKey` + a presigned
   download to `ComplianceDocRow` (admin) and `ComplianceDocView` (platform). Needs
   Terraform to inject S3 env vars into Platform WebUI, which it currently lacks.
10. **Fold admin's `IS3StorageService` image methods into the core service** so there
    aren't two storage abstractions.
11. **Promote `"deal-os-gate"` to a shared constant** while core is open (see
    [[deal-os-access-request-ops-notification]]).
12. **Wrap the compliance write in `try/finally`** to clean up partial files on a
    mid-copy throw.

## Note on the working tree

Admin's tree carried a concurrent session's uncommitted Demand Book changes
(`DemandBookFeatures`, `MatchingEngineFeatures`, `ProcurementLineProjection.cs`,
`DemandBook.razor`) throughout. Only this task's seven files were staged; those remain
uncommitted and untouched.
