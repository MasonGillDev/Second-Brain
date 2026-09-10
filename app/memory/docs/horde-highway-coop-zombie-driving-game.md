# Horde Highway — 2-Player Co-op Zombie Driving Game

**Project:** Horde Highway
**Date:** 2026-07-28
**Author:** 02e6dc52-b64e-484e-8fc0-838e3ad41055
**Directory:** /Users/masongill/ClaudeTest/HWTH

## What Was Done

### Session 2 (2026-07-28, later) -- playtest feedback round

Driven by real play feedback rather than the harness. Five changes:

**1. Fullscreen on macOS.** The window would not go fullscreen. Fixed by
creating the display with `pygame.SCALED | pygame.RESIZABLE` and toggling with
`pygame.display.toggle_fullscreen()` (F11 / F). SCALED is the key: the game
keeps rendering at a logical 1280x800 and SDL letterboxes it, *and* mouse
coordinates are translated back automatically so aiming still lines up. Without
SCALED, toggling fullscreen on mac gives a tiny window.

**2. Road hazards** (`obstacles.py`, new). Wrecks, concrete barriers, rubble and
explosive fuel drums that block the lane outright, so the driver has a reason to
work left and right. The spawner fills inward from one edge so the free lane is
always contiguous, and is hard-guaranteed to leave `OBSTACLE_MIN_GAP` open --
verified across 60s runs at both difficulty extremes with zero unpassable rows.
Everything but the barriers can be shot apart, which is the co-op out when the
driver commits to the wrong side. First version almost never spawned anything:
it picked a random type and `break`-ed out if it did not fit the remaining
budget, so a barrier roll on a narrow road produced an empty row. Now it filters
to types that still fit before choosing.

**3. The Matriarch** -- a second boss, every 4th arena (`MATRIARCH_EVERY`).
Deliberately built to punish what the Brute teaches: she keeps her distance,
spits homing acid, blinks on top of you when you get comfortable, and emits
*paired* shockwave rings so dodging the first can walk you into the second. Her
plaza is larger. Measured against the Brute with an immortal pilot and perfect
aim: 2.4x longer to kill and ~1.8x the damage output.

Her arena radius was originally 470, which is taller than the 800px screen --
with the camera locked during a fight she literally walked off the top edge.
Capped at 385 (`MATRIARCH_ARENA_RADIUS`), which is the practical ceiling: it
cannot exceed half the screen height.

**4. Directional blocking** (user request). Zombies now only stop the car in the
direction it is actually going: ones ahead kill forward momentum, ones on a
flank stop you steering *into* them but never away, and anything level with or
behind never pins you at all.

The first pass still felt like it was blocking from behind, and the thresholds
explain why: the car is 116px long, so with `behind` defined as
`dy < -half_h * 0.40` and the forward test as `dy > half_h * 0.30`, a zombie
only had to be **17px past the car's centre** to pin it -- level with the driver,
nowhere near the front bumper -- while "behind" did not begin until 23px back.
Now only the **front half** of the car can be obstructed at all (`dy >= 0`), the
forward test needs `dy > half_h * 0.45`, and the forward lane was narrowed to
`half_w * 0.9 + radius * 0.4` so a zombie merely clipping the front corner
blocks steering rather than pinning.

Verified with a placement table covering dead-ahead, front quarter, front
corner, centre, behind-centre, rear bumper and all four flanks. Time spent
pinned across a smoke run went ~30% -> ~1%.

**5. Boost economy.** Play surfaced an infinite-boost loop: plowing a horde
generated enough boost drops to fund the boosting that generated them. Fixed
from several directions at once -- drain 26 -> 30/s, ram cost 1.1 -> 1.9 per
body (this is the one that scales with how much you are plowing), pickup 42 ->
24, passive trickle 1.4 -> 0.8, drop chance 0.145 -> 0.105, boost's share of the
drop table 30 -> 19, plus a hard `MAX_PICKUPS` cap so a plow-through cannot
carpet the road. Measured worst case (holding SHIFT nonstop through hordes for
70s): boost is now actually available only 7% of the time and the meter sits
near empty, while *not* spamming it leaves the meter full for when it matters.

**6. Wider road, tougher blockers** (later feedback). Road half-width 150-330
-> 200-430 (widest leaves 210px of shoulder each side on a 1280px screen), with
the difficulty pinch strengthened 118 -> 150 so late-game still tightens: width
now runs 459-855px early and 403-558px late. Hazard health went up ~4x (wreck
340 -> 1500, rubble 200 -> 950, drum 55 -> 240) so clearing one is a real
investment -- 1.4s of full-arsenal fire, or 11.5s with just the pistol -- and
ramming was cut from 3x to 0.8x damage so blockers cannot be bulldozed. Driving
around them is the intended primary answer; shooting is the fallback.

**7. Fewer zombies** (later feedback). Horde density is expressed per pixel of
road, so widening the road in (6) had silently inflated the horde -- worth
remembering if the road is ever retuned again. Density 0.022 -> 0.0125 base
(+0.0115 per difficulty), wave interval 1.25 -> 1.70s base / 0.46 -> 0.70s at
full difficulty, second-row chance 0.45 -> 0.24, stragglers thinned, and
`MAX_ZOMBIES` 320 -> 190. Average on-screen count across a smoke run went 22.6
-> 9.5 and peak 58 -> 36. A trial nudge back up was reverted -- the user was
happy with the thinner horde.

**8. Auto-fire and a slower car** (later feedback). The gunner no longer holds a
trigger -- every weapon fires the moment it is off cooldown, so the second player
only aims. The **nuke is deliberately excluded**: it is rare enough that
auto-firing it would waste it on whatever happened to wander in front of the
turret, so it alone still waits for ENTER / click (flagged with an `[ENTER]` hint
on its HUD row). `Arsenal.update` now takes both an auto `firing` flag and a
`manual` flag and picks per weapon.

Car speed: cruise 300 -> 245 px/s, min 170 -> 140, max 430 -> 355, lateral
400 -> 355, pinned lateral 130 -> 115. Boost multiplier is unchanged so boosted
top speed fell from ~735 to ~600 px/s.

Combined with (7)'s thinner horde and directional blocking, the blind smoke bot
now survives a full 3000-frame run without dying (pinned 0%), so the game is
currently on the easy side -- worth watching in play.

### Testing bug that invalidated earlier measurements

`pygame.mouse.set_pos()` is a **silent no-op under SDL's dummy video driver** --
`get_pos()` always returns (0, 0). Every headless measurement that "aimed" at a
target was really aiming at the screen corner, so all the earlier boss
time-to-kill numbers were measuring almost nothing (bosses still died from ram
damage and point-blank spray, which masked it).

Fixed by adding `Game.aim_override`; harnesses set it instead of warping the
mouse, and `Game.aim_screen_pos()` is the single read point (the HUD crosshair
uses it too). First trustworthy numbers: full arsenal is ~1040 dps, pistol only
~130 dps. **Lesson: verify the harness can actually drive the input it claims to
before trusting any number it produces.**

### Earlier boss bug found the same way

Piercing projectiles (flamethrower) were re-damaging the boss on *every frame*
they overlapped it -- roughly 18 hits per flame puff -- because the boss damage
path had no equivalent of the `p.hit` guard the zombie path uses. That is what
made the first Brute die in half a second. Fixed with a `BOSS_HIT_KEY` sentinel
in the projectile's hit set.

Boss health then went 2400 -> 6800 base / 3400 per tier, confirmed good by the
user in play. Two supporting fixes were needed to make boss fights work at all
at that health: an **arena supply cache** on fight start plus resupply at HP
thresholds (the crew otherwise arrives with partial magazines, runs dry in ~5s
and spends the rest of the fight plinking with the pistol), and a **minion cap**
during arenas (they body-block shots at the boss, so uncapped slam-summons were
a death spiral).

Also: screen shake halved via a single `SHAKE_SCALE` knob (user request).

Built a complete two-player local co-op game in Python/pygame from an empty
directory. Player 1 drives (WASD + SHIFT boost), Player 2 aims with the mouse
and holds ENTER to fire. Endless straight road, zombie hordes, boss arenas,
persistent high score. **No asset files** — every sprite is drawn with pygame
primitives at startup and every sound effect is synthesized with numpy.

### Design decisions confirmed with the user up front
- Top-down camera, road scrolls downward (car near the bottom driving "north")
- All owned weapons fire simultaneously on **independent cooldowns** (user chose
  this over strict round-robin rotation)
- Boss = giant zombie brute with charge + ground-slam-summons-minions
- Persistent high score in `highscore.json`

Mid-build the user asked for two additions: a **flamethrower** (short-range
piercing fire puffs that ignite zombies, burns `fuel`) and a **sprite export
script** so they could eyeball the art.

### Architecture

13 modules. `settings.py` holds every tuning constant so balance can be changed
without touching logic. Coordinate system: world +Y is *forward* (up the
screen); `Camera` maps world→screen, X is 1:1. Sprites are authored facing up
and `RotSet` lazily caches rotations; `blit_rotated` takes degrees clockwise
from up. This convention is used consistently everywhere.

**Key non-obvious choices:**

- **Supersampled procedural art.** Everything in `art.py` is drawn at 4× into an
  SRCALPHA canvas then `smoothscale`d down, which is what makes shape-based art
  look antialiased rather than jagged. Sprites are built once at startup (~0.2 s
  total) and only blitted thereafter.
- **Half-resolution light map.** `effects.render_lightmap` fills a 640×400
  surface with an ambient colour, additively blits glows (headlights, fire,
  explosions, burning zombies, pickups), then smooth-scales it up and blits with
  `BLEND_RGB_MULT`. This is why lights actually illuminate the world. Half-res
  makes it affordable *and* gives naturally soft edges. `L` toggles it off.
- **Road width is a pure function of world Y** (sum of three sines + a
  difficulty term) rather than stored segments, so it can be sampled anywhere
  for drawing, car clamping and horde spawning without any state.
- **Road rendering uses per-band rect clipping.** Asphalt is tiled across the
  whole screen, then dirt is tiled back over the shoulders in 26 horizontal
  bands using `set_clip`. Masking an irregular polygon needed two full-screen
  surface allocations *per frame*; this needs none. The stepped edge is under a
  pixel or two of width change and the kerb polylines drawn on top hide it.
- **All zombie deaths funnel through `Horde.kill()`**, which queues score and a
  death position for `Game._collect_kills()` to drain. Score, drops and popups
  therefore work identically whether the kill came from a bullet, fire, splash,
  a nuke or the front bumper. An earlier version awarded score only for ram
  kills — every weapon kill was worth nothing.

### Bugs found and fixed during the build

- **Boss death paid out multiple times.** `_boss_take_fire` checked
  `if not boss.alive` after each projectile, so a burst landing in one frame
  fired the reward N times. Fixed by using `hurt()`'s return value, which is
  True only on the fatal blow.
- **Cached glow surfaces were being mutated.** `radial_glow` returns from a
  module cache; several call sites did `set_alpha` on the returned surface,
  corrupting it for every other user. Particle fading now dims the *colour*
  (quantised to keep the cache bounded) and every other site copies first.
- **Post-boss soft-lock.** After the brute died the arena was still full of the
  minions it had summoned, which could pin the car with nothing left to shoot
  and no way to drive out. The death blast now clears the arena.
- **Boss and car occupied the same space** — added hard separation so the brute
  shoves the car rather than sitting inside it.
- **Boss whited out under sustained fire.** `hit_flash = 1.0` on every hit with
  ~15 hits/second meant it never decayed. Now accumulates to a capped 0.5.
- **pygame fakes bold by smearing glyphs horizontally**, which destroys already
  condensed display faces (Impact rendered as unreadable blocks). Fonts are now
  split into three roles — `display` (Arial Black, deliberately *unbolded*),
  `ui` (Helvetica bold), `mono` — in `hud._STACKS`.
- **Sound buffer length bug**: several effects built a length-N buffer then
  `np.pad`-ed a shorter segment and sliced, which cannot extend it → broadcast
  errors. Replaced with a `_place(seg, delay, n)` helper.
- **A `sprites/` output directory would shadow `sprites.py` on import** (a
  directory is found as a namespace package before a same-named module). The art
  module was renamed to `art.py` so the user could have their `sprites/` folder.

### Balance

Two rounds of tuning driven by the headless harness:

- Contact damage started at 13 dps/zombie capped at 62 — five zombies killed an
  unarmoured car in 1.6 s. Now 4.5 capped at 20 (~5 s of full contact), which is
  long enough for the gunner to dig the driver out.
- Horde density started far too sparse: the gap-carving logic was removing ~2/3
  of each band because two 168 px corridors on a ~500 px road left almost
  nothing. Gaps narrowed to 152 px (72 px at max difficulty), density more than
  doubled.
- Ammo economy loosened (drop chance 0.10→0.145, pickup sizes up ~40%) because
  holding the trigger with a full loadout drained everything in ~10 s.

Validated with a competent scripted driver (steers for the widest clear lane,
boosts to break pins): reaches 4–4.7 km, ~1400–1900 kills and 2 bosses in a
150 s run while pinned only 4–6 % of the time — but a sloppier run still dies at
51 s. Lethal but winnable.

### Performance

Worst case measured is max difficulty with ~300 zombies and every weapon firing
continuously: **9 ms median, 14 ms p95** (~70 fps), down from 15 ms p95 before
optimisation. Three changes got it there, chosen by profiling rather than guess:

1. `Horde.query` was a full scan of all zombies, called ~33×/frame. Added a
   per-frame spatial hash (`CELL = 64`), rebuilt once at the end of
   `Horde.update`.
2. `separate()` rewritten to visit each unordered cell pair once (`_PAIR_CELLS`)
   instead of building a 9-cell neighbour list per bucket.
3. Zombie drop shadows **baked into the sprites** rather than blitted separately
   — 300 fewer blits per frame. The shadow orbits slightly as the sprite
   rotates, which is imperceptible for a soft symmetric blob.

Raw `blit` count is still the single largest cost (~1300/frame), which is the
expected shape for a sprite-heavy 2D game.

### Developer tooling built alongside

- `smoketest.py N` — headless scripted run reporting frame timings, peak object
  counts, pinned %, average life and whether the boss cycle completed. This is
  what caught the double boss payout, the sparse hordes and the damage tuning.
- `export_sprites.py` — dumps all 116 sprite PNGs plus labelled contact sheets to
  `sprites/` (user requested).
- `screenshots.py` — captures 10 gameplay/menu stills to `screenshots/`.

`pyflakes` is clean across all modules.

## To Do Next

Nothing is blocking — the game is complete and playable. Possible follow-ups if
the user wants them after playtesting:

- **Playtest tuning.** All knobs are in `settings.py`. The most likely requests
  are contact damage (`ZOMBIE_CONTACT_DPS*`), horde density (`density` in
  `Horde.spawn_wave`) and boss HP (`BOSS_BASE_HP`).
- **Gamepad support** for the driver would make the two-player-one-keyboard
  ergonomics much nicer.
- **More boss variety** — currently every arena is the same brute with more HP
  and a slightly redder tint (`_boss_body(tier)` already accepts a tier).
- Windowed-only at present; no fullscreen toggle or resolution options.
