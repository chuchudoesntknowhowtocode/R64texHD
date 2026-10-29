import sys, math, random, os
import numpy as np
from PIL import Image, ImageOps
from lib import *
import lib
import martial as M
import fight_assets as FA
from fight import hit_spark, callouts, orb, PURP
from scenes import bolt
from scenes2 import smoke
HERE = os.path.dirname(os.path.abspath(__file__))
HF = M.hip_floor('stance')                # standing hip height
AIR = HF - 22                             # airborne hip height (max the strip allows)
GHOST = (110, 220, 255)

def ghost(fr, pose, x, hy, a, col=GHOST, flip=False, clip_x=None):
    M.fplace(fr, pose, x, hy, flip=flip, clip_x=clip_x, img_fn=lambda im: tint(im, col, 1.0, a))
def ring(fr, x, y, age, col=WHITE, life=10, sp=14, sy=0.55):
    if 0 <= age < life:
        r = 10 + age * sp; D(fr).ellipse([snap(x - r), snap(y - r * sy), snap(x + r), snap(y + r * sy)], outline=col + (int(255 * (1 - age / life)),), width=4)
def speed_lines(fr, x, y, f, n=6, length=90, a=150, dirx=1):
    for k in range(n):
        yy = y - 50 + k * 18 + (f * 7 + k * 5) % 9; xx = x + dirx * (30 + (k * 37 + f * 23) % 50)
        rect(fr, xx if dirx > 0 else xx - length, yy, length, 2, WHITE, a)
def counter(fr, n, x, y, a=255):
    if n >= 2: FA.callout(fr, f'{n} HITS', x, y, s=3, a=a)
def run_pose(f): return 'run1' if (f // 3) % 2 else 'run2'

class Combo:
    """A scripted flurry: list of (frame, pose, kind). kind: 'hit' strikes target, None = no contact."""
    def __init__(self): self.steps = []
    def add(self, f0, poses, every=2, hit=True, limb=None):
        for i, p in enumerate(poses): self.steps.append((f0 + i * every, every, p, hit, limb))
        return f0 + len(poses) * every
    def at(self, f):
        for (s, d, p, h, l) in self.steps:
            if s <= f < s + d: return p, (h and f == s), l, s
        return None
    def hits_before(self, f): return sum(1 for (s, d, p, h, l) in self.steps if h and s <= f)

def strike_point(pose, limb, hx, hy):
    dx, dy = M.eff(pose, limb); return hx + dx, hy + dy
SHADOW = ['high', 'mid', 'low', 'mid', 'high', 'mid', 'low', 'high']
PUNCHES = ['punch', 'punch2'] * 4

# ====================================================================== M1 solo: massive combo on the pipe
def m1():
    out = []; N = 196; X0 = SX; XP = MOUTH + 92
    C = Combo(); t = 80
    t = C.add(t, SHADOW, 2, limb='fl'); t = C.add(t, PUNCHES[:6], 2, limb='fa'); t = C.add(t + 1, ['sweep'], 4, limb='fl'); t = C.add(t, ['upper'], 5, limb='fa')
    DEATH = t + 4                                                       # death punch frame
    trail = []
    for f in range(N):
        fr = new(pipe=False); pdx = pdy = 0; pflash = False
        pose = None; x = X0; hy = None; flip = False
        if 4 <= f < 9 and f % 2 == 0: bolt(fr, SX, SAFE + 2, SX, FLOOR, f, w=4, col=WHITE, glow=RED)
        if 6 <= f < 14: M.fplace(fr, 'stance', SX, img_fn=lambda im: bayer_mask(im, (f - 6) / 8)); burst(fr, SX, FLOOR - 8, (f - 6) / 8, n=12, speed=100, cols=(RED, WHITE, GOLD), seed=1)
        elif 14 <= f < 24: pose = 'bow' if 16 <= f < 22 else 'stance'
        elif 24 <= f < 30: pose = 'stance' if (f // 3) % 2 else 'stance2'
        elif 30 <= f < 50:                                              # chain-punch flurry while advancing
            pose = 'punch' if f % 2 else 'punch2'; x = lerp(SX, SX - 140, (f - 30) / 20)
            for k, gx in enumerate(trail[-3:][::-1]): ghost(fr, 'punch2' if f % 2 else 'punch', gx, None, 0.45 - k * 0.13)
            fx, fy = strike_point(pose, 'fa' if pose == 'punch' else 'ba', x, HF); hit_spark(fr, fx - 6, fy, 1, 0.6)
        elif 50 <= f < 54: pose = 'crouch'; x = SX - 140
        elif 54 <= f < 72:                                              # flying kick across the bar
            tt = (f - 54) / 18; x = lerp(SX - 140, XP + 40, ease_io(tt)); hy = AIR + 10 * (1 - math.sin(math.pi * tt)); pose = 'fly'
            speed_lines(fr, x + 60, hy, f); trail.append(x)
            for k, gx in enumerate(trail[-4:-1][::-1]): ghost(fr, 'fly', gx, hy, 0.4 - k * 0.12)
        elif 72 <= f < 80: pose = 'stance' if f >= 74 else 'crouch'; x = XP
        else: x = XP
        st = C.at(f)
        if st:
            pose, is_hit, limb, s0 = st
            if pose == 'upper': hy = HF - 14 * math.sin(math.pi * (f - s0) / 5)
            prev = [p for (s, d, p, h, l) in C.steps if s < s0][-3:]
            for k, gp in enumerate(prev[::-1]): ghost(fr, gp, x + 8 * (k + 1), None, 0.42 - k * 0.12)
            if is_hit:
                pdx = -4 if (f // 2) % 2 else -2; pflash = True
        if C.at(f) is None and 80 <= f < DEATH + 30:
            if f < DEATH - 4: pose = 'charge'
            elif f < DEATH: pose = 'stance2'
            elif f < DEATH + 10: pose = 'death'
            elif f < DEATH + 30: pose = 'win' if f < DEATH + 22 else 'bow'
        if DEATH - 10 <= f < DEATH:                                     # chi gathering into the fist
            for k in range(10):
                ang = k * 0.628 + f * 0.7; r_ = 40 * (DEATH - f) / 10
                px(fr, x - 30 + r_ * math.cos(ang), HF - 30 + r_ * math.sin(ang), 4, (GOLD, WHITE, RED)[k % 3], 230)
        if DEATH + 30 <= f < DEATH + 36: pose = 'crouch'
        elif DEATH + 36 <= f < DEATH + 44:
            tt = (f - DEATH - 36) / 8; x = lerp(XP, MOUTH - 110, ease_in(tt)); hy = AIR + 6; pose = 'fly'; speed_lines(fr, x + 60, hy, f)
        if pose: M.fplace(fr, pose, x, hy, clip_x=MOUTH)
        # strikes on the pipe
        st = C.at(f)
        if st and st[1]:
            sx_, sy_ = strike_point(st[0], st[2], x, HF if st[0] != 'upper' else HF - 8)
            hit_spark(fr, max(MOUTH + 10, sx_), sy_, 1, 0.9)
        n = C.hits_before(f) + (1 if f >= DEATH else 0)
        for age_src in (DEATH,):
            age = f - age_src
            if 0 <= age < 6: hit_spark(fr, MOUTH + 20, HF - 30, age, 2.0)
            for k in range(3): ring(fr, MOUTH + 20, HF - 30, age - k * 3, (WHITE, GOLD, RED)[k], life=12, sp=26)
            if 0 <= age < 3: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [150, 90, 40][age])
        if 0 <= f - DEATH < 8: pdx = [-14, -10, 8, -6, 4, -2, 1, 0][f - DEATH]; pflash = f - DEATH < 3
        pdy = min(pipe_bounce(f - DEATH), pipe_bounce(f - DEATH - 44))
        draw_pipe(fr, pdx, pdy, tint(PIPE, WHITE, 0.6) if pflash else None)
        if 80 <= f < DEATH + 26: counter(fr, n, MOUTH + 160, 238, 255 * (1 - clamp((f - DEATH - 20) / 6)))
        callouts(fr, f, [('READY?', 14, 30, 6), ('DEATH PUNCH!', DEATH - 2, DEATH + 12, 4), (f'{n} HIT COMBO!', DEATH + 12, DEATH + 34, 5)])
        out.append(finish(fr))
    return out

# ====================================================================== M2 vs goblin: juggle combo
def m2():
    out = []; N = 220; G0 = SX - 420
    C = Combo(); t = 72
    t = C.add(t, PUNCHES, 2, limb='fa'); t = C.add(t, SHADOW, 2, limb='fl'); t = C.add(t, ['knee'], 3, limb='fl'); t = C.add(t, ['sweep'], 4, limb='fl'); t = C.add(t, ['upper'], 5, limb='fa')
    DEATH = t + 4; KO = DEATH; WX0 = SX
    for f in range(N):
        fr = new(pipe=False)
        aa = clamp((f - 6) / 10) * (1 - clamp((f - 198) / 10))
        if aa > 0:
            cr = U(FA.crowd(f, 30, seed=2)); cr = bayer_mask(cr, aa) if aa < 1 else cr; fr.paste(cr, (420, FLOOR - cr.height - 64), cr)
            for tx in (330, 1300):
                t_ = U(FA.torch(f + tx)); t_ = bayer_mask(t_, aa) if aa < 1 else t_; fr.paste(t_, (tx, FLOOR - t_.height), t_)
        pose = None; x = SX; hy = None
        gpose, gx, gy, grot, gfl = None, G0, FLOOR, 0, False
        # --- goblin
        if 8 <= f < 26:
            tt = (f - 8) / 18; gx = lerp(MOUTH + 20, G0, ease_out(tt)); hop = abs(math.sin(tt * math.pi * 3)) * 24; gpose = 'jump' if hop > 4 else 'stance'; gy = FLOOR - hop
        elif 26 <= f < 70: gpose = 'stance'
        GH = G0 + 6                                                        # goblin's spot during the combo
        n = C.hits_before(f)
        if 70 <= f < DEATH:
            st = C.at(f); gpose = 'hit'; gx = GH - min(n, 12) * 3
            lift = 0
            if st and st[0] in ('high', 'mid', 'low', 'knee'): lift = 18 + 6 * math.sin(f)
            if st and st[0] == 'sweep': lift = 0
            if st and st[0] == 'upper': lift = 26
            gy = FLOOR - lift; gfl = st is not None and st[1]
        if DEATH <= f < DEATH + 22:                                       # launched into the pipe
            tt = (f - DEATH) / 20; gx = lerp(GH - 40, MOUTH - 100, ease_in(tt) * 0.4 + tt * 0.6); gy = FLOOR - 26 - 10 * math.sin(math.pi * min(1, tt)); gpose = 'hit'; grot = ((f - DEATH) * 60) % 360
            for k in range(6): px(fr, gx + 50 + k * 30, gy - 40 + (k * 7 + f) % 9, 4, WHITE, 220 - k * 35)
        # --- wizard
        WX = GH + 108                                                     # combo spacing
        if 4 <= f < 14: M.fplace(fr, 'stance', SX, img_fn=lambda im: bayer_mask(im, (f - 4) / 10)); burst(fr, SX, FLOOR - 8, (f - 4) / 10, n=12, speed=100, cols=(RED, WHITE, GOLD), seed=1)
        elif 14 <= f < 58: pose = 'stance' if (f // 6) % 2 else 'stance2'
        elif 58 <= f < 62: pose = 'crouch'
        elif 62 <= f < 72:                                                # flying kick opener
            tt = (f - 62) / 10; x = lerp(SX, WX, ease_in(tt)); hy = AIR + 8; pose = 'fly'; speed_lines(fr, x + 60, hy, f)
            for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12)
        st = C.at(f)
        if st:
            pose, is_hit, limb, s0 = st; x = WX - min(n, 12) * 3
            if pose == 'upper': hy = HF - 16 * math.sin(math.pi * (f - s0) / 5)
            prev = [p for (s, d, p, h, l) in C.steps if s < s0][-3:]
            for k, gp in enumerate(prev[::-1]): ghost(fr, gp, x + 8 * (k + 1), None, 0.42 - k * 0.12)
            if is_hit:
                sx_, sy_ = strike_point(pose, limb, x, HF if pose != 'upper' else HF - 8); hit_spark(fr, sx_, sy_, 1, 1.0)
        elif 70 <= f < 72: x = WX
        if C.at(f) is None and f >= 72 and f < DEATH + 40:
            x = WX - 36
            if f < DEATH - 4: pose = 'charge'
            elif f < DEATH: pose = 'stance2'
            elif f < DEATH + 10: pose = 'death'
            else: pose = 'win' if f < DEATH + 30 else 'bow'
        if DEATH - 6 <= f < DEATH:
            for k in range(10):
                ang = k * 0.628 + f * 0.7; r_ = 40 * (DEATH - f) / 6; px(fr, WX - 70 + r_ * math.cos(ang), HF - 30 + r_ * math.sin(ang), 4, (GOLD, WHITE, RED)[k % 3], 230)
        age = f - DEATH
        if 0 <= age < 6: hit_spark(fr, GH + 20, HF - 30, age, 2.0)
        for k in range(3): ring(fr, GH + 20, HF - 30, age - k * 3, (WHITE, GOLD, RED)[k], life=12, sp=26)
        if 0 <= age < 3: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [150, 90, 40][age])
        if DEATH + 40 <= f < 70 + DEATH + 6:                              # run then flying kick into the pipe
            tt = (f - DEATH - 40) / 30
            if tt < 0.75: x = lerp(WX - 36, MOUTH + 240, ease_io(tt / 0.75)); pose = run_pose(f); hy = None
            else: x = lerp(MOUTH + 240, MOUTH - 110, (tt - 0.75) / 0.45); pose = 'fly'; hy = AIR + 6; speed_lines(fr, x + 60, hy, f)
        if gpose:
            gim = U(FA.goblin(gpose, f)); gim = gim.rotate(grot, expand=True, resample=Image.NEAREST) if grot else gim
            if gfl or (0 <= age < 3): gim = tint(gim, WHITE, 0.85)
            place(fr, gim, gx, gy, clip_x=MOUTH)
        if pose: M.fplace(fr, pose, x, hy, clip_x=MOUTH)
        draw_pipe(fr, 0, min(pipe_bounce(f - 8), pipe_bounce(f - DEATH - 20), pipe_bounce(f - DEATH - 76)))
        nn = n + (1 if f >= DEATH else 0)
        if 70 <= f < DEATH + 1: counter(fr, nn, GH, 238)
        callouts(fr, f, [('ROUND 1', 24, 42, 6), ('FIGHT!', 42, 56, 7), ('K.O.', DEATH + 2, DEATH + 30, 8), (f'{nn} HIT COMBO!', DEATH + 30, DEATH + 50, 4)])
        out.append(finish(fr))
    return out

# ====================================================================== M3 car smash with martial arts
def m3():
    out = []; N = 236; CX = 780; WX = CX + 84 + 64
    C = Combo(); t = 40
    t = C.add(t, PUNCHES, 2, limb='fa'); t1 = t
    t = C.add(t + 6, SHADOW, 2, limb='fl'); t2 = t
    t = C.add(t + 4, ['sweep', 'sweep'], 4, limb='fl'); t3 = t
    FK = t + 4                                                           # back off + flying kick at FK..FK+14
    t = C.add(FK + 16, PUNCHES + SHADOW[:6], 2, limb='fa'); t4 = t
    DEATH = t + 8
    dmg_at = [(t1, 1), (t2, 2), (t3, 3), (FK + 14, 4), (DEATH, 5)]
    from fight import wheel_img, door_img
    W_ = wheel_img(); DR = door_img()
    for f in range(N):
        fr = new(); dmg = 0
        for (hf, dm) in dmg_at:
            if f >= hf: dmg = dm
        st = C.at(f); n = C.hits_before(f) + (1 if f >= FK + 14 else 0) + (1 if f >= DEATH else 0)
        shake = (4 if f % 2 else -4) if (st and st[1]) or 0 <= f - DEATH < 6 or 0 <= f - FK - 14 < 4 else 0
        ca = clamp((f - 8) / 8) * (1 - clamp((f - DEATH - 30) / 10))
        if ca > 0:
            cimg = U(FA.car(dmg, seed=dmg)); cimg = bayer_mask(cimg, ca) if ca < 1 else cimg; place(fr, cimg, CX + shake, FLOOR)
        if 4 <= f < 20: smoke(fr, CX, FLOOR - 36, (f - 4) / 16, seed=1, n=10, spread=70, size=28)
        if DEATH + 28 <= f < DEATH + 44: smoke(fr, CX, FLOOR - 20, (f - DEATH - 28) / 16, seed=2, n=10, spread=80, size=26)
        if t3 <= f < DEATH + 40:                                         # wheel knocked off by the sweep
            tt = (f - t3) / 50; wx_ = CX - 60 - 520 * ease_out(min(1, tt)); a_ = 1 - clamp((f - t3 - 40) / 10)
            if a_ > 0: wi = W_.rotate(-(f * 40) % 360 // 45 * 45, resample=Image.NEAREST); place(fr, bayer_mask(wi, a_) if a_ < 1 else wi, wx_, FLOOR - 26 * abs(math.sin(min(1, tt) * 9)) * (1 - min(1, tt)))
        if FK + 14 <= f < DEATH + 40:                                    # door kicked off by the flying kick
            tt = clamp((f - FK - 14) / 18); dx = CX + 10 - 300 * ease_out(tt); dy = FLOOR - 40 - 30 * math.sin(math.pi * tt) + 30 * tt
            di = DR.rotate(int(tt * 540) // 45 * 45, expand=True, resample=Image.NEAREST) if tt < 1 else DR.rotate(90, expand=True, resample=Image.NEAREST)
            a_ = 1 - clamp((f - DEATH - 30) / 10); place(fr, bayer_mask(di, a_) if a_ < 1 else di, dx, min(FLOOR, dy + 20))
        pose = None; x = WX; hy = None
        if 4 <= f < 14: M.fplace(fr, 'stance', SX, img_fn=lambda im: bayer_mask(im, (f - 4) / 10)); burst(fr, SX, FLOOR - 8, (f - 4) / 10, n=12, speed=100, cols=(RED, WHITE, GOLD), seed=1)
        elif 14 <= f < 22: pose = 'stance'; x = SX
        elif 22 <= f < 38: tt = (f - 22) / 16; x = lerp(SX, WX, ease_io(tt)); pose = run_pose(f)
        elif 38 <= f < 40: pose = 'stance'
        if st:
            pose, is_hit, limb, s0 = st
            prev = [p for (s, d, p, h, l) in C.steps if s < s0][-3:]
            for k, gp in enumerate(prev[::-1]): ghost(fr, gp, x + 8 * (k + 1), None, 0.42 - k * 0.12)
            if is_hit:
                sx_, sy_ = strike_point(pose, limb, x, HF); hit_spark(fr, min(sx_, CX + 86), sy_, 1, 1.0)
                burst(fr, CX + 70, sy_, 0.25, n=8, speed=120, cols=((80, 190, 175), (200, 230, 245)), seed=f, grav=200)
        elif 40 <= f < DEATH + 40 and pose is None:
            if FK - 4 <= f < FK: pose = 'run1' if f % 2 else 'run2'; x = WX + 60 * (f - FK + 4) / 4
            elif FK <= f < FK + 4: pose = 'crouch'; x = WX + 60
            elif FK + 4 <= f < FK + 16:                                  # flying kick into the door
                tt = (f - FK - 4) / 12; x = lerp(WX + 60, WX - 10, ease_in(tt)); hy = AIR + 4; pose = 'fly'
                speed_lines(fr, x + 60, hy, f)
                if f == FK + 14: hit_spark(fr, CX + 60, HF - 20, 1, 1.6)
            elif f < DEATH - 6: pose = 'charge' if f > t4 else 'stance'
            elif f < DEATH: pose = 'stance2'
            elif f < DEATH + 10: pose = 'death'
            else: pose = 'win' if f < DEATH + 30 else 'bow'
        if DEATH - 8 <= f < DEATH:
            for k in range(10):
                ang = k * 0.628 + f * 0.7; r_ = 40 * (DEATH - f) / 8; px(fr, x - 40 + r_ * math.cos(ang), HF - 30 + r_ * math.sin(ang), 4, (GOLD, WHITE, RED)[k % 3], 230)
        age = f - DEATH
        if 0 <= age < 6: hit_spark(fr, CX + 60, HF - 20, age, 2.2)
        for k in range(3): ring(fr, CX + 40, HF - 20, age - k * 3, (WHITE, GOLD, RED)[k], life=12, sp=28)
        if 0 <= age < 4: burst(fr, CX, FLOOR - 40, age / 6, n=28, speed=240, cols=((80, 190, 175), (45, 125, 115), (200, 230, 245)), seed=99, grav=200)
        if 0 <= age < 3: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [150, 90, 40][age])
        R0 = DEATH + 40
        if R0 <= f < R0 + 34:
            tt = (f - R0) / 34
            if tt < 0.75: x = lerp(WX, MOUTH + 240, ease_io(tt / 0.75)); pose = run_pose(f); hy = None
            else: x = lerp(MOUTH + 240, MOUTH - 110, (tt - 0.75) / 0.45); pose = 'fly'; hy = AIR + 6; speed_lines(fr, x + 60, hy, f)
        if pose: M.fplace(fr, pose, x, hy, clip_x=MOUTH)
        draw_pipe(fr, 0, pipe_bounce(f - R0 - 30))
        if 40 <= f < DEATH - 2: counter(fr, n, CX, 238)
        callouts(fr, f, [('BONUS STAGE', 6, 30, 5), ('DEATH PUNCH!', DEATH - 2, DEATH + 10, 4), ('PERFECT!', DEATH + 10, DEATH + 30, 7), (f'{n} HIT COMBO!', DEATH + 30, DEATH + 48, 4)])
        out.append(finish(fr))
    return out

MS = {1: ('martial_1_massive_combo_solo', m1), 2: ('martial_2_vs_goblin_juggle', m2), 3: ('martial_3_car_smash', m3)}
if __name__ == '__main__':
    for i in [int(x) for x in sys.argv[1:]] or list(MS):
        name, fn = MS[i]; frames = fn()
        picks = np.linspace(0, len(frames) - 1, 16).astype(int)
        sheet = Image.new('RGB', (890 * 2, 98 * 8))
        for k, p in enumerate(picks): sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
        sheet.save(os.path.join(HERE, f'sheet_m{i}.png'))
        print(i, name, len(frames), write_gif(frames, name, outdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'fighter')), flush=True)
