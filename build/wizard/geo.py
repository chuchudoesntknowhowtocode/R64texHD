"""Sacred-geometry engine. Everything is drawn on a half-resolution (1x) layer with 1px lines,
then scaled 2x with nearest-neighbour, so every line sits on the same pixel grid as the sprites."""
import math, random, colorsys
import numpy as np, scipy.ndimage as nd
from PIL import Image, ImageDraw, ImageChops
from lib import FW, FH, U, PIPE1, PIPE_HOME, snap

PHI = (1 + 5 ** 0.5) / 2
def rb(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v); return (int(r * 255), int(g * 255), int(b * 255))
LET = {'N': ["101", "111", "111", "101", "101"], 'H': ["101", "101", "111", "101", "101"]}

class Geo:
    def __init__(self): self.ops = []
    def line(self, a, b, col, al=255, glow=True): self.ops.append(('l', [a, b], col, al, glow))
    def poly(self, pts, col, al=255, glow=True, closed=True):
        pts = list(pts)
        if len(pts) < 2: return
        self.ops.append(('l', pts + ([pts[0]] if closed else []), col, al, glow))
    def circle(self, cx, cy, r, col, al=255, glow=True, a0=0.0, a1=360.0, sy=1.0):
        if r < 1 or a1 <= a0: return
        n = max(10, int(r * 0.7 * (a1 - a0) / 360) + 6)
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + r * sy * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
        self.ops.append(('l', pts, col, al, glow))
    def dot(self, x, y, col, al=255, size=1): self.ops.append(('d', (x, y), col, al, size))
    def fill(self, pts, col, al=255): self.ops.append(('f', list(pts), col, al))
    def label(self, x, y, txt, col): self.ops.append(('t', (x, y), txt, col))
    def render(self, fr):
        if not self.ops: return
        im = Image.new('RGBA', (FW // 2, FH // 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        h = lambda p: (int(round(p[0] / 2)), int(round(p[1] / 2)))
        A = lambda a: int(max(0, min(255, a)))
        for op in self.ops:
            if op[0] == 'f' and A(op[3]) > 0: d.polygon([h(p) for p in op[1]], fill=tuple(op[2]) + (A(op[3]),))
        for op in self.ops:
            if op[0] == 'l' and op[4] and A(op[3] * 0.32) > 0: d.line([h(p) for p in op[1]], fill=tuple(op[2]) + (A(op[3] * 0.32),), width=3)
        for op in self.ops:
            if op[0] == 'l' and A(op[3]) > 0: d.line([h(p) for p in op[1]], fill=tuple(op[2]) + (A(op[3]),), width=1)
            elif op[0] == 'd' and A(op[3]) > 0:
                x, y = h(op[1]); s = op[4]; d.rectangle([x - s // 2, y - s // 2, x - s // 2 + s - 1, y - s // 2 + s - 1], fill=tuple(op[2]) + (A(op[3]),))
        for op in self.ops:
            if op[0] == 't':
                x, y = h(op[1]); x0 = x - 2 * len(op[2]) + 1
                d.rectangle([x0 - 1, y - 3, x0 + 4 * len(op[2]) - 1, y + 3], fill=(10, 6, 24, 255))
                for i, ch in enumerate(op[2]):
                    for j, row in enumerate(LET[ch]):
                        for k, v in enumerate(row):
                            if v == '1': d.point((x0 + i * 4 + k, y - 2 + j), fill=tuple(op[3]) + (255,))
        big = U(im); fr.paste(big, (0, 0), big)

# ---------- 2D sacred geometry ----------
def rot2(x, y, a): c, s = math.cos(a), math.sin(a); return x * c - y * s, x * s + y * c
def flower_centers(r):
    C = [(0, 0)] + [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)]
    C += [(2 * r * math.cos(math.radians(60 * k)), 2 * r * math.sin(math.radians(60 * k))) for k in range(6)]
    C += [(r * 3 ** 0.5 * math.cos(math.radians(60 * k + 30)), r * 3 ** 0.5 * math.sin(math.radians(60 * k + 30))) for k in range(6)]
    return C
def flower_of_life(g, cx, cy, r, prog, h, al=255, rot=0.0, outer=True):
    C = flower_centers(r)
    for k, (x, y) in enumerate(C):
        p = max(0.0, min(1.0, prog * len(C) - k))
        if p > 0:
            x, y = rot2(x, y, rot); a0 = math.degrees(rot) + k * 40
            g.circle(cx + x, cy + y, r, rb(h + k * 0.045), al, a0=a0, a1=a0 + 360 * p)
    if outer and prog >= 1: g.circle(cx, cy, 3 * r, rb(h + 0.5), al); g.circle(cx, cy, 3 * r + 4, rb(h + 0.55), al * 0.6, glow=False)
def metatron(g, cx, cy, r, circ_prog, line_prog, h, al=255, rot=0.0):
    C = [(0, 0)] + [(2 * r * math.cos(math.radians(60 * k - 90)), 2 * r * math.sin(math.radians(60 * k - 90))) for k in range(6)] \
        + [(4 * r * math.cos(math.radians(60 * k - 90)), 4 * r * math.sin(math.radians(60 * k - 90))) for k in range(6)]
    C = [rot2(x, y, rot) for x, y in C]
    for k, (x, y) in enumerate(C):
        p = max(0.0, min(1.0, circ_prog * 13 - k))
        if p > 0: g.circle(cx + x, cy + y, r, rb(h + k * 0.06), al, a1=360 * p)
    pairs = [(i, j) for i in range(13) for j in range(i + 1, 13)]
    n = int(len(pairs) * line_prog)
    for idx, (i, j) in enumerate(pairs[:n]):
        g.line((cx + C[i][0], cy + C[i][1]), (cx + C[j][0], cy + C[j][1]), rb(h + 0.3 + idx * 0.004), al * 0.85, glow=False)
    for x, y in C[:max(0, int(circ_prog * 13))]: g.dot(cx + x, cy + y, (255, 255, 255), al, 2)
SRI_UP = [(-1.0, 0.48, 1.0), (-0.64, 0.74, 0.86), (-0.34, 0.30, 0.62), (-0.14, 0.58, 0.5)]
SRI_DN = [(1.0, -0.48, 1.0), (0.80, -0.70, 0.84), (0.56, -0.24, 0.66), (0.36, -0.58, 0.52), (0.16, -0.06, 0.34)]
def sri_yantra(g, cx, cy, R, prog, h, al=255, rot=0.0, petals=True):
    tris = [(a, b, w, -1) for a, b, w in SRI_UP] + [(a, b, w, 1) for a, b, w in SRI_DN]
    tris.sort(key=lambda t: -t[2])
    for k, (a, b, w, s) in enumerate(tris):
        if prog * 9 - k <= 0: break
        hw = math.sqrt(max(0.0, 1 - b * b)) * w
        pts = [(0, a), (-hw, b), (hw, b)]
        pts = [rot2(x * R, y * R, rot) for x, y in pts]
        g.poly([(cx + x, cy + y) for x, y in pts], rb(h + k * 0.09), al * min(1, prog * 9 - k))
    if prog > 0.6:
        q = (prog - 0.6) / 0.4
        g.circle(cx, cy, R * 1.06, rb(h + 0.4), al * q); g.circle(cx, cy, R * 1.16, rb(h + 0.45), al * q)
        if petals:
            for i in range(16):
                ang = rot + i / 16 * 6.283; px_, py_ = cx + R * 1.16 * math.cos(ang), cy + R * 1.16 * math.sin(ang)
                g.circle(px_, py_, R * 0.12, rb(h + 0.6 + i * 0.02), al * q * 0.8, a0=math.degrees(ang) - 90, a1=math.degrees(ang) + 90)
    g.dot(cx, cy, (255, 255, 255), al, 2)                    # bindu
def hex_tunnel(g, cx, cy, t, al, n=16, R=26, h=0.0, sides=6, twist=0.25):
    for k in range(n):
        z = ((k - t) % n) + 0.35
        r = R * 9 / z
        if r > 2400: continue
        a0 = z * twist + t * 0.12
        pts = [(cx + r * math.cos(a0 + i * 6.283 / sides), cy + r * math.sin(a0 + i * 6.283 / sides)) for i in range(sides)]
        g.poly(pts, rb(h + z * 0.06 + t * 0.03), al * min(1, (n - z) / 4) * min(1, z * 1.5), glow=r < 400)

# ---------- 3D ----------
def _norm(V): V = np.array(V, float); return V / np.linalg.norm(V, axis=1).max()
TETRA = _norm([(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)])
CUBE = _norm([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
OCTA = _norm([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])
ICOSA = _norm([(0, a, b * PHI) for a in (-1, 1) for b in (-1, 1)] + [(a, b * PHI, 0) for a in (-1, 1) for b in (-1, 1)] + [(b * PHI, 0, a) for a in (-1, 1) for b in (-1, 1)])
DODECA = _norm([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)] + [(0, a / PHI, b * PHI) for a in (-1, 1) for b in (-1, 1)]
               + [(a / PHI, b * PHI, 0) for a in (-1, 1) for b in (-1, 1)] + [(b * PHI, 0, a / PHI) for a in (-1, 1) for b in (-1, 1)])
def edges_of(V):
    D = np.linalg.norm(V[:, None] - V[None], axis=2); m = D[D > 1e-6].min()
    return [(i, j) for i in range(len(V)) for j in range(i + 1, len(V)) if abs(D[i, j] - m) < 1e-3]
SOLIDS = [(V, edges_of(V)) for V in (TETRA, CUBE, OCTA, DODECA, ICOSA)]
def rot3(V, ax, ay, az):
    cx, sx, cy_, sy_, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return np.array(V) @ (Rz @ Ry @ Rx).T
def proj(V, cx, cy, s, dist=4.0):
    f = dist / (dist + V[:, 2]); return [(cx + x * s * k, cy + y * s * k) for (x, y), k in zip(V[:, :2], f)]
def wire(g, V, E, cx, cy, s, ax, ay, az, h, al=255, hstep=0.03, glow=True):
    P = rot3(V, ax, ay, az); pts = proj(P, cx, cy, s); z = P[:, 2]
    for k, (i, j) in enumerate(E):
        depth = 0.55 + 0.45 * (1 - (z[i] + z[j]) / 2) / 2
        g.line(pts[i], pts[j], rb(h + k * hstep), al * depth, glow)
def merkaba(g, cx, cy, s, a, h, al=255, prog=1.0):
    E = edges_of(TETRA); n = int(6 * prog + 0.999)
    for sign, ang, hh in ((1, a, h), (-1, -a, h + 0.5)):
        V = TETRA * sign; P = rot3(V, 0.35, ang, 0); pts = proj(P, cx, cy, s)
        for k, (i, j) in enumerate(E[:n]): g.line(pts[i], pts[j], rb(hh + k * 0.05), al)
def torus(g, cx, cy, R, r, ax, ay, spin, h, al=255, nu=10, nv=14, prog=1.0):
    def pt(u, v): return ((R + r * math.cos(v)) * math.cos(u), r * math.sin(v), (R + r * math.cos(v)) * math.sin(u))
    rings = []
    for i in range(nu):                                   # tube cross-sections
        u = i / nu * 6.283 + spin; rings.append([pt(u, k / 16 * 6.283) for k in range(17)])
    for j in range(0, nv, 3):                             # a few long circles
        v = j / nv * 6.283; rings.append([pt(k / 32 * 6.283, v) for k in range(33)])
    nshow = int(len(rings) * prog + 0.999)
    for k, ring in enumerate(rings[:nshow]):
        P = rot3(np.array(ring), ax, ay, 0); pts = proj(P, cx, cy, 1.0, dist=400)
        g.poly(pts, rb(h + k * 0.04), al * (0.85 if k < nu else 0.5), closed=False)
def tesseract(g, cx, cy, s, a, h, al=255):
    V = np.array([(x, y, z, w) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1) for w in (-1, 1)], float)
    E = [(i, j) for i in range(16) for j in range(i + 1, 16) if np.abs(V[i] - V[j]).sum() == 2]
    c, sn = math.cos(a), math.sin(a); c2, s2 = math.cos(a * 0.7), math.sin(a * 0.7)
    X = V[:, 0] * c - V[:, 3] * sn; W = V[:, 0] * sn + V[:, 3] * c
    Y = V[:, 1] * c2 - V[:, 2] * s2; Z = V[:, 1] * s2 + V[:, 2] * c2
    k = 3.2 / (3.2 + W); P = np.stack([X * k, Y * k, Z * k], 1) / 2.0
    P = rot3(P, 0.4, a * 0.5, 0); pts = proj(P, cx, cy, s)
    for n, (i, j) in enumerate(E): g.line(pts[i], pts[j], rb(h + n * 0.03), al * (0.6 + 0.4 * (W[i] + W[j] + 2) / 4))

# ---------- the spirit molecule (skeletal formula) ----------
def _dmt():
    L = 1.0; V = {}
    for k in range(6): V[f'b{k}'] = (L * math.cos(math.radians(-90 + 60 * k)), L * math.sin(math.radians(-90 + 60 * k)))
    c5x = 0.866 + 0.688; R5 = 0.851
    V['C3'] = (c5x + R5 * math.cos(math.radians(-72)), R5 * math.sin(math.radians(-72)))
    V['C2'] = (c5x + R5, 0.0)
    V['N1'] = (c5x + R5 * math.cos(math.radians(72)), R5 * math.sin(math.radians(72)))
    def step(p, deg): return (p[0] + math.cos(math.radians(deg)), p[1] + math.sin(math.radians(deg)))
    V['Ca'] = step(V['C3'], -72); V['Cb'] = step(V['Ca'], -12); V['Na'] = step(V['Cb'], -72)
    V['M1'] = step(V['Na'], -132); V['M2'] = step(V['Na'], -12)
    bonds = [('b0', 'b1'), ('b1', 'b2'), ('b2', 'b3'), ('b3', 'b4'), ('b4', 'b5'), ('b5', 'b0'),
             ('b1', 'C3'), ('C3', 'C2'), ('C2', 'N1'), ('N1', 'b2'),
             ('C3', 'Ca'), ('Ca', 'Cb'), ('Cb', 'Na'), ('Na', 'M1'), ('Na', 'M2')]
    doubles = [('b5', 'b0', (0, 0)), ('b1', 'b2', (0, 0)), ('b3', 'b4', (0, 0)), ('C3', 'C2', (c5x, 0))]
    xs = [p[0] for p in V.values()]; ys = [p[1] for p in V.values()]
    ctr = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    return V, bonds, doubles, ctr
DMT = _dmt()
def dmt(g, cx, cy, L, prog, h, al=255, rot=0.0, labels=True):
    V, bonds, doubles, ctr = DMT
    P = {k: (cx + rot2((x - ctr[0]) * L, (y - ctr[1]) * L, rot)[0], cy + rot2((x - ctr[0]) * L, (y - ctr[1]) * L, rot)[1]) for k, (x, y) in V.items()}
    n = prog * len(bonds)
    for k, (a, b) in enumerate(bonds):
        p = max(0.0, min(1.0, n - k))
        if p <= 0: break
        A, B = P[a], P[b]; g.line(A, (A[0] + (B[0] - A[0]) * p, A[1] + (B[1] - A[1]) * p), rb(h + k * 0.06), al)
    if prog >= 1:
        for a, b, rc in doubles:
            rcx, rcy = cx + rot2((rc[0] - ctr[0]) * L, (rc[1] - ctr[1]) * L, rot)[0], cy + rot2((rc[0] - ctr[0]) * L, (rc[1] - ctr[1]) * L, rot)[1]
            A, B = P[a], P[b]; f = 0.2
            A2 = (A[0] + (rcx - A[0]) * f + (B[0] - A[0]) * 0.15, A[1] + (rcy - A[1]) * f + (B[1] - A[1]) * 0.15)
            B2 = (B[0] + (rcx - B[0]) * f + (A[0] - B[0]) * 0.15, B[1] + (rcy - B[1]) * f + (A[1] - B[1]) * 0.15)
            g.line(A2, B2, rb(h + 0.5), al * 0.9, glow=False)
        for k, p in P.items(): g.dot(p[0], p[1], (255, 255, 255), al, 2)
        if labels and L >= 18:
            g.label(P['Na'][0], P['Na'][1], 'N', rb(h + 0.6, 0.5)); g.label(P['N1'][0], P['N1'][1] + 2, 'NH', rb(h + 0.6, 0.5))
    return P

# ---------- pipe shatter + spirit outline ----------
def make_shards(cell=11, seed=0):
    rng = random.Random(seed); a = PIPE1; w, h = a.size; out = []
    for gy in range(0, h, cell):
        for gx in range(0, w, cell):
            for tri in (0, 1):
                m = Image.new('L', (cell, cell), 0); d = ImageDraw.Draw(m)
                d.polygon([(0, 0), (cell, 0), (0, cell)] if tri == 0 else [(cell, 0), (cell, cell), (0, cell)], fill=255)
                piece = a.crop((gx, gy, gx + cell, gy + cell)); al = ImageChops.multiply(piece.split()[3], m)
                if al.getbbox() is None: continue
                piece.putalpha(al)
                cx_, cy_ = gx + cell / 2 - w / 2, gy + cell / 2 - h / 2
                vx = 60 + abs(cx_) * 5 + rng.uniform(0, 220); vy = cy_ * 1.2 + rng.uniform(-30, 30)
                out.append((U(piece), gx * 2, gy * 2, vx, vy, rng.choice([-1, 1]) * rng.uniform(90, 300)))
    return out
SHARDS = make_shards()
def draw_shards(fr, s, dx=0, tintf=None):
    if s <= 0.001:
        return False
    for (img, x, y, vx, vy, spin) in SHARDS:
        ang = int(spin * s) // 30 * 30
        im = img.rotate(ang, expand=True, resample=Image.NEAREST) if ang else img
        if tintf: im = tintf(im)
        X = PIPE_HOME[0] + x + img.width / 2 + vx * s + dx; Y = PIPE_HOME[1] + y + img.height / 2 + vy * s
        fr.paste(im, (snap(X - im.width / 2), snap(Y - im.height / 2)), im)
    return True
_m = np.array(PIPE1)[..., 3] > 0
_ring = nd.binary_dilation(_m) & ~_m
PIPE_EDGE = [(x * 2 + PIPE_HOME[0] - 2, y * 2 + PIPE_HOME[1] - 2) for y, x in zip(*np.nonzero(np.pad(_ring, 0)))]
_inner = _m & ~nd.binary_erosion(_m)
PIPE_EDGE += [(x * 2 + PIPE_HOME[0], y * 2 + PIPE_HOME[1]) for y, x in zip(*np.nonzero(_inner))]
def spirit_pipe(g, h, al=255):
    for k, (x, y) in enumerate(PIPE_EDGE[::1]): g.dot(x + 1, y + 1, rb(h + (x + y) * 0.002), al, 1)
