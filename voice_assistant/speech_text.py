"""
Text tidy-ups applied immediately before synthesis.

Kokoro reads what it is given, so "6:45 PM" comes out as a literal clock reading
rather than the way a person says it. The system prompts ask for spoken-style
times, and mostly get them — but replies are assembled from tool output the model
often echoes verbatim ("deep clean at 2:50"), so a prompt alone leaves colons in
about half the time. This is the deterministic backstop: every spoken string goes
through here no matter which model produced it.
"""

import re

# Guarded on BOTH sides against a neighbouring colon: without the lookbehind, a
# rejected "10:03" in "10:03:45" just lets the scan slide forward and match the
# middle "03:45" instead. Requiring two minute digits keeps ratios and scores
# ("10:1", "3:2") out.
_TIME_RE = re.compile(r"(?<!:)\b(\d{1,2}):([0-5]\d)\b(?!:)")


def _spoken_time(match: re.Match) -> str:
    hour, minutes = match.group(1), match.group(2)
    if minutes == "00":
        return hour                       # "5:00 PM" -> "5 PM"
    if minutes[0] == "0":
        return f"{hour} oh {minutes[1]}"  # "6:05" -> "6 oh 5"
    return f"{hour} {minutes}"            # "6:45" -> "6 45"


def normalize(text: str) -> str:
    """Rewrite anything that a speech engine would mispronounce."""
    if not text:
        return text
    return _TIME_RE.sub(_spoken_time, text)
