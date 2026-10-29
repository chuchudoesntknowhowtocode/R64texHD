"""Short clips for the director:
  rerobe()            - the robe and hat rebuild out of flying pixels (before a classic or trip scene, or at
                        the start of the next job, when the robe burned off in a fight)
  idle_peek(phrase)   - with no job running: he peeks out of the pipe and says something in a dark speech
                        bubble (call-out pixel font), then ducks back
"""
import math, random
import numpy as np
from PIL import Image
from lib import *
import fights as FT
import fight_assets as FA
import martial as M
import s11

PHRASES = ["From Potato to HD", "Nintendo Forgot", "Pixels on Steroids", "Retro, Unblurred", "N64 Evolved",
           "Blurry Wasn't Better", "More Pixels!", "Nostalgia, Upscaled", "Childhood, Patched",
           "Low Poly, High Standards", "N64 but better"]

# ------------------------------------------------------------------ re-robe: pixel rebuild
def rerobe(x=SX):
    F = FT.front('hero'); gi = F['gi_nh']; robed = np.array(F['robed'])           # 2x images, same size/alignment
    H, W = robed.shape[:2]; left = snap(x - W / 2); top = FLOOR - H
    rng = random.Random(7)
    cells = []                                                                    # one per 1x pixel of the robed sprite
    for y in range(0, H, 2):
        for xx in range(0, W, 2):
            if robed[y, xx, 3] == 0: continue
            arrive = 16 + 22 * (1 - y / H) + rng.random() * 5
            sx = rng.uniform(200, 1440); sy = rng.uniform(SAFE + 6, BOTTOM - 12)
            cells.append((xx, y, tuple(int(v) for v in robed[y, xx, :3]), arrive, sx, sy))
    N = 66
    out = []
    for f in range(N):
        fr = new()
        if f < 14:                                                                # he appears in the gi (no hat)
            if FT.intro(fr, f, robed=False, x=x): pass
        elif f < 44:
            done = np.zeros_like(robed)
            for (cx, cy, col, arrive, sx, sy) in cells:
                k = f - (arrive - 10)
                if k >= 10: done[cy:cy + 2, cx:cx + 2, :3] = col; done[cy:cy + 2, cx:cx + 2, 3] = 255
            base = gi.copy(); lay = Image.fromarray(done); base.alpha_composite(lay)
            place(fr, base, x, FLOOR)
            for (cx, cy, col, arrive, sx, sy) in cells:                           # pixels still flying in
                k = f - (arrive - 10)
                if 0 <= k < 10:
                    t = ease_out(k / 10); X = lerp(sx, left + cx, t); Y = lerp(sy, top + cy, t) - 30 * math.sin(math.pi * t)
                    px(fr, X, Y, 4 if k < 6 else 2, col)
        else:
            k = f - 44; im = FT.robed_img()
            if k < 3: im = tint(im, CYAN, 0.6 - k * 0.2)
            if k >= 14: im = bayer_mask(im, 1 - (k - 14) / 8)                    # hands over to the next scene
            place(fr, im, x, FLOOR)
            if k < 8: burst(fr, x, FLOOR - 70, k / 8, n=14, speed=110, cols=(CYAN, WHITE, LBLUE), seed=3)
            if 4 <= k < 14: glyph(fr, '!', x + 40, 226, GOLD)
        out.append(finish(fr))
    return out

# ------------------------------------------------------------------ idle peek with a speech bubble
BUB_BG, BUB_EDGE, BUB_TXT = (35, 23, 60), (214, 56, 160), (250, 236, 255)
def text_px(fr, text, x, y, s=4, col=BUB_TXT, upto=None):
    """the call-out font, solid colour (for the bubble)"""
    for i, ch in enumerate(text if upto is None else text[:upto]):
        for r, row in enumerate(FA.F5.get(ch, FA.F5[' '])):
            for c, v in enumerate(row):
                if v == '1': D(fr).rectangle([x + i * 6 * s + c * s, y + r * s, x + i * 6 * s + c * s + s - 1, y + r * s + s - 1], fill=col + (255,))
def bubble(fr, x, y, w, h, scale=1.0, a=255):
    """dark box with a magenta pixel border and a tail toward the pipe"""
    if scale <= 0: return
    a = int(max(0, min(255, a)))
    cx, cy = x + w / 2, y + h / 2; w2, h2 = w * scale, h * scale
    x0, y0, x1, y1 = snap(cx - w2 / 2), snap(cy - h2 / 2), snap(cx + w2 / 2), snap(cy + h2 / 2)
    d = D(fr)
    d.rectangle([x0 + 4, y0, x1 - 4, y1], fill=BUB_EDGE + (a,)); d.rectangle([x0, y0 + 4, x1, y1 - 4], fill=BUB_EDGE + (a,))   # chunky corners
    d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=BUB_BG + (a,))
    if scale >= 0.9:                                                              # tail, pointing down-left at his head
        for k, (dx, dy) in enumerate(((20, 0), (14, 4), (8, 8), (2, 12))):
            d.rectangle([x0 + dx, y1 + dy - 4, x0 + dx + 11, y1 + dy + 3], fill=BUB_EDGE + (a,))
            if k < 3: d.rectangle([x0 + dx + 4, y1 + dy - 4, x0 + dx + 7, y1 + dy - 1], fill=BUB_BG + (a,))
def idle_peek(phrase):
    text = phrase.upper(); s = 4
    tw = len(text) * 6 * s - s; bw = tw + 40; bh = 7 * s + 28
    BX, BY = MOUTH + 110, SAFE + 8
    HW = s11.HEAD.width; CY = MOUTH_Y + 8
    T_OUT, T_BUB = 6, 24
    T_TXT = T_BUB + 6; T_HOLD = T_TXT + 2 * len(text); T_POP = T_HOLD + 90; T_DUCK = T_POP + 6; N = T_DUCK + 20
    out = []
    for f in range(N):
        fr = new(); dy = 0
        if f < T_OUT: dy = -2 if f % 2 else 0
        dy = min(dy, pipe_bounce(f - T_DUCK - 8))
        if f < T_OUT: o = 0
        elif f < T_OUT + 12: o = HW * 0.92 * ease_back((f - T_OUT) / 12, 2.2)
        elif f < T_DUCK: o = HW * 0.92 + (2 if (f // 10) % 4 == 1 else 0)
        elif f < T_DUCK + 8: o = HW * 0.92 * (1 - ease_in((f - T_DUCK) / 8))
        else: o = 0
        blink = f in (T_OUT + 20, T_OUT + 21, T_HOLD + 40, T_HOLD + 41)
        if o > 1:
            im = s11.HEADB if blink else s11.HEAD
            place(fr, im, MOUTH + o - HW / 2, 0, cy=CY + dy, clip_x=MOUTH)
        if T_BUB <= f < T_POP + 4:
            sc = ease_back(min(1, (f - T_BUB) / 6), 2.0) if f < T_POP else 1 + 0.12 * (f - T_POP) / 4
            a = 255 if f < T_POP else 255 * (1 - (f - T_POP) / 4)
            bubble(fr, BX, BY, bw, bh, sc, a)
            if T_TXT <= f < T_POP: text_px(fr, text, snap(BX + 20), snap(BY + 14), s, upto=(f - T_TXT) // 2 + 1)
        if T_POP <= f < T_POP + 8: burst(fr, BX + bw / 2, BY + bh / 2, (f - T_POP) / 8, n=14, speed=120, cols=(BUB_EDGE, BUB_TXT), seed=5)
        draw_pipe(fr, 0, dy)
        out.append(finish(fr))
    return out

if __name__ == '__main__':
    import sys, os
    if 'rerobe' in sys.argv: print(write_gif(rerobe(), 'rerobe', outdir=os.path.join(HERE, 'out', 'clips')))
    for i, p in enumerate(PHRASES if 'peeks' in sys.argv else []):
        print(write_gif(idle_peek(p), f'idle_peek_{i + 1:02d}', outdir=os.path.join(HERE, 'out', 'clips')))
