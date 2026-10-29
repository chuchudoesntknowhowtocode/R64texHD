import sys, math, random, os
import numpy as np
from PIL import Image, ImageOps
from lib import *
import lib
import martial as M
import fight_assets as FA
import opponents as OP
from fight import hit_spark, callouts, orb, PURP, wheel_img, door_img
from martial_scenes import ghost, ring, speed_lines, counter, run_pose, Combo
from scenes2 import smoke
HERE = os.path.dirname(os.path.abspath(__file__))
HF = M.hip_floor('st_stance'); AIR = HF - 22
FIRE = [(255, 70, 30), (255, 140, 30), (255, 210, 70), (255, 245, 170)]
VIOLET = [(120, 40, 200), (180, 70, 255), (230, 140, 255), (250, 220, 255)]

# ------------------------------------------------------------------ helpers
def hip_y(pose, hy, scheme='hero'): return hy if hy is not None else M.hip_floor(pose, scheme)
def tip_xy(pose, x, hy, flip=False, scheme='hero'):
    dx, dy = M.staff_tip(pose, flip); return x + dx, hip_y(pose, hy, scheme) + dy
def limb_xy(pose, limb, x, hy, flip=False):
    dx, dy = M.eff(pose, limb, flip); return x + dx, hip_y(pose, hy) + dy
def flare(fr, x, y, age, cols=FIRE, big=1.0):
    if 0 <= age < 4:
        r = (6 + age * 7) * big
        D(fr).ellipse([snap(x - r), snap(y - r), snap(x + r), snap(y + r)], outline=cols[2] + (int(255 * (1 - age / 4)),), width=4)
        px(fr, x - 6, y - 6, 12, cols[3], 255 * (1 - age / 4))
def aura(fr, pose, x, hy, f, s, flip=False, scheme='hero', hot=True, cols=FIRE, clip_x=None):
    if s <= 0: return
    fl = 0.75 + 0.25 * math.sin(f * 1.7)
    for (dx, dy, c, a) in ((-4, 0, cols[1], 0.55), (4, 0, cols[1], 0.55), (0, -6, cols[2], 0.5), (-2, -10, cols[0], 0.35), (2, -10, cols[0], 0.35)):
        M.fplace(fr, pose, x + dx, None if hy is None else hy + dy, flip=flip, scheme=scheme, hot=hot, clip_x=clip_x,
                 img_fn=(lambda im, c=c, a=a, dy=dy: _shift(tint(im, c, 1.0, a * s * fl), dy if hy is None else 0)))
    im, ox, oy, fy = M.rig(pose, flip, scheme, hot); top = hip_y(pose, hy, scheme) - oy
    rng = random.Random(f)
    for k in range(int(10 * s)):
        ph = (f * 4 + k * 11) % 36; xx = x - im.width * 0.35 + rng.random() * im.width * 0.7
        px(fr, xx, top + 30 + rng.random() * 50 - ph, 4, cols[k % 3], 230 * s * (1 - ph / 36))
def _shift(im, dy):
    if not dy: return im
    out = Image.new('RGBA', (im.width, im.height), (0, 0, 0, 0)); out.paste(im, (0, dy)); return out
def robed_img(scheme='hero', flip=False):
    a, b = OP.robe_pair(scheme); a = U(a); return ImageOps.mirror(a) if flip else a
def burn_img(t, f, scheme='hero', flip=False):
    """robe burns from the hem up, revealing the gi underneath"""
    robed, gi = OP.robe_pair(scheme); A = np.array(robed); G = np.array(gi); H = A.shape[0]
    diff = np.any(A != G, axis=-1); line = H * (1 - t)
    yy = np.arange(H)[:, None].repeat(A.shape[1], 1)
    out = np.where((yy >= line)[..., None], G, A).copy()
    band = diff & (yy >= line - 3) & (yy < line + 1)
    rng = np.random.default_rng(f); pick = rng.integers(0, 4, size=band.sum())
    cols = np.array(FIRE if scheme == 'hero' else VIOLET)
    out[band, :3] = cols[pick]
    im = U(Image.fromarray(out.astype(np.uint8))); return ImageOps.mirror(im) if flip else im
def embers(fr, x, f, t, cols=FIRE):
    rng = random.Random(f)
    for k in range(14):
        ph = rng.random(); y = FLOOR - 134 * t - ph * 60
        px(fr, x - 46 + rng.random() * 92, y, 4 if k % 3 else 2, cols[k % 4], 255 * (1 - ph))
def bonk(fr, x, y, age):
    if 0 <= age < 14:
        hit_spark(fr, x, y, min(age, 5), 1.0)
        for k in range(3):
            ang = age * 0.5 + k * 2.09; glyph(fr, '*', x + 30 * math.cos(ang) - 10, y + 10 * math.sin(ang) - 6, GOLD, s=2)
def anger(fr, x, f):
    glyph(fr, '!', x + 40, 226, (255, 70, 60), s=4)
    for k in range(3):
        ph = (f * 3 + k * 9) % 24; px(fr, x - 20 + k * 20, 250 - ph, 6, (200, 200, 210), 200 * (1 - ph / 24))
def chunks(fr, x, y, f, cols, seed, n=8, sp=120):
    burst(fr, x, y, 0.25, n=n, speed=sp, cols=cols, seed=seed, grav=200)

def build_combo(t0):
    """an even mix of staff work and martial arts -> Combo (poses may be spin dicts)"""
    C = Combo(); t = t0
    t = C.add(t, ['st_thrust', 'st_thrust2'] * 2, 2, limb='staff')
    t = C.add(t, ['high', 'mid', 'low', 'mid', 'high', 'mid'], 2, limb='fl')
    t = C.add(t, [M.spin_pose(k) for k in range(0, 12, 2)], 2, limb='staff')
    t = C.add(t, ['punch', 'punch2'] * 2, 2, limb='fa')
    t = C.add(t, ['st_sweep'], 4, limb='staff')
    t = C.add(t, ['st_up'], 5, limb='staff')
    return C, t
def strike(pose, limb, x, hy):
    if limb == 'staff': return tip_xy(pose, x, hy)
    return limb_xy(pose, limb, x, hy)

def do_combo(fr, f, C, x, hot=True, aura_s=0.35, clip_x=None):
    """draw the wizard's combo frame. returns (drew, is_hit, strike_xy)"""
    st = C.at(f)
    if not st: return False, False, None
    pose, is_hit, limb, s0 = st
    hy = HF - 16 * math.sin(math.pi * (f - s0) / 5) if pose == 'st_up' else None
    prev = [p for (s, d, p, h, l) in C.steps if s < s0][-3:]
    for k, gp in enumerate(prev[::-1]): ghost(fr, gp, x + 8 * (k + 1), None, 0.4 - k * 0.12)
    aura(fr, pose, x, hy, f, aura_s, clip_x=clip_x)
    M.fplace(fr, pose, x, hy, hot=hot, clip_x=clip_x)
    if pose == 'st_up' or isinstance(pose, dict):
        if isinstance(pose, dict):                                            # motion arc of the spinning staff
            tx, ty = tip_xy(pose, x, None); hx_, hy_ = limb_xy('stance', 'fa', x, None)
            D(fr).arc([snap(hx_ - 80), snap(hy_ - 80), snap(hx_ + 80), snap(hy_ + 80)], 0, 360, fill=(255, 200, 120, 90), width=2)
    sp = strike(pose, limb, x, hy) if is_hit else None
    return True, is_hit, sp

def finisher(fr, f, F0, x, tx):
    """charged overhead staff smash. F0 = charge start; impact at F0+20. returns (drew, x_now)"""
    k = f - F0
    if k < 0 or k >= 32: return False, x
    if k < 14:
        pose = 'st_charge'; aura(fr, pose, x, None, f, 0.5 + 0.5 * k / 14)
        M.fplace(fr, pose, x, None, hot=True)
        txp, typ = tip_xy(pose, x, None)
        for j in range(12):
            ang = j * 0.52 + f * 0.6; r_ = 70 * (1 - k / 14) + 6
            px(fr, txp + r_ * math.cos(ang), typ + r_ * math.sin(ang), 4, FIRE[j % 4], 240)
        rr = 6 + k * 1.2; D(fr).ellipse([snap(txp - rr), snap(typ - rr), snap(txp + rr), snap(typ + rr)], fill=FIRE[2] + (200,))
        return True, x
    if k < 20:
        tt = (k - 14) / 6; xx = lerp(x, tx, tt); hy = HF - 22 * math.sin(math.pi * tt * 0.9)
        aura(fr, 'st_over', xx, hy, f, 0.9); M.fplace(fr, 'st_over', xx, hy, hot=True); return True, xx
    aura(fr, 'st_smash', tx, None, f, 0.9 * (1 - (k - 20) / 12)); M.fplace(fr, 'st_smash', tx, None, hot=True)
    sx, sy = tip_xy('st_smash', tx, None); age = k - 20
    hit_spark(fr, sx, FLOOR - 10, age, 2.2)
    for j in range(3): ring(fr, sx, FLOOR - 6, age - j * 3, (FIRE[3], FIRE[2], FIRE[0])[j], life=12, sp=34, sy=0.25)
    for side in (-1, 1):                                                       # ground shockwave
        wx = sx + side * age * 40
        if age < 10: rect(fr, wx - 20, FLOOR - 8, 40, 8, FIRE[1], 220 * (1 - age / 10)); rect(fr, wx - 12, FLOOR - 14, 24, 6, FIRE[2], 200 * (1 - age / 10))
    if age < 3: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [170, 100, 40][age])
    if age < 5: burst(fr, sx, FLOOR - 10, age / 6, n=24, speed=220, cols=[(140, 120, 100), FIRE[1], FIRE[2]], seed=77, grav=260)
    return True, tx

def wizard_intro(fr, f, x=SX):
    if f < 4: return True
    if 4 <= f < 14:
        im = robed_img(); place(fr, bayer_mask(im, (f - 4) / 10), x, FLOOR)
        for i in range(12):
            ang = i * 0.5 + f * 0.4; r_ = 80 * (1 - (f - 4) / 10); px(fr, x + r_ * math.cos(ang), FLOOR - 66 + r_ * 0.5 * math.sin(ang), 4, (CYAN, WHITE, PURP)[i % 3], 230)
        return True
    return False
def unleash(fr, f, B0, x=SX, scheme='hero', flip=False):
    """robe burn B0..B0+18, then gi reveal with aura flare until B0+40. returns True if it drew the wizard"""
    k = f - B0; cols = FIRE if scheme == 'hero' else VIOLET
    if k < 0 or k >= 40: return False
    if k < 18:
        t = k / 18; place(fr, burn_img(t, f, scheme, flip), x, FLOOR + (2 if f % 2 else 0)); embers(fr, x, f, t, cols)
        return True
    s = 1.0 if k < 28 else 1 - 0.6 * (k - 28) / 12
    pose = 'st_stance' if (k // 4) % 2 else 'st_stance2'
    aura(fr, pose, x, None, f, s, flip=flip, scheme=scheme, cols=cols)
    M.fplace(fr, pose, x, None, flip=flip, scheme=scheme, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.8)) if k < 20 else None)
    if k < 21: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, cols[2], [90, 60, 30][k - 18])
    for j in range(2): ring(fr, x, FLOOR - 70, k - 18 - j * 4, cols[2 - j], life=10, sp=22)
    return True

def exit_run(fr, f, E0, x0):
    """run + flying kick into the pipe, E0..E0+30"""
    k = f - E0
    if k < 0 or k >= 30: return False
    tt = k / 30
    if tt < 0.72: x = lerp(x0, MOUTH + 240, ease_io(tt / 0.72)); M.fplace(fr, run_pose(f), x, None, hot=True, clip_x=MOUTH)
    else:
        x = lerp(MOUTH + 240, MOUTH - 120, (tt - 0.72) / 0.4); hy = AIR + 6; speed_lines(fr, x + 60, hy, f); M.fplace(fr, 'fly', x, hy, hot=True, clip_x=MOUTH)
    return True

def opp_place(fr, img, x, bottom, flash_on=False, rot=0, clip_x=MOUTH):
    im = U(img) if img.width < 200 else img
    if rot: im = im.rotate(rot, expand=True, resample=Image.NEAREST)
    if flash_on: im = tint(im, WHITE, 0.85)
    place(fr, im, x, bottom, clip_x=clip_x)

def sheet_and_gif(frames, name, idx):
    picks = np.linspace(0, len(frames) - 1, 16).astype(int)
    sheet = Image.new('RGB', (890 * 2, 98 * 8))
    for k, p in enumerate(picks): sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
    sheet.save(os.path.join(HERE, f'sheet_u{idx}.png'))
    return write_gif(frames, name, outdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'fighter'))

# ================================================================== U1 goblin
def u1():
    out = []; G0 = SX - 430; B0 = 76; OP0 = 126; C, cend = build_combo(140); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 36; N = E0 + 44
    WX = G0 + 116
    for f in range(N):
        fr = new(pipe=False); drew = False
        aa = clamp((f - 6) / 10) * (1 - clamp((f - N + 22) / 10))
        if aa > 0:
            cr = U(FA.crowd(f, 30, seed=2)); cr = bayer_mask(cr, aa) if aa < 1 else cr; fr.paste(cr, (420, FLOOR - cr.height - 64), cr)
            for tx_ in (330, 1300):
                t_ = U(FA.torch(f + tx_)); t_ = bayer_mask(t_, aa) if aa < 1 else t_; fr.paste(t_, (tx_, FLOOR - t_.height), t_)
        # ---- goblin
        g = None; gx, gy, grot, gfl = G0, FLOOR, 0, False
        if 8 <= f < 26:
            tt = (f - 8) / 18; gx = lerp(MOUTH + 20, G0, ease_out(tt)); hop = abs(math.sin(tt * math.pi * 3)) * 24; g = FA.goblin('jump' if hop > 4 else 'stance', f); gy = FLOOR - hop
        elif 26 <= f < 50:
            g = FA.goblin('jump' if (f // 4) % 2 else 'stance', f); gy = FLOOR - (10 if (f // 4) % 2 else 0)
            if f >= 30: FA.callout(fr, 'HA HA!', G0, 246 - (f % 4), s=2)
        elif 50 <= f < 56: g = FA.goblin('throw', f)
        elif 56 <= f < B0 + 18: g = FA.goblin('stance', f)
        elif B0 + 18 <= f < B0 + 34: g = FA.goblin('hit', f); gx = G0 - 30 * ease_out((f - B0 - 18) / 8)
        elif B0 + 34 <= f < OP0 + 12: g = FA.goblin('stance', f); gx = G0 - 30
        elif OP0 + 12 <= f < IMP:
            n_ = C.hits_before(f); st = C.at(f); g = FA.goblin('hit', f); gx = G0 - 30 - min(n_, 14) * 2
            lift = 18 + 6 * math.sin(f) if st and (st[0] in ('high', 'mid', 'low') or isinstance(st[0], dict)) else (26 if st and st[0] == 'st_up' else 0)
            gy = FLOOR - lift; gfl = (st is not None and st[1]) or f == OP0 + 12
            if f >= F0: g = FA.goblin('hit', f); gy = FLOOR
        elif IMP <= f < IMP + 22:
            tt = (f - IMP) / 20; gx = lerp(G0 - 60, MOUTH - 110, ease_in(tt) * 0.4 + tt * 0.6); gy = FLOOR - 24 - 10 * math.sin(math.pi * min(1, tt)); g = FA.goblin('hit', f); grot = ((f - IMP) * 60) % 360
            for k in range(6): px(fr, gx + 50 + k * 30, gy - 40 + (k * 7 + f) % 9, 4, WHITE, 220 - k * 35)
        if 52 <= f < 62:
            tt = (f - 52) / 10; rx = lerp(G0 + 30, SX - 10, tt); ry = lerp(FLOOR - 80, FLOOR - 128, tt) - 30 * math.sin(math.pi * tt)
            D(fr).rectangle([snap(rx), snap(ry), snap(rx) + 11, snap(ry) + 9], fill=(120, 110, 100, 255), outline=(10, 14, 42, 255))
        if g is not None: opp_place(fr, g, gx, gy, gfl or (0 <= f - IMP < 3), grot)
        # ---- wizard
        if wizard_intro(fr, f): drew = True
        elif f < B0:
            sh = (2 if f % 2 else -2) if f >= 62 else 0
            place(fr, robed_img(), SX + sh, FLOOR)
            if f >= 62: anger(fr, SX, f)
            bonk(fr, SX - 6, FLOOR - 126, f - 62)
        elif unleash(fr, f, B0): pass
        elif f < OP0: pose = 'st_stance' if (f // 6) % 2 else 'st_stance2'; aura(fr, pose, SX, None, f, 0.4); M.fplace(fr, pose, SX, None, hot=True)
        elif f < OP0 + 12:
            tt = (f - OP0) / 12; x = lerp(SX, WX, ease_in(tt)); hy = AIR + 8
            for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12, col=FIRE[1])
            M.fplace(fr, 'fly', x, hy, hot=True); speed_lines(fr, x + 60, hy, f)
            if f == OP0 + 11: hit_spark(fr, x - 60, hy, 1, 1.4)
        else:
            x = WX - min(C.hits_before(f), 14) * 2
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); flare(fr, *tip_xy(C.at(f)[0], x, None), 0)
            elif f < F0: aura(fr, 'st_stance', x, None, f, 0.4); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, x - 30)
            elif f < E0:
                pose = 'st_win' if f < E0 - 8 else 'bow'; aura(fr, pose, x - 30, None, f, 0.3 * (1 - (f - F0 - 32) / (E0 - F0 - 32))); M.fplace(fr, pose, x - 30, None, hot=True)
            else: exit_run(fr, f, E0, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - 8), pipe_bounce(f - IMP - 18), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, G0 - 30, 238)
        callouts(fr, f, [('UNLEASHED!', B0 + 18, B0 + 40, 5), ('FIGHT!', B0 + 40, OP0, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 4, 4)])
        out.append(finish(fr))
    return out

# ================================================================== U2 car
def u2():
    out = []; CX = 760; B0 = 76; C, cend = build_combo(150); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = CX + 84 + 70; W_ = wheel_img(); DR = door_img()
    honks = [30, 44, 58]
    dmg_steps = [(132, 1), (C.steps[9][0], 2), (C.steps[16][0], 3), (C.steps[20][0], 4), (IMP, 5)]
    for f in range(N):
        fr = new(); dmg = 0
        for (hf, dm) in dmg_steps:
            if f >= hf: dmg = dm
        st = C.at(f); hitnow = (st is not None and st[1]) or 0 <= f - IMP < 5 or 0 <= f - 132 < 4
        shake = (4 if f % 2 else -4) if hitnow else 0
        # car charges the wizard at 118..132 then gets stopped
        cx_ = CX
        if 118 <= f < 132: cx_ = CX + 120 * ease_in((f - 118) / 14)
        elif 132 <= f < 140: cx_ = CX + 120 - 120 * ease_out((f - 132) / 8)
        hop = -2 if any(0 <= f - h < 3 for h in honks) else 0
        ca = clamp((f - 8) / 8) * (1 - clamp((f - IMP - 30) / 10))
        if ca > 0:
            ci = U(FA.car(dmg, seed=dmg)); ci = bayer_mask(ci, ca) if ca < 1 else ci; place(fr, ci, cx_ + shake, FLOOR + hop)
            if any(0 <= f - h < 8 for h in honks):                              # headlight flash + exhaust
                px(fr, cx_ - 86, FLOOR - 46, 8, (255, 250, 200)); smoke(fr, cx_ + 96, FLOOR - 16, ((f - max(h for h in honks if h <= f)) / 8), seed=f // 8, n=4, spread=16, size=10)
        if 114 <= f < 132 and f % 2 == 0: smoke(fr, cx_ + 96, FLOOR - 16, 0.4, seed=f, n=3, spread=14, size=10)
        for h in honks:
            if h <= f < h + 10: FA.callout(fr, 'BEEP!', CX, 250 - (f - h), s=3)
        if 4 <= f < 20: smoke(fr, CX, FLOOR - 36, (f - 4) / 16, seed=1, n=10, spread=70, size=28)
        if IMP + 28 <= f < IMP + 44: smoke(fr, CX, FLOOR - 20, (f - IMP - 28) / 16, seed=2, n=10, spread=80, size=26)
        t3 = dmg_steps[2][0]; t4 = dmg_steps[3][0]
        if t3 <= f < IMP + 40:
            tt = (f - t3) / 50; a_ = 1 - clamp((f - IMP - 30) / 10)
            if a_ > 0: wi = W_.rotate(-(f * 40) % 360 // 45 * 45, resample=Image.NEAREST); place(fr, bayer_mask(wi, a_) if a_ < 1 else wi, CX - 60 - 500 * ease_out(min(1, tt)), FLOOR - 26 * abs(math.sin(min(1, tt) * 9)) * (1 - min(1, tt)))
        if t4 <= f < IMP + 40:
            tt = clamp((f - t4) / 18); dx = CX + 10 - 300 * ease_out(tt); dy = FLOOR - 40 - 30 * math.sin(math.pi * tt) + 30 * tt
            di = DR.rotate(int(tt * 540) // 45 * 45, expand=True, resample=Image.NEAREST) if tt < 1 else DR.rotate(90, expand=True, resample=Image.NEAREST)
            a_ = 1 - clamp((f - IMP - 30) / 10); place(fr, bayer_mask(di, a_) if a_ < 1 else di, dx, min(FLOOR, dy + 20))
        # wizard
        if wizard_intro(fr, f): pass
        elif f < B0:
            sh = (2 if f % 2 else -2) if f >= 58 else 0; place(fr, robed_img(), SX + sh, FLOOR)
            if 34 <= f < 44: glyph(fr, '?', SX + 40, 226)
            if 48 <= f < 58: glyph(fr, '!', SX + 40, 226, GOLD)
            if f >= 62: anger(fr, SX, f)
        elif unleash(fr, f, B0): pass
        elif f < 118: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 128:
            tt = (f - 118) / 10; x = lerp(SX, WX + 40, ease_in(tt)); aura(fr, run_pose(f), x, None, f, 0.4); M.fplace(fr, run_pose(f), x, None, hot=True)
        elif f < 140:
            aura(fr, 'st_death', WX + 40, None, f, 0.6); M.fplace(fr, 'st_death', WX + 40, None, hot=True)
            if f == 132: hit_spark(fr, cx_ + 90, HF - 30, 1, 1.8)
            if 0 <= f - 132 < 6: hit_spark(fr, cx_ + 90, HF - 30, f - 132, 1.8)
        elif f < 150: pose = 'st_stance'; aura(fr, pose, WX, None, f, 0.4); M.fplace(fr, pose, WX, None, hot=True)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, min(sp[0], CX + 88), sp[1], 1, 1.0); chunks(fr, CX + 70, sp[1], f, ((80, 190, 175), (200, 230, 245)), f)
            elif f < F0: aura(fr, 'st_stance', x, None, f, 0.4); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, CX + 120)
            elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; M.fplace(fr, pose, CX + 120, None, hot=True)
            else: exit_run(fr, f, E0, CX + 120)
        draw_pipe(fr, 0, pipe_bounce(f - E0 - 28))
        n = C.hits_before(f) + (1 if f >= 132 else 0) + (1 if f >= IMP else 0)
        if 152 <= f < IMP: counter(fr, n, CX, 238)
        callouts(fr, f, [('BONUS STAGE', 6, 28, 5), ('UNLEASHED!', B0 + 18, B0 + 40, 5), ('PERFECT!', IMP + 4, IMP + 28, 7), (f'{n} HIT COMBO!', IMP + 28, E0 + 6, 4)])
        out.append(finish(fr))
    return out

# ================================================================== U3 golem
def golem_crumble_parts():
    im = OP.golem('hit'); a = np.array(im); parts = []; rng = random.Random(5)
    for gy in range(0, a.shape[0], 8):
        for gx in range(0, a.shape[1], 8):
            p = a[gy:gy + 8, gx:gx + 8]
            if (p[..., 3] > 0).sum() > 6: parts.append((U(Image.fromarray(p)), gx * 2, gy * 2, rng.uniform(-60, 60), rng.uniform(-40, 10), rng.choice([0, 90, 180, 270])))
    return parts, im.width * 2, im.height * 2
def u3():
    out = []; O = SX - 470; B0 = 66; OP0 = 168; C, cend = build_combo(182); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 150; parts, GW, GH = golem_crumble_parts()
    for f in range(N):
        fr = new(pipe=False)
        # ---- golem
        gp = None; gfl = False; gb = FLOOR
        if 8 <= f < 30:
            r = ease_out((f - 8) / 20); gb = FLOOR + 150 * (1 - r); gp = 'stance'
            dust(fr, O - 60, FLOOR - 4, ((f - 8) % 10) / 30, seed=f, dirx=-1); dust(fr, O + 60, FLOOR - 4, ((f - 8) % 10) / 30, seed=f + 1)
        elif 30 <= f < 40: gp = 'stance'
        elif 40 <= f < 44: gp = 'throw'
        elif 44 <= f < 114: gp = 'stance' if f < B0 + 18 or f >= B0 + 30 else 'hit'
        elif 114 <= f < 120: gp = 'raise'
        elif 120 <= f < 130: gp = 'pound'
        elif 130 <= f < 140: gp = 'stance'
        elif 140 <= f < 150: gp = 'throw'
        elif 150 <= f < OP0 + 12: gp = 'stance'
        elif OP0 + 12 <= f < IMP:
            st = C.at(f); gp = 'hit' if (st and st[1]) or f == OP0 + 12 else 'stance'; gfl = gp == 'hit'
        if gp:
            gi = U(OP.golem(gp, f)); gi = tint(gi, WHITE, 0.8) if gfl else gi
            place(fr, gi, O, gb, clip_floor=FLOOR if f < 30 else None)
        if IMP <= f < IMP + 40:                                                  # crumbles to rubble
            k = f - IMP; a_ = 1 - clamp((k - 28) / 12)
            for (pi, x0, y0, vx, vy, rot) in parts:
                t = k / 10; X = O - GW / 2 + x0 + vx * min(t, 1.5); Y = FLOOR - GH + y0 + vy * t + 300 * t * t
                Y = min(Y, FLOOR - pi.height); im = pi.rotate(rot if t > 0.3 else 0, resample=Image.NEAREST)
                im = bayer_mask(im, a_) if a_ < 1 else im
                if a_ > 0: fr.paste(im, (snap(X), snap(Y)), im)
            if k < 12: smoke(fr, O, FLOOR - 30, k / 12, seed=33, n=10, spread=70, base=(150, 140, 130), dark=(90, 84, 80), size=24)
        # boulders / shockwave
        if 42 <= f < 52:
            tt = (f - 42) / 10; px(fr, lerp(O + 50, SX - 6, tt), lerp(FLOOR - 120, FLOOR - 126, tt) - 34 * math.sin(math.pi * tt), 6, (124, 116, 108))
        if 122 <= f < 142:
            wx = lerp(O + 70, SX + 80, (f - 122) / 20)
            for k in range(3): rect(fr, wx - 30 + k * 20, FLOOR - 8 - (k % 2) * 6, 18, 8 + (k % 2) * 6, (164, 156, 144), 230)
            burst(fr, wx, FLOOR - 6, 0.3, n=8, speed=80, cols=((164, 156, 144), (120, 112, 104)), seed=f, grav=150)
        if 120 <= f < 124: dust(fr, O, FLOOR - 4, (f - 120) / 10, n=10, seed=4)
        if 150 <= f < 160:
            tt = (f - 150) / 10; bi = U(OP.boulder(f)); place(fr, bi, lerp(O + 40, SX - 110, tt), FLOOR - 70 + 40 * tt - 50 * math.sin(math.pi * tt))
        if 160 <= f < 168: burst(fr, SX - 110, FLOOR - 70, (f - 160) / 8, n=16, speed=140, cols=((124, 116, 108), (84, 78, 74), FIRE[1]), seed=8, grav=220)
        # ---- wizard
        if wizard_intro(fr, f): pass
        elif f < B0:
            sh = (2 if f % 2 else -2) if f >= 52 else 0; place(fr, robed_img(), SX + sh, FLOOR)
            if f >= 52: anger(fr, SX, f)
            bonk(fr, SX - 6, FLOOR - 126, f - 52)
        elif unleash(fr, f, B0): pass
        elif f < 128: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 140:                                                             # jump over the shockwave
            tt = (f - 128) / 12; hy = HF - 24 * math.sin(math.pi * tt); aura(fr, 'tuck', SX, hy, f, 0.4); M.fplace(fr, 'tuck', SX, hy, hot=True)
        elif f < 156: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 168: aura(fr, 'st_thrust', SX, None, f, 0.6); M.fplace(fr, 'st_thrust', SX, None, hot=True)
        elif f < OP0 + 12:
            tt = (f - OP0) / 12; x = lerp(SX, WX, ease_in(tt)); hy = AIR + 8
            for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12, col=FIRE[1])
            M.fplace(fr, 'fly', x, hy, hot=True); speed_lines(fr, x + 60, hy, f)
            if f == OP0 + 11: hit_spark(fr, x - 60, hy, 1, 1.4)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, O + 50, sp[1], f, ((164, 156, 144), (124, 116, 108), (84, 78, 74)), f, n=10)
            elif f < F0: aura(fr, 'st_stance', x, None, f, 0.4); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, x - 40)
            elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; M.fplace(fr, pose, x - 40, None, hot=True)
            else: exit_run(fr, f, E0, x - 40)
        draw_pipe(fr, 0, pipe_bounce(f - E0 - 28))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, [('UNLEASHED!', B0 + 18, B0 + 40, 5), ('FIGHT!', B0 + 40, 112, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        out.append(finish(fr))
    return out

# ================================================================== U4 robot
def u4():
    out = []; O = SX - 440; B0 = 64; OP0 = 166; C, cend = build_combo(180); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 116; rng = random.Random(4)
    gears = [(OP.gear_piece(k), rng.uniform(-260, 260), rng.uniform(-220, -80), rng.choice([0, 1])) for k in range(16)]
    shur = [138 + k * 4 for k in range(5)]
    for f in range(N):
        fr = new(pipe=False)
        # ---- robot
        rp = None; rx = O; fl = False
        if 8 <= f < 24:
            tt = (f - 8) / 16; rx = lerp(MOUTH + 20, O, ease_out(tt)); rp = 'dash'
            for k in range(3): place(fr, tint(U(OP.robot('dash', f)), CYAN, 1, 0.35 - k * 0.1), rx - 40 * (k + 1), FLOOR)
        elif 24 <= f < 36: rp = 'stance'
        elif 36 <= f < 42: rp = 'throw'
        elif 42 <= f < 112: rp = 'stance' if not (B0 + 18 <= f < B0 + 30) else 'hit'
        elif 112 <= f < 120:
            tt = (f - 112) / 8; rx = lerp(O, O + 200, ease_out(tt)); rp = 'dash'
            for k in range(3): place(fr, tint(U(OP.robot('dash', f)), CYAN, 1, 0.35 - k * 0.1), rx - 40 * (k + 1), FLOOR)
        elif 120 <= f < 136: rx = O + 200; rp = 'punch'
        elif 136 <= f < 144: rx = lerp(O + 200, O, (f - 136) / 8); rp = 'dash'
        elif 144 <= f < 160: rp = 'throw' if (f - 138) % 4 < 2 else 'stance'
        elif 160 <= f < OP0 + 12: rp = 'stance'
        elif OP0 + 12 <= f < IMP:
            st = C.at(f); rp = 'hit' if (st and st[1]) or f == OP0 + 12 else 'stance'; fl = rp == 'hit'
        if rp:
            ri = U(OP.robot(rp, f, fist=not (120 <= f < 136))); ri = tint(ri, WHITE, 0.8) if fl else ri; place(fr, ri, rx, FLOOR)
        if 120 <= f < 136:                                                       # rocket punch on a chain
            k = f - 120; ext = (k / 7) if k < 8 else max(0, 1 - (k - 8) / 8)
            fx0 = rx + 60; fx = fx0 + ext * (SX - 140 - fx0); fy = FLOOR - 82
            for j in range(0, int(fx - fx0), 10): px(fr, fx0 + j, fy + 4, 4, (150, 156, 168))
            place(fr, U(OP.rocket_fist()), fx + 10, fy + 14)
            if k < 8: px(fr, fx0 - 6, fy, 6, FIRE[1])
            if k == 7: hit_spark(fr, fx + 20, fy + 4, 1, 1.4)
        if IMP <= f < IMP + 40:                                                  # explodes into gears
            k = f - IMP; a_ = 1 - clamp((k - 28) / 12)
            for j, (gi, vx, vy, sp) in enumerate(gears):
                t = k / 30; X = O + vx * t; Y = min(FLOOR - 24, FLOOR - 70 + vy * t + 500 * t * t)
                im = U(gi); im = im.rotate((k * 45 * (1 if sp else -1)) % 360 // 45 * 45, resample=Image.NEAREST)
                if a_ > 0: place(fr, bayer_mask(im, a_) if a_ < 1 else im, X, Y + im.height)
            if k < 10: smoke(fr, O, FLOOR - 50, k / 10, seed=21, n=10, spread=60, base=(130, 120, 110), dark=(70, 60, 50), size=24); burst(fr, O, FLOOR - 60, k / 10, n=20, speed=200, cols=FIRE, seed=22)
        if 38 <= f < 48:                                                         # provoking shuriken
            tt = (f - 38) / 10; place(fr, U(OP.shuriken(f)), lerp(O + 50, SX - 6, tt), lerp(FLOOR - 80, FLOOR - 120, tt))
        for k, s0 in enumerate(shur):                                            # barrage
            if s0 <= f < s0 + 10:
                tt = (f - s0) / 8; sx_ = lerp(O + 60, SX - 90, min(1, tt)); sy_ = FLOOR - 70 - 20 * (k % 3) + 10
                if tt < 1: place(fr, U(OP.shuriken(f)), sx_, sy_ + 10)
                else: hit_spark(fr, sx_, sy_, f - s0 - 8, 0.9)
        # ---- wizard
        if wizard_intro(fr, f): pass
        elif f < B0:
            sh = (2 if f % 2 else -2) if f >= 48 else 0; place(fr, robed_img(), SX + sh, FLOOR)
            if f >= 48: anger(fr, SX, f)
            bonk(fr, SX - 6, FLOOR - 126, f - 48)
        elif unleash(fr, f, B0): pass
        elif f < 124: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 132: aura(fr, 'st_thrust', SX, None, f, 0.6); M.fplace(fr, 'st_thrust', SX, None, hot=True)
        elif f < 138: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 162:
            pose = M.spin_pose((f - 138)); aura(fr, pose, SX, None, f, 0.5); M.fplace(fr, pose, SX, None, hot=True)
            hx_, hy_ = limb_xy('stance', 'fa', SX, None); D(fr).ellipse([snap(hx_ - 82), snap(hy_ - 82), snap(hx_ + 82), snap(hy_ + 82)], outline=(255, 200, 120, 120), width=4)
        elif f < OP0: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < OP0 + 12:
            tt = (f - OP0) / 12; x = lerp(SX, WX, ease_in(tt)); hy = AIR + 8
            for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12, col=FIRE[1])
            M.fplace(fr, 'fly', x, hy, hot=True); speed_lines(fr, x + 60, hy, f)
            if f == OP0 + 11: hit_spark(fr, x - 60, hy, 1, 1.4)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, O + 40, sp[1], f, ((200, 150, 60), (150, 156, 168)), f, n=6)
            elif f < F0: aura(fr, 'st_stance', x, None, f, 0.4); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, x - 30)
            elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; M.fplace(fr, pose, x - 30, None, hot=True)
            else: exit_run(fr, f, E0, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - 8), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, [('UNLEASHED!', B0 + 18, B0 + 40, 5), ('FIGHT!', B0 + 40, 110, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        out.append(finish(fr))
    return out

# ================================================================== U5 dark twin (final boss)
def u5():
    out = []; O = SX - 440; B0 = 64; TB = 104; OP0 = 196; C, cend = build_combo(210); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 120; orbs = [(152, 'deflect'), (164, 'deflect'), (176, 'return')]
    for f in range(N):
        fr = new(pipe=False)
        I = clamp((f - TB) / 20) * (1 - clamp((f - IMP - 20) / 20))
        if I > 0: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (30, 6, 40), 90 * I)
        # ---- twin (faces right -> flip=True)
        tw = None
        if 8 <= f < 20:
            r_ = 90 * (1 - (f - 8) / 12)
            for i in range(14): ang = i * 0.45 - f * 0.4; px(fr, O + r_ * math.cos(ang), FLOOR - 66 + r_ * 0.5 * math.sin(ang), 4, VIOLET[i % 4], 230)
            place(fr, bayer_mask(robed_img('dark', True), (f - 8) / 12), O, FLOOR)
        elif 20 <= f < TB:
            place(fr, robed_img('dark', True), O, FLOOR)
            if 24 <= f < 34: glyph(fr, '?', O - 50, 226, VIOLET[2])
        elif TB <= f < TB + 40:
            unleash(fr, f, TB, O, scheme='dark', flip=True)
        elif TB + 40 <= f < OP0 + 12:
            pose = 'st_stance'
            for (o0, kind) in orbs:
                if o0 - 4 <= f < o0 + 2: pose = 'st_thrust'
            aura(fr, pose, O, None, f, 0.35, flip=True, scheme='dark', cols=VIOLET); M.fplace(fr, pose, O, None, flip=True, scheme='dark', hot=True)
            if f in range(178, 186): M.fplace(fr, 'hit', O - 10, None, flip=True, scheme='dark', hot=True, img_fn=lambda im: tint(im, WHITE, 0.8) if f % 2 else im)
        elif OP0 + 12 <= f < IMP:
            st = C.at(f); hp = (st and st[1]) or f == OP0 + 12; nh = C.hits_before(f)
            pose = 'hit' if hp else 'st_stance'
            M.fplace(fr, pose, O - min(nh, 14) * 2, None, flip=True, scheme='dark', hot=True, img_fn=(lambda im: tint(im, WHITE, 0.8)) if hp else None)
        elif IMP <= f < IMP + 22:
            tt = (f - IMP) / 20; x = lerp(O - 40, MOUTH - 120, ease_in(tt) * 0.4 + tt * 0.6); hy = HF - 20 - 10 * math.sin(math.pi * min(1, tt))
            rot = ((f - IMP) * 60) % 360
            im, ox, oy, fy = M.rig('hit', True, 'dark', True); im = im.rotate(rot, expand=True, resample=Image.NEAREST)
            place(fr, im, x, 0, cy=hy, clip_x=MOUTH)
            for k in range(6): px(fr, x + 50 + k * 30, hy + (k * 7 + f) % 9 - 4, 4, VIOLET[k % 4], 220 - k * 35)
        # zap that provokes the wizard
        if 40 <= f < 48:
            tt = (f - 40) / 6
            if tt <= 1: D(fr).line([(O + 40, FLOOR - 120), (snap(lerp(O + 40, SX - 6, tt)), FLOOR - 126 + (6 if f % 2 else -6))], fill=VIOLET[1] + (255,), width=4)
        # dark orbs
        for (o0, kind) in orbs:
            k = f - o0
            if 0 <= k < 10:
                t = k / 10; x = lerp(O + 100, SX - 120, t); orb(fr, x, FLOOR - 96, f, r=14, trail=-1) if False else _dorb(fr, x, FLOOR - 96, f)
            elif 10 <= k < 18:
                t = (k - 10) / 8
                if kind == 'deflect': x = lerp(SX - 120, SX - 300, t); y = FLOOR - 96 - 40 * t; _dorb(fr, x, y, f, a=1 - t)
                else: x = lerp(SX - 120, O + 40, t); _dorb(fr, x, FLOOR - 90, f, hot=True)
            if k == 10: hit_spark(fr, SX - 120, FLOOR - 96, 1, 1.4)
            if kind == 'return' and k == 18: hit_spark(fr, O + 40, FLOOR - 90, 1, 1.8)
        # ---- wizard
        if wizard_intro(fr, f): pass
        elif f < B0:
            sh = (2 if f % 2 else -2) if f >= 48 else 0; place(fr, robed_img(), SX + sh, FLOOR)
            if 24 <= f < 34: glyph(fr, '?', SX + 40, 226)
            if f >= 48: anger(fr, SX, f)
            bonk(fr, SX - 6, FLOOR - 126, f - 46)
        elif unleash(fr, f, B0): pass
        elif f < OP0:
            pose = 'st_stance'
            for (o0, kind) in orbs:
                if o0 + 6 <= f < o0 + 12: pose = 'st_thrust' if kind != 'deflect' or o0 == 152 else M.spin_pose(f)
            aura(fr, pose, SX, None, f, 0.4); M.fplace(fr, pose, SX, None, hot=True)
        elif f < OP0 + 12:
            tt = (f - OP0) / 12; x = lerp(SX, WX, ease_in(tt)); hy = AIR + 8
            for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12, col=FIRE[1])
            M.fplace(fr, 'fly', x, hy, hot=True); speed_lines(fr, x + 60, hy, f)
            if f == OP0 + 11: hit_spark(fr, x - 60, hy, 1, 1.4)
        else:
            x = WX - min(C.hits_before(f), 14) * 2
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, sp[0], sp[1], f, VIOLET, f, n=6)
            elif f < F0: aura(fr, 'st_stance', x, None, f, 0.4); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, x - 30)
            elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; M.fplace(fr, pose, x - 30, None, hot=True)
            else: exit_run(fr, f, E0, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - IMP - 18), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, [('UNLEASHED!', B0 + 18, B0 + 38, 5), ('FINAL ROUND', TB + 22, TB + 42, 5), ('FIGHT!', TB + 42, TB + 56, 7),
                         ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        out.append(finish(fr))
    return out
def _dorb(fr, x, y, f, a=1.0, hot=False):
    cols = (FIRE if hot else VIOLET)
    for k in range(6): px(fr, x - (r := 0) - (16 + k * 10) * (-1 if hot else 1) * -1, y + 5 * math.sin(f * 0.9 + k), 6 - k // 2, cols[k % 3], (220 - k * 30) * a)
    for rr, c in ((16, cols[0]), (12, cols[1]), (7, cols[2]), (3, cols[3])):
        D(fr).ellipse([snap(x - rr), snap(y - rr), snap(x + rr), snap(y + rr)], fill=c + (int(255 * a),))

US = {1: ('unleashed_1_vs_goblin', u1), 2: ('unleashed_2_car_smash', u2), 3: ('unleashed_3_vs_golem', u3), 4: ('unleashed_4_vs_robot', u4), 5: ('unleashed_5_vs_dark_twin_final', u5)}
if __name__ == '__main__':
    for i in [int(x) for x in sys.argv[1:]] or list(US):
        name, fn = US[i]; frames = fn(); print(i, name, len(frames), sheet_and_gif(frames, name, i), flush=True)
