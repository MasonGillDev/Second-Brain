# Hexi Plugin Architecture — Options Analysis

**Project:** Hexi
**Date:** 2026-08-05
**Author:** ec6e2762-105a-4cc6-ab87-a3fae8ef1764
**Directory:** /Users/masongill/Hexi

## What Was Done

Surveyed the option space for a Hexi plugin system, covering two distinct needs:
simple installable commands, and plugins that fundamentally change the UI/behavior.

Key starting advantage: `AppContainer` is a composition root that hands all services
downstream as protocols (`FileOperating`, `GitInspecting`, `FilePreviewLoading`,
etc.) — Hexi already has a host API in all but name.

### Options considered

1. **Declarative/script plugin packs** — evolve the existing `.hexi` folder-script
   system into installable packs under `~/Library/Application Support/Hexi/Plugins/`
   with a manifest (palette entries, file-type associations) plus scripts. Reuses
   the existing trust store, danger grading, and header parser. Low cost; cannot
   create new UI.
2. **Compiled-in Swift package plugins** — a `HexiPlugin` protocol; each plugin is
   a Swift package registered in `AppContainer`, linked at build time. Full SwiftUI
   power; install requires a rebuild (acceptable while Mason is the only user).
3. **Dynamic loading (dylib/NSBundle)** — rejected for now: Hardened Runtime
   library validation blocks unsigned-by-team dylibs (needs
   `disable-library-validation` entitlement), plugin-API ABI fragility across
   toolchains, plugin crash = app crash. Only buys install-without-rebuild.
4. **Out-of-process (ExtensionKit / XPC / embedded JS or WASM)** — the
   real-product answer with crash isolation and sandboxing; a major infrastructure
   project that only pays off with untrusted third-party plugin authors. Deferred.

### Recommendation (proposed, not yet decided)

Two tiers:
- **Tier 1:** installable script/manifest plugin packs (option 1) for simple commands.
- **Tier 2:** static `HexiPlugin` Swift packages (option 2) for UI-changing plugins,
  keeping experimental features out of core.
- Design the Tier 2 protocol as if plugins were untrusted: plugins receive a
  `PluginContext` of the existing service protocols and contribute registrations
  (palette items, panes, sidebar sections, previewers, toolbar actions, file-list
  decorations) rather than mutating views. This surface can later move
  out-of-process without redesign if Hexi gains real users.

Candidate extension points identified from the current UI: palette items (via
`PaletteBuilder`), command panel sections, file previewers, sidebar sections,
whole panes/tabs, file-list decorations (generalizing the git-status pattern).

## To Do Next

- ~~Design and build Tier 2~~ — done 2026-08-05, see
  [hexi-plugin-system-and-claude-plugin.md](hexi-plugin-system-and-claude-plugin.md):
  HexiPluginKit + the Claude Code plugin (sessions widget + tab status dot).
- Tier 1 (installable script/manifest packs) not yet built.
