"""
Project context aggregation.

The headline capability of the project tracking toolkit: pull together everything
we know about a project from every available source into one bundle, so the agent
(or the dashboard) can reason over it without orchestrating a dozen calls.

Sources:
  - project_store      : the project record, its tasks (by status), and notes
  - the filesystem     : doc filenames under the project's docs_path
  - ToolGate (REST)    : GitHub issues, pull requests, recent commits
  - Claude Hub (REST)  : recent Claude Code sessions for the project's directory

Each external source is isolated: if a service is down or a field is missing, that
section reports the problem and the rest of the bundle still comes back.

Two REST clients live here (thin, sync httpx), modeled on
  Tool-Gate/sdk/python/toolgate/mcp_server.py   and
  app/mcp_servers/claude_hub_server.py
"""

import os
import json

import httpx

import config

try:
    from keychain import get_secret as _get_secret
except Exception:  # pragma: no cover - keychain only present on the dev mac
    def _get_secret(_name):
        raise RuntimeError("keychain unavailable")


# How many of each external item to include in the bundle (keeps it digestible).
MAX_ISSUES = 15
MAX_PRS = 15
MAX_COMMITS = 15
MAX_SESSIONS = 6
MAX_DOCS = 100

DOC_EXTENSIONS = {".md", ".txt", ".rst", ".docx", ".pdf", ".markdown"}


# ---------------------------------------------------------------------------
# ToolGate REST client (GitHub tools)
# ---------------------------------------------------------------------------

# Fallback tool ids (resolved by name at runtime; these are the safety net).
_GITHUB_TOOL_IDS = {
    "github_list_issues": "1641ab54-e277-464b-a283-195cd355f27f",
    "github_list_pull_requests": "a67b1e65-5f23-4f04-a072-06a65a2e98e7",
    "github_list_commits": "976b149c-5ec3-473f-b2a1-59762acd16b8",
    "github_create_issue": "7169d7d5-e53e-408e-8a44-aa6d1d197528",
}


class ToolGateError(Exception):
    """A user-facing error to relay back when ToolGate can't be used."""


class ToolGateClient:
    """Minimal client over the ToolGate REST API: create a session bound to the
    agent (so its vaulted GitHub connection is used) and execute tools by id."""

    def __init__(self):
        self.base_url = os.environ.get("TOOLGATE_BASE_URL", "http://localhost:5050").rstrip("/")
        self.api_key = os.environ.get("TOOLGATE_API_KEY") or _safe_secret("toolgate-api-key")
        self.agent_id = os.environ.get("TOOLGATE_AGENT_ID") or _safe_secret("toolgate-agent-id")
        self._session_id: str | None = None
        self._name_to_id: dict[str, str] = dict(_GITHUB_TOOL_IDS)
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-Api-Key": self.api_key or ""},
            timeout=30.0,
        )

    def _create_session(self) -> str:
        body = {"agentId": self.agent_id} if self.agent_id else {}
        resp = self._client.post("/api/sessions", json=body)
        resp.raise_for_status()
        self._session_id = resp.json()["sessionId"]
        return self._session_id

    def _resolve_tool_id(self, name: str) -> str:
        """Refresh github_* ids from the live catalog; fall back to known ids."""
        try:
            resp = self._client.get("/api/tools", params={"category": "development"})
            resp.raise_for_status()
            for t in resp.json():
                if t.get("name", "").startswith("github_"):
                    self._name_to_id[t["name"]] = t["id"]
        except httpx.HTTPError:
            pass
        return self._name_to_id.get(name, "")

    def execute(self, tool_name: str, params: dict, _retried: bool = False) -> str:
        """Run a ToolGate tool by name and return its body string. Raises
        ToolGateError on any failure so callers can surface a clean message."""
        if not self.api_key:
            raise ToolGateError("ToolGate API key not configured.")
        tool_id = self._name_to_id.get(tool_name) or self._resolve_tool_id(tool_name)
        if not tool_id:
            raise ToolGateError(f"Tool '{tool_name}' not found in ToolGate catalog.")
        if self._session_id is None:
            try:
                self._create_session()
            except httpx.HTTPError as e:
                raise ToolGateError(f"Couldn't open a ToolGate session: {e}")

        payload = {"sessionId": self._session_id, "toolId": tool_id, "parameters": params}
        try:
            resp = self._client.post("/api/execute", json=payload)
        except httpx.HTTPError as e:
            raise ToolGateError(f"ToolGate request failed: {e}")

        # Expired/invalid session -> recreate once and retry.
        if resp.status_code == 400 and not _retried:
            try:
                msg = resp.json().get("error", "")
            except (ValueError, AttributeError):
                msg = ""
            if "expired" in msg.lower() or "invalid" in msg.lower():
                self._create_session()
                return self.execute(tool_name, params, _retried=True)

        if resp.status_code != 200:
            raise ToolGateError(f"ToolGate returned HTTP {resp.status_code}: {resp.text[:300]}")

        result = resp.json()
        if not result.get("success"):
            err = result.get("error") or result.get("body") or "execution failed"
            raise ToolGateError(f"{err} (status {result.get('statusCode')})")
        return result.get("body", "")

    def close(self):
        self._client.close()


def _safe_secret(name: str) -> str:
    try:
        return _get_secret(name)
    except Exception:
        return ""


def _parse_body(body):
    """ToolGate bodies come back as JSON strings (usually). Parse leniently."""
    if isinstance(body, (list, dict)):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (ValueError, TypeError):
            return body
    return body


# ---------------------------------------------------------------------------
# Claude Hub REST client (recent sessions)
# ---------------------------------------------------------------------------

class ClaudeHubClient:
    def __init__(self):
        self.base_url = os.environ.get("CLAUDE_HUB_URL", "http://localhost:3000").rstrip("/")

    @staticmethod
    def project_id_for_path(path: str) -> str:
        """The Hub keys projects by their directory path with '/' -> '-'."""
        return path.rstrip("/").replace("/", "-")

    def recent_sessions(self, project_path: str, limit: int = MAX_SESSIONS) -> list[dict]:
        pid = self.project_id_for_path(project_path)
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.base_url}/api/projects/{pid}/sessions")
            resp.raise_for_status()
            sessions = resp.json().get("sessions", [])
        return sessions[:limit]


# ---------------------------------------------------------------------------
# Doc helpers (filesystem)
# ---------------------------------------------------------------------------

def list_docs(docs_path: str) -> list[str]:
    """Relative filenames of documents under docs_path (recursive)."""
    if not docs_path or not os.path.isdir(docs_path):
        return []
    found = []
    for root, dirs, files in os.walk(docs_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.startswith("."):
                continue
            if os.path.splitext(f)[1].lower() in DOC_EXTENSIONS:
                found.append(os.path.relpath(os.path.join(root, f), docs_path))
        if len(found) >= MAX_DOCS:
            break
    return sorted(found)[:MAX_DOCS]


def read_doc(docs_path: str, filename: str) -> str:
    """Read one document's text. Guards against path traversal."""
    if not docs_path or not os.path.isdir(docs_path):
        raise FileNotFoundError("This project has no valid docs_path.")
    base = os.path.realpath(docs_path)
    target = os.path.realpath(os.path.join(base, filename))
    if not (target == base or target.startswith(base + os.sep)):
        raise ValueError("Refusing to read outside the docs directory.")
    if not os.path.isfile(target):
        raise FileNotFoundError(f"No such doc: {filename}")
    ext = os.path.splitext(target)[1].lower()
    if ext == ".docx":
        from docx import Document
        return "\n\n".join(p.text for p in Document(target).paragraphs)
    if ext == ".pdf":
        return "(PDF — open it directly; text extraction not supported here.)"
    with open(target, "r", errors="replace") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# GitHub gathering (compact summaries)
# ---------------------------------------------------------------------------

def _summarize_issues(items) -> list[dict]:
    # ToolGate trims issues to {number, title, body, created_at, created_by};
    # tolerate the raw GitHub shape too (state, user.login) just in case.
    out = []
    for it in (items or [])[:MAX_ISSUES]:
        if not isinstance(it, dict):
            continue
        user = it.get("user") or {}
        author = it.get("created_by") or (user.get("login") if isinstance(user, dict) else user)
        out.append({
            "number": it.get("number"),
            "title": it.get("title", ""),
            "state": it.get("state", ""),
            "author": author or "",
        })
    return out


def _summarize_prs(items) -> list[dict]:
    out = []
    for it in (items or [])[:MAX_PRS]:
        if not isinstance(it, dict):
            continue
        user = it.get("user") or {}
        out.append({
            "number": it.get("number"),
            "title": it.get("title", ""),
            "state": it.get("state", ""),
            "author": user.get("login") if isinstance(user, dict) else user,
        })
    return out


def _summarize_commits(items) -> list[dict]:
    out = []
    for it in (items or [])[:MAX_COMMITS]:
        if not isinstance(it, dict):
            continue
        commit = it.get("commit") or {}
        author = (commit.get("author") or {}) if isinstance(commit, dict) else {}
        sha = it.get("sha", "")
        out.append({
            "sha": sha[:7] if isinstance(sha, str) else sha,
            "message": (commit.get("message", "") if isinstance(commit, dict) else "").split("\n")[0],
            "author": author.get("name", ""),
            "date": author.get("date", ""),
        })
    return out


def _resolve_owner(tg: "ToolGateClient", repo_name: str) -> str | None:
    """When only a bare repo name is stored, find its owner from the user's
    repo list (owner lives in the html_url, e.g. github.com/<owner>/<repo>)."""
    try:
        repos = _parse_body(tg.execute("github_list_repos", {}))
    except ToolGateError:
        return None
    for r in repos if isinstance(repos, list) else []:
        if isinstance(r, dict) and r.get("name") == repo_name and r.get("html_url"):
            try:
                return r["html_url"].split("github.com/")[1].split("/")[0]
            except IndexError:
                return None
    return None


def _owner_repo(tg: "ToolGateClient", github_repo: str) -> tuple[str | None, str]:
    """Split 'owner/repo', or resolve the owner for a bare repo name."""
    if "/" in github_repo:
        owner, _, repo = github_repo.partition("/")
        return owner.strip(), repo.strip()
    repo = github_repo.strip()
    return _resolve_owner(tg, repo), repo


def _gather_github(github_repo: str) -> dict:
    """Pull issues, PRs, and recent commits for a repo via ToolGate.

    Accepts either 'owner/repo' or a bare repo name (owner resolved from the
    user's GitHub account).
    """
    if not github_repo:
        return {"skipped": "No GitHub repo set for this project."}

    tg = ToolGateClient()
    owner, repo = _owner_repo(tg, github_repo)
    if not owner:
        tg.close()
        return {"skipped": f"Couldn't resolve the owner for repo '{repo}'. "
                           "Store it as 'owner/repo'."}

    result = {"repo": f"{owner}/{repo}"}
    try:
        for key, tool, extra in (
            ("issues", "github_list_issues", {"state": "open", "per_page": MAX_ISSUES}),
            ("pull_requests", "github_list_pull_requests", {"state": "open"}),
            ("commits", "github_list_commits", {"per_page": MAX_COMMITS}),
        ):
            try:
                body = _parse_body(tg.execute(tool, {"owner": owner, "repo": repo, **extra}))
            except ToolGateError as e:
                result[key] = {"error": str(e)}
                continue
            if key == "issues":
                result[key] = _summarize_issues(body)
            elif key == "pull_requests":
                result[key] = _summarize_prs(body)
            else:
                result[key] = _summarize_commits(body)
    finally:
        tg.close()
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_github_issue(github_repo: str, title: str, body: str = "") -> dict:
    """Create a GitHub issue on the project's repo via ToolGate. Returns the
    created issue's number/url. Raises ToolGateError on failure."""
    if not github_repo:
        raise ToolGateError("This project has no GitHub repo set.")
    tg = ToolGateClient()
    try:
        owner, repo = _owner_repo(tg, github_repo)
        if not owner:
            raise ToolGateError(f"Couldn't resolve the owner for '{github_repo}'.")
        resp = _parse_body(tg.execute(
            "github_create_issue",
            {"owner": owner, "repo": repo, "title": title, "body": body},
        ))
    finally:
        tg.close()
    if isinstance(resp, dict):
        return {
            "number": resp.get("number"),
            "html_url": resp.get("html_url") or resp.get("url") or "",
            "raw": resp,
        }
    return {"number": None, "html_url": "", "raw": resp}


def gather_context(project) -> dict:
    """Assemble the full context bundle for a project (id or name).

    Returns {"error": ...} only when the project itself can't be found; any
    individual source failure is captured inside its own section instead.
    """
    import project_store

    record = project_store.get_project(project)
    if record is None:
        return {"error": f"No project found matching '{project}'."}

    tasks = project_store.list_tasks(record["id"])
    by_status = {"todo": [], "in_progress": [], "done": []}
    for t in tasks:
        by_status.setdefault(t["status"], []).append(t)

    ctx = {
        "project": record,
        "tasks": by_status,
        "notes": project_store.list_notes(record["id"]),
    }

    # Docs
    try:
        ctx["docs"] = list_docs(record.get("docs_path", ""))
    except OSError as e:
        ctx["docs"] = {"error": str(e)}

    # GitHub
    ctx["github"] = _gather_github(record.get("github_repo", ""))

    # Claude Hub conversations
    path = record.get("path", "")
    if path:
        try:
            ctx["claude_sessions"] = ClaudeHubClient().recent_sessions(path)
        except httpx.HTTPError as e:
            ctx["claude_sessions"] = {"error": f"Claude Hub unavailable: {e}"}
        except Exception as e:  # noqa: BLE001 - never let Hub break the bundle
            ctx["claude_sessions"] = {"error": str(e)}
    else:
        ctx["claude_sessions"] = {"skipped": "No project path set."}

    return ctx


def _section_or_error(value, render):
    """Render a section, or show its skipped/error note if it's a status dict."""
    if isinstance(value, dict) and ("error" in value or "skipped" in value):
        return f"  ({value.get('error') or value.get('skipped')})"
    return render(value)


def format_context(ctx: dict) -> str:
    """Render a context bundle as a readable text blob for the agent."""
    if "error" in ctx:
        return ctx["error"]

    p = ctx["project"]
    lines = [
        f"# Project: {p['name']}",
        f"  repo: {p.get('github_repo') or '—'}   ·   machine: {p.get('dev_machine') or '—'}",
        f"  path: {p.get('path') or '—'}",
        f"  docs: {p.get('docs_path') or '—'}",
    ]
    if p.get("similar_projects"):
        lines.append(f"  similar projects: {p['similar_projects']}")

    # Tasks
    lines.append("\n## Tasks")
    tasks = ctx.get("tasks", {})
    if not any(tasks.values()):
        lines.append("  (none)")
    for status in ("in_progress", "todo", "done"):
        group = tasks.get(status, [])
        if not group:
            continue
        lines.append(f"  {status} ({len(group)}):")
        for t in group:
            issue = f" [{t['github_issue']}]" if t.get("github_issue") else ""
            lines.append(f"    - [{t['priority']}] {t['name']}{issue} (id {t['id']})")
            if t.get("description"):
                lines.append(f"        {t['description']}")

    # Notes
    lines.append("\n## Notes")
    notes = ctx.get("notes", [])
    if not notes:
        lines.append("  (none)")
    for n in notes:
        title = n.get("name") or f"note {n['id']}"
        lines.append(f"  - {title}: {n.get('description', '')}")

    # Docs
    lines.append("\n## Docs")
    lines.append(_section_or_error(
        ctx.get("docs", []),
        lambda docs: "\n".join(f"  - {d}" for d in docs) if docs else "  (none)",
    ))

    # GitHub
    lines.append("\n## GitHub")
    gh = ctx.get("github", {})
    if "skipped" in gh or "error" in gh:
        lines.append(f"  ({gh.get('skipped') or gh.get('error')})")
    else:
        lines.append(f"  repo: {gh.get('repo')}")
        lines.append("  Open issues:")
        lines.append(_section_or_error(
            gh.get("issues", []),
            lambda xs: "\n".join(
                f"    #{i['number']} {i['title']}"
                + (f" ({i['state']})" if i.get("state") else "")
                + (f" — {i['author']}" if i.get("author") else "")
                for i in xs
            ) if xs else "    (none)",
        ))
        lines.append("  Open pull requests:")
        lines.append(_section_or_error(
            gh.get("pull_requests", []),
            lambda xs: "\n".join(f"    #{i['number']} {i['title']} ({i['state']})" for i in xs)
            if xs else "    (none)",
        ))
        lines.append("  Recent commits:")
        lines.append(_section_or_error(
            gh.get("commits", []),
            lambda xs: "\n".join(f"    {c['sha']} {c['message']} — {c['author']}" for c in xs)
            if xs else "    (none)",
        ))

    # Claude Hub sessions
    lines.append("\n## Recent Claude Code sessions")
    lines.append(_section_or_error(
        ctx.get("claude_sessions", []),
        lambda ss: "\n".join(
            f"  - {s.get('name', '?')} ({s.get('messageCount', 0)} msgs)"
            + (f" — last: {s['lastPrompt']}" if s.get("lastPrompt") else "")
            for s in ss
        ) if ss else "  (none)",
    ))

    return "\n".join(lines)
