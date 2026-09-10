# SLYD → HubSpot Integration Spec — v2

**For: Kyle (CTO)**
**Supersedes: v1 (14 July 2026). v1's pipeline/stage/property tables remain valid and are repeated here where needed.**
**Portal ID: 246309560**

v1 covered one writer: the platform's intake seam. Since then two more signal
producers are in scope: SLYD Intel and SLYD Brief. Three independent
services each holding a HubSpot token, doing its own contact matching and its
own dedupe, will drift. v2 introduces **one internal gateway** that owns all
HubSpot writes. Everything in v1 survives — it just moves behind the gateway.

---

## 0 · Architecture in one diagram

```
  Platform (V3IntakeService,      SLYD Intel            SLYD Brief
  Lot/Deal webhooks)              (call reports)        (memory ledger)
        │                             │                      │
        └───────────────┬─────────────┴──────────┬──────────┘
                        ▼                        ▼
              ┌──────────────────────────────────────────┐
              │   HubSpot Gateway (one service, one      │
              │   token, one queue)                      │
              │   • owner-email → ownerId map            │
              │   • contact/company/deal resolution      │
              │   • dedupe table (source, source_key)    │
              │   • [UNMATCHED] review flow              │
              │   • rate limiting + retry                │
              └───────────────────┬──────────────────────┘
                                  ▼
                            HubSpot CRM API
```

Host it as a thin standalone service on Server A alongside SLYD Intel. What
matters is that **no other service holds a HubSpot token.**

---

## 1 · Constants (unchanged from v1)

**Pipelines:** Hardware Sales = `default` · Compute & Cloud = `2313007858` ·
Supply / Sourcing = `2413006553`

**Stage IDs:**

| Hardware Sales | ID | Compute & Cloud | ID | Supply / Sourcing | ID |
|---|---|---|---|---|---|
| New Inquiry | `appointmentscheduled` | Inquiry | `3743448769` | New Submission | `3981740752` |
| Qualified | `qualifiedtobuy` | Scoped | `3743448770` | Under Review | `3981740753` |
| Quote Sent | `presentationscheduled` | Proposal | `3743448771` | Offer Issued | `3981740754` |
| Negotiation | `decisionmakerboughtin` | Negotiation | `3743448772` | Accepted | `3981740755` |
| Compliance Clear | `contractsent` | Contracted | `3743448773` | Inspection & Logistics | `3981740756` |
| Contract & Payment | `3980213954` | Live / Closed Won | `3743448774` | Converted to Inventory | `3981740757` |
| Closed Won / Lost | `closedwon` / `closedlost` | Closed Lost | `3743448775` | Declined / Lost | `3981740758` |

**Owners:** hayden.gill@slyd.com = `72540685` · love.joshi@slyd.com = `79139998` ·
reginald.bailey@slyd.com = `166249620` · joseph.calamita@slyd.com = `166249621`

**Custom deal properties:** `slyd_deal_type`, `origination`, `gpu_model`,
`quantity_units`, `eccn_status`, `euc_received`, `screening_complete`,
`deal_cogs`, `gross_margin` (fraction, 0.22 = 22%), `slyd_platform_deal_id`,
`hardware_financing_status` (applied/approved/pending/rejected).

**Association type IDs (HUBSPOT_DEFINED):** deal→contact = 3, deal→company = 5,
task→deal = 216, note→deal = 214, call→contact = 194, call→deal = 206.
(Verify the engagement IDs once against `GET /crm/v4/associations/{from}/{to}/labels`
— HubSpot has changed these between API generations.)

---

## 2 · The gateway contract

One inbound endpoint, queue-backed. Producers POST an envelope; the gateway
resolves, dedupes, writes, records.

```jsonc
POST /internal/hubspot/events
{
  "source": "platform | intel | brief",
  "source_key": "SLY-2026-0041 | call:8f3a… | item:a91c… | msg:<id>",
  "event_type": "deal.create | deal.stage | product.upsert | call.report | ledger.item | lead.classified",
  "occurred_at": "2026-07-14T18:20:00Z",
  "actor_email": "reginald.bailey@slyd.com",     // maps to hubspot_owner_id
  "counterparty": {                               // all optional; gateway resolves
    "email": "gopi@wwt.com",
    "name": "Gopi",
    "company_name": "World Wide Technology",
    "company_domain": "wwt.com"
  },
  "payload": { /* event-type-specific, sections 3–6 */ }
}
```

Gateway behavior, in order:

1. **Dedupe check** — `(source, source_key, event_type)` against the dedupe
   table. Hit with unchanged `payload_hash` → drop. Hit with new hash → update
   the existing HubSpot record instead of creating.
2. **Owner resolution** — `actor_email` → ownerId via the static map. Unknown
   email → fall back to Hayden (`72540685`) and tag the record `[OWNER?]`.
3. **Counterparty resolution** (skip for product/stage events):
   a. contact by email (exact) → b. company by domain → c. company by name
   (exact, case-insensitive) → d. open deal whose name starts with the company
   name. Confidence: email or domain hit = HIGH (auto-associate); name-only
   hit = MEDIUM (associate + note the basis); nothing = UNMATCHED.
4. **UNMATCHED flow** — never guess, never drop. Create the task/note anyway,
   prefix the title `[UNMATCHED]`, assign to the actor's owner, associate to
   nothing. The rep links it to the right record in one drag; the gateway
   learns nothing (deliberately — no fuzzy auto-learning in v2).
5. **Write + record** — perform the HubSpot call(s), store
   `(source, source_key, event_type, hubspot_object_type, hubspot_object_id,
   payload_hash, written_at)` in the dedupe table.

**Dedupe table (SQLite or Postgres, one table):**

```sql
CREATE TABLE hs_sync (
  source        TEXT NOT NULL,
  source_key    TEXT NOT NULL,
  event_type    TEXT NOT NULL,
  hs_type       TEXT NOT NULL,   -- deals|contacts|companies|tasks|notes|calls|products
  hs_id         TEXT NOT NULL,
  payload_hash  TEXT NOT NULL,
  written_at    TEXT NOT NULL,
  PRIMARY KEY (source, source_key, event_type)
);
```

**Posture (unchanged from v1):** every producer fires and forgets. A HubSpot
outage must never fail an intake, a call capture, or a brief run. The gateway
queue absorbs; retry with backoff; after 5 failures park the event in a
dead-letter list surfaced on the gateway's own health page.

---

## 3 · Producer: Platform (migrates from v1)

Everything in v1 §2–3 stands. Changes:

- `V3IntakeService` now POSTs the envelope to the gateway instead of calling
  HubSpot. `event_type: deal.create`, `source_key` = the `NEED-…`/`INTAKE-…`
  ref, payload = the v1 `HubSpotLead` shape.
- **New: Lot webhook.** On Lot create/update →
  `event_type: product.upsert`, `source_key = LOT-…`, payload:
  `{ name, sku, price, condition, quantity_available, warranty, lead_time }`.
  Gateway upserts the product (search by `hs_sku`, then create/patch) and
  writes quantity/condition into the description with an `INVENTORY -` name
  prefix. This replaces the manual snapshot loaded on 14 July.
- **New: SLY- deal transitions.** `event_type: deal.stage`,
  `source_key = SLY-…`. Mapping (platform drives, HubSpot reflects):

| SLY- state | HubSpot action |
|---|---|
| Configuring | deal → Contract & Payment (`3980213954`) |
| Financing | stay; set `hardware_financing_status = pending` |
| Escrowed | stay; note "Escrow funded" on the deal |
| Live | Hardware Sales → `closedwon`; Compute & Cloud → `3743448774` |

  Match the HubSpot deal via dedupe table first, then by
  `slyd_platform_deal_id` property search. **Echo guard:** tag
  platform-originated writes; if you later add a HubSpot→platform webhook,
  ignore changes whose actor is the gateway's own token.

---

## 4 · Producer: SLYD Intel

Integrate from the **structured report + handoff layer**, never raw audio,
never full transcripts (link back to the Intel dashboard instead).

`event_type: call.report`, `source_key = call:{Call.id}`, one envelope per
analyzed call. Payload = the `slyd-intel-call-v1` structured JSON plus
`participants[].email`, `Call.title/started_at/ended_at`,
`handoff.delivery.owner_email`, `handoff.delivery.dashboard_url`, and the
`CallActionItem` rows.

Gateway writes, per call:

1. **Call engagement** — `POST /crm/v3/objects/calls` with
   `hs_call_title = Call.title`, `hs_timestamp = started_at`,
   `hs_call_duration` from start/end, `hs_call_body =
   brief_ready_summary + "\n\nFull report: " + dashboard_url`.
   Associate to every contact resolved from `participants[].email` and to the
   resolved deal.
2. **Note on the deal** — executive summary + the signal blocks that have
   content (competitors, objections, pricing_budget, power_energy,
   compute_requirements), each as a labeled line. Skip empty blocks.
3. **Tasks** — one per `CallActionItem`: subject = description (prefix
   `[UNMATCHED]` per §2 if no deal resolved), owner from `owner_name` →
   nearest team email → ownerId (else actor), due parsed from `due_text`
   (unparseable → +2 business days), associate to the deal.
   `source_key = item:{CallActionItem.id}` so re-extraction updates rather
   than duplicates.

**Hard rules:**
- `structured_json.deal.stage` and `.urgency` **never** write `dealstage`.
  They go into the note as "Intel read: stage ~Negotiation, urgency high."
  Stage moves belong to humans and the platform webhook only.
- Respect Intel's access model: only calls whose `brief_handoff_state = ready`
  sync. Held calls stay held.
- `confidence < 0.5` → sync the call engagement but mark the note
  "LOW-CONFIDENCE EXTRACTION — verify before acting."

---

## 5 · Producer: SLYD Brief

Integrate from the **MemoryStore ledger only** — never raw Slack/Outlook text.
`event_type: ledger.item`, `source_key = item:{item_key}` (the stable key
MemoryStore already generates — this is the dedupe anchor; repeated briefs
update the same HubSpot record).

**Privacy gate at the producer, not the gateway:** Brief only emits ledger
items that have a resolved external `counterparty`. Personal and internal
items (no counterparty, or counterparty domain = slyd.com) never leave the
user's private brief. This is a Brief-side filter by design.

Category → HubSpot mapping:

| Ledger category | HubSpot record |
|---|---|
| `reply`, `follow_up`, `waiting`, `needs_confirmation`, `meeting_prep` | Task (owner = ledger owner, due from `due` if parseable) |
| `sell_hardware`, `buy_hardware`, `financing`, `compute_rental` | Note on the resolved deal (these are deal-signal categories) |
| `customer_docs`, `supplier_docs` | Task titled "Docs: …" on the deal |
| `info`, `flag` | Note on the contact/company |

Field mapping: `title` → subject, `summary` → body, `status` resolved→
COMPLETED else NOT_STARTED, `source` + `confidence` appended to the body as
`(source: outlook, confidence: 0.8)` so reps know where an item came from.
Evidence links: include the Outlook/Slack deep link but label it "requires
your own access" — the gateway must not proxy or re-host evidence content.

When a ledger item is marked resolved in Slack (`/pulse` action), Brief emits
the same `source_key` with `status: resolved`; the gateway PATCHes the task
to COMPLETED. That closes the loop both directions.

---

## 6 · Hard rules (all producers, enforced in the gateway)

1. **Stage writes** come from exactly two places: the platform's `deal.stage`
   events and humans in the UI. Intel and Brief can never move a card.
2. **No secrets in HubSpot** — no tokens, keys, or credentials in any body.
3. **No raw content** — no audio, no transcripts, no raw DMs, no full email
   bodies. Summaries + deep links only.
4. **Enum safety** (v1 rule, now centralized): the gateway owns the
   `MapGpuModel`-style enum mappers. HubSpot silently drops unknown enum
   values; every enum write goes through an explicit map with `"Other"` /
   `"Not Assessed"` fallbacks.
5. **Internal domain filter**: any counterparty resolving to `slyd.com` is
   internal — note-to-self territory, not CRM territory. Drop it.
6. **One token, one writer.** If any new system ever needs to write to
   HubSpot, it becomes a producer with an envelope. No exceptions.

---

## 7 · Build order

1. **Gateway skeleton + Intel** (Intel is the first client; richest signal,
   cleanest schema). Ship when: a captured call shows up as an engagement +
   note + tasks on the right deal.
2. **Brief ledger sync** (reuses everything; only the category map is new).
3. **Migrate platform intake behind the gateway** (v1 code, new transport) +
   add the Lot and SLY- webhooks.

Each step ships independently. The sales team is already live in HubSpot;
nothing here blocks them, everything here feeds them.
