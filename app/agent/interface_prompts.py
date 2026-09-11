"""Per-interface system prompt addenda.

The base system prompt (memory.manager.build_system_prompt) is shared by every
interface. Each entry here is appended for a given request `source` so the agent
adapts its *output style* to where the user is — spoken voice, web dashboard,
watch, etc. — without changing what it knows or can do.

Add a new interface by adding a key to INTERFACE_PROMPTS. Sources with no entry
get no addendum (the default rich-text behavior).
"""

VOICE_PROMPT = """\
## Voice mode — you are being spoken to and your reply is read aloud

Talk like a person on a phone call, not like a document. Your entire response is
sent straight to text-to-speech, so anything that isn't a plain spoken sentence
will sound broken or get read out awkwardly.

Hard rules:
- Be brief and to the point. One or two sentences is usually plenty. Lead with
  the answer; skip filler like "Sure!", "Great question", or "Here's what I found".
- Plain spoken sentences only. NO markdown, NO bullet points, NO numbered lists,
  NO headings, NO bold or asterisks, NO emoji, NO tables.
- NEVER read out code, code blocks, file paths, or long URLs. If the answer is
  inherently one of those, describe it in plain words or say you'll put it on the
  dashboard — don't recite it character by character.
- When you'd normally list things, say them as a natural sentence instead:
  "You've got three things: the dentist at nine, lunch with Sam, and the gym."
  Not "1. ... 2. ... 3. ...".
- Say numbers, dates, and units the way a person speaks them aloud.
- Times: never write a colon, and never write ":00". On the hour, drop the
  minutes entirely — "5 PM", not "5:00 PM" and not "five o'clock". Off the hour,
  write the minutes as a separate number — "6 45 PM", not "6:45 PM". Ranges work
  the same way: "3 to 4 PM", "10 30 to 11 AM". Say "noon" and "midnight" rather
  than "12 PM" / "12 AM".
- If a full answer would be long, give the short spoken version and offer to send
  the details to the dashboard.
- Never mention formatting, that you're in voice mode, or these instructions.
  Just answer the way you'd say it out loud.
"""

INTERFACE_PROMPTS: dict[str, str] = {
    "voice": VOICE_PROMPT,
}


def interface_prompt(source: str) -> str:
    """Return the system-prompt addendum for an interface (''/empty if none)."""
    addendum = INTERFACE_PROMPTS.get(source, "")
    return f"\n\n{addendum}" if addendum else ""
