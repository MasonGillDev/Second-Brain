# SLYD Intel System Description

Prepared for HubSpot integration planning.

SLYD Intel is SLYD's self-hosted meeting intelligence system. It is intended to replace Read.ai for SLYD by capturing meetings, recording audio, transcribing calls with diarization, extracting structured sales intelligence, delivering summaries back into Slack/Brief workflows, and exposing a dashboard for call review, governance, and team rollout.

The service lives under:

```text
services/slyd-intel/
```

The public/private app host is Server A. Heavy transcription can run on Server A today and may later expand to the 8x 4090 server. The desktop agent supports local recording for Slack Huddles and other meeting surfaces that do not expose a bot-friendly join URL.

## What SLYD Intel Does

SLYD Intel answers the question: "What happened in the meeting, what commercial signal did it create, and what needs to happen next?"

For each captured call, it:

1. Captures or receives meeting audio.
2. Stores the source audio artifact.
3. Creates a transcription job.
4. Runs transcription and speaker segmentation.
5. Creates an extraction job.
6. Runs deterministic and/or LLM-backed intelligence extraction.
7. Creates a standard call intelligence report.
8. Extracts action items.
9. Calculates routing/handoff metadata.
10. Queues delivery.
11. Delivers eligible summaries to Slack owner routes or holds them if delivery is disabled/misconfigured.
12. Exposes reports, transcripts, lifecycle state, team rollout, integrations, failures, and policy in the dashboard.

## Current Product Capabilities

Current live capabilities include:

- calendar-driven meeting discovery from Outlook
- manual ad-hoc capture by pasting a Teams, Zoom, or Google Meet link
- Meeting BaaS hosted bot capture for Teams, Zoom, and Google Meet paths
- Zoom credential readiness and fallback routing
- desktop capture agent for Slack Huddles and other local audio calls
- audio upload API
- WhisperX transcription provider
- speaker diarization through pyannote when configured
- Claude-backed intelligence extraction through Anthropic
- deterministic fallback extraction
- Slack post-call delivery
- dashboard reports and transcript review
- per-user capture settings
- admin/team rollout visibility
- failure inbox and capture lifecycle diagnostics
- desktop device tokens per user
- call visibility controls by participant/grant/admin
- Windows and macOS desktop beta packages

## Primary Runtime Components

### FastAPI Application

Location:

```text
services/slyd-intel/apps/api/slyd_intel_api/main.py
```

The API serves:

- dashboard HTML at `/dashboard`
- health check at `/health`
- desktop package downloads
- user and device management
- call ingestion
- call search/list/detail
- scheduled meeting listing and capture controls
- ad-hoc meeting capture
- Meeting BaaS webhooks
- transcript retrieval
- intelligence retrieval/regeneration
- integration status
- team rollout
- capture policy
- failure inbox
- reliability/reconciliation endpoints

Important endpoint families:

```text
GET  /dashboard
GET  /health
GET  /v1/me
GET  /v1/users
POST /v1/users
GET  /v1/users/{email}/desktop-devices
POST /v1/users/{email}/desktop-devices
DELETE /v1/desktop-devices/{device_id}
POST /v1/calls
POST /v1/desktop-captures
GET  /v1/calls
GET  /v1/calls/{call_id}
DELETE /v1/calls/{call_id}
GET  /v1/calls/{call_id}/transcript
GET  /v1/calls/{call_id}/intelligence
POST /v1/calls/{call_id}/intelligence/regenerate
GET  /v1/meetings
POST /v1/meetings/{meeting_id}/capture-jobs
POST /v1/ad-hoc-captures
POST /v1/meeting-intakes
GET  /v1/meeting-intakes
GET  /v1/integration-hub/status
GET  /v1/zoom/readiness
GET  /v1/capture-jobs
GET  /v1/capture-jobs/{job_id}/lifecycle
POST /v1/capture-jobs/{job_id}/retry
POST /v1/capture-jobs/{job_id}/stop
POST /v1/capture-webhooks/{provider}
GET  /v1/brief-feed
GET  /v1/intelligence/search
GET  /v1/team-rollout
GET  /v1/capture-policy
GET  /v1/failure-inbox
GET  /v1/reliability/status
```

For HubSpot, the most relevant endpoints are:

- `GET /v1/calls`
- `GET /v1/calls/{call_id}`
- `GET /v1/calls/{call_id}/transcript`
- `GET /v1/calls/{call_id}/intelligence`
- `GET /v1/brief-feed`
- `GET /v1/intelligence/search`

### Database and Storage

SLYD Intel uses Postgres for application state and file/object storage for audio artifacts.

Main record types:

- users
- desktop devices
- calls
- call participants
- call access grants
- call artifacts
- speakers
- transcript segments
- intelligence reports
- call action items
- jobs
- scheduled meetings
- scheduled meeting participants
- calendar sync runs
- capture jobs
- capture job events
- user capture settings
- audit events
- failure inbox resolutions

The stored audio artifact is linked to the call record as `source_audio`. Transcription and intelligence artifacts are represented in relational tables and structured JSON fields.

### Outlook Calendar Sync

Location:

```text
services/slyd-intel/scripts/sync-outlook-calendar.py
services/slyd-intel/apps/api/slyd_intel_api/graph_calendar.py
```

SLYD Intel reads Outlook calendar through Microsoft Graph application credentials.

Graph calendar fields pulled:

- event ID
- iCal UID
- subject
- start
- end
- location
- online meeting status
- cancellation state
- online meeting join URL
- web link
- organizer
- attendees
- body preview
- sensitivity

The sync job upserts `ScheduledMeeting` records and `ScheduledMeetingParticipant` records.

It also evaluates capture policy at sync time using:

- mailbox owner
- subject
- organizer
- participants
- cancellation state
- online meeting state
- join URL
- Outlook sensitivity
- domain allowlist
- sensitive keyword list
- per-user capture settings

Calendar sync does not record audio. It creates capture candidates and policy decisions. Capture jobs are created later by the scheduler, operator queue action, or ad-hoc intake.

### Capture Policy

The capture policy determines whether a meeting is eligible.

Typical rules:

- cancelled meetings are ignored
- non-online meetings are ignored
- meetings without join URLs are not capturable by hosted bot
- sensitive/private/HR/legal/medical/confidential keywords are excluded
- capture can be paused per user
- users can allow owned meetings and/or external meetings
- SLYD domain logic distinguishes internal/external behavior
- Zoom may require configured Meeting BaaS OBF/user authorization credentials

This matters for HubSpot because not every calendar event becomes a call report. Only captured calls produce transcript/intelligence records.

### Meeting Intake and Ad-Hoc Capture

Operators can paste a meeting URL into the dashboard for immediate capture.

The ad-hoc flow:

1. User submits meeting URL, title, owner email, and expected duration.
2. API detects platform from the URL.
3. API creates an ad-hoc `ScheduledMeeting`.
4. API creates a `CaptureJob`.
5. Capture worker launches the hosted bot through Meeting BaaS.

This supports meetings that were not on the calendar or were launched manually.

### Hosted Bot Capture with Meeting BaaS

Location:

```text
services/slyd-intel/apps/api/slyd_intel_api/capture_provider.py
services/slyd-intel/apps/api/slyd_intel_api/capture_worker.py
```

SLYD Intel uses Meeting BaaS as the hosted meeting bot provider.

When a capture job is due, the capture worker:

1. Claims a queued capture job.
2. Builds a Meeting BaaS `/v2/bots` request.
3. Sends meeting URL, bot name, recording mode, timeout config, entry message, callback config, and metadata.
4. Adds Zoom credential configuration when the meeting is Zoom and a credential ID is available.
5. Stores the provider bot ID.
6. Tracks provider state as joining, recording, uploading, submitted, failed, or cancelled.

Meeting BaaS request includes:

- `bot_name`
- `meeting_url`
- `allow_multiple_bots`
- `recording_mode`
- `entry_message`
- timeout configuration
- callback URL
- callback secret
- metadata linking back to SLYD Intel capture job and scheduled meeting
- optional `zoom_config.credential_id`

Meeting BaaS sends callbacks to:

```text
POST /v1/capture-webhooks/meetingbaas
```

The API validates the callback secret and maps the provider bot ID back to the SLYD capture job.

When Meeting BaaS completes with an audio URL:

1. SLYD Intel downloads the audio.
2. Creates a `Call` record.
3. Stores the audio as a `source_audio` artifact.
4. Carries over meeting metadata and participants.
5. Creates a transcription job.
6. Marks meeting/capture status as recorded/submitted.

### Zoom Handling

Zoom requires extra care because bot joins depend on Zoom's current authentication and on-behalf-of behavior.

SLYD Intel tracks:

- global Meeting BaaS Zoom credential ID
- per-user Zoom credential IDs
- credential source
- credential owner email
- whether a meeting is internal or external
- fallback readiness
- whether external Zoom meetings require OBF/user authorization

Dashboard surfaces show Zoom readiness and credential source.

HubSpot does not need Zoom credentials. HubSpot only needs to know that Zoom source calls may have provider metadata and that failures can occur before a call exists.

### Desktop Capture Agent

Location:

```text
services/slyd-intel/capture/desktop/
```

The desktop capture agent supports local capture and upload for meeting surfaces that cannot reliably host a bot:

- Slack Huddles
- phone calls
- browser/app calls without a stable bot join path
- other ad-hoc audio conversations

The desktop agent can:

- configure API URL, token, owner email, and default platform
- list audio devices
- upload existing recordings
- record local audio and upload it
- use Windows WASAPI loopback where available
- run through the Tauri desktop app UI

Desktop uploads call:

```text
POST /v1/desktop-captures
```

The desktop API token is a per-user device token, not the global admin API token. Devices can be created and revoked through:

```text
POST   /v1/users/{email}/desktop-devices
DELETE /v1/desktop-devices/{device_id}
```

For HubSpot, desktop captures should be treated as calls owned by the desktop token's user unless the report or participants provide a better owner.

### Call Ingestion

Location:

```text
services/slyd-intel/apps/api/slyd_intel_api/call_ingest.py
```

All ingestion paths converge into a call creation function.

Allowed source types:

- `manual_upload`
- `bot`
- `desktop`

Created records:

- `Call`
- `CallArtifact` of type `source_audio`
- `CallParticipant` rows when participants are known
- queued `Job` of type `transcription`

This convergence is important for HubSpot: whether the source was Teams, Zoom, Google Meet, Slack Huddle, desktop recording, or manual upload, the downstream call/intelligence shape is the same.

### Transcription Worker

Location:

```text
services/slyd-intel/workers/transcription/
```

The transcription worker:

1. Claims a queued transcription job.
2. Loads the call's `source_audio` artifact.
3. Runs the configured transcription provider.
4. Writes speakers.
5. Writes transcript segments.
6. Marks the call `transcribed`.
7. Creates a queued extraction job.

Supported providers:

- `stub`
- `whisperx`

WhisperX provider configuration:

- device, usually CUDA
- model, currently intended for `large-v3`
- compute type, usually `float16`
- batch size
- diarization flag
- pyannote token for diarization

Transcript segment fields:

- call ID
- speaker ID
- speaker label
- start ms
- end ms
- text
- confidence
- segment index

For HubSpot, transcript segments can be stored as a call transcript artifact, summarized into notes, or linked back via SLYD Intel dashboard URL rather than copied wholesale.

### Intelligence Extraction Worker

Location:

```text
services/slyd-intel/workers/intelligence/
services/slyd-intel/apps/api/slyd_intel_api/intelligence_provider.py
```

The intelligence worker:

1. Claims a queued extraction job.
2. Loads transcript segments in order.
3. Runs the configured intelligence provider.
4. Creates or updates a standard `CallIntelligenceReport`.
5. Replaces action items for the report.
6. Applies handoff/routing metadata.
7. Creates a delivery job.
8. Marks the call `analyzed`.

Supported providers:

- deterministic
- OpenAI-compatible chat completion
- Anthropic/Claude

The deterministic provider extracts:

- executive summary
- brief-ready summary
- speaker count and speaker labels
- suspected company/customer
- deal stage
- urgency
- competitors
- objections
- pricing/budget mentions
- power/energy signals
- compute requirements
- next steps
- evidence quotes
- routing priority
- recommended follow-up

The LLM-backed providers use the deterministic report as a scaffold and ask the model to produce a more enterprise-grade structured report. If LLM extraction fails, SLYD Intel falls back to deterministic extraction and records the LLM error in structured JSON.

Current Claude/Anthropic settings include:

- `SLYD_INTEL_INTELLIGENCE_PROVIDER=anthropic`
- `SLYD_INTEL_INTELLIGENCE_MODEL`
- `SLYD_INTEL_INTELLIGENCE_ANTHROPIC_API_KEY`
- `SLYD_INTEL_INTELLIGENCE_ANTHROPIC_BASE_URL`
- `SLYD_INTEL_INTELLIGENCE_ANTHROPIC_VERSION`
- `SLYD_INTEL_INTELLIGENCE_ANTHROPIC_MAX_TOKENS`
- transcript character limit

### Handoff and Routing

Location:

```text
services/slyd-intel/apps/api/slyd_intel_api/handoff.py
```

After extraction, SLYD Intel materializes handoff metadata into the report.

Handoff fields:

- schema version
- generated time
- brief readiness
- brief priority
- brief threshold
- pulse/action readiness
- action count
- owner name
- owner email
- dashboard URL
- control hints

Owner selection:

1. Prefer organizer participant.
2. Else prefer a participant with `slyd.com` email.
3. Else use first participant with an email or display name.
4. Else owner is unknown.

Priority routing:

- `brief_min_priority`
- `action_min_priority`
- priority levels: low, medium, high

This is one of the most important HubSpot integration points. The handoff layer tells downstream systems whether a call is ready for brief/CRM routing and who should own it.

### Slack Delivery Worker

Location:

```text
services/slyd-intel/workers/delivery/
services/slyd-intel/apps/api/slyd_intel_api/delivery.py
```

The delivery worker:

1. Claims a queued delivery job.
2. Loads the analyzed call and report.
3. Loads action items.
4. Reads handoff delivery owner.
5. Resolves a route.
6. Sends to Slack if delivery is enabled and a route exists.
7. Stores delivery result back into report structured JSON.
8. Writes audit event.

Routes can come from:

- per-user default owner route in user capture settings
- `SLYD_INTEL_SLACK_OWNER_ROUTES_JSON`
- `SLYD_INTEL_SLACK_DEFAULT_CHANNEL`

If delivery is disabled, missing route, or missing Slack sender token, the delivery result is held rather than sent.

Slack delivery message includes:

- call title
- priority
- brief-ready summary
- up to five action items
- dashboard link to transcript/report
- note that controls live in SLYD Intel

This Slack delivery is how SLYD Intel connects back into the existing SLYD Brief/Pulse workflow today. It is also the natural point for HubSpot insertion.

## Dashboard

Location:

```text
services/slyd-intel/apps/dashboard/index.html
```

The dashboard includes:

- Reports
- Incomplete/failures
- Calendar/upcoming meetings
- Live capture/ad-hoc capture
- Integrations
- Team rollout
- Capture policy
- Failure inbox
- Report detail panel with summary, action items, transcript, and delivery state
- Capture lifecycle timeline
- Zoom readiness
- Desktop device and team rollout views

The dashboard uses the API token or desktop/user token to call the FastAPI endpoints.

## Authentication and Access Control

Location:

```text
services/slyd-intel/apps/api/slyd_intel_api/auth.py
services/slyd-intel/apps/api/slyd_intel_api/access_control.py
```

SLYD Intel supports two main auth paths:

1. System/admin API token.
2. Per-user desktop device token.

The system token grants admin role.

Desktop device token flow:

1. Admin/user creates a desktop device for an email.
2. API generates a `slyd_device_...` token.
3. API stores only a SHA-256 token hash.
4. Desktop app uses the token in `X-SLYD-Intel-Key` or bearer auth.
5. API maps token to `DesktopDevice` and `AppUser`.
6. API updates `last_seen_at`.

Call visibility:

- admins can see all calls
- non-admin users can see calls where they are a participant
- non-admin users can see calls explicitly granted to them
- otherwise the call is hidden with a not-found response

This matters for HubSpot because CRM sync should respect SLYD Intel visibility and ownership rules. Super-admin sync can move data globally, but user-facing CRM views should avoid exposing private call content to users who were not in the meeting.

## External Integrations

SLYD Intel currently integrates with:

- Microsoft Graph for Outlook calendar sync
- Meeting BaaS for hosted meeting bot capture
- Microsoft Teams through Meeting BaaS bot join
- Zoom through Meeting BaaS plus Zoom credential routing
- Google Meet through Meeting BaaS bot join
- Slack for post-call delivery
- WhisperX for transcription
- pyannote for diarization when enabled
- Anthropic/Claude for intelligence extraction
- OpenAI-compatible provider option for intelligence extraction
- Cloudflare tunnel for public ingress/downloads
- local desktop app for Slack Huddles and local recording
- GitHub Actions hosted macOS runner for Mac desktop build

SLYD Intel does not currently directly write to HubSpot.

## Core Data Flow

### Calendar-Based Hosted Bot Capture

```text
Outlook calendar -> Microsoft Graph sync -> ScheduledMeeting
ScheduledMeeting -> capture policy -> eligible meeting
eligible meeting -> capture scheduler -> CaptureJob
CaptureJob -> capture worker -> Meeting BaaS bot
Meeting BaaS bot -> meeting recording -> callback
callback -> audio download -> Call + source_audio artifact
Call -> transcription job -> transcript segments
transcript -> extraction job -> intelligence report + action items
report -> handoff -> delivery job
delivery job -> Slack owner route or held state
```

### Ad-Hoc Hosted Bot Capture

```text
Dashboard meeting URL -> meeting intake -> ad-hoc ScheduledMeeting
ad-hoc ScheduledMeeting -> CaptureJob -> Meeting BaaS bot
Meeting BaaS callback -> Call -> transcript -> intelligence -> delivery
```

### Desktop/Slack Huddle Capture

```text
Desktop app records or uploads audio
Desktop app -> POST /v1/desktop-captures
API authenticates device token
API creates Call + source_audio artifact
Call -> transcription job -> transcript segments
transcript -> extraction job -> intelligence report + action items
report -> handoff -> delivery job
```

## Structured Intelligence Output

The standard call intelligence report stores:

- `summary_text`
- `structured_json`
- action item rows

Expected structured JSON includes:

```json
{
  "schema_version": "slyd-intel-call-v1",
  "provider": "anthropic|openai|deterministic|deterministic_fallback",
  "confidence": 0.0,
  "executive_summary": "...",
  "brief_ready_summary": "...",
  "participants": {
    "speaker_count": 2,
    "speakers": ["SPEAKER_00", "SPEAKER_01"]
  },
  "deal": {
    "customer_or_company": "...",
    "stage": "...",
    "urgency": "..."
  },
  "signals": {
    "competitors": [],
    "objections": [],
    "pricing_budget": [],
    "power_energy": [],
    "compute_requirements": [],
    "next_steps": []
  },
  "evidence": {
    "segment_count": 0,
    "key_quotes": []
  },
  "routing": {
    "brief_priority": "low|medium|high",
    "recommended_follow_up": "...",
    "brief_handoff_state": "ready|held",
    "pulse_handoff_state": "ready|held",
    "handoff_generated_at": "..."
  },
  "handoff": {
    "schema_version": "slyd-intel-handoff-v1",
    "brief": {},
    "pulse": {},
    "delivery": {}
  }
}
```

Action item rows include:

- description
- owner name
- due text
- source transcript segment ID

## Suggested HubSpot Mapping

Recommended approach: integrate from SLYD Intel's structured report and handoff layer, not raw audio or raw transcript as the primary source.

Potential mappings:

| SLYD Intel field | HubSpot target |
|---|---|
| `Call.title` | Call/meeting engagement title |
| `Call.started_at`, `Call.ended_at` | Engagement time |
| `Call.source_type` | Custom source property |
| `Call.source_external_id` | External system ID |
| `Call.calendar_event_id` | External calendar event ID |
| `CallParticipant.email` | Contact association |
| `CallParticipant.display_name` | Contact candidate |
| `CallIntelligenceReport.summary_text` | Call summary/note body |
| `structured_json.brief_ready_summary` | Executive note body |
| `structured_json.deal.customer_or_company` | Company/deal association candidate |
| `structured_json.deal.stage` | Deal stage signal/custom property |
| `structured_json.deal.urgency` | Deal urgency/custom property |
| `structured_json.signals.competitors` | Competitor mentions/custom object or note |
| `structured_json.signals.objections` | Objection tracking/custom object or note |
| `structured_json.signals.pricing_budget` | Budget/pricing note |
| `structured_json.signals.power_energy` | Energy/site requirement note |
| `structured_json.signals.compute_requirements` | Compute requirement note |
| `CallActionItem.description` | HubSpot task body |
| `CallActionItem.owner_name` | Task owner candidate |
| `CallActionItem.due_text` | Task due date candidate |
| `handoff.delivery.owner_email` | HubSpot owner/association candidate |
| `handoff.delivery.dashboard_url` | External link back to SLYD Intel |
| `routing.brief_priority` | Priority/custom property |

Recommended HubSpot records:

- HubSpot call engagement for each analyzed SLYD Intel call
- HubSpot note for the executive/brief-ready summary
- HubSpot tasks for action items
- Optional custom object for call intelligence signals
- Optional custom object for meeting capture metadata/failures

Recommended dedupe keys:

- `Call.id` as the primary SLYD Intel call ID
- `Call.source_external_id` for bot/desktop provider source linkage
- `Call.calendar_event_id` for Outlook meeting linkage
- `CallActionItem.id` for task sync
- report `schema_version` and `updated_at` for update logic

## HubSpot Integration Cautions

- Do not push raw audio to HubSpot.
- Avoid pushing full transcripts by default; link back to SLYD Intel unless a specific CRM use case requires transcript storage.
- Preserve access control. Non-admin users should not see calls they did not participate in unless explicitly granted.
- Treat Slack Huddle/desktop captures as potentially sensitive because they may include informal or internal calls.
- Treat low-confidence company/contact inference as a candidate, not an automatic association.
- Use the handoff owner and participants to route ownership, but allow manual correction.
- Store SLYD Intel dashboard URL on HubSpot records for review/delete/control.
- Do not store Meeting BaaS, Zoom, Slack, Graph, Anthropic, OpenAI, or desktop device credentials in HubSpot.
- If HubSpot becomes a delivery target, write the HubSpot sync result back into SLYD Intel report structured JSON or audit events so the system has a durable sync trail.

## Best HubSpot Integration Entry Point

The best first sync is:

1. Poll or subscribe to analyzed calls.
2. Fetch call detail.
3. Fetch intelligence report.
4. Fetch transcript only if needed.
5. Map participants to contacts.
6. Map company/deal candidates from structured intelligence.
7. Create/update HubSpot call engagement.
8. Create/update HubSpot tasks from action items.
9. Store SLYD Intel IDs on HubSpot records for idempotency.
10. Store HubSpot IDs back into SLYD Intel in a future sync/audit table.

This keeps HubSpot focused on CRM-grade activity and follow-up, while SLYD Intel remains the source of truth for raw meeting intelligence, transcript, capture lifecycle, and governance.

