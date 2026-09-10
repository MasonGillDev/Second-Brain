# Links of the Hollow — Full Codebase Quality Review and Fixes

**Project:** Links of the Hollow (pygame golf, opus5)
**Date:** 2026-07-28
**Author:** 31abcef0-f1e0-4d0b-8a3d-21fcc0819e64
**Directory:** /Users/masongill/ClaudeTest/opus5

## What Was Done

Reviewed the whole codebase (~5,900 lines, 13 modules) with three parallel
review agents, verified the top findings against source, then **applied the
fixes**. Final state: 6,328 lines across 14 modules, pyflakes clean, a full
9-hole round auto-plays on all difficulties.

### Bugs fixed (all verified before and after)
- `game.py` — set-up forecast was built from `setup_seed`, then `start_round`
  rerolled the seed before building the real forecast, so the previewed
  weather was never the weather you played. `_roll_forecast` now owns the
  seed; `start_round` reuses it. Regression test asserts preview == played.
- `weather.py:speed_at` — could go negative at high gust multipliers,
  silently reversing the wind 180°. Gust oscillator clamped to ±1 and the
  total clamped at 0. Verified over a 4,000-step sweep on THE OPEN.
- `render.py` / `ui.py` — RGBA colours passed to `pygame.draw.*` on opaque
  targets (tracer fade, green-read fade, rain, gust ring). pygame drops the
  alpha there, so none of the fades rendered. Added a cached `_overlay()`
  RGBA scratch layer; rain uses a uniform `set_alpha` instead.
- `game.py` — `_cam_from_ball` was a `pass` stub still called from `fire()`
  and every settle frame. Implemented as `settle_camera(dt)`; removed the
  dead `cam_mode`.
- `swing.py` — `build_strike` used a fresh unseeded `random.Random()` for
  overcoil spray, breaking the seeded-determinism contract. Now draws from
  `coil.rng`. Verified: same seed → identical strike, different seeds differ.
- `terrain.py` — `material()` used `np.round` (banker's) vs `material_s()`
  `int(g+0.5)`; they disagreed on half-cell boundaries. Both now
  `floor(g+0.5)`. Verified: 0 disagreements over 16,000 sample points.
- `physics.py` — a rolling ball was glued to the terrain forever, so it
  snapped down cliff/bunker-lip faces instead of launching. Added a
  release check (`ROLL_RELEASE_DROP`).
- `physics.py:preview_flight` — ignored `axis_deg`, so previewed shots flew
  straight while the real shot drew/faded. Now shares `spin_vector()` with
  `simulate`; verified preview carry matches sim carry to 0.1 m.
- `game.py` — OB banner said "playing three off the tee" but the rule
  implemented is stroke-and-distance from the previous spot. Text corrected.

### Thread-safety
- `physics.py` — carry tables built into a local dict and published in one
  atomic rebind, with the contract documented. Readers take a single
  reference.
- `audio.py` — `_pending`/`_cur_music` now under the same lock as `music`;
  each music piece dispatches as soon as it is composed (menu track no
  longer waits for the course track). Added `set_reserved(4)` so an SFX
  burst can't have `find_channel(force=True)` steal the music channel.
- `course.py` — `Course.get` guarded by a lock (holes take seconds to build).

### Structure
- **New `golf/screens.py` (587 lines)** — all HUD and screen drawing moved
  out of `Game`, which drops from ~1,550 to 1,089 lines. The `draw()`
  if/elif ladder became a `_SCREENS` dispatch table.
- `config.py` — five parallel `MAT_*` dicts replaced by one `MATERIALS`
  tuple of `Material` dataclasses; the dicts are derived. `Difficulty` is a
  frozen dataclass. `FLIGHTS`/`VIEWS` moved here (shared by game + screens).
- `swing.py` — `readout()` returns a frozen `Readout` dataclass with units
  in the field names (`face_units` vs `path_deg`); the old dict mixed raw
  plane units and degrees with no signal.
- `physics.py` — extracted `stimp_to_mu`, `wind_profile`, `spin_vector`
  (each was duplicated); added a `Bounce` NamedTuple so consumers read
  `b.mat` not `b[4]`.
- `course.py` — `Course.yards(i)` replaces the `course._yards` dict that
  `game.py` grafted on and `ui.py` read via `getattr`. All nine hole specs
  are validated at construction.

### Performance (measured, not assumed)
- Sun glow sprite cached: 0.317 ms → ~0 ms per frame (was rebuilding a
  ~460×460 surface with 10 filled circles every frame).
- Green-read slope grid cached per hole: 2.80 → 1.81 ms, saves ~1 ms on
  every putting frame.
- `ui.panel`/`ui.text` memoised (surface alloc + double `font.render`):
  ~4% of total frame time.
- `dim()` overlay, tracer point array, intro minimap all hoisted out of the
  per-frame path; `trail` is a `deque(maxlen=90)`; rain allocates once and
  draws a prefix (also fixes a visible pop when intensity drifted).
- Frame times now ~12 ms behind-view, ~24 ms scout+rain (83 / 41 fps).
  Note: frame time is dominated by terrain rasterisation, so the HUD/alloc
  wins are real but modest in aggregate.

### Hygiene
Dead code removed (`shot_log`, `flash`, `holeout_t`, `intro_t`, `ch_coil`,
unused `quality` params — `HoleVisual.quality` now actually drives shadow
march length, the `1.22/1.22` no-op, triple-assigned spin axis, a discarded
cumsum in `_box_lp`, `np.take(np.arange(M), idx)`). Magic numbers named.
Redundant function-level imports (none were real cycles) hoisted. `_env`
rewritten as an explicit segment list — **verified bit-identical across
1,944 parameter combinations**. `box_blur(radius=0)` now returns a copy;
`catmull_rom` guards <2 points. `main.py` no longer mutates `sys.path`.

### Verification
- 3 full auto-played rounds (SUNDAY MEDAL / CLUB CHAMPIONSHIP / THE OPEN),
  all 9 holes each, exercising water drops, OB, and max-score pickups.
- All 10 screens plus HUD variants (map off, banner, tutorial, putting,
  rain, scout view) render without error.
- pyflakes clean across all 14 files.

## To Do Next
Deliberately not done — pure-structure refactors with regression risk and no
behavioural benefit:
- `course.py:build_hole` is still a ~255-line pipeline; splitting it into
  `_spine_fields` / `_apply_water` / `_apply_bunkers` / `_green_surface`
  would make the stage-ordering invariants visible.
- `physics.py:simulate` + `_ground_phase` (~245 lines combined) could split
  into `_launch_state` / `_fly` / `_bounce_step` / `_roll_step` / `_try_hole`
  so cup capture is unit-testable without running a whole shot.
- `Game` is still 1,089 lines; the rules (drop_point, forward_drop,
  max_score) and the camera rig are the next candidates to extract.
- There is no test suite in the repo — the verification above was ad-hoc
  scripts. Worth landing as `tests/`.
