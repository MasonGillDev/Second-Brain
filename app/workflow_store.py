"""
Workflow Store.

CRUD for workflow definitions, persisted as JSON at config.WORKFLOWS_FILE.
This module only stores and validates definitions; it never runs them (see
workflow_runner.py for execution).

A workflow is a named, parameterized, composable unit:

    {
      "name": "morning_brief",
      "description": "One line: what it does and when to run it.",
      "params": [
        {"name": "date", "required": false, "default": "{{today}}",
         "description": "Day to brief (YYYY-MM-DD)"}
      ],
      "steps": [
        {"id": "events", "tool": "calendar__get_day", "args": {"date": "{{date}}"}},
        {"id": "brief",  "prompt": "Write a 3-sentence brief from:\n{{events}}"}
      ],
      "output": "{{brief}}",               # optional; defaults to last step's output
      "surfaces": {"schedulable": true, "expose_as_tool": true}
    }

Each step is EXACTLY ONE of: tool | prompt | speak | shell | workflow | extract
| stop | foreach. A foreach step nests its own "steps" list, validated with the
same rules.
"""

import json
import os
import re

import config

# snake_case, 1-40 chars — same shape the agent already uses for procedures.
_NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")


def _path() -> str:
    return config.WORKFLOWS_FILE


def load_workflows() -> list[dict]:
    path = _path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_workflows(workflows: list[dict]):
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(workflows, f, indent=2)


def get_workflow(name: str) -> dict | None:
    for w in load_workflows():
        if w.get("name") == name:
            return w
    return None


def validate_workflow(defn: dict) -> list[str]:
    """Return a list of human-readable problems ([] == valid)."""
    if not isinstance(defn, dict):
        return ["definition must be a JSON object"]

    errs: list[str] = []
    if not _NAME_RE.match(defn.get("name") or ""):
        errs.append("name must be snake_case, 1-40 chars of [a-z0-9_]")
    if not defn.get("description"):
        errs.append("description is required (one line: what it does / when to run)")

    for p in defn.get("params", []) or []:
        if not p.get("name"):
            errs.append("each param needs a 'name'")

    trigs = defn.get("triggers")
    if trigs is not None and (not isinstance(trigs, list)
                              or any(not isinstance(t, str) for t in trigs)):
        errs.append("triggers must be a list of strings")

    steps = defn.get("steps") or []
    if not steps:
        errs.append("at least one step is required")
    _validate_steps(steps, errs)
    return errs


_STEP_KINDS = ("tool", "prompt", "speak", "shell", "workflow", "extract", "stop", "foreach")


def _validate_steps(steps: list, errs: list, where: str = "step "):
    """Validate a step list, recursing into foreach bodies. `where` carries the
    dotted position so errors read 'step 2.1: …' for the 1st step inside the
    2nd step's loop body."""
    for i, s in enumerate(steps, 1):
        loc = f"{where}{i}"
        kinds = [k for k in _STEP_KINDS if k in s]
        if len(kinds) != 1:
            errs.append(f"{loc}: must have exactly one of {'|'.join(_STEP_KINDS)} (got {kinds or 'none'})")
        if "speak" in s and not (isinstance(s.get("speak"), str) and s["speak"].strip()):
            errs.append(f"{loc}: speak must be a non-empty string (the text to say)")
        if "shell" in s:
            spec = s.get("shell")
            if not isinstance(spec, dict) or not (spec.get("command") or "").strip():
                errs.append(f"{loc}: shell must be an object with a non-empty 'command'")
        if "when" in s and not isinstance(s.get("when"), str):
            errs.append(f"{loc}: when must be a condition string")
        if "stop" in s and not isinstance(s.get("stop"), dict):
            errs.append(f"{loc}: stop must be an object (optionally with 'when' and 'output')")
        if "tool" in s and "__" not in (s.get("tool") or ""):
            errs.append(f"{loc}: tool must be a namespaced name like 'calendar__get_day'")
        if "extract" in s:
            spec = s.get("extract")
            if not isinstance(spec, dict):
                errs.append(f"{loc}: extract must be an object with 'input' and 'fields'")
            else:
                flds = spec.get("fields") or []
                if not flds:
                    errs.append(f"{loc}: extract needs at least one field")
                elif any(not (isinstance(f, dict) and f.get("id")) for f in flds):
                    errs.append(f"{loc}: each extract field needs an 'id'")
        if "foreach" in s:
            spec = s.get("foreach")
            if not isinstance(spec, dict):
                errs.append(f"{loc}: foreach must be an object with 'items' and 'steps'")
            else:
                items = spec.get("items")
                if not (isinstance(items, list) and items) and not (isinstance(items, str) and items.strip()):
                    errs.append(f"{loc}: foreach needs 'items' — a {{{{var}}}}/text to split or a JSON array")
                body = spec.get("steps")
                if not (isinstance(body, list) and body):
                    errs.append(f"{loc}: foreach needs a non-empty 'steps' list to run per item")
                else:
                    _validate_steps(body, errs, where=f"{where}{i}.")


def upsert_workflow(defn: dict, *, overwrite: bool = True) -> str:
    """Create or replace a workflow. Returns 'created' or 'updated'. Raises
    ValueError with a joined message if the definition is invalid.

    If the definition has no trigger phrases, ~5 are auto-generated (LLM) so the
    agent's semantic workflow-injection can match user requests against phrasings
    that sound like real requests, not just the description. The embedding index
    is resynced after every save."""
    errs = validate_workflow(defn)
    if errs:
        raise ValueError("; ".join(errs))

    if not defn.get("triggers"):
        trigs = generate_triggers(defn)
        if trigs:
            defn["triggers"] = trigs

    workflows = load_workflows()
    action = "created"
    for i, w in enumerate(workflows):
        if w.get("name") == defn["name"]:
            if not overwrite:
                raise ValueError(f"workflow '{defn['name']}' already exists")
            workflows[i] = defn
            action = "updated"
            break
    else:
        workflows.append(defn)
    save_workflows(workflows)
    sync_workflow_index()
    return action


def delete_workflow(name: str) -> bool:
    workflows = load_workflows()
    remaining = [w for w in workflows if w.get("name") != name]
    if len(remaining) == len(workflows):
        return False
    save_workflows(remaining)
    sync_workflow_index()
    return True


# ---------------------------------------------------------------------------
# Trigger phrases + embedding index (semantic workflow injection)
# ---------------------------------------------------------------------------

def generate_triggers(defn: dict) -> list[str]:
    """One cheap LLM call: phrase ~5 things the user might plausibly SAY that
    should run this workflow. Sample utterances embed in the same register as
    real requests, so they match far better than the description alone.
    Non-fatal: returns [] on any failure so a save never breaks over this."""
    try:
        import anthropic
        from keychain import get_secret

        steps_summary = ", ".join(
            s.get("tool") or ("prompt" if "prompt" in s else "speak" if "speak" in s
                              else "shell" if "shell" in s
                              else "extract" if "extract" in s
                              else "foreach-loop" if "foreach" in s
                              else f"workflow:{s.get('workflow')}" if "workflow" in s else "stop")
            for s in defn.get("steps", [])
        )
        prompt = (
            "A personal assistant has a saved workflow it can run:\n"
            f"Name: {defn['name']}\n"
            f"Description: {defn.get('description', '')}\n"
            f"Steps: {steps_summary}\n\n"
            "Write 6 short phrases the user might plausibly say (voice or chat) that "
            "SHOULD run this workflow. Casual, imperative, first-person requests. "
            "IMPORTANT: maximize variety — cover different wordings, synonyms, and "
            "framings of the same intent (including ones that describe the EFFECT, "
            "e.g. 'make it cozy in here' for a lighting workflow). At most 2 may "
            "contain the workflow's name. Output ONLY a JSON array of 6 strings."
        )
        client = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))
        resp = client.messages.create(
            model=config.SUMMARIZATION_MODEL, max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return []
        phrases = json.loads(raw[start:end + 1])
        return [p.strip() for p in phrases if isinstance(p, str) and p.strip()][:8]
    except Exception as e:
        print(f"  [workflows] trigger generation skipped: {e}")
        return []


def sync_workflow_index() -> int:
    """Rebuild the 'workflows' embedding collection from the registry: one entry
    per description + one per trigger phrase, each tagged with its workflow name.
    Separate entries (not one blob) so ANY single phrasing can match strongly.
    Full rebuild — the registry is small and this keeps index == registry.
    Non-fatal: returns -1 if chroma is unreachable."""
    try:
        import chromadb
        client = chromadb.HttpClient(host="127.0.0.1", port=8000)
        client.heartbeat()
        col = client.get_or_create_collection("workflows")
        existing = col.get()
        if existing["ids"]:
            col.delete(ids=existing["ids"])
        docs, metas, ids = [], [], []
        for w in load_workflows():
            entries = [w.get("description", "")] + list(w.get("triggers") or [])
            for i, text in enumerate(t for t in entries if (t or "").strip()):
                docs.append(text.strip())
                metas.append({"workflow": w["name"]})
                ids.append(f"wf_{w['name']}_{i}")
        if docs:
            col.add(documents=docs, metadatas=metas, ids=ids)
        return len(docs)
    except Exception as e:
        print(f"  [workflows] index sync skipped: {e}")
        return -1
