# Hexi Terminal Notifications — Command Failures + User Watch Rules

**Project:** Hexi
**Date:** 2026-08-05
**Author:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
**Directory:** /Users/masongill/Hexi

## What Was Done

### Update (same day): click-through + context lines

Clicking a terminal notification now jumps to its tab and scrolls the
scrollback to the matched line; watch-rule notifications also carry the 3
preceding output lines, shown as a monospaced block in the inbox row.

- **Anchor mechanics**: absolute line = `totalLinesTrimmed + topVisibleRow +
  cursor.y`, recorded at match/finish time. `Buffer.totalLinesTrimmed` is
  public and documented for exactly this (trim-proof anchoring);
  `Buffer.yBase` is NOT public, so the cursor row is only derivable while the
  view is pinned to the bottom — anchor is `nil` if the user is scrolled up
  (`scrollPosition < 1`) or in the alternate screen. Click calls
  `PTYSession.scroll(toAnchor:)` → `terminalView.scrollTo(row: anchor -
  totalLinesTrimmed - 3)`, clamped.
- **Widened, not redesigned**: `AppNotification` gained `details: String?`
  (display-only context block — actions stay out of the type). The
  tab/anchor target lives reporter-side in a `[notificationID: Target]` map,
  NOT in AppNotification. `NotificationInboxActions` gained `open(UUID)`
  (defaulted, so plugins/other call sites unaffected). Row tap = markRead +
  open; the inbox only slides closed when the tap actually went somewhere
  (`TabManager.openNotification` returns Bool; false for targetless/closed-tab).
- `OutputScanner.Match` gained `context: [String]` (ring buffer of last 3
  cleaned lines); `onOutputMatch` now passes an `OutputMatch` struct
  {ruleID, line, context, anchor}; `CommandOutcome` gained `anchor`.

The notification inbox's first real producers, per Mason's spec: (1) an opt-in
toggle that posts when a command exits with an error code, and (2) user-authored
watch rules — a plain word or a regex — matched against every line of terminal
output in every tab. Deliberately no built-in error patterns: the user decides
what matters in their logs. Continues
[hexi-notification-inbox-structure.md](hexi-notification-inbox-structure.md).

### How the signals are captured

- **Exit codes** were already there: the zsh shim's OSC 133 `D;<code>` marks.
  New: the shim's `preexec` now also emits **OSC 7773** (Hexi-private) carrying
  the command line (`$1`, control chars → spaces via `${1//[^[:print:]]/ }`,
  truncated to 200), so a failure notification can say *what* failed.
  `PTYSession` times commands (`ContinuousClock` at the `C` mark) and fires
  `onCommandFinished(CommandOutcome{command?, exitCode, duration, directory})`.
- **Output lines**: SwiftTerm's `LocalProcessTerminalView.dataReceived` is
  `open`, so a private `TappedTerminalView` subclass tees the raw PTY bytes to
  an `OutputScanner` before rendering. Scanner: line assembly across chunks
  (LF *and* CR flush — progress bars), ANSI/OSC stripping, then
  NSRegularExpression per rule. Word rules compile to
  `(?<!\w)escaped(?!\w)` case-insensitive ("ERR" hits `[12:10:27 ERR]`, not
  "stderr"); regex rules taken as written. 512-byte line cap; with zero rules
  the scanner does nothing at all.

### Pieces, by package

- **HexiCore** — `NotificationRule` {pattern, isRegex, isEnabled} +
  `TerminalNotificationSettings` {notifyOnCommandFailure (default OFF), rules}.
- **HexiTerminal** — `OutputScanner`, `OSCCommandLine` (7773), zshrc preexec
  change, `PTYSession.onCommandFinished` / `.onOutputMatch` /
  `.setWatchRules(_:)`, `TappedTerminalView`.
- **HexiPersistence** — `NotificationRulesStore` (`notifications.json`,
  mirrors AISettingsStore) with an `onChange` closure so live sessions get new
  rules pushed (they hold compiled copies and can't observe the store).
- **HexiUI** — `NotificationSettingsView` (toggle + editable rules list with
  Word/Regex segmented picker, enable checkbox, remove button, live regex
  validity warning). `SettingsView` gained an injected `notificationsSection`.
- **App** — `TerminalNotificationReporter` (App/Notifications/): created by
  `TabManager`, attached to every tab's session. Failure rules: code ≠ 0 and
  ≠ 130 (Ctrl-C), and only when the tab isn't visible OR the command ran ≥ 10 s
  (you watched short failures happen). Watch-rule matches: 30 s cooldown per
  (tab, rule) so a crash loop posts once. Posts through `NotificationPosting` —
  the same write path plugins use. `AppContainer.notificationRules`;
  Settings wired in `SettingsScene`.

### Decisions worth remembering

- Events are closures on `PTYSession`, not observable state — a producer needs
  each finish exactly once; `lastExitCode` can't distinguish two identical
  failures.
- Rule matching runs inside HexiTerminal against compiled rules (pushed on
  attach and on settings change), not per-line callbacks to the app — keeps
  per-byte cost near zero.
- Failure toggle ships OFF; watch rules are inherently opt-in (empty list).
- Only zsh-with-integration reports exit codes; the output scanner works for
  any process regardless.

### Verification

- 18 HexiTerminal tests (10 new scanner), 24 HexiPersistence (3 new store),
  63 HexiCore — all green. App builds clean after `xcodegen generate`.
- zsh sanitizer checked directly: ESC/tab → spaces, 200-char truncation.
- `.build` staleness gotcha again after adding the HexiCore model —
  `rm -rf .build` in dependent packages before `swift test`.

## To Do Next

- Mason to test live: Settings → Notifications (toggle + a rule, e.g. word
  "ERR"), run a failing command in a background tab, watch the bell badge.
  Needs a reinstall (`./release.sh`) — the shim rewrite also updates
  `~/Library/Application Support/Hexi/ShellIntegration`; existing shells keep
  the old hooks until a new tab.
- Possible later: click-through from notification to the offending tab (needs
  an action field on `AppNotification`), coalesced "+N more" counts instead of
  cooldown silence, per-project rules via `.hexi`.
