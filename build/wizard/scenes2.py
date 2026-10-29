import sys, math, random
import numpy as np
from PIL import Image, ImageOps
from lib import *
import props as PR
from scenes import cloud, hat_parts

HAT2, HX, HY = hat_parts()
HAT1 = HAT2.resize((HAT2.width // 2, HAT2.height // 2), Image.NEAREST)
GREEN_P = (60, 210, 80); LGREEN = (150, 250, 130); PURP = (170, 90, 240); SOOT = (60, 40, 40)

def beam(fr, cx, lvl, f, cols=(LBLUE, CYAN, WHITE), top=SAFE + 8, bottom=FLOOR):
    if lvl <= 0: return
    Hh = bottom - top
    for yy in range(top, bottom, 4):
        v = (bottom - yy) / Hh; g = (1 - v) ** 1.4 * lvl * (0.85 + 0.15 * math.sin(yy * 0.12 - f * 0.9))
        for w, c, amax in ((84, cols[0], 70), (52, cols[1], 120), (18, cols[2], 170)):
            ww = int(w * (0.7 + 0.3 * lvl)) // 4 * 4
            rect(fr, cx - ww // 2, yy, ww, 4, c, amax * g)
def smoke(fr, cx, cy, t, seed=0, n=10, spread=60, base=(175, 160, 205), dark=(70, 55, 100), size=30):
    rng = random.Random(seed)
    if t <= 0 or t >= 1: return
    puffs = [(rng.uniform(-spread, spread), rng.uniform(-spread * 0.8, spread * 0.3), rng.uniform(size * 0.6, size)) for _ in range(n)]
    k = ease_out(t * 3) if t < 0.33 else 1 - ease_in((t - 0.33) / 0.67)
    for col, grow in ((dark, 2), (base, 0)):
        for dx, dy, r in puffs:
            rr = r * k + grow
            if rr < 2: continue
            x, y = cx + dx * (0.6 + t * 0.6), cy + dy * 0.7
            D(fr).ellipse([snap(x - rr), snap(y - rr), snap(x + rr), snap(y + rr)], fill=col + (255,))
def hop_arc(t, h): return h * math.sin(math.pi * clamp(t))
def gray_region(fr, top=SAFE, bottom=BOTTOM):
    a = np.array(fr).astype(float); reg = a[top:bottom]
    g = reg @ np.array([0.3, 0.55, 0.15]); reg[:] = np.stack([g * 0.9 + 12, g * 0.88 + 8, g + 24], -1).clip(0, 255)
    return Image.fromarray(a.astype(np.uint8))
def gray_img(img):
    a = np.array(img).astype(float); g = a[..., :3] @ np.array([0.3, 0.55, 0.15])
    a[..., :3] = np.stack([g * 0.9 + 12, g * 0.88 + 8, g + 24], -1).clip(0, 255); return Image.fromarray(a.astype(np.uint8))

# ---------------- 12. Cauldron bubble tunnel ----------------
def s12():
    out = []; N = 112
    for f in range(N):
        fr = new(); CA = U(PR.cauldron(f)); liq = FLOOR - CA.height + (PR.CAULDRON_LIQ_Y + 1) * 2
        caul_a = 0
        if 5 <= f < 66: caul_a = clamp((f - 5) / 9)
        elif 66 <= f < 76: caul_a = 1 - (f - 66) / 10
        wz_before = []; wz_after = []
        if 14 <= f < 30:
            r = ease_out((f - 14) / 16); wz_before.append((spr('E'), SX, FLOOR - 10 + 130 * (1 - r), liq))
        elif 30 <= f < 40:
            t = (f - 30) / 10; cx = lerp(SX, SX - 130, ease_io(t)); b = lerp(FLOOR - 10, FLOOR, t) - hop_arc(t, 10)
            (wz_after if t > 0.35 else wz_before).append((spr('E'), cx, b, None))
        elif 40 <= f < 44: wz_after.append((spr('R', sx=[1.1, 1.05, 1, 1][f - 40], sy=[0.9, 0.95, 1, 1][f - 40]), SX - 130, FLOOR, None))
        elif 44 <= f < 56:
            wz_after.append((spr('D'), SX - 130, FLOOR, None))
        elif 56 <= f < 66:
            t = (f - 56) / 10; cx = lerp(SX - 130, SX, ease_io(t)); b = FLOOR - hop_arc(min(t * 1.6, 1), 10) + (0 if t < 0.6 else (t - 0.6) / 0.4 * 140)
            wz_before.append((spr('F', False, rot=-25), cx, b, liq if t > 0.55 else None))
        for (im, cx, b, cf) in wz_before: place(fr, im, cx, b, clip_floor=cf)
        if caul_a > 0:
            ci = CA if caul_a >= 1 else bayer_mask(CA, caul_a)
            place(fr, ci, SX, FLOOR)
            for i in range(4):                                   # rising green bubbles over the pot
                ph = (f * 2 + i * 13) % 26; px(fr, SX - 24 + i * 16, liq - ph * 2, 4 + (i % 2) * 2, LGREEN, 220 * (1 - ph / 26) * caul_a)
        if 5 <= f < 16: smoke(fr, SX, FLOOR - 50, (f - 5) / 11, seed=1, n=8, spread=50, base=(120, 220, 120), dark=(40, 110, 50), size=24)
        for (im, cx, b, cf) in wz_after: place(fr, im, cx, b, clip_floor=cf)
        if 50 <= f < 56: glyph(fr, '?' if f < 53 else '!', SX - 90, 224, WHITE if f < 53 else GOLD)
        if 62 <= f < 72: burst(fr, SX, liq, (f - 62) / 10, n=14, speed=90, cols=(GREEN_P, LGREEN, WHITE), seed=3, grav=160)
        if 66 <= f < 90:                                         # bubbles travelling under the floor
            head = lerp(SX, MOUTH + 50, (f - 66) / 24)
            for k in range(9):
                bx = head + k * 22; by = FLOOR + 10 + ((k * 5 + f) % 3) * 4; s = [8, 6, 6, 4, 4, 4, 2, 2, 2][k]
                if bx < SX + 20: px(fr, bx, by, s, LGREEN if k % 2 else GREEN_P, 255 - k * 22)
            if f % 3 == 0: burst(fr, head + 10, FLOOR - 2, 0.4, n=4, speed=40, cols=(LGREEN,), seed=f)
        if 88 <= f < 96:
            r = ease_out((f - 88) / 6); place(fr, spr('E'), MOUTH + 60, FLOOR + 130 * (1 - r), clip_floor=FLOOR)
            for i in range(10): px(fr, MOUTH + 30 + (i * 7) % 60, FLOOR - ((f - 88) * 14 + i * 9) % 90, 6, (GREEN_P, LGREEN, WHITE)[i % 3], 230)
        elif 96 <= f < 102:
            t = (f - 96) / 6; place(fr, spr('F', True, rot=30), lerp(MOUTH + 60, MOUTH - 90, t), FLOOR - 4, clip_x=MOUTH)
        draw_pipe(fr, 0, pipe_bounce(f - 101))
        if 101 <= f < 111: burst(fr, MOUTH + 6, MOUTH_Y, (f - 101) / 10, n=10, speed=70, cols=(GREEN_P, LGREEN, WHITE), seed=4)
        out.append(finish(fr))
    return out

# ---------------- 13. Spellbook ----------------
def s13():
    out = []; N = 122; BX = SX + 6
    for f in range(N):
        fr = new(); bk = None; bcy = FLOOR - 14; clipx = None
        if 5 <= f < 14: bk = bayer_mask(U(PR.book(0)), (f - 5) / 9)
        elif 14 <= f < 20: bk = U(PR.book(ease_out((f - 14) / 6)))
        elif 20 <= f < 70: bk = U(PR.book(1, 0, ((f - 20) % 8) / 8 if f < 34 else None))
        elif 70 <= f < 76: bk = U(PR.book(1 - (f - 70) / 6))
        elif 76 <= f < 106:
            t = (f - 76) / 26; bx_ = lerp(BX, MOUTH - 80, ease_in(t) * 0.4 + t * 0.6); bcy = FLOOR - 40 - 30 * math.sin(math.pi * clamp(t * 1.1)) + 6 * math.sin(f * 0.9)
            bk = U(PR.book(0.7, math.sin(f * 1.3))); clipx = MOUTH
            for k in range(6): px(fr, bx_ + 40 + k * 16 + (f * 5 % 7), bcy + ((k * 7 + f) % 9) - 4, 4, (GOLD, WHITE)[k % 2], 220 - k * 35)
        if 5 <= f < 14:
            for i in range(14):
                a_ = i * 0.45 + f * 0.3; r_ = 90 * (1 - (f - 5) / 9); px(fr, BX + r_ * math.cos(a_), bcy - 20 + r_ * 0.4 * math.sin(a_), 4, (GOLD, WHITE)[i % 2], 230)
        if 20 <= f < 44: beam(fr, BX, (1 if f < 38 else 1 - (f - 38) / 6) * clamp((f - 20) / 6), f, cols=((255, 220, 120), GOLD, WHITE))
        if 26 <= f < 42:
            r = ease_out((f - 26) / 14); place(fr, spr('E'), BX, FLOOR - 14 + 134 * (1 - r), clip_floor=FLOOR - 14)
        if bk is not None:
            if 76 <= f < 106: place(fr, bk, bx_, 0, cy=bcy, clip_x=clipx)
            else: place(fr, bk, BX, 0, cy=bcy)
        if 42 <= f < 52:
            t = (f - 42) / 10; place(fr, spr('E'), lerp(BX, SX - 120, ease_io(t)), lerp(FLOOR - 14, FLOOR, t) - hop_arc(t, 8))
        elif 52 <= f < 56: place(fr, spr('R'), SX - 120, FLOOR)
        elif 56 <= f < 60: place(fr, spr('B', True), SX - 120, FLOOR)
        elif 60 <= f < 72:
            t = (f - 60) / 12; sc = lerp(1, 0.3, ease_in(t))
            im = bayer_mask(spr('B', True, scale=round(sc, 2)), 1 - ease_in(t) * 0.9)
            place(fr, im, lerp(SX - 120, BX, ease_in(t)), lerp(FLOOR, FLOOR - 20, t))
            for k in range(8): px(fr, lerp(SX - 120, BX, ((f * 2 + k * 5) % 12) / 12), FLOOR - 60 + (k % 3) * 12, 4, (GOLD, WHITE)[k % 2], 220)
        draw_pipe(fr, 0, pipe_bounce(f - 104))
        if 104 <= f < 114: burst(fr, MOUTH + 6, MOUTH_Y, (f - 104) / 10, n=10, speed=70, cols=(GOLD, (240, 225, 190), WHITE), seed=5)
        out.append(finish(fr))
    return out

# ---------------- 14. Invisibility potion: footprints + floating hat ----------------
def s14():
    out = []; N = 138; R = spr('R'); W, Hh = R.size; left0 = snap(SX - W / 2); top0 = FLOOR - Hh
    prints = []
    for f in range(N):
        fr = new()
        for (x, y, t0) in prints:                         # footprints fade out
            age = f - t0
            if 0 <= age < 34: rect(fr, x, y, 8, 4, (90, 80, 140), 230 * (1 - age / 34))
        if 5 <= f < 15:
            t = (f - 5) / 10; place(fr, U(PR.potion(PURP, tilt=(f * 90) % 360)), SX, lerp(SAFE + 36, FLOOR, ease_in(t)))
        if 15 <= f < 30:
            burst(fr, SX, FLOOR - 10, (f - 15) / 15, n=16, speed=120, cols=(WHITE, LBLUE, (200, 220, 240)), seed=6, grav=200)
        if 17 <= f < 48: place(fr, R if f >= 27 else bayer_mask(R, (f - 17) / 10), SX, FLOOR)
        if 15 <= f < 32: smoke(fr, SX, FLOOR - 40, (f - 15) / 17, seed=2, n=9, spread=55, base=(200, 150, 240), dark=(100, 60, 150), size=26)
        hand = (SX + 36, FLOOR - 36); mouth = (SX + 6, FLOOR - 82)
        if 32 <= f < 50:
            if f < 36: pos, tilt = hand, 0; burst(fr, hand[0], hand[1] - 10, (f - 32) / 4, n=6, speed=50, seed=7)
            elif f < 42: t = ease_io((f - 36) / 6); pos = (lerp(hand[0], mouth[0] + 18, t), lerp(hand[1], mouth[1] + 18, t)); tilt = int(90 * t) // 15 * 15
            else: pos, tilt = (mouth[0] + 18, mouth[1] + 18), 105
            place(fr, U(PR.potion((80, 140, 255), tilt=tilt)), pos[0], 0, cy=pos[1])
            if 42 <= f < 50: glyph(fr, '*', SX + 40, 226 + (f % 2) * 2, LBLUE, s=2)
        if 48 <= f < 60: place(fr, bayer_mask(R, 1 - (f - 48) / 12), SX, FLOOR)
        if 48 <= f < 98:                                   # the hat that stays visible
            if f < 60: hx, hy = left0 + HX, top0 + HY
            else:
                t = (f - 60) / 38; cx = lerp(SX, MOUTH - 70, t); hx = snap(cx - W / 2) + HX; hy = top0 + HY - (4 if (f // 3) % 2 else 0)
                if f % 4 == 0 and cx > MOUTH: prints.append((snap(cx - 10 + (8 if (f // 4) % 2 else -8)), FLOOR - 4 + (4 if (f // 4) % 2 else 0), f))
            l = max(0, MOUTH - hx) if f >= 60 else 0
            if l < HAT2.width:
                h = HAT2.crop((l, 0, HAT2.width, HAT2.height)); fr.paste(h, (hx + l, hy), h)
            if 48 <= f < 60: burst(fr, SX, FLOOR - 70, (f - 48) / 12, n=12, speed=80, cols=(LBLUE, WHITE), seed=8)
        draw_pipe(fr, 0, pipe_bounce(f - 96))
        if 98 <= f < 110: glyph(fr, '?', MOUTH + 16, 252 - (f - 98) * 2, WHITE, s=2, a=255 - (f - 98) * 18)
        out.append(finish(fr))
    return out

# ---------------- 15. Owl airlift ----------------
def s15():
    out = []; N = 120
    for f in range(N):
        fr = new(); owl = None; wz = None
        fl = (f // 2) % 3
        if 5 <= f < 20:
            t = (f - 5) / 15; ox = lerp(1700, SX + 10, ease_out(t)); oy = 252 + 6 * math.sin(f * 0.8); owl = (ox, oy)
            for k in range(3): px(fr, ox - 6 + k * 6, oy + 30, 6, (CYAN, WHITE, CYAN)[k], 255)
        elif 20 <= f < 48:
            ox = lerp(SX + 10, SX - 110, ease_io((f - 20) / 10)) if f < 30 else SX - 110; oy = 252 + 6 * math.sin(f * 0.8); owl = (ox, oy)
            if f < 26: t = (f - 20) / 6; px(fr, SX + 4, lerp(286, FLOOR - 8, ease_in(t)), 8, CYAN, 255)
        if 26 <= f < 36: burst(fr, SX, FLOOR - 10, (f - 26) / 10, n=16, speed=110, cols=(CYAN, WHITE, LBLUE), seed=9)
        if 26 <= f < 34: wz = (dissolve(spr('R'), (f - 26) / 8, seed=f), SX, FLOOR)
        elif 34 <= f < 44: wz = (spr('R'), SX, FLOOR)
        elif 44 <= f < 50:
            wz = (spr('H'), SX, FLOOR); ox = lerp(SX - 110, SX, ease_io((f - 44) / 6)); owl = (ox, 246)
        elif 50 <= f < 88:
            t = (f - 50) / 38; cx = lerp(SX, MOUTH + 70, ease_io(t)); lift = 8 + 3 * math.sin(f * 0.6)
            wz = (spr('E', lean=8), cx, FLOOR - lift); owl = (cx - 10, 244 - lift + 6); fl = f % 3
            for i in range(4): rect(fr, cx + 70 + (i * 29 + f * 11) % 90, 280 + i * 18, 44, 2, WHITE, 110)
        elif 88 <= f < 96:
            t = (f - 88) / 8; wz = (spr('F', True, rot=30), lerp(MOUTH + 70, MOUTH - 90, ease_in(t)), FLOOR - 2)
            owl = (lerp(MOUTH + 60, MOUTH + 130, ease_out(t)), 250)
        elif 96 <= f < 106:
            t = (f - 96) / 10; owl = (lerp(MOUTH + 130, MOUTH - 60, ease_in(t)), lerp(250, MOUTH_Y, t))
        if wz: place(fr, *wz, clip_x=MOUTH)
        if owl:
            place(fr, U(PR.owl(fl)), owl[0], 0, cy=owl[1], clip_x=MOUTH)
        dy = min(pipe_bounce(f - 94), pipe_bounce(f - 104))
        draw_pipe(fr, 0, dy)
        if 104 <= f < 112: burst(fr, MOUTH + 6, MOUTH_Y, (f - 104) / 8, n=8, speed=60, cols=((140, 95, 55), (225, 195, 145)), seed=10)
        out.append(finish(fr))
    return out

# ---------------- 16. Crystal ball roll ----------------
def s16():
    out = []; N = 112; tiny1 = P1['R'].resize((P1['R'].width * 3 // 10, P1['R'].height * 3 // 10), Image.NEAREST)
    for f in range(N):
        fr = new(); ball_x = SX; ball_b = FLOOR; stand = True; show_ball = 5 <= f < 100; tiny_rot = 0; tiny_a = 0
        if 5 <= f < 16: ba = (f - 5) / 11
        else: ba = 1
        if 14 <= f < 34: tiny_a = clamp((f - 14) / 8)
        if 60 <= f < 100: tiny_a = clamp((f - 60) / 4)
        if 64 <= f < 70: stand = False; ball_b = FLOOR - 16 + 16 * ease_in((f - 64) / 6)
        elif f >= 70:
            stand = False; t = (f - 70) / 28; dist = (SX - (MOUTH - 70)) * (ease_in(t) * 0.45 + t * 0.55); ball_x = SX - dist
            tiny_rot = int(dist / 27 * 57.3) // 20 * 20
            for i in range(4): rect(fr, ball_x + 50 + (i * 31 + f * 13) % 80, 318 + i * 14, 40, 2, WHITE, 110)
        if 64 <= f < 72: smoke(fr, SX, FLOOR - 8, (f - 64) / 8, seed=11, n=5, spread=30, size=14)
        if show_ball:
            bi = U(PR.crystal_ball(f, stand)); bi = bi if ba >= 1 else bayer_mask(bi, ba)
            x0 = snap(ball_x - bi.width / 2); y0 = ball_b - bi.height
            place(fr, bi, ball_x, ball_b, clip_x=MOUTH)
            if tiny_a > 0:
                ti = U(tiny1.rotate(tiny_rot, expand=True, resample=Image.NEAREST)) if tiny_rot else U(tiny1)
                ti = tint(ti, (190, 160, 250), 0.25, 0.85 * tiny_a)
                cxb = x0 + PR.BALL_C[0] * 2; cyb = y0 + PR.BALL_C[1] * 2 + 2 * math.sin(f * 0.4)
                place(fr, ti, cxb, 0, cy=cyb, clip_x=MOUTH)
        if 32 <= f < 38: burst(fr, SX, FLOOR - 44, (f - 32) / 6, n=14, speed=120, cols=(WHITE, (190, 160, 250)), seed=12)
        WX = SX - 110
        if 34 <= f < 42: place(fr, dissolve(spr('R'), (f - 34) / 8, seed=f), WX, FLOOR)
        elif 42 <= f < 54:
            place(fr, spr('D'), WX, FLOOR); glyph(fr, '?' if f < 50 else '!', WX + 40, 224, WHITE if f < 50 else GOLD)
        elif 54 <= f < 64:
            t = (f - 54) / 10; place(fr, dissolve(spr('B', True), 1 - t, seed=f), WX, FLOOR)
            for k in range(10):
                tt = ((f * 3 + k * 7) % 20) / 20; px(fr, lerp(WX, SX, tt), lerp(FLOOR - 70, FLOOR - 44, tt) + 10 * math.sin(k + f * 0.5), 4, (WHITE, (190, 160, 250))[k % 2], 230)
        draw_pipe(fr, 0, pipe_bounce(f - 98))
        if 98 <= f < 108: burst(fr, MOUTH + 6, MOUTH_Y, (f - 98) / 10, n=10, speed=70, cols=((190, 160, 250), WHITE), seed=13)
        out.append(finish(fr))
    return out

# ---------------- 17. Sword in the stone ----------------
def s17():
    out = []; N = 120; STX = SX + 30; ST = U(PR.stone()); SW = U(PR.sword()); WX = SX - 70
    for f in range(N):
        fr = new(); st_b = FLOOR
        if f < 5: st_show = False
        else: st_show = True
        if 5 <= f < 18: st_b = FLOOR + ST.height * (1 - ease_out((f - 5) / 13)); dust(fr, STX - 40, FLOOR - 4, (f - 5) / 30, seed=1, dirx=-1); dust(fr, STX + 40, FLOOR - 4, (f - 5) / 30, seed=2)
        if f >= 92: st_b = FLOOR + ST.height * ease_in((f - 92) / 14)
        sw_lift = 0; sw_state = 'stone'
        if 46 <= f < 58: sw_lift = 44 * ease_out((f - 48) / 10) if f >= 48 else 0
        if 58 <= f < 64: sw_lift = 44; sw_state = 'hover'
        if 64 <= f < 90: sw_state = 'fly'
        if 90 <= f < 98: sw_state = 'return'
        if 98 <= f: sw_state = 'stone'
        if 18 <= f < 46: beam(fr, WX, (1 if f < 40 else 1 - (f - 40) / 6) * clamp((f - 18) / 6), f, cols=((255, 220, 120), GOLD, WHITE))
        # sword
        if st_show and sw_state in ('stone', 'hover'):
            sb = st_b - ST.height + 30 - sw_lift
            if f >= 92: sb += (SW.height + 10) * ease_in((f - 92) / 14)
            place(fr, SW, STX, sb, clip_floor=min(st_b, FLOOR) if sw_lift < 30 else None)
            if 18 <= f < 64 and f % 2 == 0:
                for k in range(4): px(fr, STX - 16 + (k * 11 + f * 3) % 32, sb - 70 + (k * 17 + f * 5) % 60, 4, (GOLD, WHITE)[k % 2], 230)
        if st_show and st_b < FLOOR + ST.height: place(fr, ST, STX, st_b, clip_floor=FLOOR)
        if sw_state == 'fly':
            t = (f - 64) / 26; sx_ = lerp(STX, MOUTH - 60, ease_in(t) * 0.5 + t * 0.5); sy_ = FLOOR - 62
            place(fr, U(PR.sword().rotate(90, expand=True, resample=Image.NEAREST)), sx_, 0, cy=sy_, clip_x=MOUTH)
            for k in range(5):                                   # golden slash crescents behind the sword
                cx_ = sx_ + 50 + k * 34; r_ = 26 - k * 3
                if cx_ < STX: D(fr).arc([snap(cx_ - r_), snap(sy_ - r_ * 1.6), snap(cx_ + r_), snap(sy_ + r_ * 1.6)], 120, 240, fill=GOLD + (230 - k * 40,), width=4)
            # golden comet = the wizard riding the slash
            if f >= 66:
                cx2 = sx_ + 70
                if cx2 > MOUTH:
                    D(fr).ellipse([snap(cx2 - 14), snap(sy_ - 14), snap(cx2 + 14), snap(sy_ + 14)], fill=GOLD + (255,))
                    D(fr).ellipse([snap(cx2 - 8), snap(sy_ - 8), snap(cx2 + 8), snap(sy_ + 8)], fill=WHITE + (255,))
                for k in range(10): px(fr, cx2 + 14 + k * 12, sy_ - 6 + (k * 5 + f) % 13, 6 - k // 3, (GOLD, WHITE, ORANGE)[k % 3], 255 - k * 22)
        if sw_state == 'return':
            t = (f - 90) / 8; place(fr, SW, STX, lerp(SAFE + 80, st_b - ST.height + 30, ease_in(t)))
        # wizard
        if 26 <= f < 40: place(fr, bayer_mask(spr('B'), (f - 26) / 14), WX, FLOOR)
        elif 40 <= f < 46: place(fr, spr('B'), WX, FLOOR)
        elif 46 <= f < 58: place(fr, spr('R'), WX + (2 if f % 2 and f < 54 else 0), FLOOR)
        elif 58 <= f < 64: place(fr, spr('I'), WX - 10, FLOOR)
        elif 64 <= f < 70: place(fr, dissolve(spr('I'), 1 - (f - 64) / 6, seed=f), WX - 10, FLOOR); burst(fr, WX, FLOOR - 60, (f - 64) / 6, n=12, speed=80, cols=(GOLD, WHITE), seed=14)
        if 56 <= f < 60: burst(fr, STX, FLOOR - 100, (f - 56) / 4, n=12, speed=100, cols=(GOLD, WHITE), seed=15)
        draw_pipe(fr, 0, pipe_bounce(f - 88))
        if 88 <= f < 100: burst(fr, MOUTH + 6, MOUTH_Y, (f - 88) / 12, n=12, speed=80, cols=(GOLD, WHITE, ORANGE), seed=16)
        out.append(finish(fr))
    return out

# ---------------- 18. Rune circle + frog polymorph ----------------
RUNES = [["101", "010", "101"], ["111", "010", "010"], ["010", "111", "010"], ["110", "011", "110"], ["101", "111", "101"], ["011", "110", "011"], ["111", "101", "111"], ["100", "111", "001"]]
def rune_circle(fr, cx, cy, prog, a, f, col=(80, 255, 140)):
    n = 60
    for i in range(int(n * prog)):
        ang = i / n * 6.283 - 1.57
        px(fr, cx + 74 * math.cos(ang) - 2, cy + 15 * math.sin(ang) - 2, 4, col, a)
        if i % 2 == 0: px(fr, cx + 52 * math.cos(ang) - 1, cy + 10 * math.sin(ang) - 1, 2, WHITE, a * 0.8)
    for k in range(8):
        if k / 8 > prog: break
        ang = k / 8 * 6.283 - 1.57 + f * 0.03; rx, ry = cx + 63 * math.cos(ang), cy + 12.5 * math.sin(ang)
        for j, row in enumerate(RUNES[k]):
            for i, v in enumerate(row):
                if v == '1': px(fr, rx - 3 + i * 2, ry - 3 + j * 2, 2, GOLD, a)
def s18():
    out = []; N = 116; FR0 = U(PR.frog(False, HAT1)); FR1 = U(PR.frog(True, HAT1))
    hops = [SX - i * 240 for i in range(6)]
    for f in range(N):
        fr = new()
        ra = 255 if f < 34 else 255 * (1 - clamp((f - 34) / 10))
        if 5 <= f < 44: rune_circle(fr, SX, FLOOR - 4, clamp((f - 5) / 11), ra, f)
        if 14 <= f < 40: beam(fr, SX, (1 if f < 32 else 1 - (f - 32) / 8) * clamp((f - 14) / 6), f, cols=((120, 255, 160), (80, 255, 140), WHITE))
        if 16 <= f < 34: r = ease_out((f - 16) / 16); place(fr, spr('E'), SX, FLOOR + 134 * (1 - r), clip_floor=FLOOR)
        elif 34 <= f < 44: place(fr, spr('R'), SX, FLOOR)
        elif 44 <= f < 58:
            place(fr, spr('B'), SX, FLOOR)
            for k in range(10):
                ang = k * 0.628 + f * 0.5; px(fr, SX + 70 * math.cos(ang), FLOOR - 66 + 50 * math.sin(ang) * 0.9, 4, ((80, 255, 140), WHITE)[k % 2], 230)
        if 58 <= f < 72: smoke(fr, SX, FLOOR - 40, (f - 58) / 14, seed=17, n=9, spread=55, base=(140, 230, 150), dark=(40, 110, 60), size=26)
        if 64 <= f < 76:
            place(fr, FR0, SX, FLOOR)
            if f >= 68: glyph(fr, '!', SX + 20, 300, GOLD, s=2)
        elif 76 <= f < 106:
            k = f - 76; i = k // 6; t = (k % 6) / 6
            if i < 5:
                cx = lerp(hops[i], hops[i + 1], t); h = hop_arc(t, 54)
                place(fr, FR1 if 0.1 < t < 0.9 else FR0, cx, FLOOR - h)
            else: pass
            if i == 4 or (i < 5 and hops[i + 1] < MOUTH + 60):
                pass
        if 100 <= f < 106:
            t = (f - 100) / 6; place(fr, FR1, lerp(hops[4] if hops[4] > MOUTH else MOUTH + 60, MOUTH - 70, t), FLOOR - 4 - hop_arc(t, 20), clip_x=MOUTH)
        draw_pipe(fr, 0, pipe_bounce(f - 105))
        if 105 <= f < 114: burst(fr, MOUTH + 6, MOUTH_Y, (f - 105) / 9, n=8, speed=60, cols=((80, 255, 140), WHITE), seed=18)
        out.append(finish(fr))
    return out

# ---------------- 19. Ice block + belly slide ----------------
def s19():
    out = []; N = 114; BW = 116; BH = 150
    rng = random.Random(19); cracks = [[(SX + rng.randint(-40, 40), FLOOR - rng.randint(30, 130))] for _ in range(5)]
    for c in cracks:
        for _ in range(5): x, y = c[-1]; c.append((x + rng.randint(-12, 12), y + rng.randint(-14, 14)))
    path_l = MOUTH
    for f in range(N):
        fr = new()
        # ice path
        pa = 0
        if 48 <= f < 92: pa = 1
        elif 92 <= f < 106: pa = 1 - (f - 92) / 14
        if pa > 0:
            reach = SX - 60 - (SX - 60 - path_l) * ease_out((f - 48) / 14) if f < 62 else path_l
            for x in range(snap(reach), snap(SX - 60), 8):
                if ((x // 8) + (f // 2)) % 1 == 0:
                    rect(fr, x, FLOOR - 2, 8, 10, (170, 220, 255), 170 * pa); rect(fr, x, FLOOR - 2, 8, 2, WHITE, 200 * pa)
                if (x // 8) % 7 == (f // 3) % 7: px(fr, x + 2, FLOOR, 2, WHITE, 255 * pa)
        if 5 <= f < 34:
            for i in range(14):
                ang = i * 0.45 + f * 0.4; r_ = 80 * max(0, 1 - (f - 5) / 12)
                if r_ > 0: px(fr, SX + r_ * math.cos(ang), FLOOR - 70 + r_ * 0.6 * math.sin(ang), 4, (WHITE, LBLUE)[i % 2], 230)
            h = BH * ease_out((f - 8) / 14) if f >= 8 else 0
            if f >= 12: place(fr, tint(spr('R'), (150, 210, 255), 0.45), SX, FLOOR)
            if h > 2:
                rect(fr, SX - BW // 2, FLOOR - h, BW, h, (170, 220, 255), 120)
                rect(fr, SX - BW // 2, FLOOR - h, BW, 4, WHITE, 220); rect(fr, SX - BW // 2, FLOOR - h, 4, h, WHITE, 160); rect(fr, SX + BW // 2 - 4, FLOOR - h, 4, h, (120, 180, 230), 200)
                for k in range(3): D(fr).line([(SX - 40 + k * 18, FLOOR - h + 14), (SX - 54 + k * 18, FLOOR - h + 40)], fill=WHITE + (180,), width=2)
            if f >= 22:
                for c in cracks:
                    n = min(len(c), 1 + (f - 22) // 2); D(fr).line(c[:n] if n > 1 else c[:2], fill=WHITE + (255,), width=2)
        if 34 <= f < 50:
            burst(fr, SX, FLOOR - 70, (f - 34) / 16, n=26, speed=150, cols=((170, 220, 255), WHITE, LBLUE), seed=20, grav=220, s=6)
            amt = 0.45 * (1 - (f - 34) / 16); place(fr, tint(spr('H'), (150, 210, 255), amt), SX + (2 if f % 2 else -2), FLOOR)
        elif 50 <= f < 62: place(fr, spr('B', True), SX, FLOOR)
        elif 62 <= f < 66: place(fr, spr('F', True, sy=0.88), SX - 20, FLOOR)
        elif 66 <= f < 90:
            t = (f - 66) / 24; cx = lerp(SX - 40, MOUTH - 130, ease_in(t) * 0.3 + t * 0.7)
            place(fr, spr('C', True, rot=80), cx, FLOOR + 2, clip_x=MOUTH)
            for k in range(6): px(fr, cx + 60 + k * 14, FLOOR - 6 - (k * 5 + f) % 12, 4, (WHITE, LBLUE)[k % 2], 220 - k * 30)
        pimg = PIPE
        if 88 <= f < 104: pimg = tint(PIPE, (200, 235, 255), 0.5 * (1 - (f - 88) / 16))
        draw_pipe(fr, 0, pipe_bounce(f - 88), pimg)
        out.append(finish(fr))
    return out

# ---------------- 20. Fireball ----------------
def s20():
    out = []; N = 136; scorch = []
    for f in range(N):
        fr = new()
        for (x, t0) in scorch:
            age = f - t0
            if 0 <= age < 36: rect(fr, x, FLOOR - 2, 10, 4, (60, 25, 20), 220 * (1 - age / 36))
        if 5 <= f < 18:
            t = ease_in((f - 5) / 13); x = lerp(1700, SX, t); y = lerp(250, FLOOR - 26, t)
            place(fr, U(PR.fireball(f)), x, 0, cy=y)
            for k in range(10): px(fr, x + 10 + k * 12, y - k * 3 + (k * 7 + f) % 7 - 3, 6 - k // 3, (GOLD, ORANGE, RED)[k % 3], 255 - k * 22)
        if 18 <= f < 26: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (255, 200, 120), 50 * (1 - (f - 18) / 8)); burst(fr, SX, FLOOR - 30, (f - 18) / 8, n=20, speed=150, cols=(GOLD, ORANGE, RED, WHITE), seed=21)
        if 20 <= f < 50:
            amt = 0.4 * (1 - clamp((f - 30) / 20)); place(fr, tint(spr('R'), SOOT, amt), SX, FLOOR)
            for k in range(4):                                     # smoke wisps off the hat
                ph = (f * 2 + k * 9) % 24; px(fr, SX + 8 + k * 4 + 3 * math.sin(ph * 0.5), FLOOR - 136 + 18 - ph, 4, (150, 140, 160), 200 * (1 - ph / 24))
        if 18 <= f < 40: smoke(fr, SX, FLOOR - 30, (f - 18) / 22, seed=22, n=8, spread=60, base=(110, 95, 100), dark=(50, 40, 45), size=26)
        if 50 <= f < 58:
            place(fr, spr('B'), SX, FLOOR); glyph(fr, '!', SX + 50, 224, GOLD)
        if 52 <= f < 64:
            for k in range(10): ang = k * 0.628 + f * 0.6; px(fr, SX + 66 * math.cos(ang), FLOOR - 66 + 56 * math.sin(ang), 6, (GOLD, ORANGE, RED)[k % 3], 240)
        if 58 <= f < 64:
            place(fr, dissolve(spr('B'), 1 - (f - 58) / 6, seed=f), SX, FLOOR)
            place(fr, U(PR.fireball(f, r=int(4 + (f - 58) * 1.5))), SX, 0, cy=FLOOR - 50)
        if 64 <= f < 84:
            t = (f - 64) / 20; x = lerp(SX, MOUTH - 40, ease_in(t) * 0.3 + t * 0.7)
            if f % 2 == 0 and x > MOUTH: scorch.append((snap(x), f))
            for k in range(14): px(fr, x + 20 + k * 13, FLOOR - 50 + (k * 7 + f * 3) % 15 - 7, 8 - k // 2, (WHITE, GOLD, ORANGE, RED)[min(3, k // 3)], 255 - k * 16)
            place(fr, U(PR.fireball(f, r=12)), x, 0, cy=FLOOR - 50, clip_x=MOUTH)
        pimg = PIPE
        if 82 <= f < 106: pimg = tint(PIPE, (255, 110, 40), 0.65 * (1 - clamp((f - 88) / 18)) if f >= 88 else 0.65)
        draw_pipe(fr, 0, pipe_bounce(f - 82), pimg)
        if 84 <= f < 108:
            for k in range(4):
                ph = (f * 3 + k * 7) % 28; px(fr, MOUTH + 6 + ph * 2, MOUTH_Y - 10 - ph * 1.5 + k * 6, 6, (200, 195, 215), 200 * (1 - ph / 28) * (1 - (f - 84) / 24))
        out.append(finish(fr))
    return out

# ---------------- 21. Hourglass time stop ----------------
def s21():
    out = []; N = 116; steps = [SX - i * 236 for i in range(6)]
    for f in range(N):
        fr = new(); frozen = 44 <= f < 96
        hg = None
        if 5 <= f < 30:
            sand = clamp((f - 5) / 13) if f < 18 else 1
            im = U(PR.hourglass(sand))
            if 18 <= f < 26: im = im.rotate(-((f - 18) // 2 + 1) * 45 if f < 26 else 180, expand=True, resample=Image.NEAREST)
            if f >= 26: im = U(PR.hourglass(0))
            if f < 12: im = bayer_mask(im, (f - 5) / 7)
            sc_y = FLOOR - 50
            place(fr, im, SX, 0, cy=sc_y)
        if 26 <= f < 38:
            im = scan_glitch(spr('R'), f, 10) if f < 34 else spr('R'); place(fr, bayer_mask(im, (f - 26) / 8), SX, FLOOR)
            for k in range(6): rect(fr, SX - 60, 230 + ((k * 23 + f * 9) % 140), 120, 2, WHITE, 140)
        elif 38 <= f < 46: place(fr, spr('B'), SX, FLOOR)
        if 40 <= f < 54:                                       # clock ring expanding
            r = (f - 40) * 60; a = 255 * (1 - (f - 40) / 14)
            for i in range(12):
                ang = i / 12 * 6.283; px(fr, SX + r * math.cos(ang), FLOOR - 70 + r * 0.35 * math.sin(ang), 6 if i % 3 == 0 else 4, WHITE, a)
        ghosts = []
        if frozen and f >= 46:
            k = (f - 46) // 7; ph = (f - 46) % 7
            for j in range(min(k, 6)): ghosts.append(steps[j])
            cur = steps[min(k, 5)] if k < 6 else None
        if frozen: fr = gray_region(fr)
        for gx in ghosts: place(fr, tint(gray_img(spr('R')), (0, 0, 0), 0, 0.55), gx, FLOOR)
        if frozen and f >= 46 and k < 6:
            place(fr, spr('R') if ph > 1 else bayer_mask(spr('R'), 0.5 + ph * 0.25), cur, FLOOR)
            if ph < 2: burst(fr, cur, FLOOR - 66, 0.3 + ph * 0.2, n=8, speed=70, cols=(WHITE, GOLD), seed=k)
        if frozen and 88 <= f < 96:
            t = (f - 88) / 8; im, b = walk_frame(f); place(fr, im, lerp(steps[5], MOUTH - 70, t), FLOOR - b, clip_x=MOUTH)
        if 96 <= f < 106:                                       # time resumes
            r = (f - 96) * 120
            for i in range(24):
                ang = i / 24 * 6.283; px(fr, MOUTH + r * math.cos(ang), MOUTH_Y + r * 0.3 * math.sin(ang), 4, GOLD, 255 * (1 - (f - 96) / 10))
            for j, gx in enumerate(steps[:6]): burst(fr, gx, FLOOR - 66, (f - 96) / 10, n=6, speed=60, cols=(WHITE, (180, 175, 200)), seed=j)
        dy = pipe_bounce(f - 96)
        if frozen:
            p = gray_img(PIPE); draw_pipe(fr, 0, 0, p)
        else: draw_pipe(fr, 0, dy)
        out.append(finish(fr))
    return out

SCENES = {12: ('12_cauldron_bubble_tunnel', s12), 13: ('13_flying_spellbook', s13), 14: ('14_invisibility_potion', s14),
          15: ('15_owl_airlift', s15), 16: ('16_crystal_ball_roll', s16), 17: ('17_sword_in_the_stone', s17),
          18: ('18_rune_circle_frog', s18), 19: ('19_ice_block_belly_slide', s19), 20: ('20_fireball', s20),
          21: ('21_hourglass_time_stop', s21)}
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
