"""Fast-path intent router.

Simple, high-frequency voice commands ("pause the music", "turn off the lights",
"set the volume to 40") don't need the full LLM pipeline — a 20k-token,
multi-round Claude call for "lights off" is wasteful and slow. This router
matches the transcript against a small registry of intents by embedding
similarity (via the ChromaDB service the brain already runs), extracts any slots
with plain regex, and calls the tool directly. Anything it isn't confident about
falls through to the LLM unchanged.

Design for PRECISION over recall: a wrong fast-path (firing the wrong tool) is
bad; a miss just costs the normal LLM latency. So the match threshold is high
and slot extractors return None (→ LLM) whenever they're unsure.

Embedding note: the brain runs on Python 3.14 (no local torch), so all embedding
happens server-side in ChromaDB. Intent examples are seeded into a dedicated
'voice_intents' collection at startup; matching is a single read-only query.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

import config

_COLLECTION = "voice_intents"


# ── slot extractors ──────────────────────────────────────────────────

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}


def _spoken_number(text: str) -> Optional[int]:
    """Parse a written-out number 0-100 ('forty five', 'a hundred'). None if absent."""
    words = re.findall(r"[a-z]+", text.lower())
    current = 0
    found = False
    for w in words:
        if w in _UNITS:
            current += _UNITS[w]; found = True
        elif w in _TENS:
            current += _TENS[w]; found = True
        elif w == "hundred":
            current = (current or 1) * 100; found = True
        elif w in ("a", "and"):
            continue
        elif found:
            break  # number expression ended
    return current if found else None


def _percent(text: str) -> Optional[int]:
    """Extract a 0-100 level from digits ('40') or words ('forty'). Clamped."""
    m = re.search(r"\b(\d{1,3})\b", text)
    n = int(m.group(1)) if m else _spoken_number(text)
    if n is None:
        return None
    return max(0, min(100, n))


def _volume_args(text: str) -> Optional[dict]:
    n = _percent(text)
    return {"level": n} if n is not None else None


def _tv_volume_args(text: str) -> Optional[dict]:
    """tv__tv_set_volume names the slot `volume`; music__set_volume names it `level`."""
    n = _percent(text)
    return {"volume": n} if n is not None else None


def _brightness_args(text: str) -> Optional[dict]:
    n = _percent(text)
    return {"brightness": n} if n is not None else None


# Generic remainders after "play ..." that mean "just play/resume", not a search.
_GENERIC_PLAY = {
    "", "music", "the music", "some music", "a song", "song", "songs",
    "something", "anything", "tunes", "some tunes", "stuff", "it", "that",
    "play", "some", "the",
}


def _play_args(text: str) -> Optional[dict]:
    """Pull the search query out of 'play <X>'. Returns None for generic phrases
    ('play some music') so those fall to the LLM / resume rather than searching
    the library for a song literally named 'some music'."""
    m = re.search(r"\b(?:play|put on|listen to|start playing)\b(.*)", text, re.I)
    if not m:
        return None
    query = m.group(1).strip(" .,!?")
    if query.lower() in _GENERIC_PLAY or len(query) < 2:
        return None
    return {"query": query}


# ── intent registry ──────────────────────────────────────────────────

@dataclass
class Intent:
    id: str
    tool: str
    examples: list[str]
    # extract(text) -> args dict, or None to abstain (fall through to the LLM).
    # None (the attribute) means a zero-slot intent (always {}).
    extract: Optional[Callable[[str], Optional[dict]]] = None
    # confirm: a static spoken string (may reference {slots}), or None to speak
    # the tool's own result.
    confirm: Optional[str] = None

    def build_args(self, text: str) -> Optional[dict]:
        if self.extract is None:
            return {}
        return self.extract(text)

    def confirmation(self, args: dict, result: str) -> str:
        # A canned confirmation must never paper over a failed call. The fast
        # path skips the LLM entirely, so nothing else looks at the result —
        # without this, "pause my tv" says "Paused." to a TV that is unplugged.
        text = (result or "").strip()
        if text.startswith("[ERROR]") or text.startswith("Error"):
            detail = text.removeprefix("[ERROR]").removeprefix("Error:").strip()
            return f"That didn't work — {detail[:160]}"
        if self.confirm is not None:
            try:
                return self.confirm.format(**args)
            except Exception:
                return self.confirm
        # Fall back to the tool's own (short, plain) result.
        result = (result or "").strip()
        if result and not result.startswith("[ERROR") and len(result) <= 200:
            return result
        return "Okay."


INTENTS: list[Intent] = [
    # ── music: zero-slot ──
    Intent("music.pause", "music__pause", confirm="Paused.", examples=[
        "pause the music", "pause the song", "pause playback", "pause music",
        "stop the music", "stop the song", "stop playing", "hold the music",
    ]),
    Intent("music.resume", "music__resume", confirm="Resuming.", examples=[
        "resume the music", "resume playback", "unpause", "unpause the music",
        "continue playing", "keep playing", "start the music again",
    ]),
    Intent("music.skip", "music__skip", confirm="Skipping.", examples=[
        "next song", "next track", "skip this song", "skip the song", "skip this",
        "skip", "play the next song", "go to the next song",
    ]),
    Intent("music.previous", "music__previous", confirm="Going back.", examples=[
        "previous song", "previous track", "go back a song", "last song",
        "play the previous song", "go back to the last song",
    ]),
    Intent("music.now_playing", "music__now_playing", confirm=None, examples=[
        "what's playing", "what song is this", "what's this song",
        "what am I listening to", "what's currently playing", "who sings this",
        "name this track", "name this song", "what track is this",
    ]),
    # ── music: slots ──
    Intent("music.set_volume", "music__set_volume", extract=_volume_args,
           confirm="Volume set to {level}.", examples=[
        "set the volume to 40", "set volume to 50", "change the volume to 70",
        "turn the volume up to 60", "turn the volume down to 20", "volume 30",
        "make the volume 50", "set the music volume to 80",
    ]),
    Intent("music.play", "music__play", extract=_play_args, confirm=None, examples=[
        "play some jazz", "play Taylor Swift", "play the Beatles",
        "put on some classical music", "play Bohemian Rhapsody",
        "play my discover weekly", "put on some hip hop", "listen to Radiohead",
    ]),
    # ── lights: zero-slot (all lights) ──
    Intent("lights.on", "lights__set_all_lights", confirm="Lights on.", examples=[
        "turn on the lights", "lights on", "turn the lights on",
        "turn on all the lights", "all lights on", "hit the lights",
        "can you turn on the lights", "lights on please",
    ]),
    Intent("lights.off", "lights__set_all_lights", confirm="Lights off.", examples=[
        "turn off the lights", "lights off", "turn the lights off",
        "turn off all the lights", "all lights off", "kill the lights",
        "shut off the lights", "lights out", "can you turn off the lights",
    ]),
    # ── lights: slot ──
    Intent("lights.brightness", "lights__set_all_lights", extract=_brightness_args,
           confirm="Brightness set to {brightness} percent.", examples=[
        "set the brightness to 50", "set the lights to 30 percent",
        "dim the lights to 20", "brightness 40", "set light brightness to 70",
        "make the lights 60 percent",
    ]),
    # ── tv: zero-slot ──
    Intent("tv.on", "tv__tv_power", confirm="Turning on the TV.", examples=[
        "turn on the tv", "tv on", "turn the tv on", "power on the tv",
        "turn on the television", "switch on the tv",
    ]),
    Intent("tv.off", "tv__tv_power", confirm="TV off.", examples=[
        "turn off the tv", "tv off", "turn the tv off", "power off the tv",
        "shut off the tv", "turn off the television", "switch off the tv",
    ]),
    # Playback control. Without these, ANY tv verb collapsed onto the nearest
    # tv intent, which is power: "pause my tv" and even "resume the tv" both
    # resolved to tv.off and cut the power mid-show.
    Intent("tv.pause", "tv__tv_send_keys", confirm="Paused.", examples=[
        "pause the tv", "pause my tv", "pause the television", "pause the show",
        "pause the movie", "pause it", "pause what's playing on the tv",
        "hold the tv", "freeze the tv", "pause netflix", "pause youtube",
    ]),
    Intent("tv.resume", "tv__tv_send_keys", confirm="Playing.", examples=[
        "resume the tv", "unpause the tv", "resume the show", "play the tv",
        "resume the movie", "un pause the tv", "start it again on the tv",
        "keep playing the tv", "resume netflix", "resume youtube",
    ]),
    # Volume. "turn down the tv" sits lexically right next to "turn off the tv",
    # so without these it matched tv.off ABOVE the 0.85 floor and cut the power
    # when the user only wanted it quieter.
    Intent("tv.volume_down", "tv__tv_send_keys", confirm="Turning it down.", examples=[
        "turn down the tv", "turn the tv down", "lower the tv volume",
        "turn the volume down on the tv", "make the tv quieter", "tv quieter",
        "volume down on the tv", "too loud", "turn it down",
    ]),
    Intent("tv.volume_up", "tv__tv_send_keys", confirm="Turning it up.", examples=[
        "turn up the tv", "turn the tv up", "raise the tv volume",
        "turn the volume up on the tv", "make the tv louder", "tv louder",
        "volume up on the tv", "too quiet", "turn it up",
    ]),
    Intent("tv.set_volume", "tv__tv_set_volume", extract=_tv_volume_args,
           confirm="TV volume set to {volume}.", examples=[
        "set the tv volume to 20", "set the tv to volume 30",
        "change the tv volume to 15", "tv volume 25", "make the tv volume 40",
    ]),
    Intent("tv.rewind", "tv__tv_send_keys", confirm="Rewinding.", examples=[
        "rewind the tv", "rewind the show", "rewind", "go back on the tv",
        "skip back on the tv",
    ]),
    Intent("tv.fast_forward", "tv__tv_send_keys", confirm="Fast forwarding.", examples=[
        "fast forward the tv", "fast forward the show", "fast forward",
        "skip ahead on the tv", "skip forward on the tv",
    ]),
    Intent("tv.stop", "tv__tv_send_keys", confirm="Stopped.", examples=[
        "stop the tv", "stop the show", "stop playback on the tv",
        "stop what's playing on the tv", "stop the movie",
    ]),
    # KEY_MUTE is a toggle — mute and unmute send the same key. Separate intents
    # only so the spoken confirmation matches what you asked; the action is one
    # and the same, so a mute/unmute mix-up by the embedder is harmless.
    Intent("tv.mute", "tv__tv_send_keys", confirm="Muted.", examples=[
        "mute the tv", "mute the television", "mute the volume", "mute the sound",
        "silence the tv", "mute",
    ]),
    Intent("tv.unmute", "tv__tv_send_keys", confirm="Unmuted.", examples=[
        "unmute the tv", "unmute the television", "un mute the tv", "unmute",
        "turn the sound back on", "unmute the volume",
    ]),
]

# Static args for zero-slot / fixed-arg intents that the extractor can't express.
_FIXED_ARGS: dict[str, dict] = {
    "lights.on": {"on": True},
    "lights.off": {"on": False},
    "tv.on": {"on": True},
    "tv.off": {"on": False},
    "tv.pause": {"keys": "pause"},
    # Three steps per command: one notch is imperceptible when asked out loud.
    "tv.volume_down": {"keys": "volume_down volume_down volume_down"},
    "tv.volume_up": {"keys": "volume_up volume_up volume_up"},
    "tv.rewind": {"keys": "rewind"},
    "tv.fast_forward": {"keys": "fast_forward"},
    "tv.resume": {"keys": "play"},
    "tv.stop": {"keys": "stop"},
    "tv.mute": {"keys": "mute"},
    "tv.unmute": {"keys": "mute"},  # KEY_MUTE toggles; same key as mute
}

# Hard-negative decoys: phrasings that resemble a command but are actually
# questions or unrelated. Seeding them (tagged '__reject__', which maps to no
# real intent) makes them the nearest neighbor for such inputs, so resolve()
# falls through to the LLM instead of firing an action. Without these, "is the
# tv on?" scores high against the tv.on examples and would turn the TV on.
DECOYS: list[str] = [
    "is the tv on", "is the television on", "is the tv off",
    "are the lights on", "are the lights off", "is the music playing",
    "is anything playing", "what's the volume", "what's the volume set to",
    "what is the volume", "how loud is it", "what's on tv", "what's on the tv",
    "how many lights do i have", "which lights are on",
    "turn left at the light", "play by play of the game", "what's the score",
    # TV asks that need real reasoning or a tool the fast path doesn't cover —
    # without these they land on whatever tv intent is nearest.
    "cast to the tv", "sleep the tv in 10 minutes", "set a sleep timer on the tv",
    "turn the tv to hdmi 2", "change the input on the tv", "what's on netflix",
    "put on the news", "skip the intro", "dim the tv",
]

# Intents that are costly to get wrong need a stronger match than "nearest
# neighbour wins". Cutting power mid-show, or killing every light, is not
# something to do on a 0.70 guess — "pause my tv" matched tv.off at 0.703 while
# a real "turn off the tv" scores 1.0, so there is plenty of room. Below the
# floor these fall through to the LLM, which can ask or pick a better tool.
HIGH_CONFIDENCE_INTENTS: dict[str, float] = {
    "tv.off": 0.85,
    "tv.on": 0.85,
    "lights.off": 0.85,
}

_BY_ID = {i.id: i for i in INTENTS}


@dataclass
class Resolved:
    intent: Intent
    args: dict
    relevance: float


# ── the router ───────────────────────────────────────────────────────

class IntentRouter:
    def __init__(self, vector_store, tool_router):
        self._vs = vector_store
        self._router = tool_router  # kept for parity; core.py does the call_tool
        self._ready = False
        if getattr(config, "FAST_INTENT_ENABLED", True):
            try:
                self._seed()
                self._ready = True
            except Exception as e:  # never let seeding break agent startup
                print(f"  [intent] seeding failed, fast-path disabled: {e}")

    # -- seeding --

    def _collection(self):
        return self._vs.collections[_COLLECTION]

    @staticmethod
    def _version() -> str:
        blob = "|".join(f"{i.id}:{'~'.join(i.examples)}" for i in INTENTS)
        blob += "||DECOYS:" + "~".join(DECOYS)
        return hashlib.sha1(blob.encode()).hexdigest()[:16]

    def _seed(self) -> None:
        """(Re)populate the voice_intents collection from INTENTS. Skips work when
        the registry is unchanged since the last seed (version sentinel)."""
        col = self._collection()
        version = self._version()
        try:
            sentinel = col.get(ids=["__version__"])
            if sentinel["ids"] and (sentinel["metadatas"][0] or {}).get("version") == version:
                return  # already up to date
        except Exception:
            pass

        # Clear and rebuild.
        try:
            existing = col.get()["ids"]
            if existing:
                col.delete(ids=existing)
        except Exception:
            pass

        docs, metas, ids = [], [], []
        for intent in INTENTS:
            for j, ex in enumerate(intent.examples):
                docs.append(ex)
                metas.append({"intent": intent.id})
                ids.append(f"{intent.id}#{j}")
        for j, ex in enumerate(DECOYS):
            docs.append(ex)
            metas.append({"intent": "__reject__"})
            ids.append(f"__reject__#{j}")
        docs.append("__version__")
        metas.append({"intent": "__meta__", "version": version})
        ids.append("__version__")
        col.add(documents=docs, metadatas=metas, ids=ids)
        print(f"  [intent] seeded {len(INTENTS)} intents / {len(docs) - 1} examples (v{version})")

    # -- matching --

    def resolve(self, text: str) -> Optional[Resolved]:
        """Return the matched intent + extracted args, or None to use the LLM.
        Robust: any failure (Chroma down, bad query) returns None."""
        if not self._ready or not text.strip():
            return None
        try:
            col = self._collection()
            if col.count() == 0:
                return None
            res = col.query(query_texts=[text], n_results=1)
            if not res["ids"] or not res["ids"][0]:
                return None
            intent_id = (res["metadatas"][0][0] or {}).get("intent")
            distance = res["distances"][0][0]
            relevance = 1.0 / (1.0 + distance)
        except Exception as e:
            print(f"  [intent] query failed: {e}")
            return None

        intent = _BY_ID.get(intent_id)
        if intent is None or relevance < float(getattr(config, "FAST_INTENT_THRESHOLD", 0.62)):
            return None
        floor = HIGH_CONFIDENCE_INTENTS.get(intent.id)
        if floor is not None and relevance < floor:
            print(f"  [intent] '{text}' matched {intent.id} at {relevance:.3f} but that "
                  f"intent needs {floor} — deferring to the LLM")
            return None

        args = intent.build_args(text)
        if args is None:
            # Matched an intent but couldn't extract a required slot — let the LLM
            # handle it (e.g. "turn the volume up" with no number).
            return None
        args = {**_FIXED_ARGS.get(intent.id, {}), **args}
        return Resolved(intent=intent, args=args, relevance=round(relevance, 3))
