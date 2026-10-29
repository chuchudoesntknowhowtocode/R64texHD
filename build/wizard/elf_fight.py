"""Machine elf opponent (Psychedelic on). Light-touch arena: sacred geometry only around the elf.
Moves: a hexagram shield the wizard has to smash through, reality warps (the elf teleports between small
kaleidoscope portals), a clone swarm on a hexagram that he spin-staffs down. K.O.: the elf unravels into a
rainbow double helix that pours into the pipe."""
import math, random
import numpy as np
from PIL import Image
from fights import *
import fights as FT
import elf2 as E
from geo import Geo, rb

EY = FLOOR - 74                                                              # elf centre height
def elf_img(f, form='radiant', h0=0.0, scale=0.56):
    return E.elf2(f, form, h0, scale)
def place_elf(fr, f, x, form='radiant', h0=0.0, scale=0.56, alpha=1.0, flash=False, dy=0):
    im = elf_img(f, form, h0, scale)
    if alpha < 1: im = bayer_mask(im, alpha)
    if flash: im = tint(im, WHITE, 0.8)
    place(fr, im, x, 0, cy=EY + dy)
def halo(g, f, x, al, R=58, prog=1.0, h=0.0):
    E.sacred_ring(g, x, EY, R, prog, f, al=al, h=h)

def elf(robed=True, **_):
    O = SX - 470; B0 = 66
    SH0, SH1 = 112, 172                                                      # shield
    P = [O - 120, O - 300, O - 180]                                          # warp portals
    WP = [(178, P[0]), (196, P[1]), (214, P[2])]                             # (appears at, x)
    CL0 = 232                                                                # clones
    OP0 = 280; C, cend = build_combo(OP0 + 12); F0 = cend + 3; IMP = F0 + 20; E0 = IMP + 40; N = E0 + 44
    EX = P[2]; WX = EX + 124
    def elf_x(f):
        if f < 172: return O
        for at, x in WP[::-1]:
            if f >= at: return x
        return O
    def draw(f):
        fr = new(pipe=False); gb = Geo(); gf = Geo()
        ex = elf_x(f)
        # ---- light-touch geometry around the elf
        if 8 <= f < IMP:
            al = 120 * clamp((f - 8) / 20) if f < SH0 else 70
            halo(gb, f, ex, al, R=64, prog=clamp((f - 8) / 22), h=f * 0.01)
        # ---- portals (warps)
        for at, x in WP:
            k = f - at
            if -6 <= k < 12:
                R = 70 * math.sin(math.pi * clamp((k + 6) / 18))
                fr = E.kaleido(fr, x, EY, R, f * 0.08, n=6, ring_col=rb(f * 0.03))
        gb.render(fr)
        # ---- the elf
        show = 8 <= f < IMP + 2
        if show:
            alpha = clamp((f - 16) / 12) if f < 28 else 1.0
            form = 'radiant'; flash = False; dy = 0
            if 172 <= f < WP[0][0] or any(at - 6 <= f < at for at, _ in WP[1:]): alpha = 1 - clamp((f - (max([at for at, _ in WP if at <= f + 6] + [172]) - 6)) / 6)
            for at, x in WP:
                if at <= f < at + 6: alpha = clamp((f - at) / 6)
            if CL0 <= f < CL0 + 40: form = 'orb'
            if OP0 + 12 <= f < IMP:
                st = C.at(f); flash = (st is not None and st[1]) or f == OP0 + 12; form = 'crystal' if f >= F0 else 'radiant'
            if f >= IMP: alpha = 0
            if SH0 + 12 <= f < SH0 + 20 and f % 2: flash = True
            if 220 <= f < 226: flash = True                                   # flying kick connects
            if alpha > 0: place_elf(fr, f, ex, form, 0.0, alpha=alpha, flash=flash, dy=dy)
        if 34 <= f < 60: E.chatter(fr, ex - 30, EY - 20, f, 34, n=3)       # glyph-speech provoking him
        # ---- hexagram shield
        if SH0 <= f < 162:
            hp = 1.0 if f < 132 else (1.0 - 0.25 * sum(1 for t in (136, 144, 152) if f >= t))
            E.sacred_ring(gf, ex + 70, EY, 66, 0.62, f, al=230 * hp, h=0.55)
            gf.poly([(ex + 70 + 52 * math.cos(j * 2.094 + f * 0.05), EY + 52 * math.sin(j * 2.094 + f * 0.05)) for j in range(3)], rb(f * 0.02), 255 * hp)
            gf.poly([(ex + 70 + 52 * math.cos(j * 2.094 + 1.047 - f * 0.05), EY + 52 * math.sin(j * 2.094 + 1.047 - f * 0.05)) for j in range(3)], rb(f * 0.02 + 0.5), 255 * hp)
        if 160 <= f < 172:                                                    # shield shatters
            burst(fr, ex + 70, EY, (f - 160) / 12, n=34, speed=210, cols=[rb(j / 6) for j in range(6)], seed=61, grav=120)
        # ---- clone swarm
        if CL0 <= f < CL0 + 40:
            k = f - CL0; cx0 = EX + 60
            pts = []
            for j in range(6):
                ang = j * math.pi / 3 + k * 0.05; r_ = 40 + min(1, k / 8) * 150
                pts.append((cx0 + r_ * math.cos(ang), EY + r_ * 0.32 * math.sin(ang)))
            gf.poly([pts[0], pts[2], pts[4]], rb(f * 0.03), 200); gf.poly([pts[1], pts[3], pts[5]], rb(f * 0.03 + 0.5), 200)
            for j, (x, y) in enumerate(pts):
                pop = CL0 + 12 + j * 4
                if f < pop: place(fr, E.hue_img(elf_img(f + j * 9, 'radiant', 0.0, 0.32), j * 60), x, 0, cy=y)
                elif f < pop + 6: burst(fr, x, y, (f - pop) / 6, n=14, speed=120, cols=[rb(j / 6 + q * 0.1) for q in range(4)], seed=j)
        gf.render(fr)
        # ---- the wizard
        if intro(fr, f, robed): pass
        elif f < B0:
            waiting(fr, f, robed, 56, hit=None if robed else (56, 62))
            if robed: bonk(fr, SX - 6, FLOOR - 126, f - 56)
        elif unleash(fr, f, B0, robed): pass
        elif f < SH0: pose = 'st_stance' if (f // 6) % 2 else 'st_stance2'; aura(fr, pose, SX, None, f, 0.4); M.fplace(fr, pose, SX, None, hot=True)
        elif f < SH0 + 12: fly_in(fr, f, SH0, SX, O + 160)
        elif f < SH0 + 22:                                                    # bounces off the shield
            k = f - SH0 - 12; x = O + 160 + 90 * ease_out(k / 10)
            M.fplace(fr, 'hit', x, None, hot=True, img_fn=(lambda im: tint(im, WHITE, 0.6)) if k < 2 else None)
            if k < 5: hit_spark(fr, O + 120, EY, k, 1.5)
        elif f < 134: aura(fr, 'st_stance', O + 250, None, f, 0.5); M.fplace(fr, 'st_stance', O + 250, None, hot=True); glyph(fr, '!', O + 290, 226, (255, 70, 60)) if f < 130 else None
        elif f < 160:                                                         # three staff strikes crack it
            k = f - 134; x = O + 180; pose = 'st_thrust' if k % 8 < 4 else 'st_stance'
            aura(fr, pose, x, None, f, 0.6); M.fplace(fr, pose, x, None, hot=True)
            if k % 8 == 2: hit_spark(fr, O + 132, EY, 1, 1.6)
        elif f < 172: aura(fr, 'st_win', O + 180, None, f, 0.5); M.fplace(fr, 'st_win', O + 180, None, hot=True)
        elif f < 222:                                                         # chases the elf through the portals
            xs = [O + 180] + [x + 150 for _, x in WP]; xx = xs[0]; running = False
            for i_, (at, x) in enumerate(WP):
                if f >= at + 14: xx = xs[i_ + 1]
                elif f >= at + 6: xx = lerp(xs[i_], xs[i_ + 1], ease_io((f - at - 6) / 8)); running = True
            pose = run_pose(f) if running else 'st_stance'
            aura(fr, pose, xx, None, f, 0.4); M.fplace(fr, pose, xx, None, hot=True)
            if not running and any(at - 6 <= f < at for at, _ in WP): glyph(fr, '?', xx + 40, 226)
        elif f < CL0:                                                         # flying kick lands
            aura(fr, 'high', WX, None, f, 0.6); M.fplace(fr, 'high', WX, None, hot=True)
            if f < 226: hit_spark(fr, EX + 40, EY, f - 222, 1.4)
        elif f < CL0 + 40:                                                    # spin-staff through the clones
            pose = M.spin_pose(f - CL0) if f >= CL0 + 10 else 'st_stance'
            aura(fr, pose, WX, None, f, 0.6); M.fplace(fr, pose, WX, None, hot=True)
            if f >= CL0 + 10:
                hx_, hy_ = limb_xy('stance', 'fa', WX, None); D(fr).ellipse([snap(hx_ - 82), snap(hy_ - 82), snap(hx_ + 82), snap(hy_ + 82)], outline=(255, 200, 120, 120), width=4)
        elif f < OP0: aura(fr, 'st_stance', WX, None, f, 0.4); M.fplace(fr, 'st_stance', WX, None, hot=True)
        elif f < OP0 + 12: aura(fr, 'st_charge', WX, None, f, 0.6); M.fplace(fr, 'st_charge', WX, None, hot=True)
        else:
            x = WX
            ok, is_hit, sp = do_combo(fr, f, C, x)
            if ok:
                if is_hit: hit_spark(fr, sp[0], sp[1], 1, 1.0); burst(fr, sp[0], sp[1], 0.2, n=6, speed=100, cols=[rb(f * 0.05 + q / 4) for q in range(4)], seed=f)
            elif f < F0: aura(fr, 'st_stance', x, None, f, aura_of(C, f)); M.fplace(fr, 'st_stance', x, None, hot=True)
            else: win_or_exit(fr, f, F0, E0, x, x - 30)
        # ---- K.O.: rainbow double helix into the pipe
        if IMP <= f < IMP + 30:
            k = f - IMP; head = lerp(EX, MOUTH - 20, ease_in(min(1, k / 18))); tail = lerp(EX, MOUTH - 20, ease_in(max(0, (k - 10) / 18)))
            n = 60
            for j in range(n):
                t = j / (n - 1); x = lerp(tail, head, t)
                if x < MOUTH - 4: continue
                for s in (0, math.pi):
                    y = EY + 26 * math.sin(t * 9 + k * 0.6 + s)
                    px(fr, x, y, 6 if j % 3 else 4, rb(t + k * 0.03 + s / 6.283), 255)
                if j % 6 == 0: px(fr, x, EY + 26 * math.sin(t * 9 + k * 0.6), 2, WHITE, 200)
            if k < 8: place_elf(fr, f, EX, 'crystal', scale=0.56 * (1 - k / 8) + 0.05, alpha=1 - k / 8)
        draw_pipe(fr, 0, min(pipe_bounce(f - IMP - 18), pipe_bounce(f - E0 - 28)))
        n = C.hits_before(f) + (1 if f >= OP0 + 12 else 0) + (1 if f >= IMP else 0)
        if OP0 + 14 <= f < IMP: counter(fr, n, EX, 238)
        callouts(fr, f, ([('UNLEASHED!', B0 + 18, B0 + 40, 5)] if robed else []) + [('FIGHT!', B0 + 40, SH0, 7), ('K.O.', IMP + 2, IMP + 26, 8), (f'{n} HIT COMBO!', IMP + 26, E0 + 6, 4)])
        return finish(fr)
    def actors(f):
        return (WX if f >= CL0 else SX), elf_x(f), elf_img(f)
    return Scene(C=C, B0=B0, name='elf', label='MACHINE ELF', N=N, draw=draw, V0=36, impacts=[IMP, SH0 + 12, 160], actors=actors,
                 props=lambda fr, f, a=None: None, combo=(OP0 + 12, IMP), robed=robed)

FT.SCENES['elf'] = elf
