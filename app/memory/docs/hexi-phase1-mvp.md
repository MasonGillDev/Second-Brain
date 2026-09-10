# Hexi — Phase 1 MVP (detection engine, filesystem, UI, tabs)

**Project:** Hexi (macOS file navigator + command launcher, formerly "Helm")
**Date:** 2026-07-31
**Author:** 492f24b7-a5cd-44ef-8e0a-fbc2bb597744
**Directory:** /Users/masongill/Hexi

Continues [helm-phase0-terminal-spike.md](helm-phase0-terminal-spike.md). Plan and
remaining gaps live in the repo at `Docs/phase-1-plan.md`.

## What Was Done

Built Phase 1 of the app plan. The app now does the thing it exists to do: navigate
to a project folder and that project's own commands appear as buttons, running in
that tab's shell. 109 tests across five packages; five commits on `phase-1-mvp`.

### Renamed Helm → Hexi

"Helm" collided with the Kubernetes package manager — already on most of the target
audience's machines, and the plugin doc's proposed `helm plugin install` CLI would
have fought it on PATH. Done before Phase 1 rather than after, because the name was
about to be baked into `.hexi/` and the `# hexi:` script prefix, which live in
users' own repos. `Branding` in HexiCore holds those strings so a future rename is
one edit.

Repo directory is now `/Users/masongill/Hexi`.

### Packages built

- **HexiCore** — models and protocols, no dependencies. `ProjectKind` is a string
  wrapper rather than an enum so a plugin adding "Terraform" needs no Core change.
- **HexiFileSystem** — scanner, FSEvents watcher, cancellable size calculator.
- **HexiCommands** — rules, dynamic parsers, custom `.hexi/` scripts, trust store.
- **HexiUI** — views, depends on HexiCore only.
- App gains `TabSession`/`TabManager`; `App/Spike` deleted.

### Decisions that departed from the planning docs

- **Dropped the `Detectors/` folder.** `folder-structure.md` listed both
  per-language Swift detectors and a JSON rule engine, while ADR-0004 says JSON
  rules win. `NodeDetector.swift` would have been a Swift file duplicating four
  lines of JSON. Rules are data; code handles only what data cannot express.
- **Moved the script trust flow into Phase 1.** The plan had custom commands in
  Phase 1 and the confirmation layer in Phase 2 — which ships one-click execution of
  arbitrary `.sh` files *without* the confirmation. §6.5 calls first-run confirmation
  non-negotiable, so it shipped alongside the feature it protects.
- **`CommandGroup` → `CommandSection`.** SwiftUI already defines `CommandGroup` for
  menus, and both are in scope wherever views live. Qualifying every use site forever
  is worse than renaming once.
- **`TerminalPane` is generic over its content.** The folder structure said HexiUI
  imports only HexiCore *and* that its terminal pane hosts HexiTerminal's view. App
  injects the real SwiftTerm view instead.

### Bugs found by running things rather than reading them

**FSEvents path matching was silently broken.** `resolvingSymlinksInPath()` is the
wrong tool: it *strips* a leading `/private` rather than adding one, so a watcher on
`/var/folders/…` compared against FSEvents' `/private/var/folders/…` and matched
nothing. A standalone probe printing raw callback paths found it in one run, along
with a trailing slash on reported paths. Fix: canonicalize with `realpath(3)` and
trim. Also filter events to the watched directory itself — FSEvents is recursive
whether you want it or not, so without the filter, opening a folder above
`node_modules` re-scans on every unrelated write beneath it.

**Auto-computing folder size tripped a macOS privacy prompt on launch.** Walking
`$HOME` reached `~/Pictures` and made the app demand Photo Library access before the
user had done anything. Added `FolderSizePolicy`: roots standing for a whole account
or disk offer the size on request instead, the way Get Info works. The real fix is
Full Disk Access onboarding, which does not exist yet.

**A SwiftUI View cannot be instantiated in a headless `swift test` process** — it
traps with SIGTRAP. Moving list filtering into `FileListFiltering` fixed it, which
the architecture already required ("views hold no logic beyond layout and binding").

**Not our bug, worth knowing:** the `command not found: brew` line in the terminal
comes from `~/.zshenv:5` calling `$(brew --prefix open-mpi)` before Homebrew is on
PATH. It reproduces with no shell integration at all and with a Terminal-like PATH.
Fix would be using `/opt/homebrew/bin/brew` explicitly or moving that line to
`.zprofile`. The powerlevel10k error is likewise a missing `~/powerlevel10k`.

### Detection details that decide whether the panel is trustworthy

- Makefile parsing rejects assignments, special targets, pattern rules, names built
  from variables, and tab-indented recipe lines. The fixture is written to break
  naive parsers and `make` itself parses it.
- Package manager comes from the lockfile — `npm install` in a pnpm project is a
  real way to corrupt `node_modules`.
- Script order is recovered from raw `package.json` text, since decoding a JSON
  object loses declaration order and people put `dev` first deliberately.
- Lifecycle hooks are hidden only when the `pre`/`post` remainder names another
  script, so `preview` survives while `prebuild` does not.
- `ScriptApproval` carries contents and fingerprint together; a test writes to the
  file between reading and approving to prove the swapped text cannot be blessed.

## To Do Next

`Docs/phase-1-plan.md` has the full list under "Not yet done". The ones that matter:

- **Full Disk Access onboarding** (`App/Permissions/`). Navigating into `~/Documents`
  still triggers a per-folder privacy prompt. Biggest gap before alpha testers.
- **HexiGit** — never built. The `.git` detector works without it, but the info panel
  shows no branch or dirty count.
- **HexiUI previews and `PreviewFixtures.swift`** — three tests exist, all on
  filtering; every screen is supposed to have a preview driven by fakes.
- **`PTYSession.run` appends to a half-typed prompt.** Decide whether to send Ctrl-U
  first.
- Then Phase 2: full detector set, user-editable rules, sidebar, file operations,
  settings, tab restore.
