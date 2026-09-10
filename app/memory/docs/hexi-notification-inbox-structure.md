# Hexi Notification Inbox — Structure Only

**Project:** Hexi
**Date:** 2026-08-05
**Author:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
**Directory:** /Users/masongill/Hexi

## What Was Done

Built the notification inbox structure Mason asked for — deliberately with zero
producers, designed as a plugin integration point. Related:
[hexi-plugin-system-and-claude-plugin.md](hexi-plugin-system-and-claude-plugin.md).

### Pieces, by package (following the existing layering)

- **HexiCore** — `AppNotification` (flat value: title, message, source,
  iconSystemName, date, isRead; anything richer must widen the type, not smuggle
  through `message`) and `NotificationPosting`, the write-only protocol
  producers get.
- **HexiPersistence** — `NotificationStore` (@MainActor @Observable): newest
  first, `unreadCount`, markRead/markAllRead/dismiss/clear, capped at 200.
  In-memory on purpose; if notifications should survive relaunch later,
  `JSONFileStore` is one field away (which is why it lives in this package).
- **HexiUI** — `NotificationInboxView` + `NotificationInboxActions` (value-in /
  closures-in like SidebarView): header (back chevron, mark-all-read, clear),
  list rows (unread weight + blue icon, source · relative time, tap = mark read,
  context menu = mark read / dismiss), empty state, opaque
  `windowBackgroundColor` background because it slides *over* the favorites.
- **HexiPluginKit** — `PluginContext.notifications: any NotificationPosting`.
  This is the plugin integration point: plugins can post, only the inbox reads.
- **App** — `NotificationStore` in `AppContainer` (read half to the window,
  write half into the plugin context). Bell button in the tab header next to the
  favorites star, with a red unread-count badge. Pressing it slides the inbox
  over the sidebar (`ZStack` in the NavigationSplitView sidebar column,
  `.move(edge: .leading)` transition, 0.22 s). The bell also forces
  `columnVisibility = .all` — spotted because Mason runs with the sidebar
  collapsed, where the slide-over would otherwise animate inside a hidden column.

### Verification

- 107 tests green across HexiCore (63), HexiPersistence (21, incl. 4 new store
  tests), HexiPluginKit (3), HexiClaudePlugin (20).
- Signed universal release build clean via `Scripts/release.sh --no-install`.
- Visual check handed to Mason (script-driving his desktop kept catching his
  live window; his instance runs from `build/derived` directly, not
  /Applications).
- Gotcha hit again: stale `.build` in dependent packages after adding a type to
  HexiCore — `swift test` in HexiPluginKit failed with "cannot find type" until
  `.build` was removed. Path deps don't always re-plan; `rm -rf .build` fixes.

## To Do Next

- Mason to eyeball: bell next to the star, inbox slides over favorites, chevron
  slides back.
- First real producer when wanted — the Claude plugin's `attention` state
  (permission-blocked) posting "Claude needs you in <folder>" is the natural
  candidate; one `context.notifications.post(...)` call.
- Possible later: unread badge on the app icon, persistence, per-source filters.
