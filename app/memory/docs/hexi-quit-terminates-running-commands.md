# Hexi: quitting stops the commands its shells started

**Project:** Hexi
**Date:** 2026-08-04
**Author:** 029dc7ac-4e16-4081-aaf6-c472d5db7b49
**Directory:** /Users/masongill/Hexi/Packages/HexiUI

## What Was Done

Quitting Hexi left dev servers running. Two separate causes, both fixed.

**1. Nothing was calling `terminateAll()`.** `TabManager.terminateAll()` existed but had
no caller — SwiftUI's `App` has no termination hook, and `.onDisappear` only persisted
state. Added `AppDelegate` (`App/Composition/AppDelegate.swift`), wired in via
`@NSApplicationDelegateAdaptor` on `HexiApp`, with `tabs` assigned from the scene's
`.onAppear` (SwiftUI builds the delegate before there are tabs to hand it).

**2. Killing the shell was never going to be enough.** SwiftTerm's `terminate()` sends
`SIGTERM` to the shell pid only. Under job control each job runs in its *own* process
group, so a `npm run dev` is simply reparented to launchd when its shell dies — still
holding its port. New `ProcessTree` (`Packages/HexiTerminal/.../ProcessTree.swift`) reads
the process table via `sysctl(KERN_PROC_ALL)`, walks the tree from the shell pid, and
signals every descendant plus each distinct descendant process group (the group half
catches processes forked *after* the snapshot — a build script spawning its next child).

Termination is two passes: `SIGTERM` first so a server can close listeners and drop lock
files, then `SIGKILL` 400 ms later for anything that ignored it. Ignored signal
dispositions are inherited across fork/exec, so one `trap "" TERM` ancestor makes a whole
subtree unkillable by `SIGTERM` — the second pass is not optional. This is why
`applicationShouldTerminate` returns `.terminateLater` and replies from a `Task`: quitting
immediately would skip the second pass and leave exactly the orphans this fixes.

**The prompt.** When anything is running, quit raises an alert — "Quit Hexi?" /
"“node” is still running. Quitting will stop it." / [Quit and Stop] [Cancel]. The names
come from `PTYSession.runningCommands`, which lists only the shell's *direct* children:
one `npm run dev` is three or four processes deep, and saying "3 commands are running"
when the user started one is worse than saying nothing.

Deliberately *not* based on `isExecuting`. That flag comes from OSC 133 shell-integration
marks — it misses background jobs (`&`) entirely and is always false in a shell Hexi
could not instrument. The process table is the ground truth.

**Side effect, worth knowing:** closing a single tab (⌘W) now also kills that tab's
commands, where before the server survived. There is no prompt on that path — only quit
asks. If that turns out to be surprising, the same alert can be reused.

### Verification

Built clean. `ProcessTree` was exercised standalone against a real 2-deep tree including a
`SIGTERM`-ignoring process (discovery order, direct-children filter, and the `SIGKILL`
follow-up all correct). End-to-end against a launched build, with a background job under a
tab's shell: the alert appears with the right text, **Cancel** leaves the app and the job
alone, **Quit and Stop** exits and takes the shell *and* the background job with it.

Trick worth reusing for GUI testing: `open -n --env ZDOTDIR=<tmp> --env HEXI_START_DIR=<dir>`
with a `.zshrc` that starts `sleep 500 &` gives a tab with a running background service
without needing keyboard focus. Driving the quit itself is best done with
`ignoring application responses / tell application id "com.masongill.Hexi" to quit` and then
AX-clicking the alert button — alerts raised by *synthesized* input (AX menu clicks, posted
`CGEvent` ⌘Q) dismissed themselves after ~1s, which is an automation artifact, not app
behaviour: the same alert raised by an AppleEvent quit stayed up indefinitely.
