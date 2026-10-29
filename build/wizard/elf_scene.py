"""Machine Elf: a self-transforming jewelled being that warps reality and breaks into the pipe."""
import sys, math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from lib import *
import lib
import geo as GE
from geo import Geo, rb
from props import outline
from scenes3 import trip, hue_region, wave_region, hue_rot_arr
HERE = os.path.dirname(os.path.abspath(__file__))
GY = 306

# ------------------------------------------------------------- the elf (1x pixel art)
def C(c, a=255): return tuple(int(v) for v in c) + (a,)
def _face(d, cx, cy, f, s=1.0, blink=False):
    d.ellipse([cx - 9 * s, cy - 8 * s, cx + 9 * s, cy + 8 * s], fill=C((246, 236, 255)))
    for k, ex in enumerate((-5, 0, 5)):                                      # three eyes
        ey = cy - 2 * s - (2 if k == 1 else 0) * s
        if blink and k != 1: d.line([(cx + ex * s - 1, ey), (cx + ex * s + 1, ey)], fill=C((20, 10, 40)))
        else:
            d.rectangle([cx + ex * s - 1, ey - 1, cx + ex * s + 1, ey + 1], fill=C(rb(f * 0.03 + k * 0.33)))
            d.point((cx + ex * s, ey), fill=C((10, 6, 20)))
    w = 6 * s; d.chord([cx - w, cy, cx + w, cy + 6 * s], 0, 180, fill=C((60, 10, 60)))   # huge grin
    for t in range(-4, 5, 2): d.point((cx + t * s, cy + 1 * s), fill=C((255, 255, 255)))
    d.point((cx - 7 * s, cy + 2 * s), fill=C((255, 120, 170))); d.point((cx + 7 * s, cy + 2 * s), fill=C((255, 120, 170)))
def elf_img(f, form='jester', h0=0.0):
    im = Image.new('RGBA', (60, 66), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = 30
    h = h0 + f * 0.02; blink = (f % 47) < 2
    if form == 'jester':
        bob = int(2 * math.sin(f * 0.4))
        for k, (ang, ln) in enumerate(((-150, 20), (-90, 18), (-30, 20))):       # three floppy hat points with bells
            a = math.radians(ang + 10 * math.sin(f * 0.3 + k)); tip = (cx + ln * math.cos(a), 14 + bob + ln * math.sin(a))
            d.polygon([(cx - 10 + k * 7, 18 + bob), (cx - 7 + k * 7, 13 + bob), tip, (cx - 3 + k * 7, 13 + bob), (cx - 1 + k * 7, 18 + bob)], fill=C(rb(h + k * 0.33)))
            d.ellipse([tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2], fill=C((255, 215, 70)))
        d.rectangle([cx - 10, 15 + bob, cx + 10, 19 + bob], fill=C(rb(h + 0.5, 0.6)))
        _face(d, cx, 27 + bob, f, 1.0, blink)
        body = [(cx, 35 + bob), (cx + 13, 46 + bob), (cx, 60 + bob), (cx - 13, 46 + bob)]      # faceted gem body
        d.polygon(body, fill=C(rb(h + 0.1)))
        for k in range(4):
            p0 = body[k]; p1 = body[(k + 1) % 4]; d.polygon([(cx, 47 + bob), p0, p1], fill=C(rb(h + 0.1 + k * 0.12 + f * 0.01, 0.8, 0.95)))
        d.polygon([(cx, 42 + bob), (cx + 4, 47 + bob), (cx, 52 + bob), (cx - 4, 47 + bob)], fill=C((255, 255, 255)))
        arm = int(4 * math.sin(f * 0.5))
        d.line([(cx - 11, 42 + bob), (cx - 19, 36 + bob - arm)], fill=C(rb(h + 0.6)), width=2); d.line([(cx + 11, 42 + bob), (cx + 19, 36 + bob + arm)], fill=C(rb(h + 0.6)), width=2)
        d.ellipse([cx - 22, 33 + bob - arm, cx - 17, 38 + bob - arm], fill=C((246, 236, 255))); d.ellipse([cx + 17, 33 + bob + arm, cx + 22, 38 + bob + arm], fill=C((246, 236, 255)))
        for sx in (-1, 1):                                                            # curly toes
            d.arc([cx + sx * 7 - 4, 57 + bob, cx + sx * 7 + 4, 65], 0, 300, fill=C(rb(h + 0.8)), width=2)
    elif form == 'ball':                                                              # self-dribbling faceted ball
        r = 20; cy = 40
        for k in range(10):
            a0 = k * 36 + f * 9; d.pieslice([cx - r, cy - r, cx + r, cy + r], a0, a0 + 36, fill=C(rb(h + k * 0.1)))
        d.ellipse([cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5], outline=C((255, 255, 255), 200))
        _face(d, cx, cy, f, 0.8, blink)
    elif form == 'star':
        pts = []
        for k in range(16):
            rr = 26 if k % 2 == 0 else 12; a = math.radians(k * 22.5 + f * 8); pts.append((cx + rr * math.cos(a), 36 + rr * math.sin(a)))
        d.polygon(pts, fill=C(rb(h + 0.3)))
        for k in range(0, 16, 2):
            a = math.radians(k * 22.5 + f * 8); d.line([(cx, 36), (cx + 26 * math.cos(a), 36 + 26 * math.sin(a))], fill=C(rb(h + k * 0.06, 0.6)))
        _face(d, cx, 36, f, 0.9, blink)
    a = np.array(im); a[..., 3] = np.where(a[..., 3] > 100, 255, 0); im = Image.fromarray(a)
    return outline(im.crop(im.getbbox()))
def elf(f, form='jester', h0=0.0): return U(elf_img(f, form, h0))

# ------------------------------------------------------------- glyph-language chatter
GLYPHS = [["101", "010", "101"], ["111", "101", "111"], ["010", "111", "010"], ["110", "011", "110"], ["100", "111", "001"],
          ["011", "100", "011"], ["111", "010", "111"], ["101", "111", "010"], ["001", "011", "111"], ["110", "101", "011"]]
def chatter(fr, x, y, f, t0, n=3, a=255, spread=1.0):
    for s in range(n):
        for j in range(9):
            age = (f - t0) - j * 2 - s * 5
            if age < 0 or age > 34: continue
            ang = -2.4 + s * 0.9 * spread + 0.15 * math.sin(age * 0.3 + s)
            dist = 30 + age * 9; gx = x + dist * math.cos(ang); gy = y + dist * 0.55 * math.sin(ang) - age * 0.6
            g = GLYPHS[(s * 7 + j * 3 + f // 6) % len(GLYPHS)]; col = rb(s * 0.3 + j * 0.08 + f * 0.02)
            for r, row in enumerate(g):
                for c, v in enumerate(row):
                    if v == '1': px(fr, gx + c * 4, gy + r * 4, 4, col, a * (1 - age / 34))

# ------------------------------------------------------------- reality distortions (bar region only)
def region(fr): a = np.array(fr); return a, a[SAFE:BOTTOM]
def scramble(fr, amt, f, tile=32):
    if amt <= 0.02: return fr
    a = np.array(fr); reg = a[SAFE:BOTTOM].copy(); out = reg.copy(); H, W = reg.shape[:2]; rng = random.Random(f // 3)
    for ty in range(0, H - tile + 1, tile):
        for tx in range(0, W - tile + 1, tile):
            if rng.random() < amt * 0.35:
                dx = rng.choice([-2, -1, 1, 2]) * tile; sx = min(max(0, tx + dx), W - tile)
                out[ty:ty + tile, tx:tx + tile] = reg[ty:ty + tile, sx:sx + tile]
                if rng.random() < 0.3: out[ty:ty + tile, tx:tx + tile] = out[ty:ty + tile, tx:tx + tile][::-1]
    a[SAFE:BOTTOM] = out; return Image.fromarray(a)
def mirror(fr, cx, amt):
    if amt <= 0: return fr
    a = np.array(fr); reg = a[SAFE:BOTTOM]; cx = snap(cx); w = int(min(cx, FW - cx) * amt) // 2 * 2
    if w < 4: return fr
    reg[:, cx - w:cx] = reg[:, cx:cx + w][:, ::-1]; return Image.fromarray(a)
def chroma(fr, amt):
    if amt <= 0.05: return fr
    a = np.array(fr); reg = a[SAFE:BOTTOM].copy(); s = int(6 * amt) // 2 * 2
    if s == 0: return fr
    reg[:, s:, 0] = a[SAFE:BOTTOM, :-s, 0]; reg[:, :-s, 2] = a[SAFE:BOTTOM, s:, 2]; a[SAFE:BOTTOM] = reg; return Image.fromarray(a)
def swirl_bg(fr, I, f):
    if I <= 0: return
    g = Geo(); GE.hex_tunnel(g, MOUTH + 20, GY, f * 0.18, 70 * I, h=f * 0.01, twist=0.35); g.render(fr)

# ------------------------------------------------------------- the scene
def elf_scene():
    out = []; N = 300; X0 = SX
    for f in range(N):
        I = trip(f, N, a=20, b=70, tail=30)
        fr = new(pipe=False)
        fr = hue_region(fr, f * 5, I * 0.35); rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (6, 2, 16), 110 * I)
        swirl_bg(fr, I * (0.5 if f < 200 else 1.0), f)
        g = Geo(); g2 = Geo()
        # ---------------- elf position & form
        ex, ey, form, show = X0, FLOOR, 'jester', True
        if f < 6: show = False
        elif f < 196:
            if 104 <= f < 152:                                                     # transforms while wandering left
                t = (f - 104) / 48; ex = lerp(X0, 940, ease_io(t))
                form = 'ball' if (f - 104) % 24 < 12 else 'star'
                ey = FLOOR - abs(math.sin((f - 104) * 0.4)) * 24 if form == 'ball' else FLOOR - 10
            elif 152 <= f < 196: ex = 940
        else: ex = 940
        # ---------------- merkaba intro (as in the reference)
        mx, ms = X0, 86.0
        spin = f * 0.05 + max(0, f - 176) ** 2 * 0.003
        if 6 <= f < 40: GE.merkaba(g, X0, GY, ms, spin, f * 0.01, 255 * (1 - clamp((f - 32) / 8)), prog=clamp((f - 6) / 22))
        if 176 <= f < 214:                                                        # merkaba re-forms around it, spins up, launches
            mx = 940 if f < 200 else lerp(940, MOUTH + 50, ease_in((f - 200) / 14)); ms = 80 if f < 200 else lerp(80, 50, (f - 200) / 14)
            GE.merkaba(g2, mx, GY, ms, spin, f * 0.01, 255, prog=clamp((f - 176) / 10))
            if f < 200:
                for k in range(3):
                    age = (f - 180 - k * 6) % 18; g.circle(mx, GY, 30 + age * 6, rb(k / 3 + f * 0.04), 255 * (1 - age / 18) * clamp((f - 180) / 6))
            else:
                t = (f - 200) / 14
                for k in range(7): rect(fr, mx + 60, GY - 42 + k * 12, 940 + 60 - mx, 10, rb(k / 7 + f * 0.04), 150 * min(1, t * 2))
        # ---------------- the self-transforming gem it shows off (60..104)
        if 60 <= f < 104:
            sel = ((f - 60) // 9) % 5; V, E = GE.SOLIDS[sel]; gx, gyy = X0 - 70, FLOOR - 120 + 4 * math.sin(f * 0.3)
            GE.wire(g2, V, E, gx, gyy, 14 + 2 * math.sin(f * 0.5), f * 0.11, f * 0.09, 0.3, f * 0.02, 255)
            for k in range(6):
                ang = f * 0.2 + k * 1.047; g2.dot(gx + 30 * math.cos(ang), gyy + 30 * math.sin(ang), rb(k / 6 + f * 0.03), 230, 2)
            if 74 <= f < 104:                                                        # fractal bloom behind it
                q = ease_out((f - 74) / 12) * (1 - clamp((f - 96) / 8)); GE.flower_of_life(g, gx, GY, 24 * q, 1, f * 0.015, 200 * q, rot=f * 0.03)
        # ---------------- clones ring (152..176)
        clones = []
        if 152 <= f < 178:
            r = 120 * math.sin(math.pi * (f - 152) / 26)
            for k in range(5):
                ang = (f - 152) * 0.25 + k * 1.2566; clones.append((940 + r * math.cos(ang), FLOOR - 10 * abs(math.sin(ang)), k / 5))
        # ---------------- pipe: shatters on impact, mandala, reassembles
        IMP = 214
        s = 0
        if IMP <= f < IMP + 10: s = ease_out((f - IMP) / 8)
        elif IMP + 10 <= f < 246: s = 1
        elif 246 <= f < 272: s = 1 - ease_io((f - 246) / 24)
        g.render(fr)
        # ---------------- draw elf / clones
        for (cx_, cy_, hh) in clones: place(fr, tint(elf(f, 'jester', hh), rb(hh), 0.35, 0.8), cx_, cy_)
        if show and f < IMP:
            im = elf(f, form)
            if f < 22: im = bayer_mask(tint(im, WHITE, 0.6 * (1 - (f - 6) / 16)), (f - 6) / 14)
            if 140 <= f < 152 and f % 4 < 2:                                         # dissolves into a pixel swarm
                im = dissolve(im, 0.35, seed=f)
                burst(fr, ex, ey - 50, ((f - 140) % 4) / 4, n=16, speed=80, cols=[rb(k / 8 + f * 0.02) for k in range(8)], seed=f)
            if f >= 200:
                t = (f - 200) / 14; im = elf(f, 'star'); sc = round(lerp(1, 0.55, t), 2)
                im = im.resize((max(2, int(im.width * sc) // 2 * 2), max(2, int(im.height * sc) // 2 * 2)), Image.NEAREST)
                place(fr, im, mx, 0, cy=GY, clip_x=MOUTH)
            elif 176 <= f < 200: place(fr, tint(im, WHITE, 0.25 * (f - 176) / 24), 940, 0, cy=GY + 6)
            else: place(fr, im, ex, ey)
            if (34 <= f < 62) or (86 <= f < 104) or (156 <= f < 176):
                t0 = 34 if f < 62 else (86 if f < 104 else 156)
                chatter(fr, ex - 4, ey - 70, f, t0, n=3, a=255)
        g2.render(fr)
        if not GE.draw_shards(fr, s, tintf=lambda im: hue_img(im, f * 15)): draw_pipe(fr, 0, pipe_bounce(f - 272))
        # mandala bloom where the pipe was
        if IMP + 2 <= f < 262:
            q = ease_out((f - IMP - 2) / 14) * (1 - ease_in(clamp((f - 240) / 22))); gm = Geo(); PCX = PIPE_HOME[0] + PIPE.width // 2
            for i in range(24):
                ang = i / 24 * 6.283 - f * 0.03; gm.line((PCX, GY), (PCX + 600 * q * math.cos(ang), GY + 600 * q * math.sin(ang)), rb(i / 24 + f * 0.02), 110 * q, glow=False)
            GE.sri_yantra(gm, PCX, GY, 78 * q, 1, f * 0.02, 255 * q, rot=f * 0.03)
            GE.flower_of_life(gm, PCX, GY, 17 * q, 1, f * 0.02 + 0.5, 200 * q, rot=-f * 0.04, outer=False)
            for k in range(4):                                                      # tiny elves pop out of the mandala
                ang = f * 0.12 + k * 1.57; place(fr, U(elf_img(f + k * 9, 'jester', k / 4)).resize((24, 28), Image.NEAREST), PCX + 70 * q * math.cos(ang), GY + 34 * q * math.sin(ang) + 14) if q > 0.5 else None
            gm.render(fr)
            if f >= IMP + 6 and f < 250: chatter(fr, PCX + 20, GY - 20, f, IMP + 6, n=4, a=255 * q, spread=1.4)
        if IMP <= f < IMP + 6: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [230, 190, 140, 90, 50, 20][f - IMP])
        if IMP <= f < IMP + 20: burst(fr, PIPE_HOME[0] + 120, GY, (f - IMP) / 20, n=30, speed=260, cols=[rb(k / 10) for k in range(10)], seed=13, s=6)
        # ---------------- reality distortion (whole bar)
        wav = I * (0.4 + 0.6 * clamp((f - 60) / 40)) * (1.6 if IMP <= f < 240 else 1.0)
        fr = wave_region(fr, 18 * wav, 0.07, f * 0.5)
        if 112 <= f < 150 and (f // 3) % 3 != 0: fr = scramble(fr, I * 0.8, f)
        if 120 <= f < 136: fr = mirror(fr, ex, I * math.sin(math.pi * (f - 120) / 16))
        if IMP - 4 <= f < IMP + 30: fr = chroma(fr, I * (1 - clamp((f - IMP) / 30)))
        if 62 <= f < 100 and f % 12 < 2: fr = chroma(fr, I)
        out.append(finish(fr))
    return out
def hue_img(img, deg):
    a = np.array(img); a[..., :3] = hue_rot_arr(a[..., :3].astype(float), deg).astype(np.uint8); return Image.fromarray(a)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        ims = [elf(f, form) for form in ('jester', 'ball', 'star') for f in (0, 10)]
        W = sum(i.width + 10 for i in ims); H = max(i.height for i in ims)
        o = Image.new('RGBA', (W, H + 4), (25, 15, 40, 255)); x = 0
        for i in ims: o.alpha_composite(i, (x, H - i.height)); x += i.width + 10
        o.save(os.path.join(HERE, 'elf_preview.png')); sys.exit()
    frames = elf_scene()
    picks = np.linspace(0, len(frames) - 1, 20).astype(int)
    sheet = Image.new('RGB', (890 * 2, 98 * 10))
    for k, p in enumerate(picks): sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
    sheet.save(os.path.join(HERE, 'sheet_elf.png'))
    print(len(frames), write_gif(frames, '42_dmt_machine_elf_reality_warp', outdir=os.path.join(HERE, 'out')))
