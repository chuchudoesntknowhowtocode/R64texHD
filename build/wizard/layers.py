"""Splits a rendered scene into the two layers the app draws:
  world  - the bar itself as the scene changed it (tints, hue shifts, warps); drawn UNDER the progress
           segments and behind the buttons;
  sprite - everything drawn on top (wizard, opponents, call-outs, sparks); drawn over the segments.
How: the scene is rendered twice, once on the real footer (A) and once on a scrambled copy of it (B).
A pixel the scene painted over completely comes out the same both times (sprite); a pixel that still
depends on the footer underneath differs (world)."""
import sys, os
import numpy as np
from PIL import Image
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = (lib.SAFE, lib.BOTTOM)

def _scrambled(img):
    a = np.array(img).copy(); t, b = BAND
    reg = a[t:b].astype(int); a[t:b] = ((reg + 97) % 256).astype(np.uint8)
    return Image.fromarray(a)

def _swap(bg, bgn):
    for m in list(sys.modules.values()):
        f = getattr(m, '__file__', None) or ''
        if not f.startswith(HERE): continue
        if hasattr(m, 'BG'): m.BG = bg
        if hasattr(m, 'BG_NOPIPE'): m.BG_NOPIPE = bgn

def render(scene_fn):
    """-> (frames A as uint8 arrays, world RGBA list, sprite RGBA list)"""
    A0, N0 = lib.BG, lib.BG_NOPIPE
    try:
        _swap(A0, N0); fa = [np.array(f.convert('RGB')) for f in scene_fn()]
        _swap(_scrambled(A0), _scrambled(N0)); fb = [np.array(f.convert('RGB')) for f in scene_fn()]
    finally:
        _swap(A0, N0)
    bg = np.array(A0.convert('RGB'))
    world, sprite = [], []
    for a, b in zip(fa, fb):
        same = (a == b).all(-1)
        w = np.zeros(a.shape[:2] + (4,), np.uint8); s = np.zeros_like(w)
        wm = ~same & (a != bg).any(-1)              # the footer, changed by the scene
        sm = same & (a != bg).any(-1)               # painted on top (an unmoved pipe equals the footer: left out)
        w[wm, :3] = a[wm]; w[wm, 3] = 255; s[sm, :3] = a[sm]; s[sm, 3] = 255
        t, bt = BAND; w[:t] = 0; w[bt:] = 0; s[:t] = 0; s[bt:] = 0
        world.append(w); sprite.append(s)
    return fa, world, sprite

def render_iter(scene_fn):
    """like render(), but keeps only the scene band and yields (world, sprite) band arrays frame by frame,
    so long clips fit in memory"""
    t, b = BAND
    A0, N0 = lib.BG, lib.BG_NOPIPE
    try:
        _swap(A0, N0); fa = [np.array(f.convert('RGB'))[t:b] for f in scene_fn()]
        _swap(_scrambled(A0), _scrambled(N0)); fb = [np.array(f.convert('RGB'))[t:b] for f in scene_fn()]
    finally:
        _swap(A0, N0)
    bg = np.array(A0.convert('RGB'))[t:b]
    for i in range(len(fa)):
        a, bb = fa[i], fb[i]; fa[i] = fb[i] = None
        same = (a == bb).all(-1); ch = (a != bg).any(-1)
        w = np.zeros(a.shape[:2] + (4,), np.uint8); s = np.zeros_like(w)
        wm = ~same & ch; sm = same & ch
        w[wm, :3] = a[wm]; w[wm, 3] = 255; s[sm, :3] = a[sm]; s[sm, 3] = 255
        yield w, s
