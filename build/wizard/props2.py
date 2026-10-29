"""DMT assets: meditating pose G, shaman spirit guide, machine elves (1x pixel art)."""
from PIL import Image, ImageDraw
import numpy as np, scipy.ndimage as nd, os, colorsys
from props import outline, canvas, C
HERE = os.path.dirname(os.path.abspath(__file__))

def rb(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v); return (int(r * 255), int(g * 255), int(b * 255))

def build_G():
    out = os.path.join(HERE, 'px_G.png')
    if os.path.exists(out): return
    a = np.array(Image.open(os.path.join(HERE, 'raw_G.png'))).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    keep = (b >= r - 6) | ((r - g >= 38) & (r > 170))          # blues / beard / cyan  or  skin
    m = (a[..., 3] > 0) & keep
    m = nd.binary_opening(m, iterations=1)
    lab, n = nd.label(m); sz = nd.sum(m, lab, range(1, n + 1)); m = np.isin(lab, 1 + np.nonzero(sz > 250)[0])
    m = nd.binary_fill_holes(nd.binary_closing(m, iterations=2))
    a[..., 3] = m * 255
    im = Image.fromarray(a.astype(np.uint8)); im = im.crop(im.getbbox()); im.save(os.path.join(HERE, 'raw_Gx.png'))
    ns = {}
    exec(open(os.path.join(HERE, 'clean.py')).read().split("k=66/306")[0], ns)
    prep = ns['prep']
    pal = np.unique(np.concatenate([np.array(Image.open(os.path.join(HERE, f'px_{n}.png')))[..., :3][np.array(Image.open(os.path.join(HERE, f'px_{n}.png')))[..., 3] > 0] for n in 'RECF']), axis=0).astype(float)
    k = 66 / 306
    rgb, mm = prep('Gx', round(im.height * k), 3)
    d = ((rgb[..., None, :] - pal[None, None]) ** 2).sum(-1); q = pal[d.argmin(-1)]
    H, W = mm.shape; o = np.zeros((H + 2, W + 2, 4)); M = np.zeros((H + 2, W + 2), bool); M[1:-1, 1:-1] = mm
    o[1:-1, 1:-1][mm, :3] = q[mm]; o[M, 3] = 255
    ring = nd.binary_dilation(M) & ~M; o[ring, :3] = (10, 14, 42); o[ring, 3] = 255
    Image.fromarray(o.astype(np.uint8)).save(out)

def shaman(beat=0, offer=False, eye_h=0.45):
    """hooded spirit-guide, faces right; frame drum held in front."""
    im, d = canvas(46, 66)
    cloak, dark, trim = (92, 46, 40), (52, 24, 26), (230, 175, 60)
    d.polygon([(12, 20), (30, 20), (40, 65), (4, 65)], fill=C(cloak))                       # robe
    d.polygon([(21, 0), (11, 14), (10, 24), (32, 24), (31, 14)], fill=C(cloak))            # pointed hood
    d.ellipse([13, 9, 31, 27], fill=C(cloak))
    d.ellipse([16, 12, 30, 26], fill=C((16, 8, 20)))                                       # shadowed face
    ec = rb(eye_h, 0.7, 1.0)
    d.rectangle([21, 17, 22, 18], fill=C(ec)); d.rectangle([26, 17, 27, 18], fill=C(ec))   # glowing eyes
    d.line([(21, 27), (19, 64)], fill=C(dark))                                             # robe fold
    for i, x in enumerate(range(6, 40, 4)): d.polygon([(x, 64), (x + 2, 60), (x + 4, 64)], fill=C(trim))
    for i, x in enumerate(range(16, 30, 2)): d.point((x, 28 + abs(x - 23) // 3), fill=C(rb(i / 7)))  # bead necklace
    for i in range(4): d.point((14 + i * 5, 40 + (i % 2)), fill=C(trim))                 # embroidery
    # frame drum on the right
    d.ellipse([28, 28, 45, 45], fill=C((120, 75, 45))); d.ellipse([30, 30, 43, 43], fill=C((235, 205, 155)))
    d.ellipse([34, 34, 39, 39], outline=C((180, 120, 70)))
    # arm + beater
    if offer:
        d.line([(24, 34), (33, 30)], fill=C(dark), width=3); d.rectangle([33, 28, 35, 31], fill=C((150, 110, 90)))
    elif beat:
        d.line([(16, 33), (30, 37)], fill=C(dark), width=3); d.line([(30, 37), (36, 37)], fill=C((200, 170, 120)))
        d.rectangle([35, 36, 37, 38], fill=C((240, 240, 240)))
    else:
        d.line([(16, 33), (24, 26)], fill=C(dark), width=3); d.line([(24, 26), (28, 21)], fill=C((200, 170, 120)))
        d.rectangle([27, 19, 29, 21], fill=C((240, 240, 240)))
    return outline(im)

def elf(h, blink=False):
    """tiny jewelled jester-like 'machine elf'"""
    im, d = canvas(15, 19)
    body, hat, gem = rb(h, 0.75, 1.0), rb(h + 0.33, 0.8, 1.0), rb(h + 0.66, 0.6, 1.0)
    d.polygon([(4, 7), (0, 0), (6, 4), (8, 4), (14, 0), (10, 7)], fill=C(hat))              # two-point hat
    d.point((0, 0), fill=C((255, 220, 70))); d.point((14, 0), fill=C((255, 220, 70)))
    d.rectangle([4, 6, 10, 10], fill=C((245, 200, 160)))                                     # face
    if not blink: d.point((5, 8), fill=C((10, 10, 10))); d.point((9, 8), fill=C((10, 10, 10)))
    else: d.line([(5, 8), (6, 8)], fill=C((10, 10, 10))); d.line([(8, 8), (9, 8)], fill=C((10, 10, 10)))
    d.point((7, 10), fill=C((200, 60, 80)))
    d.polygon([(7, 10), (12, 14), (7, 18), (2, 14)], fill=C(body))                           # diamond body
    d.polygon([(7, 12), (9, 14), (7, 16), (5, 14)], fill=C(gem))
    d.line([(2, 13), (0, 11)], fill=C(body)); d.line([(12, 13), (14, 11)], fill=C(body))     # arms up
    return outline(im)

if __name__ == '__main__':
    build_G()
    G = Image.open(os.path.join(HERE, 'px_G.png'))
    items = [G, shaman(0), shaman(1), shaman(offer=True)] + [elf(i / 6, i == 2) for i in range(6)]
    W = sum(i.width + 6 for i in items) + 6; H = max(i.height for i in items) + 6
    pv = Image.new('RGBA', (W, H), (25, 15, 40, 255)); x = 4
    for i in items: pv.alpha_composite(i, (x, H - 3 - i.height)); x += i.width + 6
    pv.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(HERE, 'props2_preview.png'))
    print('G size', G.size)
