# Route "Contact Us" submissions to dedicated per-use-case forms

**Project:** SLYD Platform (website / platform intake)
**Date:** 2026-08-14
**Author:** e503dc75-e0cf-4a94-b311-c18127000c13
**Directory:** /Users/masongill/Slyd-Platform/admin

## What Was Done

Nothing yet — this doc exists to hold the task. Raised by Mason on 2026-08-14.

## To Do Next

Audit **all form submissions on prod** and work out how to redirect people off
the generic "Contact Us" form and onto a dedicated form for their actual use
case, so the data lands structured instead of as free text.

Steps:

1. **Inventory what's coming in.** Pull the real Contact Us submissions from
   prod and classify them by what the person actually wanted (selling hardware,
   buying capacity, broker intro, support, partnership, press, …). The
   distribution decides which dedicated forms are worth building — do this
   before designing anything.
2. **Map each bucket to an existing intake path** where one already exists.
   Deal OS already has structured intakes (sell submissions, broker
   submissions, site submissions, Deal OS access requests) — some Contact Us
   traffic is likely people who couldn't find those.
3. **Identify the gaps** — buckets with real volume and no dedicated form.
4. **Design the routing.** Either a use-case picker in front of Contact Us, or
   better entry points on the pages where each intent starts, so the generic
   form becomes the fallback rather than the default.
5. **Keep a catch-all.** Contact Us should still exist for anything unclassified
   — the goal is to shrink it, not delete it.

**Why it matters:** free-text contact submissions can't be matched, routed,
attributed, or reported on. Every intent that gets its own form becomes a
structured record the platform can act on.
