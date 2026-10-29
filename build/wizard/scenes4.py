import sys, math, random, os
import numpy as np
from PIL import Image, ImageOps
from lib import *
import lib
import geo as GE
from geo import Geo, rb
import props2 as P2
from scenes2 import smoke
from scenes3 import trip, hue_region, scale_img, hue_rot_arr, draw_pipe_scaled

HERE = os.path.dirname(os.path.abspath(__file__))
P2.build_G(); lib.P1['G'] = Image.open(os.path.join(HERE, 'px_G.png'))
GY = 306
PCX = PIPE_HOME[0] + PIPE.width // 2          # pipe centre x

def darken(fr, I, a=120): rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (6, 2, 16), a * I)
def hue_img(img, deg):
    a = np.array(img); a[..., :3] = hue_rot_arr(a[..., :3].astype(float), deg).astype(np.uint8); return Image.fromarray(a)
def skin_top(name):
    a = np.array(lib.P1[name]).astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sk = (r > 200) & (g > 130) & (g < 200) & (b < 140) & (a[..., 3] > 0); sk[int(a.shape[0] * 0.5):] = False
    ys, xs = np.nonzero(sk); y0 = ys.min()
    return (xs.mean() + 0.5) * 2 - a.shape[1], y0 * 2 - a.shape[0] * 2
EYE = {n: skin_top(n) for n in 'GRE'}
def eye_xy(name, cx, bottom, scale=1.0):
    dx, dy = EYE[name]; return cx + dx * scale, bottom + dy * scale + 6 * scale
def third_eye(fr, x, y, o, h):
    if o <= 0: return
    for r in range(-3, 4):
        hw = int((7 - abs(r) * 2) * 1.0) // 2 * 2
        hh = 1 if abs(r) * 2 <= 6 * o else 0
        if hh: rect(fr, x - hw, y + r * 2 * o, hw * 2, 2, (250, 245, 255) if abs(r) < 3 else (10, 14, 42))
    if o > 0.4:
        rect(fr, x - 2, y - 2, 4, 4, rb(h)); rect(fr, x - 1 + (x % 2), y - 1, 2, 2, (10, 10, 10))

# ---------------------------------------------------------------- 32 Flower of Life
def s32():
    out = []; N = 138
    for f in range(N):
        I = trip(f, N, a=4, b=20, tail=22); fr = new(pipe=False)
        fr = hue_region(fr, f * 4, I * 0.3); darken(fr, I)
        if f < 44: fc, r = SX, 26
        elif f < 96: t = (f - 44) / 52; fc = lerp(SX, MOUTH + 80, ease_io(t)); r = lerp(26, 20, clamp((f - 44) / 10))
        else: fc, r = MOUTH + 80, 20
        g = Geo()
        fa = 255 * clamp((f - 6) / 4) * (1 - clamp((f - 98) / 6))
        if fa > 0: GE.flower_of_life(g, fc, GY, r, clamp((f - 6) / 28), f * 0.01, fa, rot=max(0, f - 34) * 0.03)
        if 99 <= f < 128:
            q = ease_out((f - 99) / 8) * (1 - clamp((f - 116) / 12))
            for i in range(16):
                ang = i / 16 * 6.283 + f * 0.04
                g.line((PCX, GY), (PCX + 420 * q * math.cos(ang), GY + 420 * q * math.sin(ang)), rb(i / 16 + f * 0.02), 150 * q, glow=False)
            GE.flower_of_life(g, PCX, GY, 27 * q, 1, f * 0.02, 255 * q, rot=-f * 0.05)
        g.render(fr)
        bob = 3 * math.sin(f * 0.3)
        if 16 <= f < 36: place(fr, bayer_mask(tint(spr('G'), WHITE, 0.7 * (1 - (f - 16) / 20)), (f - 16) / 12), fc, FLOOR - 6)
        elif 36 <= f < 96: place(fr, spr('G'), fc, FLOOR - 6 + bob)
        elif 96 <= f < 102:
            t = (f - 96) / 6; place(fr, tint(spr('G', scale=round(lerp(1, 0.3, t), 2)), WHITE, t * 0.6), lerp(fc, MOUTH - 20, t), FLOOR - 6, clip_x=MOUTH)
        s = 0
        if 99 <= f < 112: s = ease_out((f - 99) / 10)
        elif 112 <= f < 130: s = 1 - ease_io((f - 112) / 16)
        if not GE.draw_shards(fr, s, tintf=lambda im: tint(im, rb(f * 0.03), 0.4 * s)):
            draw_pipe(fr, 0, pipe_bounce(f - 130), tint(PIPE, rb(f * 0.03), 0.4 * clamp((f - 80) / 16)) if 80 <= f < 99 else None)
        if 99 <= f < 102: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [120, 70, 30][f - 99])
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 33 Metatron's Cube
CUBE_E = GE.edges_of(GE.CUBE)
def s33():
    out = []; N = 142
    for f in range(N):
        I = trip(f, N, a=4, b=18, tail=22); fr = new(pipe=False)
        fr = hue_region(fr, f * 3, I * 0.25); darken(fr, I)
        g = Geo(); g2 = Geo()
        if 6 <= f < 52: GE.metatron(g, SX, GY, 15, clamp((f - 6) / 14), clamp((f - 18) / 16), f * 0.01, 255 * (1 - clamp((f - 40) / 12)), rot=(f - 6) * 0.02)
        cs, cxc, roll = 0, SX, 0.0
        if 38 <= f < 50: cs = 72 * ease_back((f - 38) / 12)
        elif 50 <= f < 96: cs = 72; cxc = lerp(SX, MOUTH + 80, ease_io((f - 50) / 46)); roll = -(SX - cxc) / 72
        elif 96 <= f < 104: t = (f - 96) / 8; cs = 72 * (1 - ease_in(t)); cxc = lerp(MOUTH + 80, MOUTH + 10, t); roll = -(SX - MOUTH - 80) / 72 - t
        if cs > 1: GE.wire(g2, GE.CUBE, CUBE_E, cxc, GY, cs, 0.45 + f * 0.015, 0.6 + f * 0.02, roll, f * 0.01, 255, hstep=0.08)
        if 103 <= f < 132:
            q = ease_out((f - 103) / 10) * (1 - clamp((f - 120) / 12))
            GE.metatron(g, PCX, GY, 16 * q, 1, 1, f * 0.015, 255 * q, rot=f * 0.04)
        g.render(fr)
        if 20 <= f < 36: place(fr, bayer_mask(tint(spr('R'), WHITE, 0.7 * (1 - (f - 20) / 16)), (f - 20) / 12), SX, FLOOR)
        elif 36 <= f < 50: place(fr, spr('R') if (f // 5) % 2 == 0 else spr('D'), SX, FLOOR)
        elif 50 <= f < 104:
            im, b = walk_frame(f); x = cxc if f < 96 else lerp(MOUTH + 80, MOUTH - 70, (f - 96) / 8)
            place(fr, im, x, FLOOR - b, clip_x=MOUTH)
        g2.render(fr)
        s = 0
        if 103 <= f < 114: s = ease_out((f - 103) / 9)
        elif 114 <= f < 134: s = 1 - ease_io((f - 114) / 18)
        if not GE.draw_shards(fr, s, tintf=lambda im: hue_img(im, f * 20)): draw_pipe(fr, 0, pipe_bounce(f - 134))
        if 103 <= f < 106: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [110, 60, 25][f - 103])
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 34 The Shaman
def s34():
    out = []; N = 154; SHX = SX - 160
    E1 = lib.P1['E']; a = np.array(E1); pix = [(x, y, tuple(int(c) for c in a[y, x, :3])) for y in range(a.shape[0]) for x in range(a.shape[1]) if a[y, x, 3]]
    rng = random.Random(3); rank = [rng.random() for _ in pix]
    for f in range(N):
        I = trip(f, N, a=50, b=66, tail=26); fr = new(pipe=False)
        fr = hue_region(fr, f * 5, I * 0.35); darken(fr, I, 90)
        g = Geo()
        sh = U(P2.shaman(beat=(f // 5) % 2 if 18 <= f < 46 else 0, offer=44 <= f < 58 or (104 <= f < 116 and (f // 3) % 2)))
        sl = snap(SHX - sh.width / 2); stop = FLOOR - sh.height
        drum = (sl + 75, stop + 75); hand = (sl + 70, stop + 58)
        for b0 in range(18, 46, 10):                                  # drum ripples
            age = f - b0
            if 0 <= age < 16: g.circle(drum[0], drum[1], 8 + age * 7, rb(b0 * 0.1 + age * 0.04), 255 * (1 - age / 16), sy=0.75)
        wz = None
        if 22 <= f < 36: wz = ('G', dissolve(spr('G'), (f - 22) / 14, seed=f), FLOOR)
        elif 36 <= f < 70: wz = ('G', spr('G'), FLOOR)
        elif 70 <= f < 84: lift = 14 * ease_out((f - 70) / 10); wz = ('E', spr('E'), FLOOR - lift + 2 * math.sin(f * 0.5))
        ex, ey = eye_xy(wz[0], SX, wz[2]) if wz else eye_xy('E', SX, FLOOR - 14)
        if 44 <= f < 60:                                               # the offered orb
            t = ease_io((f - 46) / 12) if f >= 46 else 0; ox, oy = lerp(hand[0] + 10, ex, t), lerp(hand[1] - 10, ey, t) - 30 * math.sin(math.pi * t)
            g.circle(ox, oy, 18 * (1 - 0.6 * t), rb(f * 0.05), 255); g.circle(ox, oy, 22 * (1 - 0.6 * t), rb(f * 0.05 + 0.5), 140, glow=False)
            GE.dmt(g, ox, oy, 6 * (1 - 0.6 * t), 1, f * 0.04, 255, rot=f * 0.2, labels=False)
        if 60 <= f < 84:                                               # rings from the opened third eye
            for k in range(3):
                age = (f - 60 - k * 5)
                if 0 <= age < 14: g.circle(ex, ey, 6 + age * 9, rb(k / 3 + f * 0.03), 255 * (1 - age / 14))
        if 84 <= f < 112:                                              # double-helix pixel stream into the pipe
            T = (f - 84) / 20; sx0 = snap(SX - E1.width); sy0 = FLOOR - 14 - E1.height * 2
            d = D(fr)
            for i, (x, y, c) in enumerate(pix):
                u = T * 1.35 - rank[i] * 0.35
                if u <= 0: X, Y, col = sx0 + x * 2, sy0 + y * 2, c
                else:
                    u = min(u, 1.05); strand = 0 if i % 2 else math.pi
                    X = lerp(SX, MOUTH - 10, ease_in(u) * 0.3 + u * 0.7); Y = GY + 34 * math.sin(u * 14 + strand) * (1 - u * 0.6) + (y - E1.height / 2) * 0.25
                    col = rb(u + (0 if strand else 0.5) + f * 0.02)
                    if X < MOUTH: continue
                X, Y = snap(X), snap(Y); d.rectangle([X, Y, X + 1, Y + 1], fill=col)
        if 100 <= f < 122:
            q = ease_out((f - 100) / 8) * (1 - clamp((f - 112) / 10)); GE.flower_of_life(g, PCX, GY, 22 * q, 1, f * 0.02, 255 * q, rot=f * 0.05)
        g.render(fr)
        sa = clamp((f - 10) / 8) * (1 - clamp((f - 120) / 10))
        if sa > 0: place(fr, sh if sa >= 1 else bayer_mask(sh, sa), SHX, FLOOR)
        if 4 <= f < 20: smoke(fr, SHX, FLOOR - 50, (f - 4) / 16, seed=5, n=9, spread=50, base=(120, 100, 150), dark=(60, 40, 80), size=26)
        if 118 <= f < 134: smoke(fr, SHX, FLOOR - 50, (f - 118) / 16, seed=6, n=9, spread=50, base=(120, 100, 150), dark=(60, 40, 80), size=26)
        if wz: place(fr, wz[1], SX, wz[2])
        if 58 <= f < 84: third_eye(fr, ex, ey, clamp((f - 58) / 6), f * 0.05)
        if 58 <= f < 61: burst(fr, ex, ey, (f - 58) / 3, n=12, speed=90, cols=[rb(k / 6) for k in range(6)], seed=1)
        pimg = hue_img(PIPE, (f - 92) * 24) if 92 <= f < 114 else PIPE
        draw_pipe(fr, 0, pipe_bounce(f - 108), pimg)
        if 104 <= f < 116: glyph(fr, '*', SHX + 40, 232, GOLD, s=2)
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 35 Spirit Molecule
def s35():
    out = []; N = 148; MX0 = SX - 40
    for f in range(N):
        I = trip(f, N, a=4, b=20, tail=22); fr = new(pipe=False)
        fr = hue_region(fr, f * 4, I * 0.3); darken(fr, I)
        g = Geo(); mx, my, L, rot, pr = MX0, GY, 30.0, 0.0, clamp((f - 6) / 26)
        if 46 <= f < 56: L = lerp(30, 20, ease_io((f - 46) / 10))
        elif 56 <= f < 98:
            t = (f - 56) / 42; L = 20; mx = lerp(MX0, MOUTH + 90, ease_io(t)); my = GY + 14 * math.sin(f * 0.3); rot = (f - 56) * 0.08
            for k in range(8): g.dot(mx + 70 + k * 22, my + 16 * math.sin(f * 0.5 + k), rb(k / 8 + f * 0.04), 255 - k * 28, 2)
        elif 98 <= f < 106: t = (f - 98) / 8; L = 20 * (1 - t); mx = lerp(MOUTH + 90, MOUTH + 10, t); rot = 42 * 0.08 + t * 2
        P = None
        if 6 <= f < 106 and L > 1: P = GE.dmt(g, mx, my, L, pr, f * 0.01, 255, rot=rot)
        if 104 <= f < 134:
            q = ease_out((f - 104) / 10) * (1 - clamp((f - 120) / 14))
            GE.dmt(g, PCX + 30, GY + 10, 30 * q, 1, f * 0.02, 255 * q, rot=-0.4 + f * 0.02)
            g.circle(PCX + 30, GY, 90 * q, rb(f * 0.03), 200 * q)
        g.render(fr)
        if 28 <= f < 44: place(fr, bayer_mask(tint(spr('E'), WHITE, 0.6 * (1 - (f - 28) / 16)), (f - 28) / 12), MX0, FLOOR)
        elif 44 <= f < 46: place(fr, spr('E'), MX0, FLOOR)
        elif 46 <= f < 104 and P:
            bx = sum(P[f'b{k}'][0] for k in range(6)) / 6; by = sum(P[f'b{k}'][1] for k in range(6)) / 6
            if f < 56:
                t = ease_io((f - 46) / 10); sc = round(lerp(1, 0.42, t), 2); place(fr, spr('E', scale=sc), lerp(MX0, bx, t), lerp(FLOOR, by + 18, t))
            else: place(fr, spr('E', scale=0.42), bx, by + 18 + 2 * math.sin(f * 0.6), clip_x=MOUTH)
        s = 0
        if 104 <= f < 114: s = ease_out((f - 104) / 9)
        elif 114 <= f < 134: s = 1 - ease_io((f - 114) / 18)
        if not GE.draw_shards(fr, s, tintf=lambda im: tint(im, rb(f * 0.04), 0.35)): draw_pipe(fr, 0, pipe_bounce(f - 134))
        if 104 <= f < 107: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [110, 60, 25][f - 104])
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 36 Third Eye / Sri Yantra
def s36():
    out = []; N = 146
    for f in range(N):
        I = trip(f, N, a=4, b=24, tail=24); fr = new(pipe=False)
        fr = hue_region(fr, f * 3, I * 0.3); darken(fr, I)
        g = Geo(); lev = 10 * ease_out((f - 6) / 14) + 3 * math.sin(f * 0.3)
        bottom = FLOOR - lev; ex, ey = eye_xy('G', SX, bottom)
        if 30 <= f < 76:
            R = 80 * ease_out((f - 30) / 26) * (1 - clamp((f - 62) / 14))
            GE.sri_yantra(g, SX, GY, R, clamp((f - 30) / 20), f * 0.01, 255, rot=f * 0.01)
        if 62 <= f < 116:
            R = 80 * ease_out((f - 62) / 14) * (1 - ease_in(clamp((f - 100) / 14)))
            GE.sri_yantra(g, PCX + 10, GY, R, clamp((f - 62) / 12), f * 0.012, 255, rot=-(f - 62) * 0.02 * (1 + 3 * clamp((f - 92) / 12)))
        if 56 <= f < 92:                                               # beam
            p = clamp((f - 56) / 8); a_ = 255 * (1 - clamp((f - 84) / 8))
            tx, ty = lerp(ex, MOUTH + 10, p), lerp(ey, MOUTH_Y, p)
            for k in range(-2, 3): g.line((ex, ey + k * 2), (tx, ty + k * 2), rb(k * 0.1 + f * 0.03), a_, glow=k == 0)
        if 70 <= f < 86:
            t = ease_in((f - 70) / 14); ox, oy = lerp(ex, MOUTH + 10, t), lerp(ey, MOUTH_Y, t)
            for k in range(6): g.dot(ox + 14 * k * (1 if k % 2 else -1) * 0.3, oy, (255, 255, 255) if k < 2 else rb(k / 6), 255, 4 - k // 2)
        if 82 <= f < 116:
            q = clamp((f - 82) / 8) * (1 - clamp((f - 104) / 10)); GE.spirit_pipe(g, f * 0.04, 255 * q)
        g.render(fr)
        if 6 <= f < 20: place(fr, bayer_mask(tint(spr('G'), WHITE, 0.6), (f - 6) / 14), SX, bottom); burst(fr, SX, FLOOR - 10, (f - 6) / 14, n=12, speed=70, seed=2, grav=-90)
        elif 20 <= f < 66: place(fr, spr('G'), SX, bottom)
        elif 66 <= f < 80: place(fr, bayer_mask(tint(spr('G'), WHITE, clamp((f - 66) / 6)), 1 - (f - 66) / 14), SX, bottom)
        if 22 <= f < 76: third_eye(fr, ex, ey, clamp((f - 22) / 10), f * 0.04)
        pa = 1.0
        if 84 <= f < 98: pa = 1 - (f - 84) / 14
        elif 98 <= f < 104: pa = 0
        elif 104 <= f < 118: pa = (f - 104) / 14
        if pa > 0: draw_pipe(fr, 0, pipe_bounce(f - 118), bayer_mask(PIPE, pa) if pa < 1 else None)
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 37 Hyperspace Tunnel
def s37():
    out = []; N = 142; TC = (MOUTH + 10, GY)
    for f in range(N):
        I = trip(f, N, a=10, b=30, tail=26); fr = new()
        fr = hue_region(fr, f * 6, I * 0.3); darken(fr, I, 160)
        if I > 0: draw_pipe(fr, 0, 0, hue_img(PIPE, f * 18))
        g = Geo()
        if I > 0:
            sp = f * 0.3 + 1.6 * clamp((f - 80) / 24) ** 2 * (f - 80) if f > 80 else f * 0.3
            GE.hex_tunnel(g, TC[0], TC[1], sp, 255 * I, h=f * 0.01, twist=0.3)
        g.render(fr)
        if 6 <= f < 16: place(fr, scan_glitch(spr('R'), f, 8) if f < 13 else spr('R'), SX, FLOOR)
        elif 16 <= f < 30: place(fr, spr('D'), SX, FLOOR); glyph(fr, '?' if f < 24 else '!', SX + 40, 224, WHITE if f < 24 else GOLD)
        elif 30 <= f < 40: place(fr, spr('E'), SX + (2 if f % 2 else -2), FLOOR - 4 * (f - 30) / 10)
        elif 40 <= f < 98:
            t = (f - 40) / 58; u = ease_in(t); sc = lerp(1, 0.12, u ** 1.2)
            im = scale_img(spr('E'), sc * (1 + 0.8 * u), sc * (1 - 0.3 * u)); ang = int(u * 720) // 30 * 30
            if ang: im = im.rotate(ang, expand=True, resample=Image.NEAREST)
            place(fr, im, lerp(SX, TC[0], u), 0, cy=lerp(FLOOR - 70, TC[1], u))
            for k in range(6): px(fr, lerp(SX, TC[0], u) + 40 + k * 20, lerp(FLOOR - 70, TC[1], u) + 18 * math.sin(f + k), 4, rb(k / 6 + f * 0.05), 220 - k * 30)
        if 96 <= f < 108: burst(fr, TC[0], TC[1], (f - 96) / 12, n=24, speed=200, cols=[rb(k / 8) for k in range(8)], seed=4, s=6)
        if 97 <= f < 100: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [120, 70, 30][f - 97])
        if I <= 0: draw_pipe(fr)
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 38 Machine Elves
OCTA_E = GE.edges_of(GE.OCTA)
def s38():
    out = []; N = 158; NE = 6
    spots = [SX - 210 + k * 44 for k in range(NE)]
    pyr = [(SX - 36, 0), (SX, 0), (SX + 36, 0), (SX - 18, 36), (SX + 18, 36), (SX, 72)]
    for f in range(N):
        I = trip(f, N, a=6, b=24, tail=24); fr = new(pipe=False)
        fr = hue_region(fr, f * 5, I * 0.3); darken(fr, I, 90)
        g = Geo(); elves = []; wz = None; pdy = 0
        for k in range(NE):
            st = 8 + k * 4; h = k / NE + f * 0.01; blink = (f + k * 7) % 40 < 2
            if f < st: continue
            if f < st + 26:                                            # tumble out of the pipe
                t = (f - st) / 26; x = lerp(MOUTH + 10, spots[k], ease_io(t)); y = FLOOR - abs(math.sin(t * math.pi * 3)) * (34 - 20 * t)
                elves.append((k, h, x, y, (int(t * 8) * 90) % 360, blink))
                if f - st < 6: pdy = min(pdy, pipe_bounce(f - st))
            elif f < 40: elves.append((k, h, spots[k], FLOOR - (6 if (f + k) % 8 < 4 else 0), 0, blink))
            elif f < 52:
                t = ease_io((f - 40) / 12); x = lerp(spots[k], pyr[k][0], t); y = lerp(FLOOR, FLOOR - pyr[k][1], t)
                elves.append((k, h, x, y, 0, blink))
            elif f < 56: elves.append((k, h, pyr[k][0], FLOOR - pyr[k][1], 0, blink))
            elif f < 76:
                ang = (f - 56) * 0.25 + k / NE * 6.283; x = SX + 110 * math.cos(ang); y = FLOOR - abs(math.sin((f + k * 3) * 0.5)) * 18
                elves.append((k, h, x, y, 0, blink))
            elif f < 84:
                t = ease_io((f - 76) / 8); ang = 20 * 0.25 + k / NE * 6.283
                x = lerp(SX + 110 * math.cos(ang), SX - 60 + k * 24, t); elves.append((k, h, x, FLOOR, 0, blink))
            else:
                t = (f - 84) / 40; gx = lerp(SX, MOUTH - 150, ease_io(t)); x = gx - 60 + k * 24
                if x < MOUTH - 20: continue
                elves.append((k, h, x, FLOOR - (4 if (f + k * 2) % 6 < 3 else 0), 0, blink))
        if 40 <= f < 56:                                               # juggled gems
            for k in range(3):
                ang = f * 0.4 + k * 2.094; GE.wire(g, GE.OCTA, OCTA_E, SX + 40 * math.cos(ang), FLOOR - 120 + 16 * math.sin(ang), 10, f * 0.1, f * 0.13, 0, k / 3, 255, glow=False)
        if 56 <= f < 61: burst(fr, SX, FLOOR - 70, (f - 56) / 5, n=24, speed=150, cols=[rb(k / 8) for k in range(8)], seed=9)
        if 56 <= f < 70: wz = (spr('H') if f >= 60 else bayer_mask(spr('H'), (f - 56) / 4), SX, FLOOR)
        elif 70 <= f < 76: wz = (spr('E'), SX, FLOOR - 10 * (f - 70) / 6)
        elif 76 <= f < 84:
            t = (f - 76) / 8; wz = (spr('E', rot=90 if t > 0.5 else 45), SX, FLOOR - 36)
        elif 84 <= f < 124:
            t = (f - 84) / 40; gx = lerp(SX, MOUTH - 150, ease_io(t)); wz = (spr('E', rot=90), gx, FLOOR - 36 - (2 if f % 6 < 3 else 0))
            if 108 <= f < 114: pdy = min(pdy, pipe_bounce(f - 108))
        if 120 <= f < 132: pdy = min(pdy, pipe_bounce(f - 126))
        g.render(fr)
        if wz: place(fr, wz[0], wz[1], wz[2], clip_x=MOUTH)
        for (k, h, x, y, ang, blink) in elves:
            im = U(P2.elf(h, blink)); im = im.rotate(ang, expand=True, resample=Image.NEAREST) if ang else im
            place(fr, im, x, y, clip_x=MOUTH if f >= 80 else None)
        draw_pipe(fr, 0, pdy, tint(PIPE, rb(f * 0.04), 0.35 * clamp((f - 4) / 4) * (1 - clamp((f - 34) / 6))) if 4 <= f < 40 else None)
        if 124 <= f < 136: burst(fr, MOUTH + 6, MOUTH_Y, (f - 124) / 12, n=14, speed=80, cols=[rb(k / 7) for k in range(7)], seed=12)
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 39 Torus Field
def s39():
    out = []; N = 144
    for f in range(N):
        I = trip(f, N, a=4, b=22, tail=24); fr = new(pipe=False)
        fr = hue_region(fr, f * 4, I * 0.3); darken(fr, I)
        g = Geo(); g2 = Geo(); tcx, R, r = SX, 58.0, 24.0
        if 44 <= f < 92: tcx = lerp(SX, MOUTH + 90, ease_io((f - 44) / 48))
        elif 92 <= f < 104: t = (f - 92) / 12; tcx = lerp(MOUTH + 90, MOUTH + 10, t); R *= 1 - t; r *= 1 - t
        if 6 <= f < 104 and R > 2:
            GE.torus(g, tcx, GY, R, r, 1.2, 0.25 * math.sin(f * 0.05), f * 0.08, f * 0.01, 255, prog=clamp((f - 6) / 22))
            if f >= 28:
                for k in range(10):                                    # energy flowing through the centre
                    v = (f * 0.25 + k * 0.628) % 6.283; u = k * 0.628
                    x = (R + r * math.cos(v)) * math.cos(u); y = r * math.sin(v); z = (R + r * math.cos(v)) * math.sin(u)
                    P = GE.rot3(np.array([[x, y, z]]), 1.2, 0.25 * math.sin(f * 0.05), 0)[0]
                    if P[2] < 0: g2.dot(tcx + P[0], GY + P[1], rb(k / 10 + f * 0.03), 255, 2)
        if 104 <= f < 132:                                             # shockwave rings from the pipe
            for k in range(4):
                age = f - 104 - k * 4
                if 0 <= age < 20: g2.circle(PCX, GY, 20 + age * 26, rb(k / 4 + f * 0.02), 255 * (1 - age / 20), sy=0.35)
        g.render(fr)
        bob = 3 * math.sin(f * 0.3)
        if 20 <= f < 34: place(fr, bayer_mask(tint(spr('G'), WHITE, 0.7 * (1 - (f - 20) / 14)), (f - 20) / 12), tcx, FLOOR - 6)
        elif 34 <= f < 94: place(fr, spr('G'), tcx, FLOOR - 6 + bob)
        elif 94 <= f < 102: t = (f - 94) / 8; place(fr, tint(spr('G', scale=round(lerp(1, 0.2, t), 2)), WHITE, t), lerp(tcx, MOUTH - 10, t), FLOOR - 6, clip_x=MOUTH)
        g2.render(fr)
        if 102 <= f < 128:
            q = math.sin(math.pi * (f - 102) / 26); draw_pipe_scaled(fr, 1 + 0.12 * q, 1 + 0.12 * q, 0, tint(PIPE, WHITE, 0.6 * q))
        else: draw_pipe(fr, 0, pipe_bounce(f - 128))
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 40 Platonic Solids -> Tesseract
def s40():
    out = []; N = 150
    for f in range(N):
        I = trip(f, N, a=4, b=22, tail=24); fr = new(pipe=False)
        fr = hue_region(fr, f * 4, I * 0.3); darken(fr, I)
        gb = Geo(); gf = Geo(); gp = Geo()
        wx = SX
        if 44 <= f < 92: wx = lerp(SX, MOUTH + 60, ease_io((f - 44) / 48))
        elif 92 <= f < 104: wx = lerp(MOUTH + 60, MOUTH - 70, (f - 92) / 12)
        for k, (V, E) in enumerate(GE.SOLIDS):
            st = 6 + k * 4
            if f < st: continue
            a = clamp((f - st) / 6); th = f * 0.09 + k * 6.283 / 5; rad = lerp(220, 118, ease_out(clamp((f - st) / 18)))
            x, y, sz = wx + rad * math.cos(th), GY + 20 * math.sin(th), 20 + 4 * math.sin(th)
            fly = 86 + k * 2.5
            if f >= fly:
                t = clamp((f - fly) / 6); x, y, sz = lerp(x, MOUTH + 6, t), lerp(y, MOUTH_Y, t), sz * (1 - t)
                if t >= 1: continue
            GE.wire(gf if math.sin(th) > 0 else gb, V, E, x, y, sz, f * 0.05 + k, f * 0.07, 0, k / 5 + f * 0.01, 255 * a)
        if 100 <= f < 136:
            q = ease_out((f - 100) / 12) * (1 - ease_in(clamp((f - 124) / 12)))
            GE.tesseract(gp, PCX, GY, 82 * q, (f - 100) * 0.07, f * 0.01, 255 * q)
        gb.render(fr)
        if 24 <= f < 38: place(fr, bayer_mask(tint(spr('R'), WHITE, 0.7 * (1 - (f - 24) / 14)), (f - 24) / 12), SX, FLOOR)
        elif 38 <= f < 44: place(fr, spr('H'), SX, FLOOR)
        elif 44 <= f < 104: im, b = walk_frame(f); place(fr, im, wx, FLOOR - b, clip_x=MOUTH)
        gf.render(fr)
        pa = 1.0
        if 100 <= f < 108: pa = 1 - (f - 100) / 8
        elif 108 <= f < 124: pa = 0
        elif 124 <= f < 136: pa = (f - 124) / 12
        if pa > 0: draw_pipe(fr, 0, pipe_bounce(f - 136), bayer_mask(PIPE, pa) if pa < 1 else None)
        gp.render(fr)
        out.append(finish(fr))
    return out

# ---------------------------------------------------------------- 41 Merkaba Breakthrough
def s41():
    out = []; N = 158
    for f in range(N):
        I = trip(f, N, a=4, b=30, tail=26); fr = new(pipe=False)
        fr = hue_region(fr, f * 6, I * 0.35); darken(fr, I, 140)
        g = Geo(); g2 = Geo()
        spin = f * 0.05 + max(0, f - 36) ** 2 * 0.0025
        mx, ms, wsc = SX, 86.0, 1.0
        if 60 <= f < 76:
            t = ease_in((f - 60) / 16); mx = lerp(SX, MOUTH + 40, t); ms = lerp(86, 56, t); wsc = round(lerp(1, 0.7, t), 2)
            for k in range(7): rect(fr, mx + 60, GY - 42 + k * 12, SX + 60 - mx, 10, rb(k / 7 + f * 0.04), 140 * t)
        if 6 <= f < 76: GE.merkaba(g, mx, GY, ms, spin, f * 0.01, 255, prog=clamp((f - 6) / 22))
        if 36 <= f < 60:
            for k in range(3):
                age = (f - 36 - k * 7) % 21
                g.circle(mx, GY, 30 + age * 6, rb(k / 3 + f * 0.04), 255 * (1 - age / 21) * clamp((f - 36) / 6))
        if 80 <= f < 122:                                              # the mandala that blooms where the pipe was
            q = ease_out((f - 80) / 14) * (1 - ease_in(clamp((f - 108) / 14)))
            for i in range(24):
                ang = i / 24 * 6.283 - f * 0.03
                g2.line((PCX, GY), (PCX + 600 * q * math.cos(ang), GY + 600 * q * math.sin(ang)), rb(i / 24 + f * 0.02), 110 * q, glow=False)
            GE.sri_yantra(g2, PCX, GY, 78 * q, 1, f * 0.02, 255 * q, rot=f * 0.03, petals=True)
            GE.flower_of_life(g2, PCX, GY, 17 * q, 1, f * 0.02 + 0.5, 200 * q, rot=-f * 0.04, outer=False)
            GE.merkaba(g2, PCX, GY, 40 * q, spin, f * 0.02, 255 * q)
        g.render(fr)
        if 18 <= f < 34: place(fr, bayer_mask(tint(spr('E'), WHITE, 0.7 * (1 - (f - 18) / 16)), (f - 18) / 12), SX, FLOOR - 6)
        elif 34 <= f < 60: place(fr, tint(spr('E'), WHITE, 0.25 * clamp((f - 40) / 20)), SX, FLOOR - 6 - 6 * clamp((f - 36) / 10) + 2 * math.sin(f * 0.6))
        elif 60 <= f < 76: place(fr, tint(spr('E', scale=wsc), WHITE, 0.3), mx, 0, cy=GY + 6)
        g.ops = []
        if 6 <= f < 76: GE.merkaba(g, mx, GY, ms, spin + 0.0, f * 0.01, 140, prog=clamp((f - 6) / 22)); g.render(fr)
        s = 0
        if 76 <= f < 86: s = ease_out((f - 76) / 8)
        elif 86 <= f < 112: s = 1
        elif 112 <= f < 136: s = 1 - ease_io((f - 112) / 22)
        if not GE.draw_shards(fr, s, tintf=lambda im: hue_img(im, f * 15)): draw_pipe(fr, 0, pipe_bounce(f - 136))
        g2.render(fr)
        if 76 <= f < 82: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [220, 180, 130, 90, 50, 20][f - 76])
        if 76 <= f < 96: burst(fr, PCX + 40, GY, (f - 76) / 20, n=30, speed=260, cols=[rb(k / 10) for k in range(10)], seed=13, s=6)
        out.append(finish(fr))
    return out

SCENES = {32: ('32_dmt_flower_of_life', s32), 33: ('33_dmt_metatrons_cube', s33), 34: ('34_dmt_the_shaman', s34),
          35: ('35_dmt_spirit_molecule', s35), 36: ('36_dmt_third_eye_sri_yantra', s36), 37: ('37_dmt_hyperspace_tunnel', s37),
          38: ('38_dmt_machine_elves', s38), 39: ('39_dmt_torus_field', s39), 40: ('40_dmt_platonic_tesseract', s40),
          41: ('41_dmt_merkaba_breakthrough', s41)}
if __name__ == '__main__':
    ids = [int(x) for x in sys.argv[1:]] or list(SCENES)
    for i in ids:
        name, fn = SCENES[i]; frames = fn()
        picks = np.linspace(0, len(frames) - 1, 16).astype(int)
        sheet = Image.new('RGB', (890 * 2, 98 * 8))
        for k, p in enumerate(picks):
            sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
        sheet.save(os.path.join(HERE, f'sheet_{i}.png'))
        print(i, name, len(frames), write_gif(frames, name), flush=True)
