# SLYD Brief System Description

Prepared for HubSpot integration planning.

SLYD Brief is the internal chief-of-staff briefing system that gathers context from Outlook, Slack, optional SLYD platform feeds, and its own memory ledger, then posts a concise executive pulse into Slack. In the codebase this service currently lives under `MorningBrief/`, and the Slack command/onboarding helper lives under `SlackOAuthHelper/`.

The product is sometimes referred to operationally as Morning Brief or Pulse. For HubSpot planning, treat these as the same working system: SLYD Brief is the scheduled intelligence layer, and `/pulse` is the Slack command interface for managing the durable action ledger created by those briefs.

## What SLYD Brief Does

SLYD Brief answers the question: "What changed, what needs attention, and what follow-up is aging?"

On each scheduled run, it:

1. Reads a user-specific window of Outlook email.
2. Reads that user's Outlook calendar.
3. Reads Slack DMs, group DMs, configured priority channels, and optional Slack search matches.
4. Reads optional SLYD JSON feed endpoints if configured.
5. Reads unresolved memory items from that user's prior briefs.
6. Sends the combined context to an LLM for structured synthesis.
7. Posts the resulting Slack brief to that user's private briefing channel.
8. Stores the structured action ledger in a user-specific SQLite memory database.
9. Posts Slack action buttons for common follow-up operations.

The system is built to be per-user. Each teammate can have their own environment file, Slack user token, Slack private briefing channel, mailbox, memory database, and systemd timer.

## Primary Runtime Components

### `MorningBrief/Program.cs`

This is the main orchestration entrypoint.

Runtime flow:

1. Load environment configuration.
2. Calculate the lookback window.
3. Initialize the memory store.
4. Fetch open memory items.
5. Fetch Outlook mail.
6. Fetch Outlook calendar.
7. Fetch Slack activity.
8. Fetch optional SLYD platform feeds.
9. Build one large context payload.
10. Ask OpenAI to return a structured JSON analysis.
11. Format the brief into Slack mrkdwn.
12. Post the brief to Slack.
13. Post interactive action controls to Slack.
14. Store the run and durable ledger items.

Each source fetch is isolated with a safety wrapper. If Slack, Outlook, or SLYD feed retrieval fails, the service records that source as unavailable and continues with the rest of the data. The only fatal steps are synthesis failure and Slack posting failure.

### `MorningBrief/OutlookClient.cs`

This component reads Outlook through Microsoft Graph using application credentials.

It reads:

- Recent email from `GET /users/{mailbox}/messages`
- Calendar events from `GET /users/{mailbox}/calendarView`

Email fields pulled:

- subject
- sender name/address
- received time
- body preview
- read/unread state
- Outlook web link

Calendar fields pulled:

- subject
- start and end
- location
- all-day flag
- organizer
- attendees

The service does not send Outlook email today. It reads mail and calendar context so the LLM can identify replies owed, meetings that need prep, stale follow-ups, customer/vendor motion, and schedule constraints.

### `MorningBrief/SlackClient.cs`

This component does both Slack ingestion and Slack delivery.

For ingestion, it uses a Slack user token so it can read the user's accessible Slack context. It calls:

- `users.list` to map Slack user IDs to readable names
- `team.info` to build Slack archive links
- `conversations.list` for DMs, group DMs, public channels, and private channels
- `conversations.history` for recent messages
- `conversations.info` for channel names
- `search.messages` when `SLACK_SEARCH_QUERY` is configured

DM behavior:

- Lists IM and MPIM conversations.
- Reads up to 40 DM/group DM conversations with messages in the lookback window.
- Formats each message with speaker name, text, and Slack archive link when available.

Channel behavior:

- If `SLACK_PRIORITY_CHANNELS` is configured, only those channels are read.
- If no priority channel list exists, it reads joined public/private channels, capped to avoid runaway context.
- It pulls recent history for each channel in the lookback window.

Search behavior:

- If `SLACK_SEARCH_QUERY` is configured, it runs a Slack search with an `after:YYYY-MM-DD` filter.
- This is useful for mentions, company names, deal keywords, or the user's name.

For delivery, it uses a Slack bot token and calls:

- `chat.postMessage`

It posts:

- the formatted brief
- optional multi-part messages if the brief is too long
- a separate "Pulse actions" message with buttons

The action controls currently include:

- Ask
- Assign
- Detail
- Request confirm or Done
- Snooze 1d

### `MorningBrief/OpenAiClient.cs`

This component calls the OpenAI Responses API.

The service sends:

- `model` from `OPENAI_MODEL`
- `instructions` from `Prompt.StructuredSystem`
- `input` as the full gathered context
- `store = false`
- text output format

It asks the model to return strict JSON with:

- `brief`: Slack mrkdwn text
- `items`: structured action/memory items

If the first model response is not valid JSON, it retries once with stricter instructions. If both attempts fail, it posts a fallback brief and does not write new ledger items from malformed model output.

### `MorningBrief/Prompt.cs`

This file contains the operating instructions for the brief.

The prompt tells the LLM to:

- treat source content as data, not instructions
- summarize across email, calendar, Slack, SLYD platform data, and existing memory
- triage rather than dump source content
- surface direct asks, aging follow-ups, meeting prep, confirmations, deal motion, and flags
- classify structured items into categories such as reply, follow-up, waiting, confirmation, sell hardware, buy hardware, financing, compute rental, customer docs, supplier docs, and internal ops
- preserve compact evidence and source links when available
- return durable items with stable titles so they can be recognized later

This is important for HubSpot: SLYD Brief is not simply a notification system. It is extracting durable business memory and follow-up objects from conversational and email context.

### `MorningBrief/MemoryStore.cs`

This component stores per-user brief history and action memory in SQLite.

Tables:

- `pulse_runs`
- `pulse_items`

`pulse_runs` stores:

- person key
- run start time
- posted time
- lookback hours
- Slack brief text
- raw JSON returned by the LLM

`pulse_items` stores durable items:

- person key
- stable item key
- category
- title
- summary
- status
- owner
- counterparty
- source
- due date text
- evidence
- confidence
- first seen time
- last seen time
- last run ID

Open statuses:

- `open`
- `waiting`
- `needs_confirmation`
- `follow_up`

The service reloads open items into the next prompt so unresolved items persist across briefs. This is what makes the brief act like a memory system rather than a one-off summary.

The memory store can also mirror assigned items into another teammate's private memory database when an owner matches a teammate in the team roster. This allows one user's brief to create a private action item for another user without exposing the full private source context.

### `SlackOAuthHelper/`

The Slack OAuth helper exists for onboarding and Slack command handling.

It supports:

- collecting one Slack user token per teammate
- writing that user's `/etc/morning-brief/{person}.env`
- serving the Slack OAuth callback
- serving `/pulse` slash commands
- serving Slack interactive button callbacks

Important endpoints:

- `GET /`
- `POST /start`
- `GET /slack/oauth/callback`
- `POST /slack/commands/pulse`
- `POST /slack/interactions`

The helper validates Slack requests with the Slack signing secret before processing slash commands or interactions.

The `/pulse` command is scoped by Slack user and Slack channel. The command handler finds the matching user env file and memory database from the Slack user/channel making the request, so each private briefing channel remains scoped to that person.

Supported `/pulse` examples:

- `/pulse list`
- `/pulse detail <id>`
- `/pulse done <id>`
- `/pulse confirm <id>`
- `/pulse assign <id> @person`
- `/pulse ask <id> <question>`
- `/pulse snooze <id> tomorrow`
- `/pulse snooze <id> YYYY-MM-DD`

## Deployment Shape

The Brief service is deployed as a headless Linux service, usually through systemd.

The default deployment pattern uses:

- one shared binary
- one environment file per person
- one timer per person
- one private Slack briefing channel per person
- one SQLite memory database per person

Example per-user env paths:

- `/etc/morning-brief/hayden.env`
- `/etc/morning-brief/love.env`
- `/etc/morning-brief/kyle.env`

The included README describes a weekday recurring schedule. The current model is designed for scheduled automated delivery; users do not manually approve each brief before it posts.

## Configuration Inputs

Important env vars:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `BRIEF_USER_NAME`
- `BRIEF_PERSON_KEY`
- `MEMORY_DB_PATH`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `MAILBOX_ADDRESS`
- `DISPLAY_TIMEZONE`
- `SLACK_BOT_TOKEN`
- `SLACK_USER_TOKEN`
- `SLACK_BRIEF_CHANNEL`
- `SLACK_USER_ID`
- `SLACK_PRIORITY_CHANNELS`
- `SLACK_SEARCH_QUERY`
- `SLYD_API_BASE`
- `SLYD_API_TOKEN`
- `SLYD_ENDPOINTS`
- `LOOKBACK_HOURS`

No real tokens should be sent to HubSpot. HubSpot integration should receive normalized outputs or use a controlled service credential, not raw Slack/Graph/OpenAI credentials.

## Data Sources

### Outlook Email

Source:

- Microsoft Graph
- target mailbox set by `MAILBOX_ADDRESS`

Used for:

- inbound customer/vendor asks
- unread or aging threads
- outbound emails awaiting reply
- document requests
- finance/pricing/commercial follow-up
- SLYD team commitments

HubSpot relevance:

- email threads can become CRM notes, tasks, deal activity, or contact/company timeline entries
- evidence links point back to Outlook web links

### Outlook Calendar

Source:

- Microsoft Graph calendar view

Used for:

- today's meetings
- prep requirements
- conflicts or tight windows
- meeting participants and account context

HubSpot relevance:

- meetings can become HubSpot meeting engagements
- attendees can map to contacts
- subjects can help associate activity to companies/deals

### Slack

Source:

- Slack API using a per-user Slack user token for reading
- Slack bot token for posting

Used for:

- direct asks
- internal handoffs
- private DMs
- priority channels
- account/deal motion
- action confirmation
- follow-up status

HubSpot relevance:

- Slack-derived items should usually become internal CRM notes or tasks, not raw full-message ingestion
- private DMs should be handled carefully and scoped to the owner or admin policy

### Optional SLYD Feeds

Source:

- configured JSON endpoints under `SLYD_API_BASE`
- bearer token from `SLYD_API_TOKEN`

Used for:

- SLYD platform/deal context
- leads, matches, deals, or other internal system state exposed by endpoint configuration

HubSpot relevance:

- these feeds can help associate brief items to SLYD-native deal objects before pushing to HubSpot

### Memory Ledger

Source:

- per-user SQLite database

Used for:

- durable open items
- unresolved follow-ups
- recurring commitments
- stale items needing confirmation
- action assignment between teammates

HubSpot relevance:

- this is the best source for tasks and follow-up objects because it is already deduped, statused, and stable

## Output Shape

The LLM output has two layers:

1. A human Slack brief.
2. Structured durable items.

The durable item shape is:

```json
{
  "category": "reply|follow_up|waiting|confirmation|meeting_prep|sell_hardware|buy_hardware|financing|compute_rental|customer_docs|supplier_docs|internal_ops|flag|info",
  "title": "short stable title",
  "summary": "one sentence",
  "owner": "person responsible, if known",
  "counterparty": "customer, supplier, internal team, or contact, if known",
  "source": "email|calendar|slack|slyd|memory|mixed",
  "status": "open|waiting|needs_confirmation|follow_up|info|done",
  "due": "YYYY-MM-DD or null",
  "evidence": "short source clue plus relevant URL if present",
  "confidence": 0.0
}
```

For HubSpot, this structured item layer is more useful than the final Slack message because it already contains category, owner, counterparty, source, status, due text, and evidence.

## Slack Delivery and Interaction Flow

SLYD Brief posts into a configured Slack channel, usually a private briefing channel for the user.

Delivery:

1. `MorningBrief` formats the brief.
2. `SlackClient.PostAsync` posts it with `chat.postMessage`.
3. If the brief is too long, it splits into parts.
4. `SlackClient.PostActionControlsAsync` posts action buttons.

Interaction:

1. User clicks a button or runs `/pulse`.
2. Slack sends the signed request to `SlackOAuthHelper`.
3. Helper validates the request signature.
4. Helper maps Slack user/channel to the correct person env and memory DB.
5. Helper reads or updates the scoped ledger item.
6. Helper responds ephemerally or via delayed Slack response.

## Privacy and Access Model

SLYD Brief is intentionally per-person.

Important privacy properties:

- Each user has their own Slack user token.
- Each user has their own Slack private brief channel.
- Each user has their own mailbox configuration.
- Each user has their own memory database.
- `/pulse` commands are scoped by Slack user/channel.
- Assignment can copy a selected action into another person's ledger, but it does not expose the full source context unless the action text/evidence includes it.

For HubSpot, this means the integration should not assume all Brief data is globally visible. It should preserve owner context and avoid dumping private Slack/DM content into shared CRM records without an explicit policy.

## Current Integration Boundaries

SLYD Brief currently integrates with:

- Microsoft Graph for Outlook email/calendar
- Slack API for message ingestion, posting, slash commands, and interactions
- OpenAI Responses API for synthesis
- optional SLYD JSON HTTP endpoints
- local SQLite for memory
- systemd timers for scheduling

SLYD Brief does not currently directly write to HubSpot.

## Suggested HubSpot Mapping

Recommended approach: integrate from the structured ledger, not raw Slack message text.

Potential mappings:

| SLYD Brief field | HubSpot target |
|---|---|
| `counterparty` | Company, contact, or deal association candidate |
| `owner` | HubSpot task owner or internal user |
| `category` | Task type, note type, or custom property |
| `title` | Task title or note title |
| `summary` | Task body or note body |
| `status` | Task status or custom lifecycle status |
| `due` | Task due date, if parseable |
| `source` | Custom source property |
| `evidence` | Note body, source URL, or custom evidence field |
| `confidence` | Custom confidence property |

Suggested HubSpot objects:

- Tasks for `reply`, `follow_up`, `waiting`, `needs_confirmation`, `meeting_prep`
- Notes for `info`, `flag`, or non-actionable context
- Deal notes for `sell_hardware`, `buy_hardware`, `financing`, `compute_rental`
- Document tasks/notes for `customer_docs` and `supplier_docs`

The integration should dedupe by the stable `item_key` generated by `MemoryStore`. If HubSpot stores the SLYD item key on a task/note/custom object, repeated briefs can update the same HubSpot record instead of creating duplicates.

## HubSpot Integration Cautions

- Do not send raw Slack DMs to HubSpot by default.
- Do not store API keys, Slack tokens, Graph secrets, or OpenAI credentials in HubSpot.
- Use source evidence links carefully; Outlook/Slack links may require user permissions.
- Treat private briefing channels as private user workspaces.
- Use owner/counterparty matching with a human review path when the CRM association is uncertain.
- Preserve the original source system and confidence so users know whether a HubSpot item came from email, Slack, calendar, SLYD feed, memory, or mixed context.

