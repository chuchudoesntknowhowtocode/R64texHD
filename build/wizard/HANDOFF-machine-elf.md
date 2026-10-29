# Machine Elf: 8-bit DMT scene (handoff notes)

A pixel-art GIF for a desktop app's bottom bar. A **Machine Elf**, the kind of being met in a DMT breakthrough, appears next to the app's **Quit** button. It warps reality with sacred geometry and breaks into the **green pipe** at the left of the bar. This package holds the finished scene, the first draft, and exactly the code needed to re-render or extend it.

> **Links:** nothing was published as a hosted artifact and there is no git repo, so there are no URLs. Everything is in this zip.

## 1. Contents

```
gifs/
  43_dmt_machine_elf_sacred_warp.gif   FINAL: approved by the user ("incredible"). 10 s, 300 frames, 20.8 MB
  42_dmt_machine_elf_reality_warp.gif  first draft (simple jester elf, ripple/tile-scramble warps), superseded
src/
  elf2.py         the final scene: elf sprite, sacred_ring, lattice, kaleido, facets, scene()
  elf_scene.py    first draft; elf2 still imports chatter() (the glyph language) from it
  geo.py          sacred-geometry engine (Flower of Life, Sri Yantra, Platonic solids, merkaba, pipe shatter)
  lib.py          canvas, bounds, pipe, pixel helpers, GIF writer
  props.py, scenes.py, scenes2.py, scenes3.py, px_*.png   support only (helpers like outline(), trip(), hue_region();
                  lib.py loads the px_* wizard sprites at import time)
  assets/app_idle.png   the app screenshot every frame is drawn on
  assets/reference/merkaba_breakthrough_reference.gif   the user's earlier scene, which the elf's intro was asked to echo
```

## 2. Hard rules every frame must pass

| Rule | Value |
|---|---|
| Canvas | 1780×416, the app screenshot (890×208) scaled 2× nearest-neighbour. One sprite pixel = a 2×2 block. |
| Frame rate / format | 30 fps GIF, ffmpeg `palettegen` then `paletteuse=dither=none`, loops forever |
| Never draw above | y = 216 (`lib.SAFE`), the upper app panels |
| Never draw below | y = 402 (`lib.BOTTOM`), the app's bottom border line |
| Start spot | next to Quit, x ≈ 1375 |
| Pipe | `lib.PIPE` at `lib.PIPE_HOME`, mouth x = 172. It may shatter or move but must be back home at the end. |
| Clean loop | first and last frame = the idle screenshot exactly |

`lib.finish(frame)` repaints everything outside the safe band.

## 3. Creative direction (from the user)

- **The sprite is an original design.** The user shared an Alex Grey painting as a mood reference. It was **not copied**; only the general feel was used (many eyes, radiating flame-like energy). Don't reproduce that painting or anyone's character.
- **Full RGB.** Not limited to the reference's orange.
- **Elf design** (`elf2(f, form, hue, scale)`, drawn at 1× then scaled 2×, 1 px navy outline):
  - `radiant` (main form): a grinning faceted-gem face with pointy ears, two colour-shifting eyes and a glowing star third eye. Around it is a crown of 14 wavy RGB flame tendrils, each tipped with a blinking eye, plus an inner ring of 14 small eyes.
  - `orb`: a rainbow sphere covered in eyes, with one giant central eye.
  - `crystal`: an octahedron with one huge eye; used for the launch.
  - It "speaks" in streams of rainbow 3×3 glyphs (`chatter`).
- **Reality distortion must look sacred-geometric**, never like plain ripples or glitches:
  - `lattice`: a Flower of Life grid across the whole bar, pulsing outward from the elf
  - `kaleido`: an n-fold kaleidoscope portal, computed on the 1× grid so it stays pixel-art
  - `facets`: crystal-facet refraction pushed away from the elf, with triangle outlines
  - **Apply warps to the world first, then draw the elf on top**, so the elf stays crisp at the centre of each portal.
- **Intro = a spinning ring of sacred geometry** (`sacred_ring`) instead of the reference's RGB triangle lines. It builds in layers: a rune band, then 12 petals, then a counter-rotating hexagram, then a Flower of Life core, then outer rays. The same ring spins up and launches the elf into the pipe.
- **File size is not a concern.** The app has plenty of resources, so never trade quality for size.

## 4. Scene 43 timeline (`elf2.scene()`, 300 frames)

| Frames (s) | What happens |
|---|---|
| 6–48 (0.2–1.6) | Sacred ring builds and spins; elf fades in (Bayer dither) inside it |
| 14–60 | Trip intensity ramps up: hue shift, darkening, the lattice fades in |
| 30–104 (1–3.5) | Glyph chatter; 6-fold kaleidoscope portal around the elf; a Platonic-solid gem that changes shape; Flower of Life bloom |
| 104–152 (3.5–5) | Drifts left while shape-shifting radiant → orb → crystal; facet refraction; echo portals down the bar |
| 152–178 (5–5.9) | Six hue-shifted clones spin on a glowing hexagram, then merge |
| 176–216 (5.9–7.2) | Ring re-forms and spins faster; the crystal form launches on a rainbow trail |
| 216 (7.2) | Impact: white flash, the pipe shatters into hue-cycling shards |
| 218–264 (7.3–8.8) | Where the pipe was: 8-fold kaleidoscope, light rays, fast ring and Sri Yantra; tiny elves orbit; glyphs pour out |
| 248–274 | Shards fly back together; the geometry fades |
| 274–300 (9–10) | Pipe bounce, the trip fades out, clean screen |

## 5. How it's built

Each scene is a function that loops frame by frame (`for f in range(N)`). It draws the frame in this order:

1. Background with trip tint.
2. Geometry behind everything (a `Geo` layer).
3. World warps.
4. Clones, then the elf.
5. Geometry in front.
6. Pipe or shards.
7. Mandala.
8. Flashes and bursts.
9. `finish()`.

All geometry goes through `geo.Geo`: 1 px lines with a soft 3 px glow, drawn on a half-resolution layer and then scaled 2×, so every line sits on the same pixel grid as the sprites. Colours come from `rb(hue)` (rainbow HSV). Fades use an ordered Bayer dither (`bayer_mask`), never alpha blending, to keep the 8-bit look.

## 6. Render and verify

Requires Python 3 with Pillow, NumPy and SciPy, plus ffmpeg on PATH. Run from `src/`:

```bash
python3 elf2.py            # -> src/out/43_dmt_machine_elf_sacred_warp.gif (about 5 min), frames in src/frames_43_*/
python3 elf2.py preview    # -> elf2_preview.png showing the three forms
```

```python
import numpy as np, glob; from PIL import Image
bg = np.array(Image.open('assets/app_idle.png').convert('RGB').resize((1780,416), Image.NEAREST)).astype(int)
fs = sorted(glob.glob('frames_43_dmt_machine_elf_sacred_warp/[0-9]*.png'))
A = lambda p: np.array(Image.open(p).convert('RGB')).astype(int)
assert all(np.abs(A(f)[:216]-bg[:216]).max()==0 and np.abs(A(f)[402:]-bg[402:]).max()==0 for f in fs)
assert np.abs(A(fs[0])-bg).max()==0 and np.abs(A(fs[-1])-bg).max()==0
```

## 7. Ideas to continue

- More Machine Elf scenes, e.g. a tunnel of nested sacred rings, or elves building the pipe out of geometry.
- The elf as an opponent for the wizard. (The wizard and his fighter scenes are in a separate, larger package.)
