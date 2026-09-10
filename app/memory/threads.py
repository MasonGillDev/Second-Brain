"""Conversation threading — topic-scoped working memory.

One thread = one conversation about one topic, stored as a session-style JSON
file (messages + rolling summary) plus embeddings in Chroma for routing. While
you're actively talking the thread is locked (append-only → prompt-cache hits).
After THREAD_IDLE_TIMEOUT_MIN of silence the thread is parked: compacted if over
the token ceiling, given a Haiku title+summary, and indexed. The next prompt is
routed — resume the best-matching parked thread (mode "on") or start fresh.
Mode "shadow" parks/indexes but only LOGS what it would have resumed, so the
resume threshold can be tuned on real usage first.

All methods are blocking (LLM + Chroma calls) — call via asyncio.to_thread.
Failures never propagate: worst case the turn continues in the current buffer.
"""

import json
import os
import re
import time
import uuid

import anthropic

import config
from keychain import get_secret
from memory.conversation import _content_to_text, _is_turn_start, _message_to_text

_INDEX_FILE = "threads_index.json"


# ── index store (atomic JSON, mirrors trigger_store) ─────────────────

def _index_path() -> str:
    return os.path.join(config.THREADS_DIR, _INDEX_FILE)


def load_index() -> list[dict]:
    try:
        with open(_index_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_index(rows: list[dict]) -> None:
    os.makedirs(config.THREADS_DIR, exist_ok=True)
    tmp = _index_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rows, f, indent=2)
    os.replace(tmp, _index_path())


def _thread_path(thread_id: str) -> str:
    return os.path.join(config.THREADS_DIR, f"{thread_id}.json")


class ThreadManager:
    def __init__(self, vector_store, conversation):
        self._vs = vector_store
        self._conv = conversation
        self._llm = None  # lazy Anthropic client for title/summary
        self.mode = config.THREADS_MODE  # "shadow" | "on" (manager not built when "off")
        self.rows = load_index()
        self._adopt_or_attach()

    # ── startup ──────────────────────────────────────────────────────

    def _adopt_or_attach(self):
        """Attach to the active thread from a previous run, or migrate the
        legacy single-session buffer into thread #1 on first enabled startup."""
        active = self._active_row()
        if active is not None:
            try:
                with open(_thread_path(active["id"])) as f:
                    self._conv.load_state(json.load(f), _thread_path(active["id"]))
                print(f"  [threads] attached to active thread '{active.get('title') or active['id']}'")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"  [threads] active thread file unreadable ({e}) — starting fresh")
                active["active"] = False
                self._new_thread()
            return

        if not self.rows and self._conv.messages:
            # First threaded startup: legacy session becomes thread #1. Its
            # last_active is the legacy file's mtime, so if it's stale it gets
            # parked (titled + indexed) on the very next turn.
            tid = self._make_id()
            try:
                mtime = os.path.getmtime(self._conv._session_file)
            except OSError:
                mtime = time.time()
            self.rows.append(self._new_row(tid, active=True, last_active=mtime))
            self._conv._session_file = _thread_path(tid)
            self._conv.save_session()
            save_index(self.rows)
            print(f"  [threads] migrated legacy session into thread {tid}")
        else:
            # No active thread (e.g. parked at shutdown). Start an empty one
            # born STALE (last_active=0) so the very first prompt routes —
            # otherwise a fresh thread would lock out resume-after-restart.
            self._new_thread(last_active=0.0)

    # ── the per-turn state machine ───────────────────────────────────

    def begin_turn(self, user_text: str) -> dict | None:
        """Called at the start of every LLM-path turn. Returns a thread event
        ({"event": "resumed"|"new", "title": ...}) or None (locked in)."""
        try:
            return self._begin_turn(user_text)
        except Exception as e:  # never let threading break a turn
            print(f"  [threads] begin_turn failed (continuing in current buffer): {e}")
            return None

    def _begin_turn(self, user_text: str) -> dict | None:
        now = time.time()
        active = self._active_row()
        idle_limit = config.THREAD_IDLE_TIMEOUT_MIN * 60

        if active is not None and (now - active.get("last_active", 0)) < idle_limit:
            active["last_active"] = now
            save_index(self.rows)
            return None  # locked in — no routing while a conversation is live

        if active is not None:
            self.park_active()

        best = self._route(user_text)
        if best is not None:
            row, score = best
            if self.mode == "on" and score >= config.THREAD_RESUME_THRESHOLD:
                self._rehydrate(row, now)
                print(f"  [threads] resumed '{row.get('title')}' @ {score:.3f}")
                return {"event": "resumed", "title": row.get("title"), "score": round(score, 3)}
            verdict = "would resume" if score >= config.THREAD_RESUME_THRESHOLD else "below threshold"
            print(f"  [threads] {self.mode}: {verdict} '{row.get('title')}' @ {score:.3f}"
                  f" (threshold {config.THREAD_RESUME_THRESHOLD})")
        else:
            print("  [threads] no parked threads to route against")

        self._new_thread(last_active=now)
        return {"event": "new", "title": None}

    # ── parking ──────────────────────────────────────────────────────

    def park_active(self) -> None:
        """Compact, title, index, and persist the active thread, then release it.
        Safe to call when nothing is active."""
        row = self._active_row()
        if row is None:
            return
        if not self._conv.messages:
            # Empty thread — drop it rather than park a shell.
            self.rows.remove(row)
            try:
                os.remove(_thread_path(row["id"]))
            except OSError:
                pass
            save_index(self.rows)
            return

        # Embed new messages BEFORE compaction trims them out of the buffer.
        self._embed_new_messages(row)

        if (self._conv.summary_token_estimate + self._conv.messages_token_estimate) > config.THREAD_TOKEN_CEILING:
            try:
                self._conv.summarize_oldest()
            except Exception as e:
                print(f"  [threads] park compaction failed (keeping raw): {e}")

        title, summary = self._title_and_summary(row)
        row.update({
            "title": title,
            "summary": summary,
            "token_est": self._conv.summary_token_estimate + self._conv.messages_token_estimate,
            "msg_count": self._conv.total_messages_processed,
            "active": False,
        })
        self._embed_summary(row)
        self._conv.save_session()
        self._enforce_max_active()
        save_index(self.rows)
        print(f"  [threads] parked '{title}' ({row['msg_count']} msgs, ~{row['token_est']}t)")

    def _embed_new_messages(self, row: dict) -> None:
        """Index message chunks added since the last park. Global turn indices
        (total_processed - len(buffer) + i) stay unique across compactions.
        Park-time hygiene v1: turns under 8 words aren't indexed."""
        col = self._vs.collections["thread_messages"]
        upto = row.get("embedded_upto", 0)
        base = self._conv.total_messages_processed - len(self._conv.messages)
        docs, ids, metas = [], [], []
        for i, m in enumerate(self._conv.messages):
            gidx = base + i
            if gidx < upto:
                continue
            text = _message_to_text(m)
            if len(text.split()) < 8:
                continue
            for c in range(0, len(text), 800):
                docs.append(f"{m['role']}: {text[c:c + 800]}")
                ids.append(f"{row['id']}:{gidx}:{c // 800}")
                metas.append({"thread": row["id"]})
        if docs:
            try:
                col.upsert(documents=docs, ids=ids, metadatas=metas)
            except Exception as e:
                print(f"  [threads] message embedding failed: {e}")
        row["embedded_upto"] = self._conv.total_messages_processed

    def _embed_summary(self, row: dict) -> None:
        try:
            self._vs.collections["thread_summaries"].upsert(
                documents=[f"{row.get('title') or ''}: {row.get('summary') or ''}"],
                ids=[row["id"]],
                metadatas=[{"thread": row["id"]}],
            )
        except Exception as e:
            print(f"  [threads] summary embedding failed: {e}")

    def _title_and_summary(self, row: dict) -> tuple[str, str]:
        """One Haiku call → {"title", "summary"}; graceful fallbacks."""
        tail = self._conv.messages[-24:]
        transcript = "\n".join(
            f"{m['role']}: {_message_to_text(m)[:400]}" for m in tail)
        if self._conv.rolling_summary:
            transcript = f"[summary of earlier turns]\n{self._conv.rolling_summary[:1500]}\n\n{transcript}"
        try:
            if self._llm is None:
                self._llm = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))
            resp = self._llm.messages.create(
                model=config.SUMMARIZATION_MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content":
                           "Return ONLY JSON {\"title\": \"3-6 word topic\", \"summary\": "
                           "\"<=120 word summary of key facts and decisions\"} for this "
                           f"conversation:\n\n{transcript[:12000]}"}],
            )
            raw = resp.content[0].text
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0) if m else raw)
            title = str(data.get("title", "")).strip()[:80]
            summary = str(data.get("summary", "")).strip()[:1200]
            if title:
                return title, summary
        except Exception as e:
            print(f"  [threads] title generation failed: {e}")
        # Fallbacks: first user message / rolling summary
        first_user = next((m for m in self._conv.messages if _is_turn_start(m)), None)
        title = (_content_to_text(first_user["content"])[:60] if first_user else row["id"])
        return title, (self._conv.rolling_summary or "")[:1200]

    def _enforce_max_active(self) -> None:
        live = [r for r in self.rows if not r.get("archived")]
        live.sort(key=lambda r: r.get("last_active", 0))
        for row in live[:max(0, len(live) - config.THREAD_MAX_ACTIVE)]:
            self._archive(row)

    def _archive(self, row: dict) -> None:
        row["archived"] = True
        row["active"] = False
        for name in ("thread_messages", "thread_summaries"):
            try:
                self._vs.collections[name].delete(where={"thread": row["id"]})
            except Exception:
                pass
        print(f"  [threads] archived '{row.get('title') or row['id']}'")

    # ── routing ──────────────────────────────────────────────────────

    def _route(self, text: str) -> tuple[dict, float] | None:
        """Score parked threads against the prompt. Returns (row, score) for the
        best, or None when nothing is indexed. Blend: 0.6 * mean(top-3 message
        chunk relevances) + 0.4 * summary relevance; relevance = 1/(1+L2)."""
        by_id = {r["id"]: r for r in self.rows if not r.get("archived")}
        if not by_id:
            return None
        msg_scores: dict[str, list[float]] = {}
        sum_scores: dict[str, float] = {}
        try:
            col = self._vs.collections["thread_messages"]
            if col.count() > 0:
                res = col.query(query_texts=[text], n_results=min(12, col.count()))
                for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
                    tid = (meta or {}).get("thread")
                    if tid in by_id:
                        msg_scores.setdefault(tid, []).append(1.0 / (1.0 + dist))
            scol = self._vs.collections["thread_summaries"]
            if scol.count() > 0:
                res = scol.query(query_texts=[text], n_results=min(5, scol.count()))
                for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
                    tid = (meta or {}).get("thread")
                    if tid in by_id:
                        sum_scores[tid] = 1.0 / (1.0 + dist)
        except Exception as e:
            print(f"  [threads] routing query failed: {e}")
            return None

        best_row, best_score = None, 0.0
        for tid in set(msg_scores) | set(sum_scores):
            top3 = sorted(msg_scores.get(tid, []), reverse=True)[:3]
            m = sum(top3) / len(top3) if top3 else 0.0
            s = sum_scores.get(tid, 0.0)
            score = 0.6 * m + 0.4 * s
            if score > best_score:
                best_row, best_score = by_id[tid], score
        return (best_row, best_score) if best_row else None

    # ── thread switching ─────────────────────────────────────────────

    def _rehydrate(self, row: dict, now: float) -> None:
        with open(_thread_path(row["id"])) as f:
            self._conv.load_state(json.load(f), _thread_path(row["id"]))
        row["active"] = True
        row["last_active"] = now
        save_index(self.rows)

    def _new_thread(self, last_active: float | None = None) -> None:
        tid = self._make_id()
        self._conv.load_state({}, _thread_path(tid))
        self._conv.save_session()  # write the file now — a second process (debug
        # reloader) reading the index must never find an active row with no file
        ts = time.time() if last_active is None else last_active  # 0.0 = born stale
        self.rows.append(self._new_row(tid, active=True, last_active=ts))
        save_index(self.rows)

    def clear_active(self) -> None:
        """'Clear' under threading = cold start on demand: park the current
        thread (titled, indexed, still resumable by routing later) and begin a
        fresh one. Nothing is deleted — this is exactly the idle-timeout path,
        just triggered explicitly. The replacement thread is born STALE so the
        very next prompt ROUTES (a fresh thread would lock routing out for the
        whole idle window — post-clear questions silently skipped routing)."""
        self.park_active()
        self._new_thread(last_active=0.0)

    # ── helpers ──────────────────────────────────────────────────────

    def _active_row(self) -> dict | None:
        return next((r for r in self.rows if r.get("active") and not r.get("archived")), None)

    def active_info(self) -> dict | None:
        """Lightweight view of the active thread for UIs: {"id", "title"}.
        title is None until the thread has been parked at least once."""
        row = self._active_row()
        if row is None:
            return None
        return {"id": row["id"], "title": row.get("title")}

    @staticmethod
    def _make_id() -> str:
        return f"t{int(time.time())}_{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _new_row(tid: str, active: bool, last_active: float) -> dict:
        return {"id": tid, "title": None, "summary": None,
                "created_at": time.time(), "last_active": last_active,
                "token_est": 0, "msg_count": 0, "embedded_upto": 0,
                "archived": False, "active": active}
