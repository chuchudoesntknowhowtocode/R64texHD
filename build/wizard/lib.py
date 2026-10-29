from PIL import Image, ImageOps, ImageDraw
import numpy as np, scipy.ndimage as nd, math, random, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
S = 2; FPS = 30
FLOOR = 372          # feet line (2x px)
SAFE = 216           # nothing may be drawn above this row (upper panels)
SX = 1395            # standing spot next to Quit
DARK = (19, 10, 34)
CYAN = (30, 225, 255); WHITE = (235, 250, 255); LBLUE = (110, 190, 255); NAVY = (20, 40, 110)
PINK = (230, 90, 170); GOLD = (255, 200, 60); ORANGE = (255, 130, 30); PURPLE = (150, 70, 230)
DUST = (205, 165, 215); RED = (220, 50, 60); GREEN = (175, 249, 35)

bg1 = Image.open(os.path.join(HERE, 'assets', 'app_idle.png')).convert('RGB')
A1 = np.array(bg1).astype(int)
def U(im): return im.resize((im.width * S, im.height * S), Image.NEAREST)
BG = U(bg1)
FW, FH = BG.size

# ---------- movable pipe ----------
pb = (12, 112, 89, 198)
crop = A1[pb[1]:pb[3], pb[0]:pb[2]]
isdark = (np.abs(crop - np.array(DARK)).sum(2) < 4)
ismag = (crop[..., 0] > 100) & (crop[..., 1] < 90)
pm = ~isdark & ~ismag
pipe1 = np.dstack([crop, pm * 255]).astype(np.uint8)
nopipe = A1.copy(); reg = nopipe[pb[1]:pb[3], pb[0]:pb[2]]; reg[pm] = DARK
BG_NOPIPE = U(Image.fromarray(nopipe.astype(np.uint8)))
PIPE1 = Image.fromarray(pipe1, 'RGBA')
PIPE = U(PIPE1)
PIPE_HOME = (pb[0] * S, pb[1] * S)
MOUTH = 172                                   # x of pipe opening at home
MOUTH_DX = MOUTH - PIPE_HOME[0]
MOUTH_Y = 312
# split body / rim for stretching
colfill = pm.sum(0)
gapcols = [x for x in range(10, pm.shape[1] - 10) if colfill[x] < colfill.max() * 0.35]
SPLIT1 = (gapcols[0] if gapcols else 38)
BODY1 = Image.fromarray(pipe1[:, :SPLIT1]); RIM1 = Image.fromarray(pipe1[:, SPLIT1:])
TUBECOL1 = Image.fromarray(pipe1[:, SPLIT1 // 2:SPLIT1 // 2 + 1])

# ---------- movable Quit button ----------
qb = (736, 128, 885, 192)
qc = A1[qb[1]:qb[3], qb[0]:qb[2]]
qm = (np.abs(qc - np.array(DARK)).sum(2) >= 4)
QUIT = U(Image.fromarray(np.dstack([qc, qm * 255]).astype(np.uint8), 'RGBA'))
noq = A1.copy(); r2 = noq[qb[1]:qb[3], qb[0]:qb[2]]; r2[qm] = DARK
QUIT_HOME = (qb[0] * S, qb[1] * S)

# ---------- sprites ----------
P1 = {n: Image.open(os.path.join(HERE, f'px_{n}.png')) for n in 'RECFBIDH'}
_cache = {}
def lean1(img, deg):
    a = math.tan(math.radians(deg)); w, h = img.size; ext = int(abs(a) * h) + 2
    return img.transform((w + ext, h), Image.AFFINE, (1, a, -ext, 0, 1, 0), Image.NEAREST)
def stride_swap(img, frac=0.30):
    a = np.array(img).copy(); h, w = a.shape[:2]; t = int(h * (1 - frac))
    low = a[t:].copy(); cols = np.nonzero(low[..., 3].any(0))[0]
    if len(cols):
        c0, c1 = cols.min(), cols.max(); seg = low[:, c0:c1 + 1][:, ::-1]; low[:] = 0; low[:, c0:c1 + 1] = seg; a[t:] = low
    return Image.fromarray(a)
def spr(name, flip=False, sx=1.0, sy=1.0, rot=0, lean=0, swap=False, scale=1.0):
    key = (name, flip, round(sx, 3), round(sy, 3), round(rot, 1), lean, swap, round(scale, 3))
    if key in _cache: return _cache[key]
    im = P1[name]
    if flip: im = ImageOps.mirror(im)
    if swap: im = stride_swap(im)
    if scale != 1.0 or sx != 1.0 or sy != 1.0:
        im = im.resize((max(1, round(im.width * sx * scale)), max(1, round(im.height * sy * scale))), Image.NEAREST)
    if lean: im = lean1(im, lean)
    if rot: im = im.rotate(rot, expand=True, resample=Image.NEAREST)
    out = U(im); _cache[key] = out; return out
def run_frame(f, scale=1.0, lean=14):     # 4-frame run cycle facing left
    ph = f % 4
    return spr('C', True, swap=ph >= 2, sx=1.04 if ph % 2 else 1, sy=0.95 if ph % 2 else 1, lean=lean + (2 if ph % 2 else 0), scale=scale), (4 if ph % 2 else 0)
def walk_frame(f, scale=1.0):
    ph = (f // 3) % 2
    return spr('C', True, swap=ph == 1, scale=scale), (2 if (f // 3) % 2 else 0)

# ---------- drawing ----------
def new(pipe=True):
    return (BG if pipe else BG_NOPIPE).copy()
def snap(v, g=2): return int(round(v / g)) * g
def D(fr): return ImageDraw.Draw(fr, 'RGBA')
def px(fr, x, y, s, c, a=255):
    if a <= 0 or s <= 0: return
    x = snap(x); y = snap(y)
    D(fr).rectangle([x, y, x + s - 1, y + s - 1], fill=tuple(c) + (int(min(255, a)),))
def rect(fr, x, y, w, h, c, a=255):
    if a <= 0 or int(w) < 1 or int(h) < 1: return
    D(fr).rectangle([snap(x), snap(y), snap(x) + int(w) - 1, snap(y) + int(h) - 1], fill=tuple(c) + (int(min(255, a)),))
def tint(img, c, amt=1.0, alpha=1.0):
    a = np.array(img).astype(float)
    a[..., :3] = a[..., :3] * (1 - amt) + np.array(c) * amt; a[..., 3] *= alpha
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))
def place(fr, img, cx, bottom, clip_x=None, clip_xmax=None, clip_floor=None, alpha=1.0, cy=None):
    im = img
    if alpha < 1: im = tint(im, (0, 0, 0), 0, alpha)
    x = int(round(cx - im.width / 2)); y = int(round((bottom - im.height) if cy is None else cy - im.height / 2))
    x = snap(x); y = snap(y)
    l, t, r, b = 0, 0, im.width, im.height
    if clip_x is not None and x < clip_x: l = clip_x - x
    if clip_xmax is not None and x + r > clip_xmax: r = clip_xmax - x
    if clip_floor is not None and y + b > clip_floor: b = clip_floor - y
    if r <= l or b <= t: return
    im = im.crop((l, t, r, b)); fr.paste(im, (x + l, y + t), im)
def draw_pipe(fr, dx=0, dy=0, img=None):
    p = img or PIPE
    fr.paste(p, (PIPE_HOME[0] + int(dx), PIPE_HOME[1] + int(dy)), p)
def stretched_pipe(extra):        # rim moved right by `extra` 2x px, tube filled in
    extra = max(0, int(extra)) // 2
    w = PIPE1.width + extra; im = Image.new('RGBA', (w, PIPE1.height), (0, 0, 0, 0))
    im.paste(BODY1, (0, 0))
    for i in range(extra + 2): im.paste(TUBECOL1, (SPLIT1 - 1 + i, 0))
    im.paste(RIM1, (SPLIT1 + extra, 0), RIM1)
    return U(im)
BOTTOM = 402         # the app's bottom edge line: nothing may be drawn at or below it
def finish(fr):
    fr.paste(BG.crop((0, 0, FW, SAFE)), (0, 0))
    fr.paste(BG.crop((0, BOTTOM, FW, FH)), (0, BOTTOM))
    return fr
def bayer_mask(img, p, seed=0):  # ordered-dither fade (8-bit style) on 1x pixel grid
    b4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16
    a = np.array(img).copy(); h, w = a.shape[:2]
    th = np.tile(b4, (h // 8 + 2, w // 8 + 2)).repeat(2, 0).repeat(2, 1)[:h, :w]
    a[..., 3] = np.where(th < p, a[..., 3], 0)
    return Image.fromarray(a)
def dissolve(img, p, seed=1):
    rng = np.random.default_rng(seed); a = np.array(img).copy(); h, w = a.shape[:2]
    th = rng.random((h // 2 + 1, w // 2 + 1)).repeat(2, 0).repeat(2, 1)[:h, :w]
    a[..., 3] = np.where(th < p, a[..., 3], 0); return Image.fromarray(a)
def scan_glitch(img, f, amt=6, seed=0):
    rng = random.Random(f * 31 + seed); a = np.array(img).copy()
    for y in range(0, a.shape[0], 4):
        if rng.random() < 0.35: a[y:y + 4] = np.roll(a[y:y + 4], rng.randint(-amt, amt) * 2, axis=1)
    return Image.fromarray(a)
FONT = {'?': ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
        '!': ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
        'Z': ["11111", "00010", "00100", "01000", "11111", "00000", "00000"],
        '*': ["00000", "10101", "01110", "11111", "01110", "10101", "00000"]}
def glyph(fr, ch, x, y, c=WHITE, s=4, a=255, outline=True):
    rows = FONT[ch]
    if outline:
        for j, row in enumerate(rows):
            for i, v in enumerate(row):
                if v == '1':
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)): px(fr, x + (i + dx) * s, y + (j + dy) * s, s, (10, 14, 42), a)
    for j, row in enumerate(rows):
        for i, v in enumerate(row):
            if v == '1': px(fr, x + i * s, y + j * s, s, c, a)
def burst(fr, cx, cy, t, n=12, speed=60, cols=(CYAN, WHITE, LBLUE), s=4, seed=0, life=1.0, grav=0):
    rng = random.Random(seed)
    if t < 0 or t > life: return
    for i in range(n):
        ang = rng.uniform(0, 6.283); sp = speed * rng.uniform(0.5, 1.2)
        x = cx + math.cos(ang) * sp * t; y = cy + math.sin(ang) * sp * t * 0.7 + grav * t * t
        px(fr, x, y, s, cols[i % len(cols)], 255 * (1 - t / life))
def dust(fr, x, y, t, n=6, dirx=1, seed=0):
    rng = random.Random(seed)
    for i in range(n):
        if t < 0 or t > 0.4: continue
        vx = dirx * rng.uniform(20, 90); vy = -rng.uniform(10, 40)
        px(fr, x + vx * t, y + vy * t, 4, DUST, 200 * (1 - t / 0.4))
def pipe_bounce(k):       # k = frames since impact -> (dy) small hop
    seq = [4, 8, 6, 2, 0]
    return -seq[k] if 0 <= k < len(seq) else 0
def lerp(a, b, t): return a + (b - a) * t
def clamp(t): return max(0.0, min(1.0, t))
def ease_io(t): t = clamp(t); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 2
def ease_in(t): t = clamp(t); return t * t
def ease_back(t, s=1.7): t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1
def write_gif(frames, name, outdir=os.path.join(HERE, 'out')):
    os.makedirs(outdir, exist_ok=True)
    tmp = os.path.join(HERE, 'frames_' + name); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    for i, fr in enumerate(frames): fr.save(os.path.join(tmp, f'{i:03d}.png'))
    pal = os.path.join(tmp, 'pal.png'); out = os.path.join(outdir, name + '.gif'); part = out + '.part.gif'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%03d.png'),
                    '-vf', 'palettegen=max_colors=256:stats_mode=full', pal], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%03d.png'), '-i', pal,
                    '-lavfi', 'paletteuse=dither=none', '-loop', '0', part], check=True)
    os.replace(part, out)
    return out
