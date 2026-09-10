"""
First-party seed procedures.

These are the procedures the agent's routing doctrine depends on (see the
"## Procedures" section of the system prompt): when a request has no saved
procedure, the agent lands on create_procedure, which branches into
create_workflow and create_trigger. Everything else in procedural memory is
expected to be built BY the agent through these — so they ship as code, not as
hand-typed ChromaDB rows: version-controlled, reviewable, and re-synced on
every startup so an edit here is an edit everywhere.

Stored in the 'procedural' collection under deterministic ids (proc_<name>),
in the same text format save_procedure uses, so retrieval, list_procedures,
and get_procedure treat them exactly like agent-saved procedures. Metadata
type 'first_party' marks them as code-owned: they are overwritten on every
sync, so never edit them through save_procedure — edit this file.
"""

SEED_PROCEDURES = [
    {
        "name": "create_procedure",
        "description": (
            "When a request needs more than one obvious tool call and no saved "
            "procedure covers it — or the user asks to save how something was done."
        ),
        "steps": """\
1. Ask the user FIRST: "There's no procedure for this yet — want me to create one while I work it out?" If they say no, just do the task normally and stop here.
2. DISCOVERY — figure out how to do the task, recording every step that works as you go:
   - list_procedures: a related procedure may cover part of it (nest it later as "Run procedure: <name>").
   - search_memory / search_documents: prior context about this task.
   - workflows__list_workflows: an existing workflow may already automate part of it.
   - Then work the task with tools. Keep a running record of each ACTION THAT WORKED: the exact tool name (server__tool), the argument shapes, and any decision made along the way.
3. Keep working with the user until THEY explicitly say the task is complete. Never declare completion yourself — corrections mid-task are part of discovery and belong in the record.
4. Draft the steps from the record: numbered, imperative, one action per step. Reference exact tool names (server__tool), workflows as run_workflow("<name>", params), and other procedures as "Run procedure: <name>". Include decision points ("if X, skip to step N") and how to verify success. Leave out the dead ends.
5. Name it: snake_case, under 40 chars, literally naming the task (open_followup_sessions, not session_helper). Description: ONE sentence stating WHEN to use it — the trigger condition, not what it does.
6. Save with save_procedure(name, description, steps), then show the user exactly what was saved.
7. Ask: "Want me to create a workflow to streamline this so it's one call next time?" If yes, run procedure: create_workflow.""",
    },
    {
        "name": "create_workflow",
        "description": (
            "When a solved task is a repeatable, deterministic tool sequence the "
            "user wants runnable as a single call (or on a schedule/trigger)."
        ),
        "steps": """\
1. Confirm the sequence is deterministic: same inputs, same steps, no mid-flow judgment. Judgment stays in the PROCEDURE that decides when to run the workflow, or inside prompt/extract steps.
2. workflows__list_workflows first — reuse or compose before building: a step can be {"workflow": "<name>", "args": {...}}.
3. Design params: every value that changes run-to-run becomes a param, referenced as {{name}} in steps. Mark required ones and give each a one-line description.
4. For anything beyond a few steps, pick the 1-2 existing workflows most similar in shape to what you're building (from the list in step 2) and read their JSON with workflows__get_workflow — pattern-match real definitions rather than inventing structure.
5. Build the steps. Kinds (full shapes in the workflows__create_workflow tool doc): tool, prompt (isolated LLM), speak, shell, extract (LLM -> variables), stop, workflow, foreach. Core patterns:
   - guard / early-exit: {"stop": {"when": "{{x}} is empty", "output": "Nothing to do."}}
   - loop: {"foreach": {"items": "{{ids}}", "as": "id", "steps": [...]}} — items is a JSON array, one-per-line, or comma-separated text; body sees {{id}}, {{loop_index}}, {{loop_total}}
   - prefer a shell step (grep/awk) over extract when the input format is machine-written; use extract for messy or human-written text
6. Example — extraction, guard, then a sub-workflow over the result:
   {"name": "open_followup_sessions", "description": "...", "params": [],
    "steps": [
      {"id": "ids", "shell": {"command": "awk '...' /path/timeline.md"}},
      {"stop": {"when": "{{ids}} is empty", "output": "No follow-ups."}},
      {"workflow": "open_claude_sessions", "args": {"session_ids": "{{ids}}"}}],
    "output": "{{step3}}", "surfaces": {"expose_as_tool": true}}
7. Create with workflows__create_workflow(definition as a JSON string). If it returns validation errors, fix and resubmit.
8. TEST before reporting success: workflows__run_workflow with bogus/safe params when steps have side effects (a guard should stop it), real params otherwise. Verify the output is what the user expects.
9. Surfaces: expose_as_tool true so you can call it from conversation; schedulable true only if it should run on a cron schedule.
10. Ask: "Should this fire automatically on an event or condition?" If yes, run procedure: create_trigger. If the task that produced this workflow has no procedure yet, run procedure: create_procedure to record when to use it.""",
    },
    {
        "name": "create_trigger",
        "description": (
            "When the user wants something to happen automatically on an external "
            "event or a watched condition, without them asking each time."
        ),
        "steps": """\
1. Pick the source:
   - webhook: an external system can POST to us (iOS Shortcut, service callback). Fires at /hooks/<name> with a per-trigger secret.
   - poll: we must check something on an interval: {"type": "poll", "interval_seconds": <min 30>, "watch": {"url": "..."} or {"tool": "server__tool", "args": {...}}, "fire_on": "change" or "condition"} (condition example: "{{output}} contains X").
2. The action MUST be a workflow. A trigger fires repeatedly and unattended, so what it runs must be deterministic and tested — that is exactly what workflows are for. If the workflow doesn't exist yet, run procedure: create_workflow FIRST, then wire it in: {"type": "workflow", "workflow": "<name>", "args": {...}} with {{payload.*}} interpolated into args. Only use a prompt action ({"type": "prompt", "prompt": "..."}) if the user explicitly asks for judgment on each firing.
3. Optional hardening: "filter" — a condition on {{payload.*}} so only matching events fire; "debounce_seconds" for chatty sources.
4. Sinks — where the result goes: telegram (default), voice, or silent.
5. Create with triggers__create_trigger(definition as a JSON string). It returns the webhook URL + secret — give these to the user for whatever integration will call it.
6. Test-fire: tell the user you're about to, then POST to /hooks/<name> (works for poll triggers too — every trigger gets a manual test path) and confirm the action ran and the result reached the sink.
7. If the setup revealed a reusable pattern, run procedure: create_procedure to record it.""",
    },
]


def sync_seed_procedures(vector_store) -> int:
    """(Re)write every seed into the procedural collection. Delete-then-add
    under the deterministic id, so edits to this file land on next startup and
    duplicates can't accumulate. Returns how many were synced; per-procedure
    failures are printed, not raised — a down ChromaDB must not stop the brain
    from starting."""
    synced = 0
    for proc in SEED_PROCEDURES:
        try:
            doc_id = f"proc_{proc['name']}"
            text = (f"Procedure: {proc['name']}\n"
                    f"Description: {proc['description']}\n"
                    f"Steps:\n{proc['steps']}")
            vector_store.delete("procedural", doc_id)
            vector_store.add(
                "procedural", text,
                {"name": proc["name"], "description": proc["description"],
                 "type": "first_party"},
                doc_id=doc_id,
            )
            synced += 1
        except Exception as e:
            print(f"  [procedures] seed sync failed for '{proc['name']}': {e}")
    return synced
