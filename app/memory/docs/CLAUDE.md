# admin-docs — Knowledge Base Conventions

This directory is the source of truth for the SLYD admin AI assistant's knowledge base. Files here are uploaded into the Pinecone Assistant `slyd-admin-agent` and retrieved at runtime when an admin asks the assistant a question via the Cmd+K → "Ask AI" mode in the admin portal.

**Read this before writing or editing a doc.** The assistant only knows what's in these files — getting the conventions right is the whole product.

---

## Who reads these docs

You're writing for **the AI agent**, not for a human reading the file. The agent retrieves chunks via semantic search, optionally pulls the full file, then answers a human admin in a chat box.

The end-user of an answer is a SLYD admin (support, ops, finance, sales). They can act only through what they see in the admin portal UI or by coaching a user through what the user sees in their portal. They cannot read code, run SQL, hit APIs, or inspect databases. Every step you write must be something they can actually click, type, or look at.

---

## Scope — three kinds of docs

The knowledge base will grow to cover three distinct surfaces. Match your doc to the right shape:

### 1. Admin portal pages
What an admin uses. Examples we have today: Brokers, Pricing Engine, Customers, Submissions, Support Tickets.

Shape: "purpose → layout → primary tasks (step-by-step) → things to know."

### 2. User-facing surfaces
What the **customer / provider / broker** sees in *their* portal. The admin doesn't open these pages themselves — but they need to know what the user is looking at when the user calls in, what each button does, and what state the user is currently in.

Example questions the assistant should be able to answer from these docs:

> "A seller asked how they post hardware to auction — walk me through what they see."
>
> "A customer says their wallet shows 'pending funding' — what does that screen actually say and what's their next step?"

Shape: same as admin pages, but written from the user's vantage point. Include the URL/path the user would be at, the buttons they'd press, the confirmations they'd see.

### 3. Troubleshooting playbooks
Cross-cutting "user says X / admin should check Y" runbooks that span multiple surfaces.

Shape: symptom → likely causes → where to look in the admin UI → resolution steps. Reference the relevant admin and user docs by `[Title](route)` rather than duplicating their content.

---

## The cardinal rule: user-facing language only

**Docs reference what a person sees and clicks. Nothing else.**

✅ Yes — reference these:
- Button labels exactly as they appear (`**Mark earned**`)
- Panel, tab, drawer, and dialog titles
- Form field labels and placeholders
- Column headers in tables
- Status badges and pill text (`**Resolved**`, `**In Progress**`)
- Toast banner and error messages the user actually sees
- The URL path visible in the browser address bar (e.g. `/v3/platform/brokers`)
- Keyboard shortcuts the user actually presses

❌ No — never reference these:
- Class, method, interface, or file names (`AdminBrokerFeatures`, `Brokers.razor`)
- Database tables, columns, or queries
- API endpoints, SignalR hubs, internal services
- Architecture concepts ("the Pinecone Assistant," "Hangfire job," "EF migration")
- File paths or repository structure
- Feature-flag keys, environment variables, secrets
- Anything that requires reading source code to understand

If a behavior is driven by something the user can't see, describe the **observable effect**, not the cause. *"After saving, the new broker shows up in the roster within a few seconds"* — not *"the SignalR hub broadcasts a BrokerCreated event."*

---

## Frontmatter

Every doc starts with a YAML frontmatter block. The agent's system prompt tells it to read the frontmatter for the canonical route, so this is how citations get their deep-link.

```yaml
---
title: Brokers
route: /v3/platform/brokers
audience: partnership-ops, finance
slug: brokers
surface: admin
---
```

| Field | Required? | Notes |
|---|---|---|
| `title` | yes | Human-readable name. Used as the citation label `[title](route)`. |
| `route` | yes for `admin`/`user` surfaces | The exact URL path the user/admin would visit, starting with `/`. Omit for `troubleshooting` docs that don't map to a single page. |
| `audience` | yes | Comma-separated teams (e.g. `support`, `revenue-ops`, `partnership-ops`, `customer-success`, `finance`, `exec`, `deal-ops`, `supply-ops`). |
| `slug` | yes | kebab-case identifier. Must match the file name (`brokers.md` → `slug: brokers`). |
| `surface` | yes | One of `admin`, `user`, `troubleshooting`. Helps the assistant frame the answer correctly. |

---

## File naming

- One file per logical surface (page, end-to-end flow, or playbook).
- `kebab-case-name.md` matching `slug:`.
- Prefix user-facing docs with `user-` (e.g. `user-post-auction.md`). Prefix troubleshooting docs with `troubleshoot-` (e.g. `troubleshoot-funding-pending.md`). Admin docs get no prefix — they're the default.

---

## Body structure

### Admin page docs
1. **Intro paragraph** — purpose in one or two sentences + where to find the page in the sidebar nav + the route.
2. **Page layout** — bullet list of the major panels/tabs/sections, in the order they appear.
3. **Primary tasks** — one `##` heading per task. Inside, numbered steps using bolded **UI labels**. Include the confirmation step if the action requires one.
4. **Filters / columns / sorting** — if the page has a list view.
5. **Drawer / detail view** — if clicking a row opens one.
6. **Things to know** — gotchas, irreversibility, hidden defaults, role gates the admin would notice, cross-page side-effects.

### User-facing docs
Same shape as admin, but written from the user's perspective. Always include:
- *Where the user starts* (which URL or in-product nav)
- *What they see at each step* (button labels, dialog titles, what changes on screen)
- *What confirmation or notification they receive*
- *What state the user is now in* — this matters because admins often need to figure out "where did the user stop?"

### Troubleshooting docs
- **Symptom** — what the user reports or what the admin observes (one or two sentences).
- **Common causes** — numbered list of plausible reasons.
- **Where to verify** — for each cause, the admin page + panel + field to check, plus what value indicates the problem.
- **Resolution** — step-by-step fix using admin UI controls. If escalation is required, say so explicitly.
- **Related docs** — cite the admin and user docs the playbook depends on.

---

## Writing style

- **Steps are imperative and concrete.** "Click **Mark matched**, then **Confirm match?**" — not "the admin can transition the submission state."
- **Bold UI labels** when you first mention them in a step: `**Add broker**`, `**Wallet Balance**`, `**Issue Offer →**`. This makes it easy for the agent to lift the exact label into its answer.
- **Use the actual wording** the UI uses, including arrows, ellipses, and punctuation (`Issue Offer →`, not "Issue Offer button").
- **Short sentences. Active voice.** The agent will compress further when it answers — start tight.
- **Don't speculate.** If you're not sure whether a feature works a particular way, leave it out or check the page. Hallucinations propagate.
- **Cite cross-references in markdown link form**: `[Customers](/customers)` — same shape the assistant uses to cite back to the human admin.
- **Cover irreversibility explicitly.** If an action is permanent ("entries are never deleted, only reversed"), say so. Admins ask exactly these questions.

---

## A worked example of what to write vs not

> A user says they can't see a hardware lot they just posted for auction. The admin asks: *"Where do I check this?"*

**Good doc content:**
> The user starts at **Sell → My Listings** in their portal. After clicking **Post to auction** they should see the lot appear in the **Pending Review** tab with status **Awaiting Approval**. If the lot is missing from that tab, check the admin **Submissions** page at `/v3/intake/submissions` — the lot will be in status **New** until an admin clicks **Begin Review →**.

**Bad doc content (do not write this):**
> The user invokes `POST /api/auctions/submit` which writes to the `AuctionSubmissions` table with `Status = Pending`. The `IAuctionFeatures.SubmitAsync` method then enqueues a Hangfire job…

The second version is useless to the admin and prone to going stale. The first version answers the question in language the admin can act on.

---

## Authoring + upload workflow

1. Draft the `.md` here, in `/Users/masongill/Slyd/admin-docs/`. Keep it under version control on your own machine if you want history (the repo doesn't track this directory).
2. Open the SLYD admin agent in Pinecone — `app.pinecone.io` → Assistants → `slyd-admin-agent`.
3. Drag the `.md` file into the **Files** panel on the right.
4. Wait for the file's status to flip from `Processing` to `Available` (usually a few seconds).
5. Test by opening the admin portal → `⌘K` → **Ask AI** → ask a question the new doc should cover.

To update an existing doc, delete the old file in the Pinecone UI and re-upload the new version. Files are immutable in Pinecone — there is no in-place edit.

---

## When in doubt

- Read 2–3 existing docs in this directory to match tone and density.
- If the answer requires architecture knowledge, you're writing the wrong doc — find the user-visible reframing.
- If a single doc would be longer than ~800 lines, split it: usually the boundary is one logical surface or one end-to-end flow per file.
- The assistant works better with **more, shorter, well-scoped docs** than with one giant catch-all. The retriever's job is to find the right chunk; smaller docs make that easier.
