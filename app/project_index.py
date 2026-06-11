"""
Project knowledge index — semantic search over a project's content.

Ingests a project's docs (chunked), tasks, notes, and commits into the Chroma
`project_knowledge` collection, each chunk tagged with its project so search can
be scoped with a metadata filter. `search_project` returns relevant snippets with
a reference (doc filename / task id / note id / commit sha) so the agent can fetch
the full item via get_doc/get_task/get_notes instead of reading everything.

Freshness model (lazy auto-sync): search_project cheaply re-syncs docs/tasks/notes
first (hash-based skip, so unchanged content costs nothing), then queries. Commits
and full rebuilds run via reindex_project.

Reuses the existing chunking + hash-skip machinery from memory/ingestion.py and the
ToolGate/doc helpers from project_context.py.
"""

import os
import hashlib

import project_store
import project_context as pctx
from memory.ingestion import chunk_by_heading, file_hash

COLLECTION = "project_knowledge"

# Doc extensions we can actually extract text from (pdf is listed for browsing,
# but yields no useful text, so it's skipped at ingestion time).
_INGESTIBLE_DOC_EXT = {".md", ".markdown", ".txt", ".rst", ".docx"}

# Inclusive relevance floor — project search should surface loosely-related
# passages, unlike the strict long-term-memory floor.
SEARCH_MIN_RELEVANCE = 0.30

# Max chars of a hit's text returned as the snippet. Commits get plenty of room
# so their full message body comes back; doc/task/note chunks get a generous cap.
SNIPPET_CHARS = 800
COMMIT_SNIPPET_CHARS = 4000

_vs = None


def _store(vector_store=None):
    """Return a VectorStore, creating a lazy module-level one if none is passed
    (so the MCP subprocess only pays the Chroma cost on first use)."""
    global _vs
    if vector_store is not None:
        return vector_store
    if _vs is None:
        from memory.vector_store import VectorStore
        _vs = VectorStore()
    return _vs


def _col(vs):
    return vs.collections[COLLECTION]


def _where(**kw):
    """Chroma needs $and for multi-key filters; a single key passes through."""
    if len(kw) == 1:
        return dict(kw)
    return {"$and": [{k: v} for k, v in kw.items()]}


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", "replace")).hexdigest()


def _safe(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# Per-source sync
# ---------------------------------------------------------------------------

def _sync_docs(vs, p) -> int:
    """Ingest new/changed doc files; drop chunks for files removed from disk."""
    docs_path = p.get("docs_path", "")
    pid = p["id"]
    files = [f for f in pctx.list_docs(docs_path)
             if os.path.splitext(f)[1].lower() in _INGESTIBLE_DOC_EXT]
    added = 0
    for fname in files:
        h = None
        full = os.path.join(docs_path, fname)
        try:
            h = file_hash(full)
        except OSError:
            continue
        existing = _col(vs).get(where=_where(project_id=pid, source_type="doc", ref=fname, file_hash=h))
        if existing["ids"]:
            continue  # unchanged — already indexed
        # Replace any prior version of this file
        vs.delete_by_metadata(COLLECTION, _where(project_id=pid, source_type="doc", ref=fname))
        try:
            content = pctx.read_doc(docs_path, fname)
        except (OSError, ValueError):
            continue
        chunks = chunk_by_heading(content, fname)
        if not chunks:
            continue
        texts = [c["text"] for c in chunks]
        metas = [{
            "project_id": pid, "project_name": p["name"], "source_type": "doc",
            "ref": fname, "title": fname, "file_hash": h,
            "heading": c.get("heading", ""), "chunk_index": i,
        } for i, c in enumerate(chunks)]
        ids = [f"pk{pid}_doc_{_safe(fname)}_{i}" for i in range(len(chunks))]
        vs.add_batch(COLLECTION, texts, metas, ids)
        added += len(chunks)

    # Cleanup: remove chunks for docs that no longer exist on disk
    present = _col(vs).get(where=_where(project_id=pid, source_type="doc"))
    live = set(files)
    stale = {m.get("ref") for m in (present["metadatas"] or []) if m.get("ref") not in live}
    for ref in stale:
        vs.delete_by_metadata(COLLECTION, _where(project_id=pid, source_type="doc", ref=ref))
    return added


def _sync_rows(vs, p, source_type: str, rows, render, title_of) -> int:
    """Shared upsert for tasks/notes: one chunk per row, refreshed when its
    content hash changes; chunks for deleted rows are removed."""
    pid = p["id"]
    col = _col(vs)
    changed = 0
    live_ids = set()
    for row in rows:
        doc_id = f"pk{pid}_{source_type}_{row['id']}"
        live_ids.add(doc_id)
        text = render(row)
        chash = _md5(text)
        existing = col.get(ids=[doc_id])
        if existing["ids"] and (existing["metadatas"][0] or {}).get("content_hash") == chash:
            continue
        if existing["ids"]:
            col.delete(ids=[doc_id])
        vs.add(COLLECTION, text, {
            "project_id": pid, "project_name": p["name"], "source_type": source_type,
            "ref": str(row["id"]), "title": title_of(row), "content_hash": chash,
        }, doc_id=doc_id)
        changed += 1

    # Cleanup deleted rows
    present = col.get(where=_where(project_id=pid, source_type=source_type))
    stale = [i for i in (present["ids"] or []) if i not in live_ids]
    if stale:
        col.delete(ids=stale)
    return changed


def _sync_tasks(vs, p) -> int:
    rows = project_store.list_tasks(p["id"])
    return _sync_rows(
        vs, p, "task", rows,
        render=lambda t: f"Task: {t['name']}\nStatus: {t['status']} | Priority: {t['priority']}\n\n{t.get('description','')}",
        title_of=lambda t: t["name"],
    )


def _sync_notes(vs, p) -> int:
    rows = project_store.list_notes(p["id"])
    return _sync_rows(
        vs, p, "note", rows,
        render=lambda n: f"Note: {n.get('name','')}\n\n{n.get('description','')}",
        title_of=lambda n: n.get("name") or f"note {n['id']}",
    )


def _fetch_commits(github_repo: str, limit: int = 100) -> list[dict]:
    """Pull commits via ToolGate, returning {sha, message, author, date}."""
    if not github_repo:
        return []
    tg = pctx.ToolGateClient()
    try:
        owner, repo = pctx._owner_repo(tg, github_repo)
        if not owner:
            return []
        body = pctx._parse_body(tg.execute(
            "github_list_commits", {"owner": owner, "repo": repo, "per_page": limit}))
    except pctx.ToolGateError:
        return []
    finally:
        tg.close()
    out = []
    for it in body if isinstance(body, list) else []:
        if not isinstance(it, dict):
            continue
        commit = it.get("commit") or {}
        author = (commit.get("author") or {}) if isinstance(commit, dict) else {}
        out.append({
            "sha": it.get("sha", ""),
            "message": (commit.get("message", "") if isinstance(commit, dict) else ""),
            "author": author.get("name", ""),
            "date": author.get("date", ""),
        })
    return out


def _sync_commits(vs, p, limit: int = 100) -> int:
    """Add any commits not yet indexed (commits are immutable)."""
    pid = p["id"]
    col = _col(vs)
    added = 0
    for c in _fetch_commits(p.get("github_repo", ""), limit):
        sha = c["sha"]
        if not sha:
            continue
        doc_id = f"pk{pid}_commit_{sha}"
        if col.get(ids=[doc_id])["ids"]:
            continue
        subject = (c["message"] or "").split("\n")[0]
        text = f"{sha[:7]} {c['message']}\n— {c['author']} {c['date']}".strip()
        vs.add(COLLECTION, text, {
            "project_id": pid, "project_name": p["name"], "source_type": "commit",
            "ref": sha, "title": subject,
        }, doc_id=doc_id)
        added += 1
    return added


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reindex_project(project, include_commits: bool = True, vector_store=None) -> dict:
    """Full (re)build of a project's knowledge. Hash-skips unchanged content.
    Returns counts of items added/changed per source. Raises ValueError if the
    project doesn't exist."""
    p = project_store.get_project(project)
    if p is None:
        raise ValueError(f"No project found matching '{project}'.")
    vs = _store(vector_store)
    counts = {
        "docs": _sync_docs(vs, p),
        "tasks": _sync_tasks(vs, p),
        "notes": _sync_notes(vs, p),
    }
    counts["commits"] = _sync_commits(vs, p) if include_commits else 0
    return counts


def sync_for_search(p, vector_store=None):
    """Cheap local refresh before a query: docs + tasks + notes (no network)."""
    vs = _store(vector_store)
    _sync_docs(vs, p)
    _sync_tasks(vs, p)
    _sync_notes(vs, p)


def search_project(project, query: str, source_type: str | None = None,
                   top_k: int = 8, vector_store=None) -> list[dict]:
    """Semantic search across a project's indexed content. Returns matches as
    {source_type, ref, title, relevance, snippet}. Raises ValueError if the
    project doesn't exist."""
    p = project_store.get_project(project)
    if p is None:
        raise ValueError(f"No project found matching '{project}'.")
    vs = _store(vector_store)
    sync_for_search(p, vs)
    where = _where(project_id=p["id"], source_type=source_type) if source_type else _where(project_id=p["id"])
    results = vs.query(COLLECTION, query, top_k=top_k, where=where, min_relevance=SEARCH_MIN_RELEVANCE)
    out = []
    for r in results:
        m = r.get("metadata") or {}
        cap = COMMIT_SNIPPET_CHARS if m.get("source_type") == "commit" else SNIPPET_CHARS
        out.append({
            "source_type": m.get("source_type", "?"),
            "ref": m.get("ref", ""),
            "title": m.get("title", ""),
            "relevance": r.get("relevance", 0),
            "snippet": (r.get("text") or "").strip()[:cap],
        })
    return out


def remove_project(project, vector_store=None) -> int:
    """Delete all of a project's chunks (call when a project is deleted).
    Accepts an int id or a name/record."""
    if isinstance(project, dict):
        pid = project["id"]
    elif isinstance(project, int) or (isinstance(project, str) and project.isdigit()):
        pid = int(project)
    else:
        rec = project_store.get_project(project)
        if rec is None:
            return 0
        pid = rec["id"]
    vs = _store(vector_store)
    before = _col(vs).get(where=_where(project_id=pid))
    n = len(before["ids"] or [])
    if n:
        vs.delete_by_metadata(COLLECTION, _where(project_id=pid))
    return n
