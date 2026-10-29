import sys, math, random
import numpy as np, scipy.ndimage as nd
from PIL import Image, ImageOps
from lib import *

def portal(fr, cx, o, f, rim=PURPLE, inner=(40, 10, 70), spark=PINK):
    if o <= 0.02: return
    rx = 36 * o; ry = 64 * min(1, o * 1.4); cy = FLOOR - 68
    D(fr).ellipse([snap(cx - rx), snap(cy - ry), snap(cx + rx), snap(cy + ry)], fill=inner + (int(235 * min(1, o)),))
    for i in range(18):
        ang = i / 18 * 6.283 + f * 0.35; rr = 0.25 + 0.6 * ((i * 7) % 5) / 5
        px(fr, cx + rx * rr * math.cos(ang), cy + ry * rr * math.sin(ang), 4, spark if i % 2 else rim, 220 * o)
    for i in range(44):
        ang = i / 44 * 6.283 - f * 0.18
        px(fr, cx + rx * math.cos(ang) - 2, cy + ry * math.sin(ang) - 2, 4, rim if i % 4 else WHITE, 255 * min(1, o))

# ---------------- 1. Portal Hop ----------------
def s1():
    out = []; PA = SX; PB = 300
    for f in range(100):
        fr = new()
        oA = ease_back((f - 5) / 10) if f < 68 else 1 - ease_io((f - 68) / 8)
        oB = ease_back((f - 54) / 10) if f < 84 else 1 - ease_io((f - 84) / 8)
        portal(fr, PA, oA if f >= 5 else 0, f)
        portal(fr, PB, oB if f >= 54 else 0, f, rim=CYAN, inner=(10, 30, 70), spark=WHITE)
        if 16 <= f < 34:                                   # step out of portal A
            t = (f - 16) / 18; cx = lerp(PA + 60, PA - 90, t); im, b = walk_frame(f)
            place(fr, im, cx, FLOOR - b, clip_xmax=PA)
        elif 34 <= f < 40: place(fr, spr('R'), PA - 90, FLOOR)
        elif 40 <= f < 54:
            place(fr, spr('I'), PA - 90, FLOOR)
            if f >= 42:                                    # orb shot flies to pipe side
                t = ease_in((f - 42) / 12); x = lerp(PA - 170, PB, t); y = FLOOR - 92 + 30 * t
                for k in range(5): px(fr, x + k * 14, y, 8 - k, CYAN if k else WHITE, 255 - k * 45)
        elif 54 <= f < 68:                                 # walk back into portal A
            t = (f - 54) / 14; cx = lerp(PA - 90, PA + 70, t)
            im, b = walk_frame(f); im = ImageOps.mirror(im)
            place(fr, im, cx, FLOOR - b, clip_xmax=PA)
        elif 66 <= f < 90:                                 # out of portal B, into the pipe
            t = (f - 66) / 22; cx = lerp(PB + 60, MOUTH - 80, t); im, b = walk_frame(f)
            place(fr, im, cx, FLOOR - b, clip_xmax=PB, clip_x=MOUTH)
        if 54 <= f < 62: burst(fr, PB, FLOOR - 70, (f - 54) / 8, n=14, speed=90, seed=4, life=1)
        k = f - 88; draw_pipe(fr, 0, pipe_bounce(k))
        if 88 <= f < 98: burst(fr, MOUTH + 6, MOUTH_Y, (f - 88) / 10, n=10, speed=70, cols=(PINK, PURPLE, WHITE), seed=2)
        out.append(finish(fr))
    return out

# ---------------- 2. Out from behind Quit, bunny hops ----------------
def s2():
    out = []; QCX = QUIT_HOME[0] + QUIT.width // 2
    hops = [SX - 40 - i * 230 for i in range(6)]          # landing spots
    for f in range(116):
        fr = new()
        qx = qy = 0
        if 6 <= f < 18: qx = 4 * math.sin(f * 2.4)
        if 18 <= f < 28: qy = -28 * ease_out((f - 18) / 10)
        elif 28 <= f < 40: qy = -28 * (1 - ease_back((f - 28) / 12, 2.5))
        # base without Quit, wizard behind, Quit on top
        base = fr; base.paste(Image.fromarray(noq_img), (0, 0)) if False else None
        fr.paste(QBG, (0, 0))
        if 20 <= f < 28:
            rise = ease_out((f - 20) / 8); place(fr, spr('E'), QCX - 40, FLOOR + 130 * (1 - rise), clip_floor=FLOOR)
        elif 28 <= f < 42:                                 # leap out
            t = (f - 28) / 14; cx = lerp(QCX - 40, SX - 40, ease_io(t)); h = 22 * math.sin(math.pi * t)
            place(fr, spr('E'), cx, FLOOR - h)
        elif 42 <= f < 46: place(fr, spr('R', sx=[1.12, 1.06, 1, 1][f - 42], sy=[0.88, 0.94, 1, 1][f - 42]), SX - 40, FLOOR)
        elif 46 <= f < 50: place(fr, spr('F', True, sy=0.88), SX - 40, FLOOR)
        elif 50 <= f < 104:                                # 5 hops + dive
            k = f - 50; i = k // 10; t = (k % 10) / 10
            if i < 5:
                x0, x1 = hops[i], hops[i + 1]; cx = lerp(x0, x1, t); h = 24 * math.sin(math.pi * t)
                im = spr('C', True, lean=18) if 0.15 < t < 0.85 else spr('F', True, sy=0.9)
                place(fr, im, cx, FLOOR - h)
                if k % 10 == 0: pass
            else:
                t = (k - 50) / 4; cx = lerp(hops[5], MOUTH - 90, t)
                place(fr, spr('F', True, rot=30), cx, FLOOR - 4, clip_x=MOUTH)
        for i in range(5):
            k = f - (50 + i * 10 + 9); dust(fr, hops[i + 1] + 30, FLOOR - 4, k / 30, seed=i)
        fr.paste(QUIT, (QUIT_HOME[0] + snap(qx), QUIT_HOME[1] + snap(qy)), QUIT)
        if 26 <= f < 36: burst(fr, QCX - 40, FLOOR - 40, (f - 26) / 10, n=10, speed=80, cols=(DUST, WHITE), seed=3)
        draw_pipe(fr, 0, pipe_bounce(f - 102))
        if 102 <= f < 112: burst(fr, MOUTH + 6, MOUTH_Y, (f - 102) / 10, n=8, speed=60, cols=(DUST, WHITE), seed=5)
        out.append(finish(fr))
    return out

# ---------------- 3. Pixel rain + telekinetic pipe ----------------
def s3():
    out = []; tgt = P1['R']; a = np.array(tgt); h1, w1 = a.shape[:2]
    x0 = snap(SX - w1); y0 = FLOOR - h1 * 2
    rng = np.random.default_rng(5)
    pix = [(x, y, tuple(a[y, x, :3]), (h1 - y) / h1 * 14 + rng.random() * 7) for y in range(h1) for x in range(w1) if a[y, x, 3]]
    STOP = SX - 66; DX = STOP - MOUTH
    for f in range(118):
        fr = new(pipe=False); pdx = 0; pdy = 0
        if 44 <= f < 50: pdy = -6 * ease_out((f - 44) / 6) + (2 if f % 2 else 0)
        elif 50 <= f < 66: pdx = DX * ease_io((f - 50) / 16); pdy = -6
        elif 66 <= f < 80: pdx = DX; pdy = -6 * (1 - ease_io((f - 66) / 4)) + pipe_bounce(f - 76)
        elif 80 <= f < 106: pdx = DX * (1 - ease_io((f - 80) / 26)); pdy = -4 * math.sin(math.pi * (f - 80) / 26)
        else: pdy = pipe_bounce(f - 106)
        if f < 32:
            for (x, y, c, d) in pix:
                t = (f - 4 - d) / 7
                if t < 0: continue
                ty = y0 + y * 2; yy = lerp(SAFE + 2, ty, ease_in(t)) if t < 1 else ty
                if t < 1 and yy > ty: yy = ty
                px(fr, x0 + x * 2, yy, 2, c)
            if f >= 28: burst(fr, SX, FLOOR - 66, (f - 28) / 6, n=12, speed=110, seed=1, life=1)
        elif f < 42: place(fr, spr('R'), SX, FLOOR)
        elif f < 62:
            place(fr, spr('I'), SX - 14, FLOOR)
            for i in range(8):                                 # telekinesis sparkles around pipe
                ang = f * 0.4 + i * 0.785; px(fr, PIPE_HOME[0] + pdx + 77 + 95 * math.cos(ang), MOUTH_Y + 70 * math.sin(ang), 4, CYAN if i % 2 else WHITE, 220)
            if f % 2 == 0:
                for k in range(6): px(fr, lerp(SX - 90, PIPE_HOME[0] + pdx + 150, k / 6), FLOOR - 92 + (k % 2) * 6, 4, CYAN, 140)
        elif f < 70: place(fr, spr('R'), SX, FLOOR)
        elif f < 78:
            t = (f - 70) / 8; cx = lerp(SX, STOP - 100, ease_in(t)); h = 22 * math.sin(math.pi * min(1, t * 1.3))
            place(fr, spr('E'), cx, FLOOR - h, clip_x=STOP)
        if 50 <= f < 66 or 80 <= f < 106:                      # whoosh lines behind moving pipe
            back = PIPE_HOME[0] + pdx + (-30 if f < 66 else 170)
            for i in range(5): rect(fr, back - (i * 17 % 40) - (70 if f < 66 else -10), 270 + i * 18, 60, 2, WHITE, 120)
        draw_pipe(fr, pdx, pdy)
        out.append(finish(fr))
    return out

# ---------------- 4. Smoke bomb + flying carpet ----------------
def carpet_img(f):
    w, h = 54, 7; im = Image.new('RGBA', (w, h + 3), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=(170, 30, 60, 255)); d.rectangle([0, 0, w - 1, 0], fill=GOLD + (255,)); d.rectangle([0, h - 1, w - 1, h - 1], fill=GOLD + (255,))
    for x in range(3, w - 3, 6): d.rectangle([x, 2, x + 2, 4], fill=(255, 200, 60, 255)); d.point((x + 1, 3), fill=(40, 10, 60, 255))
    for x in range(0, w, 3): d.point((x, h + (1 if (x // 3 + f // 3) % 2 else 2)), fill=GOLD + (255,)); d.point((x, h), fill=GOLD + (255,))
    for y in range(h): d.point((0, y), fill=GOLD + (255,)); d.point((w - 1, y), fill=GOLD + (255,))
    return U(im)
def s4():
    out = []; rng = random.Random(4)
    puffs = [(rng.uniform(-80, 30), rng.uniform(-110, -10), rng.uniform(26, 44), rng.random() * 4) for _ in range(12)]
    for f in range(112):
        fr = new(); wz = None; cpos = None
        if 14 <= f < 34: wz = (spr('B'), SX, FLOOR)
        elif 34 <= f < 46: wz = (spr('D'), SX, FLOOR)
        if 32 <= f < 46: cpos = (lerp(1820, SX, ease_out((f - 32) / 14)), FLOOR - 6)
        if 46 <= f < 54:                                  # hop on
            t = (f - 46) / 8; cpos = (SX, FLOOR - 6); wz = (spr('E'), SX, FLOOR - 20 - 16 * math.sin(math.pi * t) + (0 if t < 0.5 else 0))
        if 54 <= f < 100:                                 # fly left, skimming
            t = (f - 54) / 40; cx = lerp(SX, MOUTH - 110, ease_in(t) * 0.5 + t * 0.5); bob = 3 * math.sin(f * 0.6)
            cpos = (cx, FLOOR - 6 + bob); wz = (spr('R'), cx + 2, FLOOR - 20 + bob)
            for i in range(6): rect(fr, cx + 70 + (i * 23 + f * 9) % 80, 270 + i * 16, 50, 2, WHITE, 110)
        if wz: place(fr, *wz, clip_x=MOUTH)
        if cpos: place(fr, carpet_img(f), cpos[0], cpos[1], clip_x=MOUTH)
        if 6 <= f < 32:                                   # smoke puff
            t = (f - 6) / 26
            for (dx, dy, r, ph) in puffs:
                rr = r * (ease_out(t * 3) if t < 0.33 else 1 - ease_in((t - 0.33) / 0.67)) * (1 + 0.1 * math.sin(f + ph))
                if rr < 2: continue
                cx_, cy_ = SX + dx * (0.6 + t), FLOOR - 40 + dy * 0.6
                D(fr).ellipse([snap(cx_ - rr - 2), snap(cy_ - rr - 2), snap(cx_ + rr + 2), snap(cy_ + rr + 2)], fill=(70, 55, 100, 255))
            for (dx, dy, r, ph) in puffs:
                rr = r * (ease_out(t * 3) if t < 0.33 else 1 - ease_in((t - 0.33) / 0.67)) * (1 + 0.1 * math.sin(f + ph))
                if rr < 2: continue
                cx_, cy_ = SX + dx * (0.6 + t), FLOOR - 40 + dy * 0.6
                D(fr).ellipse([snap(cx_ - rr), snap(cy_ - rr), snap(cx_ + rr), snap(cy_ + rr)], fill=(175, 160, 205, 255))
                D(fr).ellipse([snap(cx_ - rr * 0.6), snap(cy_ - rr * 0.8), snap(cx_ + rr * 0.1), snap(cy_ - rr * 0.2)], fill=(215, 205, 235, 255))
        draw_pipe(fr, 0, pipe_bounce(f - 98))
        if 98 <= f < 110: burst(fr, MOUTH + 6, MOUTH_Y, (f - 98) / 12, n=12, speed=80, cols=(GOLD, ORANGE, WHITE), seed=6)
        out.append(finish(fr))
    return out

# ---------------- 5. Lightning + pipe teleport ----------------
def bolt(fr, x0, y0, x1, y1, f, w=6, col=WHITE, glow=CYAN):
    rng = random.Random(f); n = max(4, int(abs(y1 - y0 + x1 - x0) / 22)); pts = []
    for i in range(n + 1):
        t = i / n; j = 0 if i in (0, n) else rng.uniform(-14, 14)
        pts.append((x0 + (x1 - x0) * t + (j if abs(y1 - y0) > abs(x1 - x0) else 0), y0 + (y1 - y0) * t + (j if abs(y1 - y0) <= abs(x1 - x0) else 0)))
    d = D(fr)
    d.line(pts, fill=glow + (150,), width=w * 3); d.line(pts, fill=col + (255,), width=w)
def s5():
    out = []; NEWM = SX - 80; DX = NEWM - MOUTH
    for f in range(106):
        fr = new(pipe=False); pdx = 0; pal = 1.0; pimg = PIPE
        if 7 <= f <= 8 or f == 10: rect(fr, 0, SAFE, FW, FH - SAFE, WHITE, 40)
        if 6 <= f <= 10 and f != 9: bolt(fr, SX, SAFE + 2, SX, FLOOR, f)
        if 8 <= f < 22:
            im = spr('H') if f >= 12 else scan_glitch(spr('H'), f, 8)
            place(fr, im, SX, FLOOR); burst(fr, SX, FLOOR - 6, (f - 8) / 14, n=16, speed=120, cols=(CYAN, WHITE, GOLD), seed=8, grav=80)
        elif 22 <= f < 28: place(fr, spr('R'), SX, FLOOR)
        elif 28 <= f < 66 and not (f >= 62):
            place(fr, spr('I'), SX + 20, FLOOR)
            if 32 <= f < 46 and f % 3 != 2: bolt(fr, SX - 56, FLOOR - 104, MOUTH - 20, MOUTH_Y, f, w=4)
        elif 62 <= f < 72:
            t = (f - 62) / 10; cx = lerp(SX, NEWM - 110, ease_in(t)); place(fr, spr('E'), cx, FLOOR - 22 * math.sin(math.pi * min(1, t * 1.4)), clip_x=NEWM)
        # pipe state
        if f < 40: pimg = PIPE
        elif f < 46: pimg = scan_glitch(PIPE, f, 10)
        elif f < 52: pimg = dissolve(scan_glitch(PIPE, f, 6), 1 - (f - 46) / 6, seed=f)
        elif f < 54: pimg = None
        elif f < 62: pdx = DX; pimg = dissolve(PIPE, (f - 54) / 8, seed=3)
        elif f < 80: pdx = DX; pimg = PIPE
        elif f < 86: pdx = DX; pimg = dissolve(scan_glitch(PIPE, f, 8), 1 - (f - 80) / 6, seed=f)
        elif f < 88: pimg = None
        elif f < 96: pimg = dissolve(PIPE, (f - 88) / 8, seed=9)
        dy = pipe_bounce(f - 72) if 60 < f < 80 else pipe_bounce(f - 96)
        if pimg: draw_pipe(fr, pdx, dy, pimg)
        if 54 <= f < 62: burst(fr, NEWM - 70, MOUTH_Y, (f - 54) / 8, n=14, speed=100, seed=2)
        if 88 <= f < 96: burst(fr, MOUTH - 70, MOUTH_Y, (f - 88) / 8, n=14, speed=100, seed=3)
        out.append(finish(fr))
    return out

# ---------------- 6. Falling hat + shrink spell ----------------
def hat_parts():
    a = np.array(P1['R']); rgb = a[..., :3].astype(int)
    skin = (rgb[..., 0] > 200) & (rgb[..., 1] > 130) & (rgb[..., 1] < 200) & (rgb[..., 2] < 140) & (a[..., 3] > 0)
    face_row = np.nonzero(skin.any(1))[0][0] + 2
    m = a[:face_row, :, 3] > 0; lab, n = nd.label(m)
    cx = a.shape[1] // 2 + 4; col = lab[:, cx]; idx = np.bincount(col[col > 0]).argmax()
    hm = (lab == idx) & ~skin[:face_row]; hat = np.zeros_like(a[:face_row]); hat[hm] = a[:face_row][hm]
    ys, xs = np.nonzero(hm)
    return U(Image.fromarray(hat).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))), xs.min() * 2, ys.min() * 2
HAT, HX, HY = None, 0, 0
def s6():
    global HAT, HX, HY
    HAT, HX, HY = hat_parts(); out = []; W = spr('R').width; Hh = spr('R').height
    sx_left = SX - W // 2; hat_rest_top = FLOOR - HAT.height
    for f in range(112):
        fr = new()
        if 5 <= f < 30:                                  # hat falls, bounces, wiggles
            if f < 17: y = lerp(SAFE + 4, hat_rest_top, ease_in((f - 5) / 12))
            elif f < 23: y = hat_rest_top - 14 * math.sin(math.pi * (f - 17) / 6)
            else: y = hat_rest_top
            im = HAT if (f // 3) % 2 == 0 or f >= 17 else ImageOps.mirror(HAT)
            dx = (2 if f % 2 else -2) if f >= 24 else 0
            fr.paste(im, (snap(sx_left + HX + dx), snap(y)), im)
        if 30 <= f < 46:                                 # rises under the hat, lifting it
            rise = ease_out((f - 30) / 14); bottom = FLOOR + (Hh - HAT.height) * (1 - rise) + 2 * (1 - rise)
            place(fr, spr('R'), SX, bottom, clip_floor=FLOOR)
            top = bottom - Hh
            if top + HY > hat_rest_top: fr.paste(HAT, (snap(sx_left + HX), hat_rest_top), HAT)
        elif 46 <= f < 50: place(fr, spr('R', sx=1.08 if f < 48 else 1, sy=0.92 if f < 48 else 1), SX, FLOOR)
        elif 50 <= f < 62:
            place(fr, spr('D'), SX, FLOOR); glyph(fr, '?' if f < 58 else '!', SX + 40, 222, GOLD if f >= 58 else WHITE)
        elif 62 <= f < 74:
            sc = [1, .86, .86, .72, .72, .58, .58, .46, .46, .36, .36, .36][f - 62]
            place(fr, spr('R', scale=sc), SX, FLOOR); burst(fr, SX, FLOOR - 50, ((f - 62) % 4) / 4, n=8, speed=90, seed=f // 4, life=1)
        elif 74 <= f < 98:
            t = (f - 74) / 24; cx = lerp(SX, MOUTH - 40, ease_in(t) * 0.4 + t * 0.6)
            im, b = run_frame(f, scale=0.36, lean=12); place(fr, im, cx, FLOOR - b // 2, clip_x=MOUTH)
            if f % 2 == 0: px(fr, cx + 30, FLOOR - 6, 2, DUST, 200); px(fr, cx + 40, FLOOR - 10, 2, DUST, 120)
        draw_pipe(fr, 0, pipe_bounce(f - 96) // 2)
        if 98 <= f < 108: glyph(fr, '!', MOUTH - 30, 238 - (f - 98) * 2, GOLD, s=2, a=255 - (f - 98) * 20)
        out.append(finish(fr))
    return out

# ---------------- 7. Bubble float ----------------
def bubble(fr, cx, cy, rx, ry, a=255, f=0):
    n = 64
    for i in range(n):
        ang = i / n * 6.283; x = cx + rx * math.cos(ang); y = cy + ry * math.sin(ang)
        px(fr, x - 2, y - 2, 4, LBLUE if i % 8 else WHITE, a * 0.9)
    for i in range(6): ang = 3.6 + i * 0.12; px(fr, cx + rx * 0.72 * math.cos(ang) - 2, cy + ry * 0.72 * math.sin(ang) - 2, 4, WHITE, a)
    px(fr, cx + rx * 0.45, cy - ry * 0.55, 4, WHITE, a * 0.8)
    D(fr).ellipse([snap(cx - rx + 4), snap(cy - ry + 4), snap(cx + rx - 4), snap(cy + ry - 4)], fill=(110, 190, 255, int(a * 0.10)))
def s7():
    out = []; R0 = 60; small = 0.6
    for f in range(106):
        fr = new(); cy0 = FLOOR - 64
        if 5 <= f < 80:
            if f < 26: cx, cy, rx, ry, a = SX, cy0, R0, R0, 255 * ease_io((f - 5) / 16)
            elif f < 34: w = 6 * math.sin((f - 26) * 1.6) * (1 - (f - 26) / 8); cx, cy, rx, ry, a = SX, cy0, R0 + w, R0 - w, 255
            else:
                t = (f - 34) / 44; cx = lerp(SX, MOUTH + 70, ease_io(t)); cy = cy0 - 4 + 5 * math.sin(f * 0.35); rx = R0 + 2 * math.sin(f * 0.7); ry = R0 - 2 * math.sin(f * 0.7); a = 255
            im = spr('E', scale=small)
            if f < 28: im = bayer_mask(im, (f - 10) / 16)
            place(fr, im, cx, cy + 40 + 2 * math.sin(f * 0.5))
            bubble(fr, cx, cy, rx, ry, a, f)
        elif 80 <= f < 92:
            t = (f - 80) / 12; cx = lerp(MOUTH + 70, MOUTH - 70, ease_in(t)); y = min(FLOOR, cy0 + 40 + 60 * t * t * 2)
            im = spr('F', True, scale=small, rot=20 if t > 0.3 else 0); place(fr, im, cx, y, clip_x=MOUTH)
        if 80 <= f < 92: burst(fr, MOUTH + 70, cy0, (f - 80) / 12, n=18, speed=110, cols=(LBLUE, WHITE), seed=7, grav=120)
        draw_pipe(fr, 0, pipe_bounce(f - 90))
        if 90 <= f < 100: burst(fr, MOUTH + 4, MOUTH_Y, (f - 90) / 10, n=6, speed=50, cols=(LBLUE, WHITE), seed=1)
        out.append(finish(fr))
    return out

# ---------------- 8. Illusion clones conga ----------------
def s8():
    out = []; starts = [(SX - 220, 40, 0.0), (SX - 110, 44, 0.0), (SX, 48, 0.0)]
    for f in range(104):
        fr = new(); impacts = []
        if 5 <= f < 24:
            vis = f in (5, 6, 9, 12, 13, 16, 18, 19, 21, 22, 23)
            if vis:
                g = scan_glitch(spr('R'), f, 6)
                place(fr, tint(g, CYAN, 1, 0.5), SX + 8, FLOOR); place(fr, tint(g, PINK, 1, 0.5), SX - 8, FLOOR); place(fr, g, SX, FLOOR)
        elif 24 <= f < 38:
            t = ease_out((f - 26) / 10)
            for i, (x1, _, _) in enumerate(starts):
                im = spr('R') if i == 2 else tint(spr('R'), CYAN, 0.25)
                place(fr, im, lerp(SX, x1, t), FLOOR)
            if f == 26 or f == 27: burst(fr, SX, FLOOR - 70, 0.3, n=10, speed=60, seed=f)
        elif 38 <= f < 100:
            for i, (x1, st, _) in enumerate(starts):
                if f < st: im = spr('F', True, sy=0.9); cx = x1
                else:
                    t = (f - st) / 26; cx = lerp(x1, MOUTH - 100, ease_in(t) * 0.35 + t * 0.65)
                    im, b = run_frame(f + i)
                    if cx < MOUTH - 99: continue
                if i < 2: im = tint(im, CYAN, 0.25)
                place(fr, im, cx, FLOOR, clip_x=MOUTH)
        hits = [40 + 25, 44 + 25, 48 + 25]
        dy = 0
        for hh in hits: dy = min(dy, pipe_bounce(f - hh))
        draw_pipe(fr, 0, dy)
        for j, hh in enumerate(hits[:2]):
            if hh + 4 <= f < hh + 14: burst(fr, MOUTH + 6, MOUTH_Y, (f - hh - 4) / 10, n=8, speed=60, cols=(CYAN, PINK, WHITE), seed=j)
        if 78 <= f < 90: glyph(fr, '*', MOUTH - 30, 230, GOLD, s=4, a=255 - (f - 78) * 18)
        out.append(finish(fr))
    return out

# ---------------- 9. Magic puddle + vacuum pipe ----------------
def s9():
    out = []; TARGET = SX - 70 - MOUTH
    for f in range(116):
        fr = new(pipe=False); extra = 0; dy = 0
        pr = 0
        if 5 <= f < 44: pr = ease_back((f - 5) / 9) if f < 34 else 1 - ease_io((f - 34) / 10)
        if pr > 0:
            for k in range(3):                               # ripples
                t = ((f - 5) / 12 + k / 3) % 1
                rxx = 56 * pr + 50 * t; ry_ = 10 * pr + 8 * t
                for i in range(36):
                    ang = i / 36 * 6.283; px(fr, SX + rxx * math.cos(ang), FLOOR - 4 + ry_ * math.sin(ang), 2, CYAN, 200 * (1 - t))
            D(fr).ellipse([snap(SX - 56 * pr), snap(FLOOR - 4 - 11 * pr), snap(SX + 56 * pr), snap(FLOOR - 4 + 11 * pr)], fill=(8, 4, 20, 255), outline=CYAN + (255,), width=2)
        if 14 <= f < 34:
            rise = ease_out((f - 14) / 18); place(fr, spr('E'), SX, FLOOR + 136 * (1 - rise), clip_floor=FLOOR - 2)
            if pr > 0: D(fr).arc([snap(SX - 56 * pr), snap(FLOOR - 4 - 11 * pr), snap(SX + 56 * pr), snap(FLOOR - 4 + 11 * pr)], 0, 180, fill=CYAN + (255,), width=4)
        elif 34 <= f < 38: place(fr, spr('R', sx=1.1 if f < 36 else 1, sy=0.9 if f < 36 else 1), SX, FLOOR)
        elif 38 <= f < 70:
            place(fr, spr('D') if f < 62 else spr('B'), SX, FLOOR)
            if f < 54: glyph(fr, '?', SX + 40, 224)
            elif f >= 62: glyph(fr, '!', SX + 40, 224, GOLD)
        mouth = MOUTH
        if 50 <= f < 70: extra = TARGET * ease_out((f - 50) / 16) + (6 * math.sin((f - 50) * 1.3) if f >= 60 else 0)
        elif 70 <= f < 86: extra = TARGET
        elif 86 <= f < 104: extra = TARGET * (1 - ease_in((f - 86) / 18))
        dy = pipe_bounce(f - 104)
        mouth = MOUTH + snap(extra)
        if 70 <= f < 84:                                     # suction
            t = (f - 70) / 12
            for i in range(7): rect(fr, mouth + 20 + ((i * 37 - f * 22) % 100), 262 + i * 15, 36, 2, WHITE, 160)
            if f >= 74:
                tt = clamp((f - 74) / 8); sxs = 1 + 0.6 * tt; sys_ = 1 - 0.3 * tt
                cx = lerp(SX, mouth - 120, ease_in(tt)); place(fr, spr('B', sx=sxs, sy=sys_, lean=int(20 * tt)), cx, FLOOR - 8 * tt, clip_x=mouth)
            else: place(fr, spr('B', lean=6 * (f % 2)), SX - 4 * (f % 2), FLOOR)
        if extra < 2: draw_pipe(fr, 0, dy)
        else: p = stretched_pipe(extra); fr.paste(p, (PIPE_HOME[0], PIPE_HOME[1] + dy), p)
        if 82 <= f < 92: burst(fr, mouth + 6, MOUTH_Y, (f - 82) / 10, n=10, speed=70, cols=(CYAN, WHITE), seed=9)
        out.append(finish(fr))
    return out

# ---------------- 10. Thought cloud + rocket dash ----------------
def cloud(fr, cx, cy, s, a=255):
    blobs = [(-50, 6, 26), (-22, -12, 32), (14, -16, 30), (46, 0, 26), (-8, 14, 28), (28, 14, 24)]
    for col, grow in (((90, 80, 130), 4), ((225, 215, 245), 0)):
        for (dx, dy, r) in blobs:
            rr = r * s + grow
            D(fr).ellipse([snap(cx + dx * s - rr), snap(cy + dy * s - rr), snap(cx + dx * s + rr), snap(cy + dy * s + rr)], fill=col + (int(a),))
def s10():
    out = []; R = spr('R'); a = np.array(R); m = a[..., 3] > 0
    ring = m & ~nd.binary_erosion(m, iterations=2); ys, xs = np.nonzero(ring)
    ang = np.arctan2(ys - ys.mean(), xs - xs.mean()); order = np.argsort(ang)
    hero = spr('E', True, rot=90)                        # superman pose, head first to the left
    for f in range(108):
        fr = new()
        if 5 <= f < 34:                                  # thought bubbles + cloud
            for i, (dx, dy, r) in enumerate([(70, -20, 5), (56, -44, 8)]):
                if f >= 5 + i * 3: px(fr, SX + dx - r, FLOOR + dy - r, r * 2, (225, 215, 245), 255 * (1 if f < 26 else 1 - (f - 26) / 8))
            s = ease_back((f - 11) / 10) if f >= 11 else 0
            if s > 0:
                al = 255 if f < 26 else 255 * (1 - (f - 26) / 8)
                cloud(fr, SX - 10, 278, s, al)
                if f >= 16: place(fr, tint(spr('R', scale=0.3), (90, 80, 130), 0.2, al / 255), SX - 10, 300)
        if 22 <= f < 34:                                 # sketch outline
            n = int(len(order) * clamp((f - 22) / 10)); x0 = snap(SX - R.width / 2); y0 = FLOOR - R.height
            for j in order[:n]: px(fr, x0 + xs[j], y0 + ys[j], 2, WHITE, 230)
        if 34 <= f < 40:
            place(fr, bayer_mask(R, (f - 33) / 6), SX, FLOOR)
            x0 = snap(SX - R.width / 2); y0 = FLOOR - R.height
            for j in order[::2]: px(fr, x0 + xs[j], y0 + ys[j], 2, WHITE, 230 - (f - 34) * 38)
        elif 40 <= f < 56:
            place(fr, spr('D') if f < 50 else spr('H'), SX, FLOOR)
            glyph(fr, '?' if f < 50 else '!', SX + 40, 224, WHITE if f < 50 else GOLD)
        elif 56 <= f < 64:
            place(fr, spr('F', True, sy=0.86), SX + (2 if f % 2 else -2), FLOOR)
            for i in range(4): px(fr, SX + 20 + i * 10, FLOOR - 4 - ((f + i) % 3) * 4, 4, (ORANGE, GOLD)[i % 2], 220)
        elif 64 <= f < 92:                               # rocket dash
            t = (f - 64) / 26; cx = lerp(SX, MOUTH - 140, ease_in(t) * 0.5 + t * 0.5); cy = FLOOR - hero.height / 2 - 6 - 6 * math.sin(f * 0.5)
            tail = cx + hero.width / 2
            for k in range(14):                          # smoke trail
                age = k / 14; rr_ = random.Random(k * 13 + (f // 2)); sx_ = tail + k * 24 + rr_.randint(-6, 6); r = 6 + 22 * age + rr_.randint(-3, 3)
                yy_ = cy + 8 - 10 * age * rr_.random() + rr_.randint(-4, 4)
                if sx_ < SX + 90:
                    D(fr).ellipse([snap(sx_ - r), snap(yy_ - r * 0.8), snap(sx_ + r), snap(yy_ + r * 0.8)], fill=(110, 95, 140, int(150 * (1 - age))))
                    D(fr).ellipse([snap(sx_ - r * 0.6), snap(yy_ - r * 0.7), snap(sx_ + r * 0.3), snap(yy_)], fill=(190, 175, 215, int(140 * (1 - age))))
            for k in range(8):                           # flame
                fx = tail - 6 + k * 6 + random.Random(f * 9 + k).randint(0, 6); col = (WHITE, GOLD, ORANGE, RED)[min(3, k // 2)]
                px(fr, fx, cy + 2 + random.Random(f + k).randint(-10, 10), 6, col, 255 - k * 20)
            place(fr, hero, cx, 0, cy=cy, clip_x=MOUTH)
            if f == 64: pass
        if 64 <= f < 74: burst(fr, SX + 30, FLOOR - 8, (f - 64) / 10, n=14, speed=90, cols=(DUST, ORANGE), seed=10)
        draw_pipe(fr, 0, pipe_bounce(f - 88))
        if 88 <= f < 104:
            t = (f - 88) / 16
            for k in range(5): r = 8 + 30 * t + k * 4; D(fr).ellipse([snap(MOUTH + 10 + k * 14 - r), snap(MOUTH_Y - r), snap(MOUTH + 10 + k * 14 + r), snap(MOUTH_Y + r)], fill=(160, 145, 190, int(150 * (1 - t))))
            burst(fr, MOUTH + 8, MOUTH_Y, t, n=10, speed=90, cols=(GOLD, WHITE), seed=11)
        out.append(finish(fr))
    return out

QBG = Image.fromarray(np.array(new()).copy())
_q = np.array(QBG); _q[QUIT_HOME[1]:QUIT_HOME[1] + QUIT.height, QUIT_HOME[0]:QUIT_HOME[0] + QUIT.width][np.array(QUIT)[..., 3] > 0] = DARK
QBG = Image.fromarray(_q)

SCENES = {1: ('01_portal_hop', s1), 2: ('02_quit_button_bunny_hops', s2), 3: ('03_pixel_rain_pipe_comes_to_him', s3),
          4: ('04_smoke_bomb_flying_carpet', s4), 5: ('05_lightning_pipe_teleport', s5), 6: ('06_hat_trick_shrink_dash', s6),
          7: ('07_bubble_float', s7), 8: ('08_illusion_clone_conga', s8), 9: ('09_magic_puddle_vacuum_pipe', s9),
          10: ('10_thought_cloud_rocket_dash', s10)}
if __name__ == '__main__':
    ids = [int(x) for x in sys.argv[1:]] or list(SCENES)
    for i in ids:
        name, fn = SCENES[i]; frames = fn()
        np.save(f'/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/n_{i}.npy', np.array([len(frames)]))
        # contact sheet
        picks = np.linspace(0, len(frames) - 1, 12).astype(int)
        sheet = Image.new('RGB', (890 * 2, 104 * 6))
        for k, p in enumerate(picks):
            sheet.paste(frames[p].crop((0, 208, FW, 416)).resize((890, 104)), ((k % 2) * 890, (k // 2) * 104))
        sheet.save(f'/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/sheet_{i}.png')
        globals()['_frames_' + str(i)] = frames
        import pickle
        out = write_gif(frames, name); print(i, name, len(frames), out)
