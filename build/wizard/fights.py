"""Fight clips for the footer director (spec v2, 2026-10-28), built from the unleashed scenes:
  - a VS card (slide-in banners, R64 WIZARD vs the opponent) after the opponent arrives;
  - robed start: the robe burns from the hem up and his hat burns off with it; or gi start (robe already
    gone this job): no burn, just a power-up;
  - the aura grows with the hit counter; no white flashes (impacts get a hit-stop freeze and a shake);
  - the odd hit lands on him (golem shockwave, robot rocket punch, goblin rock in the gi);
  - the dark twin: red eyes, MIRROR MATCH, and sometimes wins round 1 before the comeback;
  - endings for when the job finishes early: instant exit (success), yellow burst (cancel), red burst (error).
Each scene builder returns a Scene; assemble() turns it into frames.   python3 fights.py [name ...]"""
import sys, math, random, os
import numpy as np
from PIL import Image, ImageOps
from unleashed import *                     # lib helpers, M (rig), FA, OP, aura, combo engine...
import unleashed as UL
import hats

# ------------------------------------------------------------------ outfit sprites (front view, 2x)
_FRONT = {}
def front(scheme='hero'):
    """robed (with hat), robed without hat, the hat alone + its 1x box, gi without hat"""
    if scheme not in _FRONT:
        robed, gi = OP.robe_pair(scheme)
        if scheme == 'dark':
            robed = Image.fromarray(M.red_eyes_arr(np.array(robed))); gi = Image.fromarray(M.red_eyes_arr(np.array(gi)))
        hat = hats.hat_only(robed); hb = hat.getbbox()
        _FRONT[scheme] = dict(robed=U(robed), robed_nh=U(hats.remove_hat(robed)), hat=U(hat.crop(hb)), hat_box=hb,
                              gi_nh=U(hats.remove_hat(gi)), size=robed.size,
                              robed1=np.array(hats.remove_hat(robed)), gi1=np.array(hats.remove_hat(gi)))
    return _FRONT[scheme]
def robed_img(scheme='hero', flip=False, hat=True):
    im = front(scheme)['robed' if hat else 'robed_nh']; return ImageOps.mirror(im) if flip else im
def burn_img(t, f, scheme='hero', flip=False):
    """robe burns from the hem up (hat already gone), revealing the gi"""
    F = front(scheme); A, G = F['robed1'], F['gi1']; H = A.shape[0]
    diff = np.any(A != G, axis=-1); line = H * (1 - t)
    yy = np.arange(H)[:, None].repeat(A.shape[1], 1)
    out = np.where((yy >= line)[..., None], G, A).copy()
    band = diff & (yy >= line - 3) & (yy < line + 1)
    rng = np.random.default_rng(f); pick = rng.integers(0, 4, size=band.sum())
    out[band, :3] = np.array(FIRE if scheme == 'hero' else VIOLET)[pick]
    im = U(Image.fromarray(out.astype(np.uint8))); return ImageOps.mirror(im) if flip else im
def hat_flight(fr, k, x, scheme='hero', flip=False):
    """the hat pops off in flames and burns up (k = frames since the burn started)"""
    if k < 0 or k >= 18: return
    F = front(scheme); w, h = F['size']; hb = F['hat_box']; cols = FIRE if scheme == 'hero' else VIOLET
    left = snap(x - w); top = FLOOR - h * 2
    hx = left + (hb[0] + hb[2]); hy = top + (hb[1] + hb[3])
    if flip: hx = left + 2 * w - (hb[0] + hb[2])
    d = -1 if flip else 1
    cx = hx + d * k * 5; cy = hy - k * 10 + k * k * 0.25
    im = F['hat'].rotate(-d * k * 24 // 45 * 45 if k > 2 else 0, expand=True, resample=Image.NEAREST)
    if flip: im = ImageOps.mirror(im)
    im = tint(im, cols[1], min(0.8, k / 12))
    if k >= 8: im = bayer_mask(im, 1 - (k - 8) / 10)
    place(fr, im, cx, 0, cy=cy)
    rng = random.Random(k * 7)
    for j in range(10 + k):
        px(fr, cx - 24 + rng.random() * 48, cy - 10 - rng.random() * 30 - k, 4 if j % 3 else 2, cols[j % 4], 230 * (1 - k / 18))

# ------------------------------------------------------------------ wizard phases
def intro(fr, f, robed, x=SX):
    """appears next to Quit (sparkle ring + dither fade). True while it drew"""
    if f < 4: return True
    if f < 14:
        if robed: im = robed_img(); place(fr, bayer_mask(im, (f - 4) / 10), x, FLOOR)
        else: M.fplace(fr, 'st_stance', x, None, hot=True, img_fn=lambda im: bayer_mask(im, (f - 4) / 10))
        for i in range(12):
            ang = i * 0.5 + f * 0.4; r_ = 80 * (1 - (f - 4) / 10); px(fr, x + r_ * math.cos(ang), FLOOR - 66 + r_ * 0.5 * math.sin(ang), 4, (CYAN, WHITE, PURP)[i % 3], 230)
        return True
    return False
def waiting(fr, f, robed, angry_from=None, x=SX, hit=None):
    """standing before the fight starts; angry (shaking) from angry_from; hit=(f0, f1) stagger in the gi"""
    if hit and hit[0] <= f < hit[1]:
        k = f - hit[0]; M.fplace(fr, 'hit', x + min(k, 4) * 4, None, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.7)) if k < 2 else None)
        return
    sh = (2 if f % 2 else -2) if angry_from is not None and f >= angry_from else 0
    if robed: place(fr, robed_img(), x + sh, FLOOR)
    else:
        pose = 'st_stance' if (f // 6) % 2 else 'st_stance2'; aura(fr, pose, x + sh, None, f, 0.15); M.fplace(fr, pose, x + sh, None, hot=True)
    if angry_from is not None and f >= angry_from: anger(fr, x, f)
def unleash(fr, f, B0, robed, x=SX, scheme='hero', flip=False):
    """robed: hat flies off and burns, robe burns from the hem up (B0..B0+18), gi reveal and aura to B0+40.
    gi start: a power-up flare instead. True while it drew"""
    k = f - B0; cols = FIRE if scheme == 'hero' else VIOLET
    if k < 0 or k >= 40: return False
    if robed and k < 18:
        t = k / 18; place(fr, burn_img(t, f, scheme, flip), x, FLOOR + (2 if f % 2 else 0)); embers(fr, x, f, t, cols)
        hat_flight(fr, k, x, scheme, flip)
        return True
    if not robed and k < 18:
        s = 0.2 + 0.8 * k / 18; pose = 'st_charge' if k > 6 else 'st_stance'
        aura(fr, pose, x, None, f, s, flip=flip, scheme=scheme, cols=cols); M.fplace(fr, pose, x, None, flip=flip, scheme=scheme, hot=True)
        for j in range(2): ring(fr, x, FLOOR - 70, k - 8 - j * 4, cols[2 - j], life=10, sp=22)
        return True
    s = 1.0 if k < 28 else 1 - 0.6 * (k - 28) / 12
    pose = 'st_stance' if (k // 4) % 2 else 'st_stance2'
    aura(fr, pose, x, None, f, s, flip=flip, scheme=scheme, cols=cols)
    M.fplace(fr, pose, x, None, flip=flip, scheme=scheme, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.8)) if robed and k < 20 else None)
    for j in range(2): ring(fr, x, FLOOR - 70, k - 18 - j * 4, cols[2 - j], life=10, sp=22)
    return True
def aura_of(C, f):
    """the aura grows with the hit counter"""
    return 0.3 + 0.7 * min(1.0, C.hits_before(f) / 20)
def do_combo(fr, f, C, x, hot=True, clip_x=None):
    return UL.do_combo(fr, f, C, x, hot=hot, aura_s=aura_of(C, f), clip_x=clip_x)
def finisher(fr, f, F0, x, tx):
    """charged overhead staff smash, without the white flash (the assembler adds a freeze + shake)"""
    k = f - F0
    if k < 0 or k >= 32: return False, x
    if k < 20: return UL.finisher(fr, f, F0, x, tx)
    aura(fr, 'st_smash', tx, None, f, 0.9 * (1 - (k - 20) / 12)); M.fplace(fr, 'st_smash', tx, None, hot=True)
    sx, sy = tip_xy('st_smash', tx, None); age = k - 20
    hit_spark(fr, sx, FLOOR - 10, age, 2.2)
    for j in range(3): ring(fr, sx, FLOOR - 6, age - j * 3, (FIRE[3], FIRE[2], FIRE[0])[j], life=12, sp=34, sy=0.25)
    for side in (-1, 1):
        wx = sx + side * age * 40
        if age < 10: rect(fr, wx - 20, FLOOR - 8, 40, 8, FIRE[1], 220 * (1 - age / 10)); rect(fr, wx - 12, FLOOR - 14, 24, 6, FIRE[2], 200 * (1 - age / 10))
    if age < 5: burst(fr, sx, FLOOR - 10, age / 6, n=24, speed=220, cols=[(140, 120, 100), FIRE[1], FIRE[2]], seed=77, grav=260)
    return True, tx
def fly_in(fr, f, OP0, x0, x1, cols=FIRE):
    tt = (f - OP0) / 12; x = lerp(x0, x1, ease_in(tt)); hy = AIR + 8
    for k in range(3): ghost(fr, 'fly', x + 40 * (k + 1), hy, 0.4 - k * 0.12, col=cols[1])
    M.fplace(fr, 'fly', x, hy, hot=True); speed_lines(fr, x + 60, hy, f)
    if f == OP0 + 11: hit_spark(fr, x - 60, hy, 1, 1.4)
def win_or_exit(fr, f, F0, E0, x, tx):
    if f < F0 + 32: finisher(fr, f, F0, x, tx)
    elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; aura(fr, pose, tx, None, f, 0.3 * (1 - (f - F0 - 32) / max(1, E0 - F0 - 32))); M.fplace(fr, pose, tx, None, hot=True)
    else: exit_run(fr, f, E0, tx)

# ------------------------------------------------------------------ VS card
VL = 46
def vs_card(fr, k, name):
    """two banners slide in from the pipe side and the Quit side, VS pops between them, then they wipe out"""
    if k < 0 or k >= VL: return
    keep = np.array(fr)                                                         # banners come out from behind the pipe and Quit
    lay = Image.new('RGBA', fr.size, (0, 0, 0, 0)); _vs_draw(lay, k, name)
    a = np.array(lay); a[:, :190, 3] = 0; a[:, 1460:, 3] = 0
    if k >= VL - 8: a = np.array(bayer_mask(Image.fromarray(a), 1 - (k - VL + 8) / 8))
    lay = Image.fromarray(a); fr.paste(lay, (0, 0), lay)
def _vs_draw(fr, k, name):
    t_in = ease_out(min(1, k / 10)); t_out = 0
    W_ = 560; mid = 890
    lx = lerp(-W_, mid - W_ + 10, t_in) - t_out * (mid + 40); rx = lerp(FW, mid - 10, t_in) + t_out * (mid + 40)
    for (bx, y, col, edge, txt) in ((lx, 230, (22, 44, 130), (90, 200, 255), 'R64 WIZARD'), (rx, 292, (120, 22, 34), (255, 120, 60), name)):
        d = D(fr); x0, x1 = snap(bx), snap(bx + W_)
        d.rectangle([x0, y, x1, y + 54], fill=col + (235,)); d.rectangle([x0, y, x1, y + 3], fill=edge + (255,)); d.rectangle([x0, y + 51, x1, y + 54], fill=edge + (255,))
        for j in range(0, W_, 16):                                             # pixel speed stripes
            if (j // 16 + k) % 5 == 0: d.rectangle([x0 + j, y + 10, x0 + j + 7, y + 13], fill=edge + (120,))
        FA.callout(fr, txt, (x0 + x1) / 2, y + 28, s=4)
    if 10 <= k < VL - 8:
        pop = ease_back(min(1, (k - 10) / 6), 2.4)
        FA.callout(fr, 'VS', mid, 288, s=8, pop=max(0.3, pop))

# ------------------------------------------------------------------ scenes
class Scene:
    """N frames on its own clock; draw(clock) -> frame; V0 = clock to hold for the VS card; impacts = clocks;
    actors(clock) -> (wizard x, opponent x, opponent hit sprite 2x) for the early endings; props(fr, f, a) arena"""
    def __init__(self, **kw): self.__dict__.update(kw)

def arena(fr, f, aa, crowd_x=420, torches=(330, 1300)):
    if aa <= 0: return
    cr = U(FA.crowd(f, 30, seed=2)); cr = bayer_mask(cr, aa) if aa < 1 else cr; fr.paste(cr, (crowd_x, FLOOR - cr.height - 64), cr)
    for tx_ in torches:
        t_ = U(FA.torch(f + tx_)); t_ = bayer_mask(t_, aa) if aa < 1 else t_; fr.paste(t_, (tx_, FLOOR - t_.height), t_)

def goblin(robed=True, **_):
    G0 = SX - 430; B0 = 76; OP0 = 126; C, cend = build_combo(140); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 36; N = E0 + 44
    WX = G0 + 116
    def props(fr, f, a=None):
        aa = clamp((f - 6) / 10) * (1 - clamp((f - N + 22) / 10)) if a is None else a; arena(fr, f, aa)
    def draw(f):
        fr = new(pipe=False); props(fr, f)
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
        if 52 <= f < 62:                                                         # the rock
            tt = (f - 52) / 10; rx = lerp(G0 + 30, SX - 10, tt); ry = lerp(FLOOR - 80, FLOOR - (128 if robed else 110), tt) - 30 * math.sin(math.pi * tt)
            D(fr).rectangle([snap(rx), snap(ry), snap(rx) + 11, snap(ry) + 9], fill=(120, 110, 100, 255), outline=(10, 14, 42, 255))
        if g is not None: opp_place(fr, g, gx, gy, gfl or (0 <= f - IMP < 3), grot)
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 62, hit=None if robed else (62, 70))
            if robed: bonk(fr, SX - 6, FLOOR - 126, f - 62)
            elif 62 <= f < 66: hit_spark(fr, SX - 20, FLOOR - 100, f - 62, 1.2)
        elif unleash(fr, f, B0, robed): pass
        elif f < OP0: pose = 'st_stance' if (f // 6) % 2 else 'st_stance2'; aura(fr, pose, SX, None, f, 0.4); M.fplace(fr, pose, SX, None, hot=True)
        elif f < OP0 + 12: fly_in(fr, f, OP0, SX, WX)
        else:
            x = WX - min(C.hits_before(f), 14) * 2
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); flare(fr, *tip_xy(C.at(f)[0], x, None), 0)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            else: win_or_exit(fr, f, F0, E0, x, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - 8), pipe_bounce(f - IMP - 18), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, G0 - 30, 238)
        callouts(fr, f, ([('UNLEASHED!', B0 + 18, B0 + 40, 5)] if robed else []) + [('FIGHT!', B0 + 40, OP0, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 4, 4)])
        return finish(fr)
    def actors(f):
        x = WX - min(C.hits_before(f), 14) * 2 if f >= OP0 else SX
        return x, G0 - 30 - min(C.hits_before(f), 14) * 2, U(FA.goblin('hit', f))
    return Scene(name='goblin', label='GOBLIN', N=N, draw=draw, V0=26, impacts=[IMP], actors=actors, props=props,
                 combo=(OP0 + 12, IMP), robed=robed, odd=[] if robed else [62])

def golem(robed=True, odd_hit=False, **_):
    O = SX - 470; B0 = 66; OP0 = 168; C, cend = build_combo(182); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 150; parts, GW, GH = UL.golem_crumble_parts()
    HIT0 = 136                                                                   # odd hit: the shockwave reaches him
    def draw(f):
        fr = new(pipe=False)
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
        if IMP <= f < IMP + 40:
            k = f - IMP; a_ = 1 - clamp((k - 28) / 12)
            for (pi, x0, y0, vx, vy, rot) in parts:
                t = k / 10; X = O - GW / 2 + x0 + vx * min(t, 1.5); Y = FLOOR - GH + y0 + vy * t + 300 * t * t
                Y = min(Y, FLOOR - pi.height); im = pi.rotate(rot if t > 0.3 else 0, resample=Image.NEAREST)
                im = bayer_mask(im, a_) if a_ < 1 else im
                if a_ > 0: fr.paste(im, (snap(X), snap(Y)), im)
            if k < 12: smoke(fr, O, FLOOR - 30, k / 12, seed=33, n=10, spread=70, base=(150, 140, 130), dark=(90, 84, 80), size=24)
        if 42 <= f < 52:
            tt = (f - 42) / 10; px(fr, lerp(O + 50, SX - 6, tt), lerp(FLOOR - 120, FLOOR - (126 if robed else 104), tt) - 34 * math.sin(math.pi * tt), 6, (124, 116, 108))
        wave_end = HIT0 + 2 if odd_hit else 142
        if 122 <= f < wave_end:
            wx = lerp(O + 70, SX + 80, (f - 122) / 20)
            for k in range(3): rect(fr, wx - 30 + k * 20, FLOOR - 8 - (k % 2) * 6, 18, 8 + (k % 2) * 6, (164, 156, 144), 230)
            burst(fr, wx, FLOOR - 6, 0.3, n=8, speed=80, cols=((164, 156, 144), (120, 112, 104)), seed=f, grav=150)
        if 120 <= f < 124: dust(fr, O, FLOOR - 4, (f - 120) / 10, n=10, seed=4)
        if 150 <= f < 160:
            tt = (f - 150) / 10; bi = U(OP.boulder(f)); place(fr, bi, lerp(O + 40, SX - 110, tt), FLOOR - 70 + 40 * tt - 50 * math.sin(math.pi * tt))
        if 160 <= f < 168: burst(fr, SX - 110, FLOOR - 70, (f - 160) / 8, n=16, speed=140, cols=((124, 116, 108), (84, 78, 74), FIRE[1]), seed=8, grav=220)
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 52, hit=None if robed else (52, 58))
            if robed: bonk(fr, SX - 6, FLOOR - 126, f - 52)
        elif unleash(fr, f, B0, robed): pass
        elif f < 128: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 140 and not odd_hit:
            tt = (f - 128) / 12; hy = HF - 24 * math.sin(math.pi * tt); aura(fr, 'tuck', SX, hy, f, 0.4); M.fplace(fr, 'tuck', SX, hy, hot=True)
        elif odd_hit and f < 152:
            if f < HIT0: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
            else:                                                                # knocked back, shakes it off
                k = f - HIT0; back = 34 * math.sin(math.pi * min(1, k / 14))
                M.fplace(fr, 'hit' if k < 10 else 'st_stance', SX + back, None, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.7)) if k < 2 else None)
                if k < 6: hit_spark(fr, SX - 10, FLOOR - 30, k, 1.5); dust(fr, SX + back, FLOOR - 4, k / 12, n=8, seed=9, dirx=1)
                if 10 <= k: glyph(fr, '!', SX + 40, 226, (255, 70, 60))
        elif f < 156: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 168: aura(fr, 'st_thrust', SX, None, f, 0.6); M.fplace(fr, 'st_thrust', SX, None, hot=True)
        elif f < OP0 + 12: fly_in(fr, f, OP0, SX, WX)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, O + 50, sp[1], f, ((164, 156, 144), (124, 116, 108), (84, 78, 74)), f, n=10)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            else: win_or_exit(fr, f, F0, E0, x, x - 40)
        draw_pipe(fr, 0, pipe_bounce(f - E0 - 28))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, ([('UNLEASHED!', B0 + 18, B0 + 40, 5)] if robed else []) + [('FIGHT!', B0 + 40, 112, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        return finish(fr)
    def actors(f): return (WX if f >= OP0 else SX), O, U(OP.golem('hit', f))
    return Scene(name='golem', label='GOLEM', N=N, draw=draw, V0=30, impacts=[IMP] + ([HIT0] if odd_hit else []), actors=actors,
                 props=lambda fr, f, a=None: None, combo=(OP0 + 12, IMP), robed=robed)

def robot(robed=True, odd_hit=False, **_):
    O = SX - 440; B0 = 64; OP0 = 166; C, cend = build_combo(180); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 116; rng = random.Random(4)
    gears = [(OP.gear_piece(k), rng.uniform(-260, 260), rng.uniform(-220, -80), rng.choice([0, 1])) for k in range(16)]
    shur = [138 + k * 4 for k in range(5)]
    HIT0 = 127
    def draw(f):
        fr = new(pipe=False)
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
        if 120 <= f < 136:
            k = f - 120; ext = (k / 7) if k < 8 else max(0, 1 - (k - 8) / 8)
            fx0 = rx + 60; target = SX - 70 if odd_hit else SX - 140; fx = fx0 + ext * (target - fx0); fy = FLOOR - 82
            for j in range(0, int(fx - fx0), 10): px(fr, fx0 + j, fy + 4, 4, (150, 156, 168))
            place(fr, U(OP.rocket_fist()), fx + 10, fy + 14)
            if k < 8: px(fr, fx0 - 6, fy, 6, FIRE[1])
            if k == 7: hit_spark(fr, fx + 20, fy + 4, 1, 1.4)
        if IMP <= f < IMP + 40:
            k = f - IMP; a_ = 1 - clamp((k - 28) / 12)
            for j, (gi, vx, vy, sp) in enumerate(gears):
                t = k / 30; X = O + vx * t; Y = min(FLOOR - 24, FLOOR - 70 + vy * t + 500 * t * t)
                im = U(gi); im = im.rotate((k * 45 * (1 if sp else -1)) % 360 // 45 * 45, resample=Image.NEAREST)
                if a_ > 0: place(fr, bayer_mask(im, a_) if a_ < 1 else im, X, Y + im.height)
            if k < 10: smoke(fr, O, FLOOR - 50, k / 10, seed=21, n=10, spread=60, base=(130, 120, 110), dark=(70, 60, 50), size=24); burst(fr, O, FLOOR - 60, k / 10, n=20, speed=200, cols=FIRE, seed=22)
        if 38 <= f < 48:
            tt = (f - 38) / 10; place(fr, U(OP.shuriken(f)), lerp(O + 50, SX - 6, tt), lerp(FLOOR - 80, FLOOR - (120 if robed else 100), tt))
        for k, s0 in enumerate(shur):
            if s0 <= f < s0 + 10:
                tt = (f - s0) / 8; sx_ = lerp(O + 60, SX - 90, min(1, tt)); sy_ = FLOOR - 70 - 20 * (k % 3) + 10
                if tt < 1: place(fr, U(OP.shuriken(f)), sx_, sy_ + 10)
                else: hit_spark(fr, sx_, sy_, f - s0 - 8, 0.9)
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 48, hit=None if robed else (48, 54))
            if robed: bonk(fr, SX - 6, FLOOR - 126, f - 48)
        elif unleash(fr, f, B0, robed): pass
        elif f < 124: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 138 and odd_hit:
            if f < HIT0: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
            else:
                k = f - HIT0; back = 30 * math.sin(math.pi * min(1, k / 11))
                M.fplace(fr, 'hit' if k < 8 else 'st_stance', SX + back, None, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.7)) if k < 2 else None)
                if k >= 8: glyph(fr, '!', SX + 40, 226, (255, 70, 60))
        elif f < 132: aura(fr, 'st_thrust', SX, None, f, 0.6); M.fplace(fr, 'st_thrust', SX, None, hot=True)
        elif f < 138: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 162:
            pose = M.spin_pose((f - 138)); aura(fr, pose, SX, None, f, 0.5); M.fplace(fr, pose, SX, None, hot=True)
            hx_, hy_ = limb_xy('stance', 'fa', SX, None); D(fr).ellipse([snap(hx_ - 82), snap(hy_ - 82), snap(hx_ + 82), snap(hy_ + 82)], outline=(255, 200, 120, 120), width=4)
        elif f < OP0: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < OP0 + 12: fly_in(fr, f, OP0, SX, WX)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, O + 40, sp[1], f, ((200, 150, 60), (150, 156, 168)), f, n=6)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            else: win_or_exit(fr, f, F0, E0, x, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - 8), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, ([('UNLEASHED!', B0 + 18, B0 + 40, 5)] if robed else []) + [('FIGHT!', B0 + 40, 110, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        return finish(fr)
    def actors(f): return (WX if f >= OP0 else SX), O, U(OP.robot('hit', f))
    return Scene(name='robot', label='ROBOT', N=N, draw=draw, V0=24, impacts=[IMP] + ([HIT0] if odd_hit else []), actors=actors,
                 props=lambda fr, f, a=None: None, combo=(OP0 + 12, IMP), robed=robed)

def _dorb(fr, x, y, f, a=1.0, hot=False): UL._dorb(fr, x, y, f, a, hot)
def twin(robed=True, twin_wins_r1=False, **_):
    """the dark twin. twin_wins_r1: the twin takes round 1 (combo + smash, the wizard is floored), then the
    wizard gets back up for round 2 and wins. The extra round is inserted at clock R1AT."""
    O = SX - 440; B0 = 64; TB = 104; OP0 = 196; C, cend = build_combo(210); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = O + 120; orbs = [(152, 'deflect'), (164, 'deflect'), (176, 'return')]
    R1AT = 188
    def dim(fr, f): I = clamp((f - TB) / 20) * (1 - clamp((f - IMP - 20) / 20)); rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (30, 6, 40), 90 * I) if I > 0 else None
    def draw(f):
        fr = new(pipe=False); dim(fr, f)
        if 8 <= f < 20:
            r_ = 90 * (1 - (f - 8) / 12)
            for i in range(14): ang = i * 0.45 - f * 0.4; px(fr, O + r_ * math.cos(ang), FLOOR - 66 + r_ * 0.5 * math.sin(ang), 4, VIOLET[i % 4], 230)
            place(fr, bayer_mask(robed_img('dark', True), (f - 8) / 12), O, FLOOR)
        elif 20 <= f < TB:
            place(fr, robed_img('dark', True), O, FLOOR)
            if 24 <= f < 34: glyph(fr, '?', O - 50, 226, VIOLET[2])
        elif TB <= f < TB + 40:
            unleash(fr, f, TB, True, O, scheme='dark', flip=True)
        elif TB + 40 <= f < OP0 + 12:
            pose = 'st_stance'
            for (o0, kind) in orbs:
                if o0 - 4 <= f < o0 + 2: pose = 'st_thrust'
            aura(fr, pose, O, None, f, 0.35, flip=True, scheme='dark', cols=VIOLET); M.fplace(fr, pose, O, None, flip=True, scheme='dark', hot=True)
            if f in range(178, 186): M.fplace(fr, 'hit', O - 10, None, flip=True, scheme='dark', hot=True, img_fn=lambda im: tint(im, WHITE, 0.8) if f % 2 else im)
        elif OP0 + 12 <= f < IMP:
            st = C.at(f); hp = (st and st[1]) or f == OP0 + 12; nh = C.hits_before(f)
            M.fplace(fr, 'hit' if hp else 'st_stance', O - min(nh, 14) * 2, None, flip=True, scheme='dark', hot=True, img_fn=(lambda im: tint(im, WHITE, 0.8)) if hp else None)
        elif IMP <= f < IMP + 22:
            tt = (f - IMP) / 20; x = lerp(O - 40, MOUTH - 120, ease_in(tt) * 0.4 + tt * 0.6); hy = HF - 20 - 10 * math.sin(math.pi * min(1, tt))
            im, ox, oy, fy = M.rig('hit', True, 'dark', True); im = im.rotate(((f - IMP) * 60) % 360, expand=True, resample=Image.NEAREST)
            place(fr, im, x, 0, cy=hy, clip_x=MOUTH)
            for k in range(6): px(fr, x + 50 + k * 30, hy + (k * 7 + f) % 9 - 4, 4, VIOLET[k % 4], 220 - k * 35)
        if 40 <= f < 48:
            tt = (f - 40) / 6
            if tt <= 1: D(fr).line([(O + 40, FLOOR - 120), (snap(lerp(O + 40, SX - 6, tt)), FLOOR - (126 if robed else 104) + (6 if f % 2 else -6))], fill=VIOLET[1] + (255,), width=4)
        for (o0, kind) in orbs:
            k = f - o0
            if 0 <= k < 10: t = k / 10; _dorb(fr, lerp(O + 100, SX - 120, t), FLOOR - 96, f)
            elif 10 <= k < 18:
                t = (k - 10) / 8
                if kind == 'deflect': _dorb(fr, lerp(SX - 120, SX - 300, t), FLOOR - 96 - 40 * t, f, a=1 - t)
                else: _dorb(fr, lerp(SX - 120, O + 40, t), FLOOR - 90, f, hot=True)
            if k == 10: hit_spark(fr, SX - 120, FLOOR - 96, 1, 1.4)
            if kind == 'return' and k == 18: hit_spark(fr, O + 40, FLOOR - 90, 1, 1.8)
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 48, hit=None if robed else (46, 52))
            if 24 <= f < 34: glyph(fr, '?', SX + 40, 226)
            if robed: bonk(fr, SX - 6, FLOOR - 126, f - 46)
        elif unleash(fr, f, B0, robed): pass
        elif f < OP0:
            pose = 'st_stance'
            for (o0, kind) in orbs:
                if o0 + 6 <= f < o0 + 12: pose = 'st_thrust' if kind != 'deflect' or o0 == 152 else M.spin_pose(f)
            aura(fr, pose, SX, None, f, 0.4); M.fplace(fr, pose, SX, None, hot=True)
        elif f < OP0 + 12: fly_in(fr, f, OP0, SX, WX)
        else:
            x = WX - min(C.hits_before(f), 14) * 2
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); chunks(fr, sp[0], sp[1], f, VIOLET, f, n=6)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            else: win_or_exit(fr, f, F0, E0, x, x - 30)
        draw_pipe(fr, 0, min(pipe_bounce(f - IMP - 18), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, O, 238)
        callouts(fr, f, ([('UNLEASHED!', B0 + 18, B0 + 38, 5)] if robed else []) + [('MIRROR MATCH', TB + 22, TB + 42, 5), ('FIGHT!', TB + 42, TB + 56, 7),
                                                                                  ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        return finish(fr)
    # ---- round 1 goes to the twin (inserted at R1AT; both start and end standing where the base scene has them)
    C2 = Combo(); t = 14
    t = C2.add(t, ['st_thrust', 'st_thrust2'] * 2, 2, limb='staff'); t = C2.add(t, ['high', 'mid', 'low', 'mid'], 2, limb='fl')
    t = C2.add(t, ['punch', 'punch2'] * 3, 2, limb='fa'); t = C2.add(t, ['st_sweep'], 4, limb='staff'); C2END = t
    TX = SX - 150                                                                # where the twin fights from
    R1N = C2END + 92
    def r1(k):
        fr = new(pipe=False); dim(fr, R1AT)
        # the twin
        if k < 12:
            tt = k / 12; x = lerp(O, TX, ease_in(tt)); hy = AIR + 8
            for j in range(3): ghost(fr, 'fly', x - 40 * (j + 1), hy, 0.4 - j * 0.12, col=VIOLET[1], flip=True)
            M.fplace(fr, 'fly', x, hy, flip=True, scheme='dark', hot=True); speed_lines(fr, x - 120, hy, k, dirx=-1)
        elif k < C2END:
            st = C2.at(k)
            if st:
                pose, is_hit, limb, s0 = st
                aura(fr, pose, TX, None, k, 0.35 + 0.5 * min(1, C2.hits_before(k) / 14), flip=True, scheme='dark', cols=VIOLET)
                M.fplace(fr, pose, TX, None, flip=True, scheme='dark', hot=True)
                if is_hit:
                    sx_, sy_ = (tip_xy(pose, TX, None, flip=True) if limb == 'staff' else limb_xy(pose, limb, TX, None, flip=True))
                    hit_spark(fr, sx_, sy_, 1, 1.0); chunks(fr, sx_, sy_, k, VIOLET, k, n=5)
            else: aura(fr, 'st_stance', TX, None, k, 0.5, flip=True, scheme='dark', cols=VIOLET); M.fplace(fr, 'st_stance', TX, None, flip=True, scheme='dark', hot=True)
        elif k < C2END + 20:                                                     # the twin's smash
            j = k - C2END; pose = 'st_charge' if j < 8 else ('st_over' if j < 12 else 'st_smash')
            aura(fr, pose, TX, None, k, 0.8, flip=True, scheme='dark', cols=VIOLET); M.fplace(fr, pose, TX, None, flip=True, scheme='dark', hot=True)
            if j >= 12:
                age = j - 12; sx_ = TX + 70
                hit_spark(fr, sx_, FLOOR - 10, age, 2.0)
                for q in range(2): ring(fr, sx_, FLOOR - 6, age - q * 3, (VIOLET[3], VIOLET[1])[q], life=10, sp=30, sy=0.25)
        elif k < C2END + 60:                                                     # taunts while he's down
            j = k - C2END - 20; pose = 'st_win' if (j // 8) % 2 else 'st_stance'
            M.fplace(fr, pose, TX, None, flip=True, scheme='dark', hot=True)
            if j < 30: FA.callout(fr, 'HA HA!', TX, 246 - (k % 4), s=2, grad=[(240, 200, 255)] * 7)
        else:                                                                    # backs off to his spot
            j = k - C2END - 60; tt = min(1, j / 14); x = lerp(TX, O, ease_io(tt))
            M.fplace(fr, 'run1' if (j // 3) % 2 and tt < 1 else 'st_stance', x, None, flip=True, scheme='dark', hot=True)
        # the wizard
        n = C2.hits_before(k)
        if k < 14: aura(fr, 'st_stance', SX, None, k, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif k < C2END + 12:
            st = C2.at(k); hp = st is not None and st[1]; push = min(n, 12) * 2
            M.fplace(fr, 'hit', SX + push, None, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.7)) if hp else None)
        elif k < C2END + 60:                                                     # floored
            j = k - C2END - 12; im, ox, oy, fy = M.rig('hit', False, 'hero', True); im = im.rotate(-90 if j > 2 else -45, expand=True, resample=Image.NEAREST)
            place(fr, im, SX - 20 + min(j, 6) * 3, FLOOR + 2)
            if j < 6: dust(fr, SX - 10, FLOOR - 4, j / 10, n=10, seed=5, dirx=1)
            if 14 <= j: glyph(fr, "Z", SX + 30, 250 - (j % 20), WHITE, s=3) if j % 20 < 14 else None
        else:                                                                    # gets back up, fired up
            j = k - C2END - 60; s = min(1.0, j / 10)
            pose = 'st_charge' if j < 18 else 'st_stance'
            aura(fr, pose, SX, None, k, 0.6 + 0.6 * s); M.fplace(fr, pose, SX, None, hot=True)
            for q in range(2): ring(fr, SX, FLOOR - 70, j - 4 - q * 5, FIRE[2 - q], life=12, sp=26)
        draw_pipe(fr)
        if 16 <= k < C2END + 4: counter(fr, n, TX + 60, 238)
        callouts(fr, k, [('DOWN!', C2END + 16, C2END + 40, 7), ('ROUND 2', C2END + 66, C2END + 90, 6)])
        return finish(fr)
    def actors(f):
        x = WX - min(C.hits_before(f), 14) * 2 if f >= OP0 else SX
        return x, O - min(C.hits_before(f), 14) * 2, M.rig('hit', True, 'dark', True)[0]
    sc = Scene(name='twin', label='DARK TWIN', N=N, draw=draw, V0=20, impacts=[IMP], actors=actors, props=lambda fr, f, a=None: None,
               combo=(OP0 + 12, IMP), robed=robed, inserts=[])
    if twin_wins_r1: sc.inserts = [(R1AT, R1N, r1, [C2END + 12])]                  # (clock, length, draw, impacts inside)
    return sc

def car(robed=False, **_):
    """bonus stage (earned every 3 wins; he's usually in the gi by then)"""
    CX = 760; B0 = 76; C, cend = build_combo(150); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    WX = CX + 84 + 70; W_ = UL.wheel_img(); DR = UL.door_img()
    honks = [30, 44, 58]
    dmg_steps = [(132, 1), (C.steps[9][0], 2), (C.steps[16][0], 3), (C.steps[20][0], 4), (IMP, 5)]
    def draw(f):
        fr = new(); dmg = 0
        for (hf, dm) in dmg_steps:
            if f >= hf: dmg = dm
        st = C.at(f); hitnow = (st is not None and st[1]) or 0 <= f - IMP < 5 or 0 <= f - 132 < 4
        shake = (4 if f % 2 else -4) if hitnow else 0
        cx_ = CX
        if 118 <= f < 132: cx_ = CX + 120 * ease_in((f - 118) / 14)
        elif 132 <= f < 140: cx_ = CX + 120 - 120 * ease_out((f - 132) / 8)
        hop = -2 if any(0 <= f - h < 3 for h in honks) else 0
        ca = clamp((f - 8) / 8) * (1 - clamp((f - IMP - 30) / 10))
        if ca > 0:
            ci = U(FA.car(dmg, seed=dmg)); ci = bayer_mask(ci, ca) if ca < 1 else ci; place(fr, ci, cx_ + shake, FLOOR + hop)
            if any(0 <= f - h < 8 for h in honks):
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
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 62)
            if 34 <= f < 44: glyph(fr, '?', SX + 40, 226)
            if 48 <= f < 58: glyph(fr, '!', SX + 40, 226, GOLD)
        elif unleash(fr, f, B0, robed): pass
        elif f < 118: aura(fr, 'st_stance', SX, None, f, 0.4); M.fplace(fr, 'st_stance', SX, None, hot=True)
        elif f < 128:
            tt = (f - 118) / 10; x = lerp(SX, WX + 40, ease_in(tt)); aura(fr, run_pose(f), x, None, f, 0.4); M.fplace(fr, run_pose(f), x, None, hot=True)
        elif f < 140:
            aura(fr, 'st_death', WX + 40, None, f, 0.6); M.fplace(fr, 'st_death', WX + 40, None, hot=True)
            if 0 <= f - 132 < 6: hit_spark(fr, cx_ + 90, HF - 30, f - 132, 1.8)
        elif f < 150: aura(fr, 'st_stance', WX, None, f, 0.4); M.fplace(fr, 'st_stance', WX, None, hot=True)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, min(sp[0], CX + 88), sp[1], 1, 1.0); chunks(fr, CX + 70, sp[1], f, ((80, 190, 175), (200, 230, 245)), f)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            elif f < F0 + 32: finisher(fr, f, F0, x, CX + 120)
            elif f < E0: pose = 'st_win' if f < E0 - 8 else 'bow'; M.fplace(fr, pose, CX + 120, None, hot=True)
            else: exit_run(fr, f, E0, CX + 120)
        draw_pipe(fr, 0, pipe_bounce(f - E0 - 28))
        n = C.hits_before(f) + (1 if f >= 132 else 0) + (1 if f >= IMP else 0)
        if 152 <= f < IMP: counter(fr, n, CX, 238)
        callouts(fr, f, [('BONUS STAGE', 6, 28, 5)] + ([('UNLEASHED!', B0 + 18, B0 + 40, 5)] if robed else []) + [('PERFECT!', IMP + 4, IMP + 28, 7), (f'{n} HIT COMBO!', IMP + 28, E0 + 6, 4)])
        return finish(fr)
    def actors(f): return (WX if f >= 140 else SX), CX, U(FA.car(3))
    return Scene(name='car', label='BONUS CAR', N=N, draw=draw, V0=None, impacts=[132, IMP], actors=actors, props=lambda fr, f, a=None: None,
                 combo=(150, IMP), robed=robed)

SCENES = {'goblin': goblin, 'golem': golem, 'robot': robot, 'twin': twin, 'car': car}

# ------------------------------------------------------------------ endings when the job finishes early
EXIT_N = 26
def instant_exit(sc, at):
    """success mid-fight: the opponent is knocked into the pipe, he follows (under 1 s)"""
    wx, ox, img = sc.actors(at)
    def draw(k):
        fr = new(pipe=False); sc.props(fr, at + k, max(0.0, 1 - k / 8))
        if k < 16:                                                               # opponent flies into the pipe
            tt = k / 14; x = lerp(ox, MOUTH - 110, ease_in(min(1, tt)) * 0.5 + min(1, tt) * 0.5); y = FLOOR - 30 - 40 * math.sin(math.pi * min(1, tt))
            im = img.rotate((k * 60) % 360 // 45 * 45, expand=True, resample=Image.NEAREST)
            if k < 2: im = tint(im, WHITE, 0.8)
            place(fr, im, x, 0, cy=y, clip_x=MOUTH)
            for j in range(5): px(fr, x + 50 + j * 28, y + (j * 7 + k) % 9 - 4, 4, WHITE, 200 - j * 35)
        if k < 4:
            M.fplace(fr, 'st_up', wx, HF - 12, hot=True); aura(fr, 'st_up', wx, HF - 12, k, 0.6)
            if k < 3: hit_spark(fr, wx - 60, FLOOR - 110, k, 1.6)
        else:                                                                    # run and flying kick in
            j = k - 4; tt = j / 22
            if tt < 0.6: x = lerp(wx, MOUTH + 240, ease_io(tt / 0.6)); M.fplace(fr, run_pose(k), x, None, hot=True, clip_x=MOUTH)
            else: x = lerp(MOUTH + 240, MOUTH - 120, (tt - 0.6) / 0.4); hy = AIR + 6; speed_lines(fr, x + 60, hy, k); M.fplace(fr, 'fly', x, hy, hot=True, clip_x=MOUTH)
        draw_pipe(fr, 0, min(pipe_bounce(k - 15), pipe_bounce(k - 24)))
        return finish(fr)
    return [draw(k) for k in range(EXIT_N)]

BURST_N = 34
BURST = {'cancel': ((255, 214, 40), (255, 245, 170)), 'error': ((255, 64, 64), (255, 170, 160))}
def burst_rings(fr, cx, cy, k, kind, scale=1.0):
    """two rings of 8 pixel energy circles: the outer one faster and blinking; gone after 1 s"""
    col, hi = BURST[kind]
    if k >= 30: return
    a = 255 if k < 18 else 255 * (1 - (k - 18) / 12)
    for ring_i, (speed, size, blink) in enumerate(((7, 12, False), (11, 8, True))):
        if blink and (k // 2) % 2: continue
        r = (8 + k * speed) * scale
        for j in range(8):
            ang = j * math.pi / 4 + ring_i * math.pi / 8
            x = cx + r * math.cos(ang); y = cy + r * 0.6 * math.sin(ang)
            s = size
            D(fr).ellipse([snap(x - s), snap(y - s), snap(x + s), snap(y + s)], fill=col + (int(a),))
            D(fr).rectangle([snap(x - s / 3), snap(y - s / 3), snap(x - s / 3) + 3, snap(y - s / 3) + 3], fill=hi + (int(a),))
def burst_end(sc, at, kind):
    """cancel (yellow) or error (red) mid-fight: the wizard bursts into rings, the opponent dissolves"""
    wx, ox, img = sc.actors(at)
    def draw(k):
        fr = new(pipe=False); sc.props(fr, at + k, max(0.0, 1 - k / 10))
        if k < 10: place(fr, dissolve(img, 1 - k / 10, seed=3), ox, FLOOR)
        burst_rings(fr, ox, FLOOR - 60, k - 2, kind, scale=0.6)
        burst_rings(fr, wx, FLOOR - 70, k, kind)
        draw_pipe(fr)
        return finish(fr)
    return [draw(k) for k in range(BURST_N)]

# ------------------------------------------------------------------ assembling
def shake_frame(img, dx):
    """shift the scene band sideways; the pipe and the buttons stay still"""
    a = np.array(img); out = a.copy(); t, b = SAFE, BOTTOM
    band = a[t:b]; sh = np.roll(band, dx, axis=1)
    out[t:b, 190:1460] = sh[:, 190:1460]
    return Image.fromarray(out)
def hitstop(frames, impacts, freeze=3, shake=(8, -6, 4, -2)):
    """big impacts: hold the frame for a beat, then shake (no white flash)"""
    out = []; imp = set(impacts); sh_left = []
    for i, fr in enumerate(frames):
        if sh_left: fr = shake_frame(fr, sh_left.pop(0))
        out.append(fr)
        if i in imp:
            out.extend([fr] * freeze); sh_left = list(shake)
    return out
def assemble(sc, vs=True, end=None):
    """frames for a scene: base clock with the VS card held at V0 and any inserted segments; end=(kind, at clock)
    cuts it short with an early ending ('exit', 'cancel', 'error')."""
    frames = []; impacts = []
    ins = {c: (n, fn, imps) for (c, n, fn, imps) in getattr(sc, 'inserts', [])}
    stop = sc.N if end is None else end[1]
    for c in range(stop):
        if vs and sc.V0 is not None and c == sc.V0:
            base = sc.draw(c)
            for k in range(VL): fr = base.copy(); vs_card(fr, k, sc.label); frames.append(finish(fr))
        if c in ins:
            n, fn, imps = ins[c]
            for k in range(n):
                if k in imps: impacts.append(len(frames))
                frames.append(fn(k))
        if c in sc.impacts: impacts.append(len(frames))
        frames.append(sc.draw(c))
    if end is not None:
        kind, at = end
        frames += instant_exit(sc, at) if kind == 'exit' else burst_end(sc, at, kind)
    return hitstop(frames, impacts)

def render(name, **kw):
    vs = kw.pop('vs', True); end = kw.pop('end', None)
    return assemble(SCENES[name](**kw), vs=vs, end=end)

if __name__ == '__main__':
    todo = sys.argv[1:] or ['goblin']
    for t in todo:
        name, *flags = t.split(':')
        kw = {f: True for f in flags if f in ('odd_hit', 'twin_wins_r1')}
        kw['robed'] = 'gi' not in flags
        frames = render(name, **kw)
        out = write_gif(frames, f'fight_{t.replace(":", "_")}', outdir=os.path.join(HERE, 'out', 'fights'))
        print(t, len(frames), out, flush=True)
