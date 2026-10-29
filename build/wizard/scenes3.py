import sys, math, random, colorsys
import numpy as np
from PIL import Image, ImageOps
from lib import *
import lib
from scenes import cloud
from scenes2 import smoke, hop_arc, beam

lib.FONT['N'] = ["00011", "00110", "00100", "00100", "11100", "11100", "00000"]   # music note

def rb(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v); return (int(r * 255), int(g * 255), int(b * 255))
def trip(f, N, a=6, b=20, tail=18):
    if f <= a or f >= N - 3: return 0.0
    if f < b: return ease_io((f - a) / (b - a))
    if f > N - 3 - tail: return ease_io((N - 3 - f) / tail)
    return 1.0
def hue_rot_arr(a, deg):
    if deg % 360 == 0: return a
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B; I = 0.596 * R - 0.274 * G - 0.322 * B; Q = 0.211 * R - 0.523 * G + 0.312 * B
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); I2 = I * c - Q * s; Q2 = I * s + Q * c
    return np.stack([Y + 0.956 * I2 + 0.621 * Q2, Y - 0.272 * I2 - 0.647 * Q2, Y - 1.106 * I2 + 1.703 * Q2], -1).clip(0, 255)
def region_op(fr, fn):
    a = np.array(fr).astype(float); reg = a[SAFE:BOTTOM].copy(); a[SAFE:BOTTOM] = fn(reg)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))
def hue_region(fr, deg, amt=1.0, sat=1.0):
    if amt <= 0: return fr
    def fn(r):
        h = hue_rot_arr(r, deg)
        if sat != 1.0: g = h.mean(-1, keepdims=True); h = g + (h - g) * sat
        return r * (1 - amt) + h.clip(0, 255) * amt
    return region_op(fr, fn)
def wave_region(fr, amp, k, ph):
    if amp < 1: return fr
    def fn(r):
        out = r.copy()
        for y in range(r.shape[0]):
            sh = int(amp * math.sin(y * k + ph)) // 2 * 2
            if sh > 0: out[y, sh:] = r[y, :-sh]; out[y, :sh] = r[y, 0]
            elif sh < 0: out[y, :sh] = r[y, -sh:]; out[y, sh:] = r[y, -1]
        return out
    return region_op(fr, fn)
def tint_rb(img, h, amt):
    return tint(img, rb(h), amt) if amt > 0 else img
def melt(img, amt, f, seed=0):
    """columns sag down by varying amounts (clip at the floor when placing)"""
    if amt <= 0: return img
    a = np.array(img); h, w = a.shape[:2]; mx = int(amt) + 2; out = np.zeros((h + mx, w, 4), np.uint8)
    rng = random.Random(seed)
    drips = {rng.randrange(w) for _ in range(max(1, w // 10))}
    for x in range(w):
        d = int(amt * (0.5 + 0.5 * math.sin(x * 0.18 + f * 0.25)) * (1.0 if x // 2 not in drips else 1.0))
        d = d // 2 * 2; out[d:d + h, x] = a[:, x]
        if x in drips and d > 4:
            col = a[:, x]; last = np.nonzero(col[:, 3])[0]
            if len(last): ly = last[-1]; out[d + ly: d + ly + int(amt * 0.4), x] = col[ly]
    return Image.fromarray(out)
def place_melt(fr, img, amt, f, cx, bottom, floor=FLOOR, clip_x=None, seed=0):
    m = melt(img, amt, f, seed); place(fr, m, cx, bottom + (m.height - img.height), clip_floor=floor, clip_x=clip_x)
def scale_img(img, sx, sy=None):
    sy = sx if sy is None else sy
    return img.resize((max(2, round(img.width * sx / 2) * 2), max(2, round(img.height * sy / 2) * 2)), Image.NEAREST)
def draw_pipe_scaled(fr, sx, sy, dy=0, img=None):
    p = img or PIPE; q = scale_img(p, sx, sy)
    bx = PIPE_HOME[0] + p.width // 2; by = PIPE_HOME[1] + p.height
    fr.paste(q, (snap(bx - q.width / 2), snap(by - q.height + dy)), q)
def end_clean(frames):
    return frames

# ---------------- 22. Rainbow melt ----------------
def s22():
    out = []; N = 128
    for f in range(N):
        I = trip(f, N); fr = new(pipe=False)
        if 6 <= f < 30:                                             # rainbow drips fall and form him
            for i in range(12):
                x = SX - 46 + i * 8; L = clamp((f - 6 - i * 0.6) / 14) * (FLOOR - SAFE - 4)
                if L > 0: rect(fr, x, SAFE + 4, 8, L, rb(i / 12 + f * 0.03), 230 * (1 - clamp((f - 24) / 6)))
        pmelt = 0
        if 84 <= f < 100: pmelt = 40 * ease_io((f - 84) / 10)
        elif 100 <= f < 112: pmelt = 40 * (1 - ease_io((f - 100) / 12))
        pdy = pipe_bounce(f - 112)
        if pmelt > 0: place_melt(fr, PIPE, pmelt, f, PIPE_HOME[0] + PIPE.width // 2, PIPE_HOME[1] + PIPE.height, floor=PIPE_HOME[1] + PIPE.height, seed=3)
        else: draw_pipe(fr, 0, pdy)
        fr = hue_region(fr, f * 9, I * 0.85)
        if 18 <= f < 34: place(fr, tint_rb(bayer_mask(spr('R'), (f - 18) / 10), f * 0.05, 0.4), SX, FLOOR)
        elif 34 <= f < 96:
            t = (f - 34) / 62; cx = lerp(SX, MOUTH - 70, ease_io(t)); im, b = walk_frame(f)
            amt = 18 + 14 * math.sin(f * 0.2)
            place_melt(fr, tint_rb(im, f * 0.04, 0.35 * I), amt, f, cx, FLOOR - b, clip_x=MOUTH, seed=f // 6)
            pw = 60 + amt * 2; D(fr).ellipse([snap(cx - pw / 2), FLOOR - 6, snap(cx + pw / 2), FLOOR + 6], fill=rb(f * 0.04) + (180,))
            for k in range(5): px(fr, cx + 40 + k * 22, FLOOR - 2 + (k % 2) * 4, 6, rb(f * 0.04 + k * 0.1), 200 - k * 35)
        if pmelt > 0 and 96 <= f: pass
        out.append(finish(fr))
    return out

# ---------------- 23. Breathing, wobbling world ----------------
def spiral(fr, cx, cy, r, f, arms=6, a=255):
    for arm in range(arms):
        for k in range(18):
            rr = r * k / 18; ang = arm * 6.283 / arms + k * 0.35 - f * 0.3
            px(fr, cx + rr * math.cos(ang), cy + rr * 0.8 * math.sin(ang), 4 + k // 6 * 2, rb(arm / arms + k * 0.03 + f * 0.02), a)
def s23():
    out = []; N = 124
    for f in range(N):
        I = trip(f, N, a=4, b=16); fr = new(pipe=False)
        sp = clamp((f - 4) / 10) * (1 - clamp((f - 28) / 8))
        if sp > 0: spiral(fr, SX, FLOOR - 70, 70 * sp, f, a=255)
        breath = 1 + 0.04 * math.sin(f * 0.35) * I
        if f >= 100: breath = 1
        draw_pipe_scaled(fr, breath, breath, pipe_bounce(f - 104))
        if 12 <= f < 30:
            t = (f - 12) / 18; sc = lerp(0.2, 1, ease_out(t)); ang = int((1 - t) * 720) // 30 * 30
            im = spr('R', scale=round(sc, 2)); im = im.rotate(ang, expand=True, resample=Image.NEAREST) if ang else im
            place(fr, im, SX, 0, cy=FLOOR - 66 * sc)
        elif 30 <= f < 104:
            t = (f - 30) / 70; base = lerp(SX, MOUTH - 70, ease_io(min(1, t)))
            sway = 50 * math.sin(f * 0.22) * (1 - clamp((f - 90) / 10)); cx = base + sway
            dirx = math.cos(f * 0.22)                       # moving right when sway increasing
            im, b = walk_frame(f); im = ImageOps.mirror(im) if dirx > 0.3 else im
            if f >= 96: im, b = walk_frame(f)
            place(fr, tint_rb(im, f * 0.03, 0.25 * I), cx, FLOOR - b - 4 * abs(math.sin(f * 0.4)), clip_x=MOUTH)
            if f % 6 == 0: glyph(fr, '?' if f % 12 else '!', cx + 30, 226, rb(f * 0.05), s=2)
        fr = hue_region(fr, 40 * math.sin(f * 0.15), I * 0.6)
        fr = wave_region(fr, 14 * I, 0.09, f * 0.45)
        out.append(finish(fr))
    return out

# ---------------- 24. Kaleidoscope clones ----------------
def s24():
    out = []; N = 124
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new()
        if I > 0:                                                 # rotating rainbow rays behind
            cxr = SX if f < 40 else lerp(SX, MOUTH + 120, clamp((f - 40) / 56))
            for i in range(12):
                ang = i * 0.5236 + f * 0.06; x2 = cxr + 260 * math.cos(ang); y2 = FLOOR - 70 + 120 * math.sin(ang)
                D(fr).polygon([(cxr, FLOOR - 70), (x2, y2), (cxr + 260 * math.cos(ang + 0.2), FLOOR - 70 + 120 * math.sin(ang + 0.2))], fill=rb(i / 12 + f * 0.02) + (int(60 * I),))
        R = spr('R')
        if 6 <= f < 26:                                           # copies converge into one
            t = ease_out((f - 6) / 20)
            for i in range(8):
                off = (i - 3.5) * 76 * (1 - t) - 20 * (1 - t); im = ImageOps.mirror(R) if i % 2 else R
                place(fr, tint_rb(im, i / 8, 0.6 * (1 - t)), SX + off, FLOOR)
        elif 26 <= f < 104:
            if f < 40: cx = SX; r = 110 * ease_out((f - 26) / 14)
            else: cx = lerp(SX, MOUTH - 80, ease_io((f - 40) / 62)); r = 110 * (1 - clamp((f - 84) / 14))
            n = 4; alive = n if f < 70 else max(0, n - (f - 70) // 6)
            for i in range(alive):
                th = f * 0.18 + i * 6.283 / n; ox = r * math.cos(th)
                im = ImageOps.mirror(R) if math.sin(th) > 0 else R
                place(fr, tint_rb(im, i / n + f * 0.02, 0.55), cx + ox, FLOOR - 6 * math.sin(th * 2), clip_x=MOUTH)
            im, b = walk_frame(f); place(fr, im, cx, FLOOR - b, clip_x=MOUTH)
            if 70 <= f < 94 and (f - 70) % 6 < 2: burst(fr, cx + 60, FLOOR - 70, 0.4, n=10, speed=70, cols=[rb(f * 0.1 + k * 0.2) for k in range(5)], seed=f)
        fr = hue_region(fr, f * 6, I * 0.5)
        draw_pipe(fr, 0, pipe_bounce(f - 102))
        if 102 <= f < 112: burst(fr, MOUTH + 6, MOUTH_Y, (f - 102) / 10, n=12, speed=80, cols=[rb(k / 6) for k in range(6)], seed=7)
        out.append(finish(fr))
    return out

# ---------------- 25. Prism rainbow trails ----------------
def s25():
    out = []; N = 126; trail = []
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new(); PX_, PY_ = SX + 30, 250
        pa = clamp((f - 4) / 6) * (1 - clamp((f - 30) / 8))
        if pa > 0:                                               # prism splitting a white beam
            rect(fr, PX_ + 14, PY_ + 4, 1600, 4, WHITE, 220 * pa) if False else rect(fr, PX_ + 14, PY_ + 4, QUIT_HOME[0] - PX_ - 14, 4, WHITE, 220 * pa)
            D(fr).polygon([(PX_, PY_ - 16), (PX_ - 16, PY_ + 14), (PX_ + 16, PY_ + 14)], fill=(200, 230, 255, int(230 * pa)), outline=WHITE + (int(255 * pa),))
            for i in range(7):
                ex = SX - 60 + i * 14; D(fr).line([(PX_ - 4, PY_ + 6), (ex, FLOOR - 4)], fill=rb(i / 7) + (int(220 * pa),), width=4)
        if 14 <= f < 30: place(fr, tint_rb(bayer_mask(spr('R'), (f - 14) / 10), f * 0.06, 0.5 * (1 - (f - 14) / 16)), SX, FLOOR)
        elif 30 <= f < 36: place(fr, spr('F', True, sy=0.88), SX, FLOOR)
        elif 36 <= f < 84:
            t = (f - 36) / 48; cx = lerp(SX, MOUTH - 110, ease_in(t) * 0.4 + t * 0.6); im, b = run_frame(f)
            trail.append(cx)
            for i in range(7):                                   # rainbow streak behind him
                rect(fr, cx + 30, FLOOR - 104 + i * 12 + 4 * math.sin(f * 0.8 + i * 0.6), min(SX + 40, cx + 30 + 900) - (cx + 30), 12, rb(i / 7), 150 * I)
            place(fr, tint(im, (255, 40, 80), 1, 0.55), cx + 10, FLOOR - b, clip_x=MOUTH)
            place(fr, tint(im, (40, 120, 255), 1, 0.55), cx - 10, FLOOR - b, clip_x=MOUTH)
            place(fr, im, cx, FLOOR - b, clip_x=MOUTH)
        elif 84 <= f < 100:
            fade = 1 - (f - 84) / 16
            for i in range(7): rect(fr, MOUTH, FLOOR - 104 + i * 12, (SX + 40 - MOUTH) * fade, 12, rb(i / 7), 150 * I * fade)
        pimg = PIPE
        if 80 <= f < 106: pimg = Image.fromarray(np.dstack([hue_rot_arr(np.array(PIPE)[..., :3].astype(float), (f - 80) * 30).astype(np.uint8), np.array(PIPE)[..., 3]]))
        draw_pipe(fr, 0, pipe_bounce(f - 84), pimg if f < 104 else PIPE)
        fr = hue_region(fr, f * 4, 0.25 * I)
        out.append(finish(fr))
    return out

# ---------------- 26. The pipe is alive ----------------
def eye(fr, cx, cy, rx, ry, look=0.0, iris_h=0.0, lid=1.0):
    ry2 = ry * lid
    if ry2 < 2: D(fr).line([(cx - rx, cy), (cx + rx, cy)], fill=(10, 14, 42, 255), width=4); return
    D(fr).ellipse([snap(cx - rx - 4), snap(cy - ry2 - 4), snap(cx + rx + 4), snap(cy + ry2 + 4)], fill=(10, 14, 42, 255))
    D(fr).ellipse([snap(cx - rx), snap(cy - ry2), snap(cx + rx), snap(cy + ry2)], fill=(250, 245, 255, 255))
    ir = min(rx, ry2) * 0.7; ix = cx + look * (rx - ir)
    D(fr).ellipse([snap(ix - ir), snap(cy - ir), snap(ix + ir), snap(cy + ir)], fill=rb(iris_h) + (255,))
    D(fr).ellipse([snap(ix - ir * 0.45), snap(cy - ir * 0.45), snap(ix + ir * 0.45), snap(cy + ir * 0.45)], fill=(10, 10, 10, 255))
    px(fr, ix - ir * 0.5, cy - ir * 0.6, 4, WHITE)
def s26():
    out = []; N = 130
    for f in range(N):
        I = trip(f, N, a=4, b=16); fr = new(pipe=False)
        sq = 1.0; pdy = 0
        if 40 <= f < 116: sq = 1 + 0.03 * math.sin(f * 0.4)
        if 100 <= f < 106: sq = [0.9, 0.86, 0.9, 1.05, 1.02, 1.0][f - 100]
        draw_pipe_scaled(fr, 2 - sq if 100 <= f < 106 else 1, sq, pipe_bounce(f - 116))
        # pipe face
        if 40 <= f < 120:
            lid = clamp((f - 40) / 6) * (1 - clamp((f - 112) / 6)); wx = SX if f < 50 else (lerp(SX, MOUTH - 70, ease_io((f - 50) / 34)) if f < 84 else MOUTH + 120)
            look = clamp((wx - 100) / 600)
            eye(fr, PIPE_HOME[0] + 100, PIPE_HOME[1] + 40, 18, 16, look, f * 0.03, lid); eye(fr, PIPE_HOME[0] + 136, PIPE_HOME[1] + 40, 18, 16, look, f * 0.03 + 0.5, lid)
            if 44 <= f < 52: glyph(fr, '!', PIPE_HOME[0] + 150, 226, GOLD)
        # tongue
        tip = None
        if 82 <= f < 102:
            L = (420 * ease_out((f - 82) / 8)) if f < 90 else 420 * (1 - ease_in((f - 90) / 12)); tip = MOUTH + L
            rect(fr, MOUTH - 4, FLOOR - 16, L + 4, 16, (240, 90, 140)); rect(fr, MOUTH - 4, FLOOR - 10, L, 4, (190, 50, 100))
            D(fr).ellipse([snap(tip - 14), FLOOR - 18, snap(tip + 14), FLOOR + 2], fill=(240, 90, 140, 255))
        # giant eye he steps out of
        el = clamp((f - 4) / 8) * (1 - clamp((f - 30) / 8))
        if el > 0: eye(fr, SX, FLOOR - 70, 66, 40, 0.15 * math.sin(f * 0.3), f * 0.02, el)
        if 16 <= f < 32:
            t = (f - 16) / 16; sc = round(lerp(0.15, 1, ease_out(t)), 2); place(fr, spr('R', scale=sc), SX, lerp(FLOOR - 50, FLOOR, ease_out(t)))
        elif 32 <= f < 50: place(fr, spr('D'), SX, FLOOR); glyph(fr, '?', SX + 40, 224) if f >= 40 else None
        elif 50 <= f < 84:
            t = (f - 50) / 34; cx = lerp(SX, MOUTH + 420 - 10, ease_io(t)); im, b = walk_frame(f); place(fr, im, cx, FLOOR - b)
        elif 84 <= f < 90: place(fr, spr('E'), MOUTH + 410, FLOOR - 16)
        elif 90 <= f < 102: place(fr, spr('E'), (tip or MOUTH) - 10, FLOOR - 16, clip_x=MOUTH)
        if 106 <= f < 116:
            burst(fr, MOUTH + 6, MOUTH_Y, (f - 106) / 10, n=14, speed=90, cols=[rb(k / 7) for k in range(7)], seed=8); glyph(fr, '*', MOUTH + 20, 232, GOLD)
        fr = hue_region(fr, f * 5, I * 0.45)
        out.append(finish(fr))
    return out

# ---------------- 27. Hypno spiral spin ----------------
def hypno(fr, cx, cy, r, f, a=255):
    n = 16
    for i in range(n):
        a0 = i / n * 6.283 + f * 0.25; a1 = a0 + 6.283 / n
        pts = [(cx, cy)] + [(cx + r * math.cos(a0 + (a1 - a0) * k / 4 + 0.6 * (rr := 1)), cy + r * 0.8 * math.sin(a0 + (a1 - a0) * k / 4 + 0.6)) for k in range(5)]
        D(fr).polygon(pts, fill=(rb(i / n + f * 0.01) if i % 2 else (20, 10, 40)) + (int(a),))
def s27():
    out = []; N = 124
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new()
        hr = 72 * clamp((f - 4) / 10) * (1 - clamp((f - 32) / 10))
        if hr > 2: hypno(fr, SX, FLOOR - 74, hr, f, 230)
        spin = None
        if 14 <= f < 32:
            t = (f - 14) / 18; sc = round(lerp(0.3, 1, ease_out(t)), 2); spin = (spr('R', scale=sc), SX, FLOOR - (1 - t) * 40, f * 0.9)
        elif 32 <= f < 104:
            t = (f - 32) / 70; cx = lerp(SX, MOUTH - 80, ease_io(t)); spin = (spr('R'), cx, FLOOR - 6 * abs(math.sin(f * 0.5)), f * 0.7)
            for k in range(8): px(fr, cx + 50 + k * 18, FLOOR - 40 - ((k * 13 + f * 7) % 70), 4, rb(k / 8 + f * 0.05), 230 - k * 25)
        if spin:
            im, cx, b, th = spin; c = math.cos(th); w = max(0.08, abs(c))
            im2 = scale_img(im, w, 1.0); im2 = ImageOps.mirror(im2) if c < 0 else im2
            place(fr, tint_rb(im2, th * 0.1, 0.3 * I), cx, b, clip_x=MOUTH)
        ps = 1.0
        if 102 <= f < 118: ps = math.cos((f - 102) / 16 * 6.283 * 1.5) if f < 116 else 1
        if ps < 0: draw_pipe_scaled(fr, max(0.06, abs(ps)), 1, 0, ImageOps.mirror(PIPE))
        else: draw_pipe_scaled(fr, max(0.06, ps), 1, pipe_bounce(f - 118))
        fr = hue_region(fr, f * 7, I * 0.4)
        out.append(finish(fr))
    return out

# ---------------- 28. Grow / shrink ----------------
def s28():
    out = []; N = 126
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new(pipe=False)
        if I > 0:                                               # pulsing checker floor overlay
            beat = (f // 6) % 2
            for x in range(0, FW, 40):
                if ((x // 40) + beat) % 2: rect(fr, x, FLOOR - 4, 40, 28, rb(x / FW + f * 0.02), 90 * I)
        s = 1.0
        if 6 <= f < 24: s = 1.08 * ease_back((f - 6) / 18, 1.4) if f < 22 else 1.0
        elif 24 <= f < 106: s = 0.55 + 0.45 * (0.5 + 0.5 * math.cos((f - 24) * 0.3))
        if f >= 96: s = min(s, 0.6)
        ps = 1.0 if f < 24 or f >= 108 else 1 + 0.04 * (1 - (s - 0.55) / 0.45) - 0.05 * ((s - 0.55) / 0.45)
        draw_pipe_scaled(fr, ps, ps, pipe_bounce(f - 108))
        if 6 <= f < 106:
            if f < 24: im = spr('R', scale=round(max(0.05, s), 2)); cx = SX; b = FLOOR
            else:
                t = (f - 24) / 80; cx = lerp(SX, MOUTH - 50, ease_io(t)); w, bb = walk_frame(f, scale=round(s, 2)); im, b = w, FLOOR - bb
            place(fr, tint_rb(im, f * 0.03, 0.25 * I), cx, b if f >= 24 else FLOOR, clip_x=MOUTH)
        if 6 <= f < 12: burst(fr, SX, FLOOR - 10, (f - 6) / 6, n=10, speed=60, cols=[rb(k / 5) for k in range(5)], seed=2)
        fr = hue_region(fr, f * 5, I * 0.35)
        out.append(finish(fr))
    return out

# ---------------- 29. Pixel swarm snake ----------------
def s29():
    out = []; N = 126; a = np.array(P1['R']); h1, w1 = a.shape[:2]
    rng = np.random.default_rng(9)
    pix = [(x, y, tuple(int(c) for c in a[y, x, :3])) for y in range(h1) for x in range(w1) if a[y, x, 3]]
    x0 = snap(SX - w1); y0 = FLOOR - h1 * 2
    starts = [(rng.uniform(300, 1700), rng.uniform(SAFE + 4, BOTTOM - 6)) for _ in pix]
    order = sorted(range(len(pix)), key=lambda i: (pix[i][1], pix[i][0]))
    rank = {i: r / len(pix) for r, i in enumerate(order)}
    def path(u):
        x = lerp(SX, MOUTH - 60, u); y = FLOOR - 70 + 50 * math.sin(u * 14) * (1 - u * 0.5); return x, y
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new(); d = D(fr)
        if 6 <= f < 30:
            t = ease_io((f - 6) / 22)
            for i, (x, y, c) in enumerate(pix):
                sx_, sy_ = starts[i]; tx, ty = x0 + x * 2, y0 + y * 2
                col = tuple(int(lerp(cc, c[k], t)) for k, cc in enumerate(rb(i * 0.002 + f * 0.05)))
                X = snap(lerp(sx_, tx, t) + (1 - t) * 30 * math.sin(f * 0.4 + i)); Y = snap(lerp(sy_, ty, t))
                d.rectangle([X, Y, X + 1, Y + 1], fill=col)
        elif 30 <= f < 44:
            place(fr, spr('D'), SX, FLOOR)
            if f >= 34: glyph(fr, '?', SX + 40, 224)
        elif 44 <= f < 104:
            T = (f - 44) / 50
            for i, (x, y, c) in enumerate(pix):
                u = T * 1.4 - rank[i] * 0.5
                if u <= 0: X, Y = x0 + x * 2, y0 + y * 2; col = c
                else:
                    u = min(u, 1.08); X, Y = path(u); X += (x - w1 / 2) * 0.6; Y += (y - h1 / 2) * 0.35
                    col = rb(rank[i] * 2 + f * 0.04)
                    if X < MOUTH: continue
                X, Y = snap(X), snap(Y); d.rectangle([X, Y, X + 1, Y + 1], fill=col)
        pimg = PIPE
        if 88 <= f < 108: pimg = Image.fromarray(np.dstack([hue_rot_arr(np.array(PIPE)[..., :3].astype(float), (f - 88) * 36).astype(np.uint8), np.array(PIPE)[..., 3]]))
        draw_pipe(fr, 0, pipe_bounce(f - 104), pimg if f < 107 else PIPE)
        fr = hue_region(fr, f * 5, I * 0.3)
        out.append(finish(fr))
    return out

# ---------------- 30. Disco moonwalk ----------------
def twinkles(fr, f, I, n=22, seed=30):
    """4-point twinkling stars scattered over the bar, each fading in and out on its own beat"""
    rng = random.Random(seed)
    for k in range(n):
        x = rng.uniform(120, FW - 360); y = rng.uniform(SAFE + 14, BOTTOM - 24); per = rng.choice((16, 20, 24)); off = rng.randrange(per)
        ph = (f + off) % per; t = ph / per
        if t > 0.6: continue
        a = 255 * I * math.sin(math.pi * t / 0.6)
        col = WHITE if k % 3 == 0 else rb(k / n + f * 0.01, 0.5, 1.0)
        arm = 2 + int(3 * math.sin(math.pi * t / 0.6))
        px(fr, x - 2, y - 2, 4, col, a)
        for j in range(1, arm + 1):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): px(fr, x - 2 + dx * j * 2, y - 2 + dy * j * 2, 2, col, a * (1 - j / (arm + 1)))
def s30():
    out = []; N = 130
    dance = [('H', False), ('B', False), ('E', False), ('B', True), ('H', False), ('D', False), ('E', False), ('B', True)]
    for f in range(N):
        I = trip(f, N, a=4, b=12); fr = new(); beat = f // 8
        if I > 0:
            for x in range(96, FW - 340, 48):
                for y in range(252, 372, 40):
                    if ((x // 48) + (y // 40) + beat) % 3 == 0: rect(fr, x, y, 44, 36, rb((x + y) / 900 + beat * 0.13), 110 * I)
            twinkles(fr, f, I)                                       # sparkles instead of the strobe flash (owner, 2026-10-28)
        dy = pipe_bounce(f - 106)
        if 24 <= f < 104 and f % 8 < 2: dy = min(dy, -4)
        draw_pipe(fr, 0, dy)
        if 8 <= f < 24:
            if f % 3 != 1: place(fr, spr('H'), SX, FLOOR)
        elif 24 <= f < 42:
            n, fl = dance[((f - 24) // 4) % len(dance)]; place(fr, spr(n, fl), SX, FLOOR - (6 if f % 4 < 2 else 0))
        elif 42 <= f < 106:
            t = (f - 42) / 62; cx = lerp(SX, MOUTH - 70, t)
            if 70 <= f < 76:
                n, fl = ('E', False) if f % 2 else ('R', False); place(fr, spr(n, fl), cx, FLOOR)
            else:
                im = spr('C', False, swap=(f // 4) % 2 == 1)            # facing right, gliding left
                place(fr, im, cx, FLOOR - (2 if (f // 4) % 2 else 0), clip_x=MOUTH)
        if 24 <= f < 106 and f % 8 == 0:
            pass
        for k in range(3):                                           # floating music notes
            st = 24 + k * 22
            if st <= f < st + 30 and f < 108:
                t = (f - st) / 30; glyph(fr, 'N', SX - 200 * k - 120 * t * (k % 2) + 60 - (f - 24) * 9 * 0 , 330 - 90 * t, rb(k / 3 + f * 0.03), s=4, a=255 * (1 - t))
        fr = hue_region(fr, f * 8, I * 0.3)
        out.append(finish(fr))
    return out

# ---------------- 31. Upside-down world ----------------
def flip_region(fr, amt):
    """amt 0 = normal, 1 = fully upside down (card-flip squash in between)"""
    if amt <= 0: return fr
    a = np.array(fr); reg = a[SAFE:BOTTOM].copy(); H = reg.shape[0]
    sc = abs(math.cos(amt * math.pi)); src = reg[::-1] if amt > 0.5 else reg
    h2 = max(2, int(H * sc) // 2 * 2); squ = np.array(Image.fromarray(src).resize((src.shape[1], h2), Image.NEAREST))
    bgreg = np.array(BG)[SAFE:BOTTOM].copy(); bgreg[:] = np.array(DARK, np.uint8)
    o = (H - h2) // 2; bgreg[o:o + h2] = squ; a[SAFE:BOTTOM] = bgreg
    return Image.fromarray(a)
def invert_region(fr, amt):
    if amt <= 0: return fr
    return region_op(fr, lambda r: r * (1 - amt) + (255 - r) * amt)
def s31():
    out = []; N = 132
    for f in range(N):
        I = trip(f, N, a=4, b=14); fr = new()
        if 6 <= f < 16: place(fr, spr('R') if f >= 9 else dissolve(spr('R'), (f - 6) / 3, seed=f), SX, FLOOR)
        elif 16 <= f < 30: place(fr, spr('D'), SX, FLOOR); glyph(fr, '?', SX + 40, 224) if f >= 22 else None
        elif 30 <= f < 106:
            t = (f - 30) / 74; cx = lerp(SX, MOUTH - 70, ease_io(t)); im, b = walk_frame(f); place(fr, im, cx, FLOOR - b, clip_x=MOUTH)
            for k in range(4):
                ph = (f * 3 + k * 20) % 60; glyph(fr, '?!'[k % 2], cx - 300 + k * 160, 240 + ph, rb(k / 4 + f * 0.04), s=2, a=200)
        draw_pipe(fr, 0, pipe_bounce(f - 118))
        if 6 <= f < 12: fr = invert_region(fr, 1.0 if f % 2 == 0 else 0.6)
        fr = hue_region(fr, 180 * I + f * 3, I * 0.5)
        fl = 0
        if 28 <= f < 40: fl = ease_io((f - 28) / 12)
        elif 40 <= f < 104: fl = 1
        elif 104 <= f < 116: fl = 1 - ease_io((f - 104) / 12)
        fr = flip_region(fr, fl)
        out.append(finish(fr))
    return out

SCENES = {22: ('22_trip_rainbow_melt', s22), 23: ('23_trip_breathing_world', s23), 24: ('24_trip_kaleidoscope', s24),
          25: ('25_trip_prism_rainbow_dash', s25), 26: ('26_trip_the_pipe_is_alive', s26), 27: ('27_trip_hypno_spin', s27),
          28: ('28_trip_grow_shrink', s28), 29: ('29_trip_pixel_swarm_snake', s29), 30: ('30_trip_disco_moonwalk', s30),
          31: ('31_trip_upside_down_world', s31)}
if __name__ == '__main__':
    ids = [int(x) for x in sys.argv[1:]] or list(SCENES)
    for i in ids:
        name, fn = SCENES[i]; frames = fn()
        picks = np.linspace(0, len(frames) - 1, 16).astype(int)
        sheet = Image.new('RGB', (890 * 2, 98 * 8))
        for k, p in enumerate(picks):
            sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
        sheet.save(f'/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/sheet_{i}.png')
        print(i, name, len(frames), write_gif(frames, name), flush=True)
