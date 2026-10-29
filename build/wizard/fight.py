import sys, math, random, os
import numpy as np
from PIL import Image, ImageOps
from lib import *
import lib
from scenes import bolt
from scenes2 import smoke
import fight_assets as FA
HERE = os.path.dirname(os.path.abspath(__file__))
TOPC = 258                                      # call-out centre line
PURP = (150, 70, 230)

def hit_spark(fr, x, y, age, big=1.0):
    if age < 0 or age > 5: return
    r = (6 + age * 6) * big; a = 255 * (1 - age / 6)
    for ang in range(0, 360, 45):
        L = r * (1.0 if ang % 90 == 0 else 0.6)
        for k in range(0, int(L), 4):
            px(fr, x + k * math.cos(math.radians(ang)) - 2, y + k * math.sin(math.radians(ang)) - 2, 4, (255, 255, 255) if k < L * 0.4 else (255, 220, 60), a)
    px(fr, x - 6, y - 6, 12, (255, 255, 255), a)
def orb(fr, x, y, f, r=14, trail=1):
    for k in range(8):                                             # trail behind (to the right when moving left)
        px(fr, x + trail * (r + 6 + k * 10), y + 6 * math.sin(f * 0.9 + k), 6 - k // 2, (PURP, CYAN, WHITE)[k % 3], 230 - k * 28)
    for rr, col in ((r + 4, PURP), (r, (200, 120, 255)), (r - 5, CYAN), (r - 9, WHITE)):
        if rr > 0: D(fr).ellipse([snap(x - rr), snap(y - rr), snap(x + rr), snap(y + rr)], fill=col + (255,))
    for k in range(4):
        ang = f * 0.6 + k * 1.57; px(fr, x + (r + 6) * math.cos(ang), y + (r + 6) * math.sin(ang), 4, WHITE)
def shield(fr, x, y, a=255):
    for rr, col in ((46, CYAN), (40, LBLUE)):
        pts = [(x + rr * 0.55 * math.cos(math.radians(60 * k)), y + rr * math.sin(math.radians(60 * k))) for k in range(6)]
        D(fr).polygon([(snap(p[0]), snap(p[1])) for p in pts], outline=col + (int(a),))
        D(fr).polygon([(snap(p[0]) + 2, snap(p[1])) for p in pts], outline=col + (int(a * 0.6),))
def flash(img, on):
    return tint(img, WHITE, 0.85) if on else img
def stance(f, x):            # side-on fighting stance facing left
    return spr('C', True, swap=(f // 6) % 2 == 1), x, FLOOR - (2 if (f // 6) % 2 else 0)
def spin_kick(f0, f):
    k = ((f - f0) // 3) % 4; return spr('F', True, rot=[0, 90, 180, 270][k])
def callouts(fr, f, items):
    for (txt, t0, t1, s) in items:
        if t0 <= f < t1:
            pop = ease_back(clamp((f - t0) / 6), 2.2) if f - t0 < 6 else 1.0
            a = 255 * (1 - clamp((f - (t1 - 5)) / 5))
            FA.callout(fr, txt, 890, TOPC, s=s, a=a, pop=max(0.2, pop))
def appear_fx(fr, f, f0, x):
    t = (f - f0) / 10
    if 0 <= t < 1:
        for i in range(14):
            ang = i * 0.45 + f * 0.4; r_ = 80 * (1 - t)
            px(fr, x + r_ * math.cos(ang), FLOOR - 66 + r_ * 0.5 * math.sin(ang), 4, (CYAN, WHITE, PURP)[i % 3], 230)

# ======================================================= Example 1: solo combo run
def ex1():
    out = []; N = 152; X1 = SX - 260; X2 = X1 - 220; X3 = MOUTH + 140
    for f in range(N):
        fr = new(); pdy = 0; wz = None
        if 4 <= f < 9 and f % 2 == 0: bolt(fr, SX, SAFE + 2, SX, FLOOR, f, w=4, col=WHITE, glow=PURP)
        if 6 <= f < 16: wz = (bayer_mask(spr('R'), (f - 6) / 8), SX, FLOOR); burst(fr, SX, FLOOR - 8, (f - 6) / 10, n=14, speed=110, cols=(PURP, CYAN, WHITE), seed=1)
        elif 16 <= f < 24: wz = stance(f, SX)
        elif 24 <= f < 34:
            t = (f - 24) / 10; im, b = run_frame(f); wz = (im, lerp(SX, X1, ease_io(t)), FLOOR - b)
            if f % 2 == 0: dust(fr, lerp(SX, X1, ease_io(t)) + 40, FLOOR - 4, 0.1, seed=f)
        elif 34 <= f < 42:
            wz = (spr('I'), X1 - (8 if 36 <= f < 40 else 0), FLOOR); hit_spark(fr, X1 - 110, FLOOR - 90, f - 37)
        elif 42 <= f < 56:
            t = (f - 42) / 14; x = lerp(X1, X2, ease_io(t)); wz = (spin_kick(42, f), x, FLOOR - 22 * math.sin(math.pi * t))
            for k in range(3): D(fr).arc([snap(x - 60 - k * 10), snap(FLOOR - 110), snap(x + 60 + k * 10), snap(FLOOR - 10)], 200 + f * 40 % 360, 280 + f * 40 % 360, fill=WHITE + (150 - k * 40,), width=4)
            if f in (47, 52): hit_spark(fr, x - 80, FLOOR - 70, 1)
        elif 56 <= f < 60: wz = (spr('F', True, sy=0.9), X2, FLOOR)
        elif 60 <= f < 76:
            wz = (spr('I'), X2, FLOOR)
            if f < 64:
                for k in range(8): ang = k * 0.785 + f; px(fr, X2 - 80 + 20 * math.cos(ang), FLOOR - 96 + 20 * math.sin(ang), 4, (PURP, CYAN)[k % 2])
        elif 76 <= f < 94:
            t = (f - 76) / 18; im, b = run_frame(f); wz = (im, lerp(X2, X3, ease_io(t)), FLOOR - b)
        elif 94 <= f < 106:
            t = (f - 94) / 12; rise = 22 * math.sin(math.pi * min(1, t * 1.4))
            wz = (spr('H', lean=-10 if t < 0.5 else 0), X3, FLOOR - rise)
            if f < 102 and f % 2 == 0: bolt(fr, X3 - 30, FLOOR, X3 - 30, SAFE + 2, f, w=6, col=WHITE, glow=PURP)
            if f == 96: pass
        elif 106 <= f < 112:
            t = (f - 106) / 6; wz = (spr('F', True, rot=30), lerp(X3, MOUTH - 90, ease_in(t)), FLOOR - 2)
        if 64 <= f < 78:                                                # arcane fireball to the pipe
            t = ease_in((f - 64) / 14); ox = lerp(X2 - 90, MOUTH + 30, t)
            if f < 77: orb(fr, ox, FLOOR - 96 + 30 * t, f)
        if 77 <= f < 85: hit_spark(fr, MOUTH + 30, FLOOR - 66, f - 77, 1.4); burst(fr, MOUTH + 30, FLOOR - 66, (f - 77) / 8, n=16, speed=120, cols=(PURP, CYAN, WHITE), seed=3)
        pdy = min(pipe_bounce(f - 77), pipe_bounce(f - 112))
        if wz: place(fr, *wz, clip_x=MOUTH)
        draw_pipe(fr, 0, pdy)
        if 96 <= f < 101: hit_spark(fr, X3 - 40, FLOOR - 150, f - 96, 1.3)
        callouts(fr, f, [('READY?', 14, 30, 6), ('3 HIT COMBO!', 80, 100, 4), ('PERFECT!', 112, 140, 6)])
        out.append(finish(fr))
    return out

# ======================================================= Example 2: vs. goblin brawler
def ex2():
    out = []; N = 206; G0 = SX - 330
    rng = random.Random(4)
    for f in range(N):
        fr = new(pipe=False)
        # ---- arena elements: crowd + two torches (bayer fade in/out so the loop stays clean)
        aa = clamp((f - 6) / 10) * (1 - clamp((f - 186) / 10))
        if aa > 0:
            cr = U(FA.crowd(f, 30, seed=2)); cr = bayer_mask(cr, aa) if aa < 1 else cr
            fr.paste(cr, (420, FLOOR - cr.height - 64), cr)
            for tx in (330, 1300):
                t_ = U(FA.torch(f + tx)); t_ = bayer_mask(t_, aa) if aa < 1 else t_
                fr.paste(t_, (tx, FLOOR - t_.height), t_)
                fl = 18 + 4 * math.sin(f * 0.7 + tx)
                D(fr).ellipse([snap(tx + 14 - fl * 2), snap(FLOOR - 92 - fl), snap(tx + 14 + fl * 2), snap(FLOOR - 92 + fl)], fill=(255, 140, 40, int(28 * aa)))
        wz = None; gb = None; gx = G0; pdy = 0
        # ---- wizard
        appear_fx(fr, f, 4, SX)
        if 4 <= f < 14: wz = (bayer_mask(spr('R'), (f - 4) / 10), SX, FLOOR)
        elif 14 <= f < 60: wz = stance(f, SX)
        elif 60 <= f < 72: wz = (spr('B'), SX, FLOOR)
        elif 72 <= f < 82: wz = (spr('I'), SX - (10 if 74 <= f < 78 else 0), FLOOR)
        elif 82 <= f < 96:
            t = (f - 82) / 14; wz = (spin_kick(82, f), lerp(SX, SX - 90, ease_io(t)), FLOOR - 24 * math.sin(math.pi * t))
        elif 96 <= f < 112: wz = (spr('I'), SX - 90, FLOOR)
        elif 112 <= f < 124: t = (f - 112) / 12; im, b = run_frame(f); wz = (im, lerp(SX - 90, G0 - 100 + 170, ease_io(t)), FLOOR - b)
        elif 124 <= f < 136:
            t = (f - 124) / 12; wz = (spr('H', lean=-10 if t < 0.5 else 0), G0 + 70, FLOOR - 22 * math.sin(math.pi * min(1, t * 1.4)))
            if f < 132 and f % 2 == 0: bolt(fr, G0 + 40, FLOOR, G0 + 40, SAFE + 2, f, w=6, col=WHITE, glow=PURP)
        elif 136 <= f < 160: wz = (spr('H'), G0 + 70, FLOOR - (6 if (f // 4) % 2 else 0))
        elif 160 <= f < 188:
            t = (f - 160) / 28; im, b = run_frame(f); wz = (im, lerp(G0 + 70, MOUTH - 90, ease_in(t) * 0.3 + t * 0.7), FLOOR - b)
        # ---- goblin
        if 8 <= f < 26:                                             # hops out of the pipe
            t = (f - 8) / 18; gx = lerp(MOUTH + 20, G0, ease_out(t)); hop = abs(math.sin(t * math.pi * 3)) * 24
            gb = (FA.goblin('jump' if hop > 4 else 'stance', f), gx, FLOOR - hop)
            if f < 12: pdy = min(pdy, pipe_bounce(f - 8))
        elif 26 <= f < 60: gb = (FA.goblin('stance', f), G0, FLOOR)
        elif 60 <= f < 72:
            t = (f - 60) / 10; gx = lerp(G0, SX - 175, ease_in(clamp(t))); gb = (FA.goblin('punch' if t > 0.6 else 'stance', f), gx, FLOOR)
        elif 72 <= f < 82:
            t = (f - 72) / 10; gx = lerp(SX - 175, SX - 230, ease_out(t)); gb = (FA.goblin('hit' if f < 78 else 'stance', f), gx, FLOOR)
        elif 82 <= f < 96:
            gx = SX - 230
            if f < 86: gb = (FA.goblin('throw', f), gx, FLOOR)
            elif f < 90: gb = (FA.goblin('stance', f), gx, FLOOR)
            else: t = (f - 90) / 6; gx = lerp(SX - 230, SX - 300, ease_out(t)); gb = (FA.goblin('hit', f), gx, FLOOR)
        elif 96 <= f < 108: gx = SX - 300; gb = (FA.goblin('stance', f), gx, FLOOR)
        elif 108 <= f < 124: t = (f - 108) / 8; gx = lerp(SX - 300, G0, ease_out(clamp(t))); gb = (FA.goblin('hit' if f < 116 else 'stance', f), gx, FLOOR)
        elif 124 <= f < 128: gb = (FA.goblin('hit', f), G0, FLOOR)
        elif 128 <= f < 148:                                         # launched across the arena into the pipe
            t = (f - 128) / 18; gx = lerp(G0, MOUTH - 100, ease_in(t) * 0.4 + t * 0.6)
            img = FA.goblin('hit', f).rotate(((f - 128) * 60) % 360, expand=True, resample=Image.NEAREST)
            gb = (img, gx, FLOOR - 30 * math.sin(math.pi * min(1, t)) - 10)
            for k in range(5): px(fr, gx + 50 + k * 26, FLOOR - 40 + ((k * 7 + f) % 9), 4, WHITE, 200 - k * 35)
        # ---- projectiles & effects
        if 84 <= f < 92:                                             # goblin's thrown rock, kicked to dust
            t = (f - 84) / 6; rx = lerp(SX - 200, SX - 120, t)
            if f < 90: D(fr).rectangle([snap(rx), snap(FLOOR - 100 + 20 * t), snap(rx) + 13, snap(FLOOR - 100 + 20 * t) + 11], fill=(120, 110, 100, 255), outline=(10, 14, 42, 255))
            else: burst(fr, rx, FLOOR - 82, (f - 90) / 6, n=12, speed=80, cols=((140, 120, 100), (90, 80, 70)), seed=7, grav=120)
        if 98 <= f < 108:
            t = ease_in((f - 98) / 10); orb(fr, lerp(SX - 180, SX - 270, t), FLOOR - 96 + 20 * t, f)
        if 66 <= f < 74: shield(fr, SX - 66, FLOOR - 70, 255 * (1 - clamp((f - 71) / 3)))
        for (h0, hx, hy, big) in ((70, SX - 70, FLOOR - 76, 1), (75, SX - 120, FLOOR - 90, 1), (92, SX - 150, FLOOR - 70, 1.1),
                                  (108, SX - 270, FLOOR - 80, 1.3), (127, G0 + 30, FLOOR - 110, 1.6)):
            hit_spark(fr, hx, hy, f - h0, big)
        if gb:
            im = U(gb[0]); im = flash(im, f in (73, 75, 91, 109, 111, 125, 127)); place(fr, im, gb[1], gb[2], clip_x=MOUTH)
        if wz: place(fr, *wz, clip_x=MOUTH)
        pdy = min(pdy, pipe_bounce(f - 146), pipe_bounce(f - 188))
        draw_pipe(fr, 0, pdy)
        if 146 <= f < 156: glyph(fr, '*', MOUTH - 10, 232 + (f % 2) * 2, GOLD, s=4)
        callouts(fr, f, [('ROUND 1', 24, 44, 6), ('FIGHT!', 44, 60, 7), ('K.O.', 128, 158, 8)])
        out.append(finish(fr))
    return out

# ======================================================= Example 3: car-smash bonus round
def wheel_img():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); d = __import__('PIL.ImageDraw', fromlist=['Draw']).Draw(im)
    d.ellipse([1, 1, 14, 14], fill=(30, 30, 36, 255)); d.ellipse([5, 5, 10, 10], fill=(170, 175, 185, 255)); return U(FA.outline(im))
def door_img():
    im = Image.new('RGBA', (22, 15), (0, 0, 0, 0)); d = __import__('PIL.ImageDraw', fromlist=['Draw']).Draw(im)
    d.rectangle([0, 0, 21, 14], fill=(80, 190, 175, 255)); d.rectangle([2, 1, 18, 6], fill=(120, 160, 190, 255)); d.rectangle([14, 9, 17, 10], fill=(45, 125, 115, 255))
    return U(FA.outline(im))
def ex3():
    out = []; N = 232; CX = 780; WX = CX + 84 + 76
    hits = [(44, 1, 'jab'), (54, 1, 'jab'), (66, 2, 'kick'), (86, 3, 'orb'), (98, 3, 'jab'), (102, 3, 'jab'), (106, 3, 'jab'), (116, 4, 'upper'), (140, 5, 'slam')]
    W = wheel_img(); DR = door_img()
    for f in range(N):
        fr = new(); dmg = 0
        for (hf, dm, _) in hits:
            if f >= hf: dmg = dm
        last = max([hf for hf, _, _ in hits if hf <= f], default=-99)
        shake = (4 if (f - last) % 2 == 0 else -4) if 0 <= f - last < 5 else 0
        # ---- the car
        ca = clamp((f - 8) / 8) * (1 - clamp((f - 162) / 10))
        if ca > 0:
            cimg = U(FA.car(dmg, seed=dmg)); cimg = bayer_mask(cimg, ca) if ca < 1 else cimg
            place(fr, cimg, CX + shake, FLOOR)
        if 4 <= f < 20: smoke(fr, CX, FLOOR - 36, (f - 4) / 16, seed=1, n=10, spread=70, size=28)
        if 160 <= f < 176: smoke(fr, CX, FLOOR - 20, (f - 160) / 16, seed=2, n=10, spread=80, size=26)
        # ---- flying parts
        if 86 <= f < 150:                                           # front wheel rolls away
            t = (f - 86) / 64; wx_ = CX - 60 - 520 * ease_out(t); wy = FLOOR - 32 - 26 * abs(math.sin(t * 9)) * (1 - t)
            wi = W.rotate(-(f * 40) % 360 // 45 * 45, resample=Image.NEAREST)
            a_ = 1 - clamp((f - 138) / 12); place(fr, bayer_mask(wi, a_) if a_ < 1 else wi, wx_, wy + 32)
        if 116 <= f < 172:                                          # door flies off and lands, then fades with the wreck
            t = clamp((f - 116) / 18); dx = CX + 30 - 260 * ease_out(t); dy = FLOOR - 40 - 30 * math.sin(math.pi * t) + 30 * t
            di = DR.rotate(int(t * 540) // 45 * 45, expand=True, resample=Image.NEAREST) if t < 1 else DR.rotate(90, expand=True, resample=Image.NEAREST)
            a_ = 1 - clamp((f - 162) / 10); place(fr, bayer_mask(di, a_) if a_ < 1 else di, dx, min(FLOOR, dy + 20))
        # ---- wizard
        wz = None
        appear_fx(fr, f, 4, SX)
        if 4 <= f < 14: wz = (bayer_mask(spr('R'), (f - 4) / 10), SX, FLOOR)
        elif 14 <= f < 22: wz = stance(f, SX)
        elif 22 <= f < 38: t = (f - 22) / 16; im, b = run_frame(f); wz = (im, lerp(SX, WX, ease_io(t)), FLOOR - b)
        elif 38 <= f < 60: wz = (spr('I'), WX - (10 if f in (42, 43, 44, 52, 53, 54) else 0), FLOOR) if f < 58 else stance(f, WX)
        elif 60 <= f < 72: t = (f - 60) / 12; wz = (spin_kick(60, f), WX + 10 * math.sin(math.pi * t), FLOOR - 22 * math.sin(math.pi * t))
        elif 72 <= f < 94: wz = (spr('I'), WX, FLOOR) if f >= 76 else (spr('B'), WX, FLOOR)
        elif 94 <= f < 110: wz = (spr('I') if f % 4 < 2 else spr('C', True), WX - (8 if f % 4 < 2 else 0), FLOOR)
        elif 110 <= f < 124:
            t = (f - 110) / 14; wz = (spr('H', lean=-10 if t < 0.5 else 0), WX, FLOOR - 22 * math.sin(math.pi * min(1, t * 1.4)))
            if 112 <= f < 120 and f % 2 == 0: bolt(fr, WX - 40, FLOOR, WX - 40, SAFE + 2, f, w=6, col=WHITE, glow=PURP)
        elif 124 <= f < 140:                                         # leap up and spin-slam the roof
            t = (f - 124) / 16; x = lerp(WX, CX + 10, ease_io(t)); y = FLOOR - 22 * math.sin(math.pi * t) - (60 if dmg < 5 else 0) * math.sin(math.pi * t) * 0.4
            wz = (spin_kick(124, f), x, min(FLOOR, y))
        elif 140 <= f < 146: wz = (spr('F', True, sy=0.88), CX + 10, FLOOR)
        elif 146 <= f < 168: wz = (spr('H'), CX + 120, FLOOR - (6 if (f // 4) % 2 else 0))
        elif 168 <= f < 200:
            t = (f - 168) / 32; im, b = run_frame(f); wz = (im, lerp(CX + 120, MOUTH - 90, ease_in(t) * 0.3 + t * 0.7), FLOOR - b)
        if 78 <= f < 87:
            t = ease_in((f - 78) / 8); orb(fr, lerp(WX - 90, CX + 70, t), FLOOR - 96 + 30 * t, f)
        if wz: place(fr, *wz, clip_x=MOUTH)
        for (hf, dm, kind) in hits:
            age = f - hf
            if 0 <= age < 6:
                hx = CX + 70 if kind != 'slam' else CX + 10; hy = FLOOR - (60 if kind in ('jab', 'orb') else 40 if kind == 'kick' else 90 if kind == 'upper' else 70)
                hit_spark(fr, hx, hy, age, 1.6 if kind == 'slam' else 1.1)
                if age == 0 or age < 4:
                    burst(fr, hx, hy, age / 6, n=10 if kind != 'slam' else 26, speed=120 if kind != 'slam' else 220,
                          cols=((80, 190, 175), (45, 125, 115), (200, 230, 245)), seed=hf, grav=200)
        draw_pipe(fr, 0, pipe_bounce(f - 200))
        callouts(fr, f, [('BONUS STAGE', 6, 30, 5), ('PERFECT!', 144, 168, 7)])
        out.append(finish(fr))
    return out

EX = {1: ('sf_example_1_solo_combo', ex1), 2: ('sf_example_2_vs_goblin', ex2), 3: ('sf_example_3_car_smash_bonus', ex3)}
if __name__ == '__main__':
    for i in [int(x) for x in sys.argv[1:]] or list(EX):
        name, fn = EX[i]; frames = fn()
        picks = np.linspace(0, len(frames) - 1, 16).astype(int)
        sheet = Image.new('RGB', (890 * 2, 98 * 8))
        for k, p in enumerate(picks): sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
        sheet.save(os.path.join(HERE, f'sheet_sf{i}.png'))
        print(i, name, len(frames), write_gif(frames, name, outdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'fighter')), flush=True)
