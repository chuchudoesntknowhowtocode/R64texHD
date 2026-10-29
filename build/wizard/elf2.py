"""Machine Elf v2: original radiant, many-eyed jewelled being + sacred-geometry reality warping."""
import sys, math, random, os
import numpy as np
from PIL import Image, ImageDraw
from lib import *
import lib
import geo as GE
from geo import Geo, rb
from props import outline
from scenes3 import trip, hue_region, hue_rot_arr
from elf_scene import chatter, GLYPHS
HERE = os.path.dirname(os.path.abspath(__file__))
GY = 306
IRIS = [(40, 110, 255), (30, 220, 120), (235, 60, 225), (20, 220, 245), (255, 200, 40)]
def C(c, a=255): return tuple(int(v) for v in c) + (int(a),)

# ================================================================= sprite (1x)
def _eye(d, x, y, w, col, blink=False, angle=0.0):
    if blink: d.line([(x - w, y), (x + w, y)], fill=C((20, 8, 30))); return
    h = max(1, w * 0.6)
    d.polygon([(x - w - 1, y), (x - w * 0.4, y - h), (x + w * 0.4, y - h), (x + w + 1, y), (x + w * 0.4, y + h), (x - w * 0.4, y + h)], fill=C((10, 6, 24)))
    d.polygon([(x - w, y), (x - w * 0.4, y - h + 1), (x + w * 0.4, y - h + 1), (x + w, y), (x + w * 0.4, y + h - 1), (x - w * 0.4, y + h - 1)], fill=C((250, 248, 255)))
    ir = max(1, w * 0.5); d.ellipse([x - ir, y - ir, x + ir, y + ir], fill=C(col)); d.point((x, y), fill=C((5, 5, 10))); d.point((x - 1, y - 1), fill=C((255, 255, 255)))
def _tendril(d, cx, cy, ang, r0, L, wid, f, k, h):
    left, right = [], []
    for i in range(9):
        t = i / 8; r = r0 + L * t; off = math.sin(t * 3.2 + f * 0.18 + k) * 4 * t
        a = ang + off / max(r, 1); w = wid * (1 - t) + 0.6
        x, y = cx + r * math.cos(a), cy + r * math.sin(a); nx, ny = -math.sin(a), math.cos(a)
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    d.polygon(left + right[::-1], fill=C(rb(h, 0.85, 1.0)))
    inner = [(cx + (r0 + L * t * 0.85) * math.cos(ang), cy + (r0 + L * t * 0.85) * math.sin(ang)) for t in (0.1, 0.7)]
    d.line(inner, fill=C(rb(h + 0.08, 0.35, 1.0)))
    t = 0.78; r = r0 + L * t; off = math.sin(t * 3.2 + f * 0.18 + k) * 4 * t; a = ang + off / r
    return cx + r * math.cos(a), cy + r * math.sin(a)
def _gem_face(d, cx, cy, f, h, s=1.0):
    R = 13 * s
    for k in range(8):                                                         # faceted gem body/head
        a0 = k * 45 + f * 4; d.pieslice([cx - R, cy - R * 1.25, cx + R, cy + R * 1.25], a0, a0 + 45, fill=C(rb(h + k * 0.125, 0.75, 1.0)))
    for sx in (-1, 1): d.polygon([(cx + sx * 8 * s, cy - 2 * s), (cx + sx * 17 * s, cy - 8 * s), (cx + sx * 10 * s, cy + 3 * s)], fill=C((250, 236, 255)))  # pointy ears
    d.ellipse([cx - 9 * s, cy - 8 * s, cx + 9 * s, cy + 8 * s], fill=C((252, 242, 255)))
    blink = (f % 53) < 2
    _eye(d, cx - 4 * s, cy - 1 * s, 3.2 * s, IRIS[(f // 20) % 5], blink); _eye(d, cx + 4 * s, cy - 1 * s, 3.2 * s, IRIS[(f // 20 + 2) % 5], blink)
    d.chord([cx - 6 * s, cy + 2 * s, cx + 6 * s, cy + 8 * s], 0, 180, fill=C((70, 10, 70)))
    for t in range(-4, 5, 2): d.point((cx + t * s, cy + 3 * s), fill=C((255, 255, 255)))
    p = 2 + (f // 3) % 2                                                       # glowing third eye star
    tx, ty = cx, cy - 10 * s
    for (dx, dy) in ((p, 0), (-p, 0), (0, p), (0, -p)): d.line([(tx, ty), (tx + dx, ty + dy)], fill=C((255, 255, 210)))
    d.rectangle([tx - 1, ty - 1, tx + 1, ty + 1], fill=C((255, 255, 255)))
def elf2_img(f, form='radiant', h0=0.0):
    im = Image.new('RGBA', (100, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx, cy = 50, 46
    h = h0 + f * 0.012
    if form == 'radiant':
        n = 14; tips = []
        for k in range(n):
            a = k * 6.283 / n + f * 0.02 - 1.57
            tips.append((_tendril(d, cx, cy, a, 12, 32 + 3 * math.sin(f * 0.15 + k), 3.4, f, k, h + k / n), k))
        for k in range(n):                                                     # inner ring of small eyes
            a = (k + 0.5) * 6.283 / n + f * 0.02 - 1.57; _eye(d, cx + 19 * math.cos(a), cy + 19 * math.sin(a), 1.6, IRIS[(k + 1) % 5], (f + k * 7) % 70 < 3)
        for (tx, ty), k in tips: _eye(d, tx, ty, 2.4, IRIS[k % 5], (f + k * 5) % 60 < 3)
        _gem_face(d, cx, cy, f, h, 1.3)
    elif form == 'orb':                                                        # sphere covered in eyes
        R = 24
        for k in range(12):
            a0 = k * 30 + f * 6; d.pieslice([cx - R, cy - R, cx + R, cy + R], a0, a0 + 30, fill=C(rb(h + k / 12, 0.8, 1.0)))
        for k in range(9):
            a = k * 0.698 + f * 0.05; rr = 15 if k % 2 else 9
            _eye(d, cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.9, 2.2, IRIS[k % 5], (f + k * 9) % 50 < 3)
        _eye(d, cx, cy, 5, IRIS[(f // 10) % 5], (f % 61) < 2)
        for k in range(8):                                                      # little flame flicks
            a = k * 0.785 + f * 0.04; _tendril(d, cx, cy, a, R - 2, 10, 2.2, f, k, h + k / 8)
    elif form == 'crystal':                                                    # octahedral crystal with one huge eye
        pts = [(cx, cy - 38), (cx + 22, cy), (cx, cy + 38), (cx - 22, cy)]
        for k in range(4): d.polygon([(cx, cy), pts[k], pts[(k + 1) % 4]], fill=C(rb(h + k * 0.25 + f * 0.01, 0.7, 1.0)))
        for k in range(4): d.line([(cx, cy), pts[k]], fill=C((255, 255, 255)))
        _eye(d, cx, cy, 8, IRIS[(f // 12) % 5], (f % 59) < 2)
        for k in range(4): a = k * 1.5708 + f * 0.03 - 1.5708; _tendril(d, cx + 30 * math.cos(a) * 0.7, cy + 30 * math.sin(a), a, 4, 10, 2.4, f, k, h + k / 4)
    a = np.array(im); a[..., 3] = np.where(a[..., 3] > 100, 255, 0); im = Image.fromarray(a)
    return outline(im.crop(im.getbbox()))
_ec = {}
def elf2(f, form='radiant', h0=0.0, scale=1.0):
    key = (f, form, round(h0, 3), scale)
    if key not in _ec:
        im = U(elf2_img(f, form, h0))
        if scale != 1.0: im = im.resize((max(2, int(im.width * scale) // 2 * 2), max(2, int(im.height * scale) // 2 * 2)), Image.NEAREST)
        _ec[key] = im
    return _ec[key]

# ================================================================= sacred geometry
def sacred_ring(g, cx, cy, R, prog, f, al=255, h=0.0, speed=1.0):
    """multi-layer spinning ring: rune band, petal ring, hexagram, flower core. prog 0..1 builds it in layers."""
    sp = f * 0.04 * speed; L = lambda k: max(0.0, min(1.0, prog * 5 - k))
    if L(0) > 0:
        g.circle(cx, cy, R, rb(h), al * L(0), a1=360 * L(0)); g.circle(cx, cy, R * 0.9, rb(h + 0.1), al * L(0) * 0.8, a1=360 * L(0))
        for i in range(int(36 * L(0))):
            a = i / 36 * 6.283 + sp; g.line((cx + R * 0.9 * math.cos(a), cy + R * 0.9 * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a)), rb(h + i / 36), al * 0.8, glow=False)
    if L(1) > 0:
        for i in range(12):
            a = i / 12 * 6.283 - sp * 1.3; px_, py_ = cx + R * 0.72 * math.cos(a), cy + R * 0.72 * math.sin(a)
            g.circle(px_, py_, R * 0.2, rb(h + 0.3 + i / 12), al * L(1))
    if L(2) > 0:
        for sgn, hh in ((1, 0.55), (-1, 0.75)):
            pts = [(cx + R * 0.62 * math.cos(sp * 1.6 * sgn + j * 2.094 + (0 if sgn > 0 else 1.047)), cy + R * 0.62 * math.sin(sp * 1.6 * sgn + j * 2.094 + (0 if sgn > 0 else 1.047))) for j in range(3)]
            g.poly(pts, rb(h + hh), al * L(2))
    if L(3) > 0: GE.flower_of_life(g, cx, cy, R * 0.13, L(3), h + 0.2, al, rot=-sp * 2, outer=False)
    if L(4) > 0:
        for i in range(8):
            a = i / 8 * 6.283 + sp * 0.7; g.line((cx + R * 1.06 * math.cos(a), cy + R * 1.06 * math.sin(a)), (cx + R * 1.2 * math.cos(a), cy + R * 1.2 * math.sin(a)), rb(h + 0.9 + i / 8), al * L(4))
def lattice(g, f, al, h0=0.0, r=26, pulse_c=None):
    """flower-of-life lattice across the whole bar"""
    if al <= 1: return
    dy = r * math.sqrt(3) / 2; j = 0; y = SAFE + 10
    while y < BOTTOM + r:
        x = (r / 2 if j % 2 else 0) - r
        while x < FW + r:
            d = 0 if pulse_c is None else math.hypot(x - pulse_c[0], y - pulse_c[1])
            a = al * (0.55 + 0.45 * math.sin(f * 0.25 - d * 0.02))
            g.circle(x, y, r, rb(h0 + x / FW * 0.6 + y * 0.002 + f * 0.01, 0.9, 1.0), a, glow=False)
            x += r
        y += dy; j += 1

def kaleido(fr, cx, cy, R, rot, n=6, ring_col=(255, 255, 255)):
    """n-fold kaleidoscope disk (computed on the 1x grid so it stays pixel-art)"""
    if R < 8: return fr
    a = np.array(fr); R2 = int(R) // 2; cx2, cy2 = int(cx) // 2, int(cy) // 2
    small = a[::2, ::2].copy(); H, W = small.shape[:2]
    ys, xs = np.mgrid[-R2:R2 + 1, -R2:R2 + 1]; rr = np.hypot(xs, ys); m = rr <= R2
    th = np.arctan2(ys, xs) - rot; seg = 2 * np.pi / n
    th = np.mod(th, seg); th = np.where(th > seg / 2, seg - th, th) + rot * 0.3
    sx = np.clip((cx2 + rr * np.cos(th)).astype(int), 0, W - 1); sy = np.clip((cy2 + rr * np.sin(th)).astype(int), SAFE // 2, BOTTOM // 2 - 1)
    ty = cy2 + ys; tx = cx2 + xs; ok = m & (ty >= SAFE // 2) & (ty < BOTTOM // 2) & (tx >= 0) & (tx < W)
    out = small.copy(); out[ty[ok], tx[ok]] = small[sy[ok], sx[ok]]
    big = out.repeat(2, 0).repeat(2, 1)[:a.shape[0], :a.shape[1]]
    reg = slice(SAFE, BOTTOM); a[reg] = big[reg]
    fr2 = Image.fromarray(a); D(fr2).ellipse([snap(cx - R), snap(cy - R), snap(cx + R), snap(cy + R)], outline=ring_col + (230,), width=4)
    return fr2
def facets(fr, cx, cy, amt, f, cell=48):
    """crystal-facet refraction: each cell is pushed radially away from the elf, then outlined as triangles"""
    if amt <= 0.02: return fr
    a = np.array(fr); reg = a[SAFE:BOTTOM]; src = reg.copy(); H, W = reg.shape[:2]
    g = Geo()
    for y0 in range(0, H, cell):
        for x0 in range(0, W, cell):
            mx, my = x0 + cell / 2, y0 + cell / 2 + SAFE; dx, dy = mx - cx, my - cy; dd = math.hypot(dx, dy) + 1
            s = amt * 10 * math.sin(f * 0.3 + dd * 0.01)
            ox, oy = int(dx / dd * s) // 2 * 2, int(dy / dd * s) // 2 * 2
            y1, x1 = min(H, y0 + cell), min(W, x0 + cell)
            sy0, sx0 = np.clip(y0 - oy, 0, H - (y1 - y0)), np.clip(x0 - ox, 0, W - (x1 - x0))
            reg[y0:y1, x0:x1] = src[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
            col = rb(f * 0.01 + (x0 + y0) * 0.0015)
            g.line((x0, y0 + SAFE), (x1, y0 + SAFE), col, 120 * amt, glow=False); g.line((x0, y0 + SAFE), (x0, y1 + SAFE), col, 120 * amt, glow=False)
            g.line((x0, y0 + SAFE), (x1, y1 + SAFE) if (x0 // cell + y0 // cell) % 2 else (x1, y0 + SAFE), col, 120 * amt, glow=False)
            g.line((x1, y0 + SAFE), (x0, y1 + SAFE), col, 90 * amt, glow=False)
    fr2 = Image.fromarray(a); g.render(fr2); return fr2
def hue_img(img, deg):
    a = np.array(img); a[..., :3] = hue_rot_arr(a[..., :3].astype(float), deg).astype(np.uint8); return Image.fromarray(a)

# ================================================================= the scene
def scene():
    out = []; N = 300; X0 = SX - 20; XM = 940; IMP = 216; PCX = PIPE_HOME[0] + PIPE.width // 2
    for f in range(N):
        I = trip(f, N, a=14, b=60, tail=34)
        fr = new(pipe=False)
        fr = hue_region(fr, f * 4, I * 0.3); rect(fr, 0, SAFE, FW, BOTTOM - SAFE, (4, 2, 14), 130 * I)
        gb = Geo(); gf = Geo()
        # ---- where is the elf
        ex, ecy, form, show = X0, GY, 'radiant', 6 <= f < IMP
        if 104 <= f < 152:
            t = (f - 104) / 48; ex = lerp(X0, XM, ease_io(t)); form = ['radiant', 'orb', 'crystal', 'orb'][((f - 104) // 12) % 4]
            ecy = GY + (-abs(math.sin((f - 104) * 0.35)) * 16 if form == 'orb' else 0)
        elif 152 <= f < IMP: ex = XM
        # ---- lattice of reality (behind everything)
        lat = I * (0.35 + 0.65 * clamp((f - 60) / 50)) * (1.4 if IMP <= f < 250 else 1.0)
        lattice(gb, f, 150 * lat, pulse_c=(ex if f < IMP else PCX, GY))
        # ---- spinning sacred ring: intro + launch
        if 6 <= f < 48:
            q = clamp((f - 6) / 26) if f < 40 else 1.0; a_ = 255 * (1 - clamp((f - 40) / 8))
            sacred_ring(gf, X0, GY, 86, q, f, a_, h=f * 0.01, speed=1.6)
        rcx = XM; rR = 86
        if 176 <= f < IMP:
            if f >= 200: t = ease_in((f - 200) / 16); rcx = lerp(XM, MOUTH + 40, t); rR = lerp(86, 60, t)
            sacred_ring(gf, rcx, GY, rR, clamp((f - 176) / 14), f, 255, h=f * 0.012, speed=1.0 + 3 * clamp((f - 186) / 20) ** 2)
            if f >= 200:
                t = (f - 200) / 16
                for k in range(7): rect(fr, rcx + 70, GY - 42 + k * 12, XM + 60 - rcx, 10, rb(k / 7 + f * 0.04), 160 * min(1, t * 2))
        # ---- gem showcase + bloom (60..104)
        if 60 <= f < 104:
            sel = ((f - 60) // 9) % 5; V, E = GE.SOLIDS[sel]; gx, gyy = X0 - 110, GY - 6 + 4 * math.sin(f * 0.3)
            GE.wire(gf, V, E, gx, gyy, 16 + 2 * math.sin(f * 0.5), f * 0.11, f * 0.09, 0.3, f * 0.02, 255)
            if 72 <= f < 104:
                q = ease_out((f - 72) / 12) * (1 - clamp((f - 96) / 8)); GE.flower_of_life(gb, gx, GY, 24 * q, 1, f * 0.015, 220 * q, rot=f * 0.03)
        # ---- clones on a hexagram (152..178)
        clones = []
        if 152 <= f < 178:
            r = 130 * math.sin(math.pi * (f - 152) / 26)
            for k in range(6):
                ang = (f - 152) * 0.2 + k * 1.047; clones.append((XM + r * math.cos(ang), GY + r * 0.45 * math.sin(ang), k / 6))
            pts = [(XM + r * math.cos((f - 152) * 0.2 + k * 1.047), GY + r * 0.45 * math.sin((f - 152) * 0.2 + k * 1.047)) for k in range(6)]
            gb.poly([pts[0], pts[2], pts[4]], rb(f * 0.02), 220); gb.poly([pts[1], pts[3], pts[5]], rb(f * 0.02 + 0.5), 220)
        gb.render(fr)
        # ---- sacred-geometric reality distortion (warps the world, not the elf)
        if 36 <= f < IMP:
            kr = 92 * I * (0.5 + 0.5 * clamp((f - 60) / 40)); fr = kaleido(fr, ex, ecy, kr, f * 0.05, n=6, ring_col=rb(f * 0.02))
        if 104 <= f < 156: fr = facets(fr, ex, ecy, I * math.sin(math.pi * (f - 104) / 52), f)
        if IMP + 4 <= f < 256:
            kq = math.sin(math.pi * (f - IMP - 4) / 52); fr = kaleido(fr, PCX + 40, GY, 90 * kq * I, -f * 0.06, n=8, ring_col=rb(f * 0.03))
        if 120 <= f < 200 and (f // 4) % 5 == 0:                                   # extra kaleidoscope echoes down the bar
            for k, xx in enumerate((ex - 360, ex + 360)):
                if 200 < xx < FW - 200: fr = kaleido(fr, xx, GY, 70 * I, f * 0.07 * (1 if k else -1), n=6, ring_col=rb(f * 0.02 + k * 0.5))
        # ---- elf + clones
        for (cx_, cy_, hh) in clones: place(fr, hue_img(elf2(f, 'radiant', hh), hh * 360), cx_, 0, cy=cy_)
        if show:
            if f >= 200:
                t = (f - 200) / 16; im = elf2(f, 'crystal', scale=round(lerp(1, 0.5, t), 2)); place(fr, im, rcx, 0, cy=GY, clip_x=MOUTH)
            else:
                im = elf2(f, form)
                if f < 26: im = bayer_mask(tint(im, WHITE, 0.6 * (1 - (f - 6) / 20)), (f - 6) / 18)
                place(fr, im, ex, 0, cy=ecy)
            if (30 <= f < 60) or (84 <= f < 104) or (156 <= f < 178): chatter(fr, ex - 4, ecy - 80, f, 30 if f < 60 else (84 if f < 104 else 156), n=4, a=255)
        gf.render(fr)
        # ---- pipe: shatter, mandala, reassemble
        s = 0
        if IMP <= f < IMP + 10: s = ease_out((f - IMP) / 8)
        elif IMP + 10 <= f < 248: s = 1
        elif 248 <= f < 274: s = 1 - ease_io((f - 248) / 24)
        if not GE.draw_shards(fr, s, tintf=lambda im: hue_img(im, f * 15)): draw_pipe(fr, 0, pipe_bounce(f - 274))
        if IMP + 2 <= f < 264:
            q = ease_out((f - IMP - 2) / 14) * (1 - ease_in(clamp((f - 242) / 22))); gm = Geo()
            for i in range(24):
                ang = i / 24 * 6.283 - f * 0.03; gm.line((PCX, GY), (PCX + 700 * q * math.cos(ang), GY + 700 * q * math.sin(ang)), rb(i / 24 + f * 0.02), 120 * q, glow=False)
            sacred_ring(gm, PCX, GY, 84 * q, 1, f, 255 * q, h=f * 0.02, speed=2.0)
            GE.sri_yantra(gm, PCX, GY, 50 * q, 1, f * 0.02 + 0.3, 220 * q, rot=-f * 0.03, petals=False)
            gm.render(fr)
            if q > 0.5:
                for k in range(5):
                    ang = f * 0.1 + k * 1.2566; place(fr, elf2(f + k * 9, 'radiant', k / 5, scale=0.3), PCX + 120 * math.cos(ang), 0, cy=GY + 40 * math.sin(ang))
            if IMP + 8 <= f < 252: chatter(fr, PCX + 30, GY - 30, f, IMP + 8, n=5, a=255 * q, spread=1.4)
        if IMP <= f < IMP + 6: rect(fr, 0, SAFE, FW, BOTTOM - SAFE, WHITE, [230, 190, 140, 90, 50, 20][f - IMP])
        if IMP <= f < IMP + 20: burst(fr, PCX + 60, GY, (f - IMP) / 20, n=36, speed=280, cols=[rb(k / 12) for k in range(12)], seed=13, s=6)
        out.append(finish(fr))
    return out

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        ims = [elf2(f, form) for form in ('radiant', 'orb', 'crystal') for f in (0, 12)]
        W = sum(i.width + 10 for i in ims); H = max(i.height for i in ims)
        o = Image.new('RGBA', (W, H + 4), (12, 6, 24, 255)); x = 0
        for i in ims: o.alpha_composite(i, (x, H - i.height)); x += i.width + 10
        o.save(os.path.join(HERE, 'elf2_preview.png')); sys.exit()
    frames = scene()
    picks = np.linspace(0, len(frames) - 1, 20).astype(int)
    sheet = Image.new('RGB', (890 * 2, 98 * 10))
    for k, p in enumerate(picks): sheet.paste(frames[p].crop((0, 208, FW, 404)).resize((890, 98)), ((k % 2) * 890, (k // 2) * 98))
    sheet.save(os.path.join(HERE, 'sheet_elf2.png'))
    print(len(frames), write_gif(frames, '43_dmt_machine_elf_sacred_warp', outdir=os.path.join(HERE, 'out')))
