# Pulse Fairways — 9-Hole Golf Game in Python

**Project:** ClaudeTest/fable5 (Pulse Fairways)
**Date:** 2026-07-28
**Author:** 4986f611-8ce1-41bd-b123-f7cc4ceadbd6
**Directory:** /Users/masongill/ClaudeTest/fable5

## What Was Done

**2026-07-28 (later still): intermittent macOS rendering corruption fix.**
Mason hit occasional glitch frames (static ground layers dark/missing,
scene scaled). Headless repro was clean → macOS/Metal display issue, not
draw logic. Fixes: `.convert()` all cached surfaces to display format,
`set_mode(..., pygame.SCALED, vsync=1)` for safe fullscreen/HiDPI, reuse
the rain overlay surface, cache minimap scaling (was smoothscaling every
frame). Lesson: always convert() prerendered surfaces on macOS pygame.

**2026-07-28 (later): aim-arc accuracy fix after first playtest.** Mason
reported shots always landing short of the white preview arc. Three causes,
all fixed:
1. The arc always assumed 100% power — now it recomputes live against the
   breathing ring's power (quantized 0.04, cached, ~1 ms/sim) and stays on
   screen through the power/strike phases, so the line shows where *your*
   power actually lands.
2. Any non-centred strike bled up to 20% ball speed even inside the gate —
   added a grace zone (no loss below |err| 0.35, then 0.22/unit).
3. Preview integrated at h=0.02 vs live physics h=1/240 — aligned; preview
   carry now matches live carry exactly.
Also replaced the guessed rollout line with a per-club calibrated value
(full flat-fairway sim total minus preview carry: DR 53 m … LW 10 m,
halved in rain), scaled by power.

Built a complete 9-hole golf game from scratch in Python (pygame-ce 2.5.7 +
numpy, venv at `.venv/`). Run with `.venv/bin/python run_golf.py`. Everything
is procedural — zero asset files.

**Architecture** (`golf/` package):
- `config.py` — screen/scale constants, palettes, club table, difficulty presets
- `audio.py` — all SFX + generative soundtrack synthesized with numpy at startup
  (FFT bandpass filtering, envelopes; ~51 s seamless pad/pluck music loop)
- `weather.py` — 9-hole forecast with frontal progression (Sunny→Breezy→Windy→
  Showers→Storm Markov chain), time-varying gusting wind model
- `course.py` — 9 hand-designed holes (par 36): geometry as fairway centrelines
  with widths, bunker ellipses, water polygons, tree clumps; greens are slope
  plane + gaussian mounds with analytic gradient
- `physics.py` — 3D flight (quadratic drag, Magnus lift/sidespin, altitude-scaled
  wind), surface-dependent bounce/roll, backspin bite/suck-back, tree canopy
  deflection, cup capture with lip-outs (capture speed 1.63 m/s), slope-driven
  putting
- `swing.py` — the "Pulse Swing": breathing power ring (release to lock) then an
  orbiting comet struck through a gold gate at the top; angular error → push/pull
  + unwanted sidespin; deliberately NOT a power-bar or 3-click meter
- `render.py` — procedural art: mow-striped fairways (BLEND_RGBA_MIN polygon
  masking), noise-textured rough, slope-shaded greens, animated break dots that
  drift downhill, water shimmer, rain overlay, waving flag, HUD, minimap,
  forecast panel, weather icons
- `game.py` — state machine (menu/intro/round/hole-done/round-done/pause),
  tutorial on hole 1 (toggleable, T hides), scorecard (TAB), forecast (F)

**Key decisions & tuning:**
- Club ball-speeds were calibrated by binary search against target carries
  (Driver 210 m … LW 50 m) with MAGNUS_K=0.00024 — naive values gave broken
  gapping (spin lift made a 6-iron carry like a driver).
- Difficulty scales wind (0.55×/1.0×/1.45×), ring breathing speed, comet speed,
  and strike-gate width — not stroke penalties.
- Two prerendered surfaces per hole (course @2.3 px/m, green closeup @11 px/m)
  keep 58+ fps with no per-frame scaling; camera clamps to surface bounds.
- Putter max speed 7.5 m/s (9.0 rolled 65 m on green decel 0.62 m/s² — absurd).
- **Bug worth remembering:** input events were processed before the
  aim-follows-mouse update in `update_round`, so a swing begun immediately after
  the ball stopped committed a stale heading from the previous ball position.
  Fixed by updating aim before the event loop. Found via headless autoplay test.

**Testing:** headless (SDL dummy drivers) autoplay bot in scratchpad completes
full 9-hole rounds (~42–47 strokes on Pro — believable), plus screenshot
rendering of every screen state for visual review. Real-window run: 1 s init,
58 fps.

## To Do Next

- Menu backdrop is functional but plain — could compose a nicer title scene.
- Possible enhancements: hole flyover camera at intro, persistent best-score
  save file, gamepad support, per-hole wind exposure shown in HUD.
