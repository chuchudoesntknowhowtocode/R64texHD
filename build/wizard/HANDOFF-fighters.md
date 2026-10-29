# Pipe Wizard – 8-bit GIF scenes (handoff notes)

Pixel-art GIF animations for a desktop app's bottom bar. A wizard starts next to the **Quit** button and always ends up **inside the green pipe** at the left of the bar. This package holds every scene from the **DMT set onward**, the full Python toolkit that renders them, and the notes another chat needs to carry on.

> **Links:** nothing was published as a hosted artifact and there is no git repo, so there are no URLs. Every GIF and all the source are inside this zip.

---

## 1. What's in the zip

```
gifs/
  dmt/                10 DMT "breakthrough" scenes (32–41), the delivered set
  dmt_earlier_run/     9 alternate DMT GIFs from an earlier run (not described here; kept for completeness)
  fighter/            arcade-fighter scenes in delivery order:
                        sf_example_1-3          first look (blue robe, staff magic)
                        sf_red_gi_example_1-3   same, wizard recoloured into a red/black gi
                        martial_1-3             martial-arts rig, rapid-fire combos, death punch
                        unleashed_1-5           CURRENT STYLE: robe burns away, staff + martial arts
src/                  all scripts, cleaned sprites (px_*.png), raw cut-outs (raw_*.png), assets/
  assets/app_idle.png         the app screenshot every frame is drawn on (= first & last frame)
  assets/app_with_wizard.png  screenshot showing the wizard's in-app size
  assets/wizard_reference.png the "Great Wizard of R64" reference art
  assets/pose_sheets/         the user's two pose sheets (A–I poses)
```

## 2. Hard rules (every scene must pass these)

| Rule | Value |
|---|---|
| Canvas | 1780×416, the app screenshot (890×208) scaled **2× nearest-neighbour**. One sprite pixel = a 2×2 block. |
| Frame rate | 30 fps. GIF via ffmpeg `palettegen` then `paletteuse=dither=none`, loop forever. |
| Floor (feet line) | y = 372 (`lib.FLOOR`) |
| Never draw above | y = 216 (`lib.SAFE`), the bottom edge of the upper panels |
| Never draw below | y = 402 (`lib.BOTTOM`), the app's bottom border line |
| Start spot | x = 1395 (`lib.SX`), just left of Quit |
| Pipe | movable sprite `lib.PIPE` at `lib.PIPE_HOME` (24,224); mouth x = 172 (`lib.MOUTH`). It can move or stretch mid-scene but must be back home by the end. |
| Clean loop | the **first and last frame must equal the idle screenshot exactly** |

`lib.finish(frame)` repaints everything above SAFE and below BOTTOM, so a scene can't break the bounds by accident. The check in section 7 confirms all three rules.

## 3. Creative direction (decided with the user)

- 8-bit retro feel: everything sits on the 2× pixel grid, no blur and no gradients except the deliberate fades. Fades use an ordered Bayer dither (`lib.bayer_mask`), never alpha blending.
- **No Street Fighter / Capcom material.** The user supplied a zip of SF2 sprite rips, stage backgrounds and the car bonus stage. These were **not used**, and the fighters were not imitated, because they're protected characters and artwork. Everything here is original: the goblin brawler, stone golem, clockwork ninja robot, dark twin, an original boxy car, an original call-out font, original arena props (crowd silhouettes and torches). Keep it that way.
- Fight HUD = **call-outs only** (ROUND 1, FIGHT!, K.O., PERFECT!, UNLEASHED!, FINAL ROUND, "N HITS" counter, "N HIT COMBO!"). No health bars.
- Current wizard character (the **unleashed** scenes):
  - He starts calm in his **full blue robe, staff in hand**.
  - Something provokes him: a taunt, a bonk on the hat, a car honk, a zap.
  - The **robe burns away from the hem up** in red/gold flames, revealing a **red gi with black trim and a black belt**. A **fiery red/gold aura** flares and "**UNLEASHED!**" appears.
  - His staff orb turns **red/gold** and **flares on every hit**.
  - He fights with an **even mix** of staff work (thrusts, spinning staff, sweep, rising strike) and fast martial arts (flying kick, shadow kicks, chain punches). The combos are rapid-fire, a hit every 2 frames (about 15 hits a second), with cyan afterimages and a live hit counter.
  - **Finisher:** he charges the staff (energy converges on the orb), leaps, and does an **overhead staff smash** with ground shockwaves and a screen flash.
  - He keeps his navy hat and white beard throughout. The hat is his identity.
- Opponents and their gimmicks:
  - **Goblin:** taunts "HA HA!", throws a rock, gets knocked into the pipe.
  - **Golem:** slow but tanky; chunks fly off each hit. Ground-pound shockwave the wizard jumps over, boulder throws he smashes. **Crumbles to rubble.**
  - **Robot:** lightning dashes with afterimages, rocket punch on a chain, shuriken barrage blocked by the spinning staff. **Explodes into gears.**
  - **Dark twin (final boss):** a recoloured mirror of the wizard. **Disrobes too** (violet flames, black and purple gi), fires purple dark-magic orbs the wizard bats back, gets a "FINAL ROUND" call-out.
  - **Car bonus round:** honks "BEEP!" three times, charges and gets stopped by one staff thrust, then takes damage in stages.
- Opponents mostly end up knocked into the pipe; the golem and robot are destroyed instead. The wizard always exits with a run and a flying kick into the pipe.
- Vs. scenes aim for 8–10 s. Golem, robot and twin currently run 11–12 s.

## 4. How it's built (pipeline)

1. **Sprite cleanup** (`extract.py` → `clean.py`, `clean2.py`, `props2.build_G`). The poses came from the user's AI-generated pose sheets on checkerboard backgrounds. Steps:
   1. Cut each pose out.
   2. Remove the checkerboard, which is low-saturation grey.
   3. Erode the soft fringe and drop pale edge pixels.
   4. Downscale with BOX to in-app size (about 66 px tall at 1×).
   5. Snap every pixel to a shared palette of about 18 colours (k-means).
   6. Add a 1 px navy outline (10,14,42).

   This removed the white halo edges the user disliked. The results are `px_R, C, I, F, B, H, E, D, G` (front, walk, attack, sneak, cast, celebrate, levitate, ponder, pray).
2. **Gi recolour** (`suit.py` → `px_suit_*.png`): navy robe → reds, cyan trim → black, belt band + knot tails. The hat, beard and staff orb are protected.
3. **Martial-arts rig** (`martial.py`): his real hat, face and beard pixels (`HEAD`) on a procedural gi body. Arms and legs are two-segment limbs posed by joint angles: 0° points down, positive angles point toward the facing direction (left). Everything is drawn at 1× and outlined, then scaled 2×.
   - Poses live in `POSES`: stance, punch, punch2, death, fly, tuck, high, mid, low, sweep, upper, crouch, hit, win, run1, run2, charge, knee, bow, plus the staff set `st_*`. `spin_pose(k)` gives the staff spin.
   - The staff is drawn into the rig: `staff=(arm, angle, grip)`.
   - Rendering: `rig(pose, flip, scheme='hero'|'dark', hot=bool)`. `fplace(...)` puts the feet on the floor or the hip at a given height. `eff()` and `staff_tip()` give strike points for hit sparks.
   - `scheme='dark'` recolours everything for the twin (`dark_recolor_arr`).
4. **Shared toolkit** (`lib.py`):
   - frame/background: `new()`, `finish()`
   - placement: `place()` with `clip_x` (clip at the pipe mouth so he vanishes "into" it), `clip_floor`
   - pipe: `draw_pipe()`, `pipe_bounce()`, `stretched_pipe()`
   - effects: `burst`, `dust`, `glyph` (? ! * Z)
   - fades: `bayer_mask`, `dissolve`, `scan_glitch`
   - easing functions
   - output: `write_gif()`
5. **Effects libraries**:
   - `geo.py`: sacred geometry on a 1× grid (Flower of Life, Metatron, Sri Yantra, Platonic solids, Merkaba, torus, tesseract, hex tunnel, DMT skeletal formula) and pipe shatter/reassemble.
   - `fight_assets.py`: call-out font, goblin, car with damage states 0–5, torches, crowd.
   - `opponents.py`: golem, robot, shuriken, boulder, gears, robed/gi front sprites for the burn.
   - `unleashed.py`: robe burn, aura, embers, combo engine, finisher, exit run.
6. **Scene scripting.** Each scene is a function that loops frame by frame (`for f in range(N)`). It decides what to draw from the frame number (timeline windows like `if 62 <= f < 76:`) and ends with `finish(fr)`. The `Combo` class (`martial_scenes.py`) scripts rapid flurries as (start frame, pose, hits?) steps. It drives hit sparks, afterimages and the counter.
7. **Review loop.** After rendering, build a 16-frame contact sheet (`sheet_*.png`) and look at it, zoom key frames at full size, run the bounds/loop check, and only then deliver.

## 5. Scene catalogue

**DMT set (`gifs/dmt`).** The trip fades in after he appears and is gone by the last frame.

| # | Scene |
|---|---|
| 32 | Flower of Life seed-orb carries him; the pipe shatters into a mandala and rebuilds |
| 33 | Metatron's Cube → rolling 3D cube → pipe shatters into Metatron |
| 34 | Hooded spirit-guide shaman drums, offers an orb with the spirit molecule inside; third eye opens, he flows into the pipe as a rainbow double helix |
| 35 | The DMT molecule builds bond by bond; he rides it into the pipe |
| 36 | Third eye opens → Sri Yantra → beam to the pipe; the pipe becomes a glowing outline |
| 37 | Hexagonal hyperspace tunnel in the pipe mouth pulls him in |
| 38 | Machine elves tumble out of the pipe, summon him and crowd-surf him in |
| 39 | Torus energy field carries him; the pipe emits shockwave rings |
| 40 | Five Platonic solids orbit him; the pipe becomes a rotating tesseract |
| 41 | Merkaba launches him; the pipe explodes into a mandala and reassembles |

**Fighter set (`gifs/fighter`).** The unleashed scenes are the current direction.

| File | Scene |
|---|---|
| unleashed_1_vs_goblin | taunt + rock bonk → burn → flying kick, 23-hit combo, staff smash, goblin into the pipe |
| unleashed_2_car_smash | three honks → burn → stops the charging car with one thrust, damage stages, PERFECT! |
| unleashed_3_vs_golem | pebble flick → jumps the shockwave, smashes the boulder → combo → golem crumbles |
| unleashed_4_vs_robot | shuriken bonk → parries the rocket punch, spin-blocks the barrage → robot explodes into gears |
| unleashed_5_vs_dark_twin_final | zap → both disrobe → FINAL ROUND → bats back dark orbs → combo → twin into the pipe |
| martial_1-3 | earlier rig test without the staff or robe (solo pipe combo, goblin juggle, car) |
| sf_example / sf_red_gi_example 1-3 | first fighter look (sprite-based staff magic) |

## 6. Rendering

Requires Python 3 with Pillow, NumPy and SciPy, plus ffmpeg on PATH. Run from `src/`:

```bash
python3 unleashed.py 3        # one scene  -> src/out/fighter/unleashed_3_vs_golem.gif
python3 unleashed.py          # all five unleashed scenes
python3 scenes4.py 32 33      # DMT scenes -> src/out/
python3 martial.py            # writes rig_preview.png with every rig pose
```

Frames are also written to `src/frames_<name>/` for checking. Rendering a 10 s scene takes about 1–3 minutes.

## 7. Verification snippet

```python
import numpy as np, glob; from PIL import Image
bg = np.array(Image.open('assets/app_idle.png').convert('RGB').resize((1780,416), Image.NEAREST)).astype(int)
fs = sorted(glob.glob('frames_unleashed_3_vs_golem/[0-9]*.png'))
A = lambda p: np.array(Image.open(p).convert('RGB')).astype(int)
assert all(np.abs(A(f)[:216]-bg[:216]).max()==0 and np.abs(A(f)[402:]-bg[402:]).max()==0 for f in fs)  # bounds
assert np.abs(A(fs[0])-bg).max()==0 and np.abs(A(fs[-1])-bg).max()==0                                # clean loop
```

## 8. Open questions (asked, not yet answered)

1. Robe-burn speed: it currently burns for 0.6 s, then the aura flares for about 0.7 s.
2. During fights, should the aura stay as a low flicker, fade out, or grow with the hit counter?
3. Should the charged staff smash get a named call-out?
4. Should the hat fly off at the robe burn, or stay as his signature?
5. Should opponents ever land hits on the wizard (stagger, knockback)?
6. Should the dark twin be more sinister, e.g. glowing red eyes?
7. For the full tournament: how many scenes per opponent, what order, and should the twin be the final boss?
8. Should golem, robot and twin be trimmed to the requested 8–10 s?

Earlier answers already given: magic-powered martial arts; all four opponents; call-outs only; generic car bonus; staff always in hand; robe burns away with a red/gold aura and "UNLEASHED!"; even staff/fist mix; finisher = charged overhead staff smash; orb flares on hits and turns red/gold.
