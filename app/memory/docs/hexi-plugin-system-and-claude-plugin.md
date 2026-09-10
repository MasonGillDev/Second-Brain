# Hexi Plugin System (HexiPluginKit) + Claude Code Plugin

**Project:** Hexi
**Date:** 2026-08-05
**Author:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
**Directory:** /Users/masongill/Hexi

## What Was Done

**Update (same day):** Mason's live test caught the status dot never appearing.
Root cause: the dot's polling `.task` was attached to a `Group` whose content is
empty until claude is detected — Group forwards modifiers to its children, and
with no children the task attaches to nothing, so the poll that would detect
claude only starts after claude is detected. Rewritten around
`TimelineView(.periodic(by: 2))`, a concrete view that re-evaluates on schedule
even while rendering nothing. Lesson for future SwiftUI work: never hang
`.task`/`.onAppear` on conditionally-empty content. Also patched
`Scripts/release.sh` to pass `ARCHS="arm64 x86_64" ONLY_ACTIVE_ARCH=NO` on the
xcodebuild command line (command-line settings reach SwiftPM packages; the
project.yml target-level pin does not), verified with a cold signed build.
The sessions widget was confirmed working in Mason's installed build.

Implemented the Tier-2 plugin system decided in
[hexi-plugin-architecture-options.md](hexi-plugin-architecture-options.md), plus the
first real plugin: Claude Code integration.

### HexiPluginKit (new package)

Static compiled-in plugins held to out-of-process discipline: a plugin sees only
`PluginContext` (home, shared `FolderWatching`, a per-plugin data directory under
`~/Library/Application Support/Hexi/Plugins/<id>/`) and contributes registrations
rather than touching sessions or views.

- `HexiPlugin` — `id` + `activate(context) -> PluginContributions`
- Extension points: `FolderPanelProviding` (view above the command panel, nil = no
  chrome) and `TabAccessoryProviding` (small live view beside the tab title,
  given a `TabContexting`: directory + `ShellProcess` list only)
- `PluginRegistry` — activates plugins at startup in `AppContainer`; the only
  place plugins and app meet. Adding a plugin = one line in
  `AppContainer.installedPlugins`.

Wiring: `TabBarView` gained an `accessory: (UUID) -> AnyView?` closure (HexiUI
stays plugin-ignorant); `TabContentView` renders `plugins.panels(for:)` above
`CommandPanelView`; `TabSession` owns a stable `TabPluginContext` (weak adapter,
so accessory polling can never outlive-crash a closed tab).

### HexiClaudePlugin (new package)

**Recent-sessions widget** in the folder detail area. Claude Code stores
transcripts at `~/.claude/projects/<encoded-path>/<uuid>.jsonl` where encoding =
every non-alphanumeric char of the absolute path → `-` (lossy to decode, but we
only ever encode). Reads only the head (256 KB) of each transcript — files reach
45 MB — for title (summary line wins over first real user message; caveat/command
wrappers, sidechains, tool-result arrays skipped) and git branch. Newest 5 by
mtime. Click copies `claude --resume <uuid>` to the pasteboard (deliberately does
not spawn anything). Live-refreshes via FSEvents on the project dir.

**Tab status dot** for tabs whose shell has a descendant process named `claude`
(via the existing ProcessTree machinery from the quit feature). Colors: orange =
working, green = waiting for input, red = waiting on a permission decision, gray =
running but hooks not installed. State comes from Claude Code hooks: an installer
merges five events (SessionStart/UserPromptSubmit/Stop/Notification/SessionEnd)
into `~/.claude/settings.json`, each running a small sh script that writes
`state/<pid>.json` under the plugin data dir (SessionEnd deletes it). The pid link:
Claude runs hooks via `sh -c`, so `$PPID` inside the hook's shell IS the claude
process — the same pid Hexi sees in the tab's process tree. Install is
consent-gated behind a popover on the gray dot, additive/idempotent, refuses to
rewrite unparseable settings, and backs up `settings.json` to `.hexi-backup`
before first touch. Dot polls every 2 s (process snapshot + tiny state-dir read).

### Verification

- 46 tests green: HexiPluginKit 3, HexiClaudePlugin 20 (incl. an end-to-end run
  of the hook script through real /bin/sh), HexiUI 23.
- Full app build succeeds; sessions widget verified live in a launched build
  (showed the in-progress session with branch + relative time).
- Status dot unit-tested; live verification handed to Mason (driving keystrokes
  into the terminal from script proved flaky — input landed in the filter field).

### Gotcha discovered (pre-existing, not fixed)

The uncommitted release work pins `ARCHS: "arm64 x86_64"` + `ONLY_ACTIVE_ARCH: NO`
at **target level** in project.yml. Target-level ARCHS does not apply to SwiftPM
package targets, so a cold universal CLI build fails ("unable to resolve module
dependency" / x86_64 link errors) — packages build arm64-only while the app wants
both slices. Workaround that works: pass the settings globally on the command
line, `xcodebuild -scheme Hexi ARCHS="arm64 x86_64" ONLY_ACTIVE_ARCH=NO build`.
Proper fix: move those two settings from the target's `settings.base` to the
top-level `settings.base` in project.yml (left alone — it's Mason's uncommitted
release work).

## To Do Next

- Mason to live-test the status dot: launch the new build, run `claude` in a tab,
  click the gray dot → Enable Status Tracking → colors appear from the next
  session event onward.
- Possible follow-ups: `attention` state could also badge the app icon; sessions
  widget could offer "resume in this tab" once plugins get a way to run terminal
  commands (a deliberate context widening).
- Tier 1 (installable script/manifest packs) from the options doc remains unbuilt.
