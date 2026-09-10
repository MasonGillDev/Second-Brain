"""
Composio MCP Server.

Gives the agent access to Composio's 1000+ app integrations (GitHub, Gmail,
Slack, and many more) through Composio's Python SDK. This replaces the old
ToolGate MCP server as the agent's gateway to external app actions.

Design: rather than inject hundreds of per-app tool schemas (which would blow
the agent's token budget), this server exposes a small set of *meta-tools*. The
agent searches Composio's catalog for the right tool, then executes it by slug —
mirroring the project's tiered tool-injection philosophy.

  - composio_search_tools : find tool slugs in the catalog (optionally per app)
  - composio_execute      : run a tool by slug with a JSON arguments object
  - composio_authorize    : start an OAuth connection for an app (returns a link)
  - composio_list_connections : show which app accounts are connected

All connections are scoped to a single user id (COMPOSIO_USER_ID) since this is
a personal, single-user agent. Requires COMPOSIO_API_KEY (env or, via config.py,
the macOS Keychain entry 'composio-api-key').
"""

import os
import sys
import json
import contextlib

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("composio")

API_KEY = os.environ.get("COMPOSIO_API_KEY", "").strip()
# Composio scopes every connection to a user id. One id for this single-user agent.
USER_ID = os.environ.get("COMPOSIO_USER_ID", "default").strip() or "default"

# Lazily-built Composio client — kept as a module global so we only construct it
# once, and so the server still starts (and returns a clean error) when the key
# isn't configured yet.
_client = None


class ComposioError(Exception):
    """A user-facing error to surface back to the agent as a tool result."""


def _get_client():
    """Build (once) and return the Composio SDK client, or raise a clean error."""
    global _client
    if _client is not None:
        return _client
    if not API_KEY:
        raise ComposioError(
            "Composio isn't configured. Set the COMPOSIO_API_KEY (the agent reads "
            "it from the macOS Keychain entry 'composio-api-key'), then restart."
        )
    # This is a stdio MCP server: stdout carries the JSON-RPC protocol, so any
    # stray prints from the SDK during import/init must go to stderr instead.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            from composio import Composio
            _client = Composio(api_key=API_KEY)
    except ImportError:
        raise ComposioError(
            "The 'composio' package isn't installed. Run: pip install composio"
        )
    except Exception as e:  # noqa: BLE001 - surface any SDK init failure cleanly
        raise ComposioError(f"Couldn't initialize the Composio client: {e}")
    return _client


def _extract_id(obj):
    """Pull an id off a model or dict (handles .id / .nanoid / .uuid)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("id") or obj.get("nanoid") or obj.get("uuid")
    return getattr(obj, "id", None) or getattr(obj, "nanoid", None) or getattr(obj, "uuid", None)


def _toolkit_name(tool) -> str:
    """Best-effort display name for a tool's toolkit (shape varies by SDK)."""
    tk = getattr(tool, "toolkit", None)
    if tk is None:
        return ""
    for attr in ("slug", "name"):
        val = getattr(tk, attr, None)
        if val:
            return str(val)
    return str(tk)


def _input_schema(tool):
    """A tool's input_parameters JSON schema as a dict (or {})."""
    ip = getattr(tool, "input_parameters", None)
    return ip if isinstance(ip, dict) else {}


def _params_summary(tool) -> str:
    """One-line required/optional arg summary so the agent picks the right tool
    and supplies correct arguments (the #1 cause of failed executions)."""
    schema = _input_schema(tool)
    props = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []
    if not props:
        return "args: none — call with arguments={}"
    optional = [k for k in props if k not in required]
    req_str = ", ".join(required) if required else "none"
    out = f"args — required: {req_str}"
    if optional:
        preview = ", ".join(optional[:6]) + (" …" if len(optional) > 6 else "")
        out += f"  ·  optional: {preview}"
    return out


# Headline fields tried in order to label a list item compactly.
_ITEM_LABEL_KEYS = (
    "full_name", "name", "title", "subject", "slug", "login", "path",
    "key", "display_name", "email", "filename",
)
# Short notable fields appended after the label, when present.
_ITEM_FLAG_KEYS = ("state", "status", "visibility", "type")
_ITEM_BOOL_KEYS = ("private", "draft", "merged", "archived", "fork")
# Max list items rendered in a summary (the rest are counted, not dropped silently).
_SUMMARY_ITEM_CAP = 60


def _compact_item(item) -> str:
    """One short line describing a single list item (a dict, usually)."""
    if not isinstance(item, dict):
        return str(item)[:120]
    label = None
    for k in _ITEM_LABEL_KEYS:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            label = v.strip()
            break
    if label is None:
        for k in ("number", "id", "sha"):
            if item.get(k) is not None:
                label = f"{k} {str(item[k])[:12]}"
                break
    if label is None:
        label = ", ".join(list(item.keys())[:3]) or "(item)"
    extras = [str(item[k]) for k in _ITEM_FLAG_KEYS if isinstance(item.get(k), (str, int)) and str(item[k]).strip()]
    extras += [k for k in _ITEM_BOOL_KEYS if item.get(k) is True]
    # Dedupe (e.g. visibility="private" + private=True both say "private").
    seen, deduped = set(), []
    for x in extras:
        if x.lower() not in seen:
            seen.add(x.lower())
            deduped.append(x)
    return f"{label}" + (f" ({', '.join(deduped)})" if deduped else "")


def _summarize_list_result(data):
    """If `data` holds a large list of objects (e.g. repos, issues, emails),
    return a compact multi-line summary string. Returns None when there's no
    big list (caller then renders the raw JSON). This is the fix for verbose
    API payloads blowing the token budget / getting hard-truncated mid-JSON."""
    list_key, lst = None, None
    if isinstance(data, list):
        lst = data
    elif isinstance(data, dict):
        best = None  # the longest list-of-objects value in the dict
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], (dict, str)):
                if best is None or len(v) > len(best[1]):
                    best = (k, v)
        if best:
            list_key, lst = best
    if lst is None:
        return None
    # Small results are fine raw — only summarize when it'd otherwise be bulky.
    try:
        raw_len = len(json.dumps(lst, default=str))
    except (TypeError, ValueError):
        raw_len = 10_000
    if raw_len <= 2000 and len(lst) <= 15:
        return None

    lines = [f"- {_compact_item(it)}" for it in lst[:_SUMMARY_ITEM_CAP]]
    header = f"{len(lst)} item(s)" + (f" in '{list_key}'" if list_key else "") + ":"
    # Surface sibling scalar fields (e.g. total_count) for context.
    prefix = ""
    if isinstance(data, dict):
        scalars = {
            k: v for k, v in data.items()
            if k != list_key and isinstance(v, (str, int, float, bool)) and str(v) != ""
        }
        if scalars:
            prefix = "  ".join(f"{k}={v}" for k, v in list(scalars.items())[:5]) + "\n"
    more = f"\n… ({len(lst) - _SUMMARY_ITEM_CAP} more not shown)" if len(lst) > _SUMMARY_ITEM_CAP else ""
    note = ("\n(Compact summary — the full objects were large. For more detail on one "
            "item, use a more specific tool, e.g. a GET_*/get-by-id slug.)")
    return prefix + header + "\n" + "\n".join(lines) + more + note


# ---------------------------------------------------------------------------
# Meta-tools
# ---------------------------------------------------------------------------

@mcp.tool()
def composio_search_tools(query: str, toolkits: str = "", limit: int = 10) -> str:
    """
    Search Composio's catalog for tools that can perform an action, returning
    their slugs so you can run them with composio_execute.

    Use this first whenever you need to act on an external app (e.g. "create a
    GitHub issue", "send an email", "post to Slack"). Search by what you want to
    DO, not just the app name.

    Args:
        query: What you want to do, in plain words (e.g. "create issue",
               "send email", "list pull requests").
        toolkits: Optional comma-separated app slugs to restrict the search to
                  (e.g. "github" or "github,gmail,slack"). Leave empty to search
                  all apps.
        limit: Max number of tools to return (default 10).
    """
    try:
        client = _get_client()
    except ComposioError as e:
        return str(e)

    tk_list = [t.strip().lower() for t in toolkits.split(",") if t.strip()] or None
    try:
        tools = client.tools.get_raw_composio_tools(
            search=query or None,
            toolkits=tk_list,
            limit=limit if limit and limit > 0 else 10,
        )
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] Composio tool search failed: {e}"

    if not tools:
        scope = f" in {toolkits}" if toolkits else ""
        return f"No Composio tools found for '{query}'{scope}."

    lines = [f"Found {len(tools)} tool(s) — run one with composio_execute(slug, arguments):\n"]
    for t in tools:
        slug = getattr(t, "slug", "") or getattr(t, "name", "")
        tk = _toolkit_name(t)
        desc = (getattr(t, "description", "") or "").strip().split("\n")[0]
        no_auth = getattr(t, "no_auth", False)
        auth_note = "" if no_auth else "  (needs a connected account)"
        head = f"- {slug}" + (f"  [{tk}]" if tk else "") + auth_note
        lines.append(head)
        if desc:
            lines.append(f"    {desc}")
        lines.append(f"    {_params_summary(t)}")
    lines.append(
        "\nPrefer the tool whose required args you can satisfy (a tool needing only "
        "optional args is callable with arguments={}). For a slug's full argument "
        "schema, call composio_get_tool(slug)."
    )
    return "\n".join(lines)


@mcp.tool()
def composio_get_tool(slug: str) -> str:
    """
    Show a Composio tool's exact input arguments — each parameter's name, type,
    whether it's required, default, and description — so you can call
    composio_execute with correct arguments.

    Use this when you're unsure what a tool needs, or when composio_execute
    returns a "missing field" / "invalid request" error.

    Args:
        slug: The tool slug, e.g. "GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER".
    """
    try:
        client = _get_client()
    except ComposioError as e:
        return str(e)

    try:
        tools = client.tools.get_raw_composio_tools(tools=[slug.strip()])
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] Couldn't fetch tool '{slug}': {e}"
    if not tools:
        return (
            f"No Composio tool found with slug '{slug}'. "
            "Use composio_search_tools to find the right slug."
        )

    t = tools[0]
    schema = _input_schema(t)
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    tk = _toolkit_name(t)
    desc = (getattr(t, "description", "") or "").strip()

    lines = [f"{getattr(t, 'slug', '') or slug}" + (f"  [{tk}]" if tk else "")]
    if desc:
        lines.append(desc)
    if not props:
        lines.append("\nParameters: none — call composio_execute with arguments={}.")
        return "\n".join(lines)

    lines.append("\nParameters:")
    for name, spec in props.items():
        spec = spec if isinstance(spec, dict) else {}
        typ = spec.get("type", "any")
        req = "REQUIRED" if name in required else "optional"
        default = spec.get("default")
        dflt = f", default={default!r}" if default is not None else ""
        pdesc = (spec.get("description") or "").strip()
        lines.append(f"  - {name} ({typ}, {req}{dflt}): {pdesc}")
    lines.append(f"\nrequired: {', '.join(sorted(required)) if required else '(none — arguments={} works)'}")
    return "\n".join(lines)


@mcp.tool()
def composio_execute(slug: str, arguments: dict | None = None) -> str:
    """
    Execute a Composio tool by its slug (find slugs with composio_search_tools).

    Args:
        slug: The tool slug, e.g. "GITHUB_CREATE_AN_ISSUE", "GMAIL_SEND_EMAIL".
        arguments: A JSON object of the tool's input parameters
                   (e.g. {"owner": "me", "repo": "x", "title": "Bug"}).

    If the tool needs an app account you haven't connected, the result will say
    so — use composio_authorize(toolkit) to connect it, then retry.
    """
    try:
        client = _get_client()
    except ComposioError as e:
        return str(e)

    # Be tolerant of models that pass the arguments object as a JSON string.
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return "[ERROR] 'arguments' must be a JSON object, not a string."
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return "[ERROR] 'arguments' must be a JSON object."

    try:
        # Low-level "manual execution" requires a concrete toolkit version and
        # rejects "latest". dangerously_skip_version_check just uses the current
        # tool version (the behavior we want for a single-user agent) — without
        # it every execute fails with "Toolkit version not specified".
        resp = client.tools.execute(
            slug, arguments, user_id=USER_ID, dangerously_skip_version_check=True
        )
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] Composio execution failed: {e}"

    # resp is a dict-like {data, error, successful}
    successful = resp.get("successful") if isinstance(resp, dict) else getattr(resp, "successful", None)
    error = resp.get("error") if isinstance(resp, dict) else getattr(resp, "error", None)
    data = resp.get("data") if isinstance(resp, dict) else getattr(resp, "data", None)

    if successful is False or error:
        msg = error or "execution failed"
        low = msg.lower() if isinstance(msg, str) else ""
        hint = ""
        if any(w in low for w in ("auth", "connect", "credential", "not connected", "no connected")):
            tk = slug.split("_", 1)[0].lower() if "_" in slug else ""
            hint = f"\nHint: connect the app first with composio_authorize('{tk}')."
        elif any(w in low for w in ("missing", "required", "invalid request", "field", "schema", "parameter")):
            hint = (
                f"\nHint: call composio_get_tool('{slug}') to see the exact required "
                "arguments. If this tool needs an id you don't have (e.g. installation_id), "
                "search for a simpler tool with composio_search_tools."
            )
        return f"[ERROR] {slug} failed: {msg}{hint}"

    # Large list payloads (repos, issues, emails…) get a compact summary instead
    # of raw JSON, so they stay complete and within the token budget.
    summary = _summarize_list_result(data)
    if summary is not None:
        return f"{slug} succeeded.\n{summary}"

    try:
        body = json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        body = str(data)
    if len(body) > 8000:
        body = body[:8000] + (
            "\n… (result truncated; for a specific field use a more specific "
            "tool/slug or pass filters)"
        )
    return f"{slug} succeeded.\n{body}"


@mcp.tool()
def composio_authorize(toolkit: str) -> str:
    """
    Start connecting an app account to Composio so its tools can be used.

    Returns an OAuth link — give it to the user and ask them to open it and
    approve access. Once they've done so, the app's tools will work via
    composio_execute. Connection is one-time per app.

    Args:
        toolkit: The app slug to connect, e.g. "github", "gmail", "slack".
    """
    try:
        client = _get_client()
    except ComposioError as e:
        return str(e)
    tk = toolkit.strip().lower()

    # Composio v3 flow: a toolkit needs an "auth config" before a user can link
    # an account. Reuse an existing one for this toolkit, else create a
    # Composio-managed-OAuth config (no app credentials needed).
    auth_config_id = None
    try:
        existing = client.auth_configs.list(toolkit_slug=tk)
        items = getattr(existing, "items", None) or []
        if items:
            auth_config_id = _extract_id(items[0])
    except Exception:  # noqa: BLE001 - listing is best-effort; fall through to create
        pass

    if not auth_config_id:
        try:
            created = client.auth_configs.create(
                toolkit=tk, options={"type": "use_composio_managed_auth"}
            )
            auth_config_id = _extract_id(getattr(created, "auth_config", None)) or _extract_id(created)
        except Exception as e:  # noqa: BLE001
            return f"[ERROR] Couldn't create an auth config for '{toolkit}': {e}"

    if not auth_config_id:
        return f"[ERROR] Couldn't resolve an auth config id for '{toolkit}'."

    # Create a Composio Connect Link the user opens to approve access.
    try:
        req = client.connected_accounts.link(user_id=USER_ID, auth_config_id=auth_config_id)
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] Couldn't create a connect link for '{toolkit}': {e}"

    url = getattr(req, "redirect_url", None)
    status = getattr(req, "status", "") or ""
    cid = getattr(req, "id", "") or ""
    if not url:
        return (
            f"Link for '{toolkit}' returned status '{status}' (id {cid}) but no URL — "
            "it may already be connected (check composio_list_connections)."
        )
    return (
        f"To connect {toolkit}, open this link and approve access:\n\n{url}\n\n"
        f"(connection id: {cid}, status: {status}, auth config: {auth_config_id}). "
        "Once approved, retry the action."
    )


@mcp.tool()
def composio_list_connections() -> str:
    """
    List the app accounts currently connected to Composio for this agent, with
    their status (ACTIVE means ready to use). Use this to check what's already
    connected before authorizing or executing.
    """
    try:
        client = _get_client()
    except ComposioError as e:
        return str(e)

    try:
        resp = client.client.connected_accounts.list(user_ids=[USER_ID])
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] Couldn't list Composio connections: {e}"

    items = getattr(resp, "items", None)
    if items is None and isinstance(resp, dict):
        items = resp.get("items")
    items = items or []
    if not items:
        return (
            "No app accounts are connected yet. Use composio_authorize('<app>') "
            "to connect one (e.g. github, gmail, slack)."
        )

    lines = [f"Connected accounts ({len(items)}):"]
    for it in items:
        get = (lambda k: it.get(k)) if isinstance(it, dict) else (lambda k: getattr(it, k, None))
        tk = get("toolkit")
        tk_name = tk.get("slug") if isinstance(tk, dict) else (getattr(tk, "slug", None) or tk)
        lines.append(f"  - {tk_name or '?'}: {get('status') or '?'}  (id {get('id') or '?'})")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
