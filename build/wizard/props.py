"""1x pixel-art props for the spells & potions scenes (scaled 2x with U())."""
from PIL import Image, ImageDraw
import numpy as np, scipy.ndimage as nd, math
from lib import U
OL = (10, 14, 42)

def outline(im, col=OL):
    a = np.array(im); m = a[..., 3] > 0
    H, W = m.shape; o = np.zeros((H + 2, W + 2, 4), np.uint8); o[1:-1, 1:-1] = a
    mm = np.zeros((H + 2, W + 2), bool); mm[1:-1, 1:-1] = m
    ring = nd.binary_dilation(mm) & ~mm; o[ring, :3] = col; o[ring, 3] = 255
    return Image.fromarray(o)
def canvas(w, h): im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)
def C(c, a=255): return tuple(c) + (a,)

def cauldron(f=0):
    im, d = canvas(34, 26)
    d.rectangle([5, 21, 8, 25], fill=C((40, 36, 52))); d.rectangle([25, 21, 28, 25], fill=C((40, 36, 52)))
    d.ellipse([1, 5, 32, 25], fill=C((48, 44, 62)))
    d.ellipse([4, 9, 14, 19], fill=C((70, 66, 88)))                     # sheen
    d.rectangle([0, 4, 33, 8], fill=C((70, 66, 88))); d.rectangle([0, 4, 33, 4], fill=C((110, 105, 130)))
    d.ellipse([3, 2, 30, 8], fill=C((60, 210, 80)))                     # potion surface
    d.ellipse([7, 3, 18, 6], fill=C((140, 255, 120)))
    for i in range(3):                                                    # bubbles on surface
        x = 6 + ((f * 3 + i * 9) % 22); d.point((x, 3 + (i % 2)), fill=C((210, 255, 200)))
    return outline(im)
CAULDRON_LIQ_Y = 4     # 1x row of the potion surface (+1 for outline)

def book(open_=1.0, flap=0.0, page=None):
    """open_: 0 closed .. 1 flat. flap: -1..1 wing angle when flying. page: 0..1 flipping page."""
    W, H = 40, 30; im, d = canvas(W, H); cx, cy = 20, 18
    if open_ < 0.15:
        d.rectangle([cx - 9, cy - 3, cx + 9, cy + 3], fill=C((150, 40, 50))); d.rectangle([cx - 9, cy - 1, cx + 9, cy], fill=C((240, 225, 190)))
        d.rectangle([cx - 2, cy - 3, cx + 2, cy + 3], fill=C((255, 200, 60)))
        return outline(im)
    ang = math.radians(15 + 60 * (1 - open_) + 35 * flap)
    L = 16
    for side in (-1, 1):
        ex = cx + side * L * math.cos(ang); ey = cy - L * math.sin(ang)
        d.polygon([(cx, cy + 3), (cx, cy), (ex, ey), (ex, ey + 4)], fill=C((150, 40, 50)))               # cover
        d.polygon([(cx, cy + 1), (cx, cy - 1), (ex - side, ey - 1), (ex - side, ey + 2)], fill=C((240, 225, 190)))  # pages
        for k in (0.35, 0.6, 0.85):
            d.point((round(cx + side * L * k * math.cos(ang)), round(cy - 1 - L * k * math.sin(ang) + 1)), fill=C((120, 100, 140)))
    if page is not None:
        pa = math.radians(15 + 150 * page); ex = cx + L * math.cos(pa) * (1 if page < 1 else -1); ey = cy - L * math.sin(pa)
        d.polygon([(cx, cy), (cx, cy - 1), (ex, ey - 1), (ex, ey + 1)], fill=C((255, 245, 215)))
    d.rectangle([cx - 1, cy - 1, cx + 1, cy + 3], fill=C((255, 200, 60)))
    return outline(im)

def potion(col=(80, 140, 255), tilt=0):
    im, d = canvas(13, 17)
    d.ellipse([1, 5, 11, 15], fill=C((200, 220, 240, ), 255)); d.ellipse([2, 8, 10, 15], fill=C(col))
    d.rectangle([4, 1, 8, 6], fill=C((200, 220, 240))); d.rectangle([4, 0, 8, 2], fill=C((150, 100, 60)))
    d.point((3, 9), fill=C((255, 255, 255))); d.point((4, 10), fill=C((255, 255, 255)))
    im = outline(im)
    return im.rotate(tilt, expand=True, resample=Image.NEAREST) if tilt else im

def owl(flap=0):
    im, d = canvas(26, 20); cx = 13
    wy = [2, 7, 12][flap % 3]
    d.polygon([(cx - 5, 9), (1, wy), (3, wy + 6), (cx - 4, 14)], fill=C((90, 58, 34)))     # wings
    d.polygon([(cx + 5, 9), (25, wy), (23, wy + 6), (cx + 4, 14)], fill=C((90, 58, 34)))
    d.ellipse([cx - 6, 4, cx + 6, 19], fill=C((140, 95, 55)))
    d.ellipse([cx - 4, 10, cx + 4, 18], fill=C((225, 195, 145)))
    d.polygon([(cx - 6, 5), (cx - 5, 1), (cx - 3, 5)], fill=C((140, 95, 55))); d.polygon([(cx + 6, 5), (cx + 5, 1), (cx + 3, 5)], fill=C((140, 95, 55)))
    for ex in (cx - 3, cx + 3):
        d.ellipse([ex - 2, 5, ex + 2, 9], fill=C((255, 240, 180))); d.point((ex, 7), fill=C((20, 10, 10))); d.point((ex, 6), fill=C((20, 10, 10)))
    d.polygon([(cx - 1, 9), (cx + 1, 9), (cx, 11)], fill=C((255, 180, 40)))
    d.point((cx - 2, 19), fill=C((255, 180, 40))); d.point((cx + 2, 19), fill=C((255, 180, 40)))
    return outline(im)

def frog(jump=False, hat=None):
    im, d = canvas(24, 22)
    G, LG, DG = (70, 200, 70), (150, 240, 120), (30, 120, 40)
    if jump:
        d.ellipse([5, 7, 19, 17], fill=C(G)); d.ellipse([8, 11, 16, 17], fill=C(LG))
        d.line([(6, 15), (1, 21)], fill=C(DG), width=2); d.line([(18, 15), (23, 21)], fill=C(DG), width=2)
        d.line([(7, 11), (3, 6)], fill=C(G), width=2); d.line([(17, 11), (21, 6)], fill=C(G), width=2)
    else:
        d.ellipse([3, 10, 21, 21], fill=C(G)); d.ellipse([7, 14, 17, 21], fill=C(LG))
        d.ellipse([1, 16, 7, 21], fill=C(DG)); d.ellipse([17, 16, 23, 21], fill=C(DG))
    ey = 8 if not jump else 5
    for ex in (8, 16):
        d.ellipse([ex - 3, ey - 2, ex + 2, ey + 3], fill=C(G)); d.rectangle([ex - 2, ey - 1, ex + 1, ey + 1], fill=C((255, 255, 255))); d.point((ex - 1, ey), fill=C((10, 10, 10)))
    d.line([(9, ey + 6), (15, ey + 6)], fill=C(DG))
    im = outline(im)
    if hat is not None:
        h = hat.resize((max(1, hat.width // 2), max(1, hat.height // 2)), Image.NEAREST)
        out = Image.new('RGBA', (im.width, im.height + h.height - 4), (0, 0, 0, 0))
        out.paste(im, (0, h.height - 4), im); out.paste(h, ((im.width - h.width) // 2, 0), h); im = out
    return im

def crystal_ball(swirl=0, stand=True):
    im, d = canvas(32, 36); cx, cy, r = 16, 15, 13
    if stand:
        d.polygon([(8, 34), (24, 34), (21, 27), (11, 27)], fill=C((200, 150, 40))); d.rectangle([8, 33, 24, 35], fill=C((150, 100, 30)))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C((120, 80, 200)))
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=C((160, 120, 235)))
    d.ellipse([cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5], fill=C((190, 160, 250)))
    for i in range(6):
        a = swirl * 0.25 + i * 1.047; d.point((round(cx + 7 * math.cos(a)), round(cy + 7 * math.sin(a))), fill=C((250, 230, 255)))
    d.rectangle([cx - 8, cy - 9, cx - 6, cy - 7], fill=C((255, 255, 255))); d.point((cx - 9, cy - 5), fill=C((255, 255, 255)))
    return outline(im)
BALL_C = (17, 16)   # ball centre in the outlined 1x image

def stone():
    im, d = canvas(40, 18)
    d.polygon([(2, 17), (5, 6), (12, 2), (26, 1), (34, 5), (38, 17)], fill=C((110, 110, 125)))
    d.polygon([(6, 16), (8, 7), (14, 4), (20, 4), (16, 10), (12, 16)], fill=C((140, 140, 158)))
    d.line([(24, 8), (30, 12)], fill=C((80, 80, 95))); d.line([(28, 3), (32, 7)], fill=C((80, 80, 95)))
    return outline(im)
def sword():
    im, d = canvas(13, 36); cx = 6
    d.rectangle([cx - 1, 0, cx + 1, 2], fill=C((255, 200, 60)))                        # pommel
    d.rectangle([cx - 1, 3, cx + 1, 8], fill=C((120, 70, 40)))                          # grip
    d.rectangle([0, 9, 12, 10], fill=C((255, 200, 60)))                                 # guard
    d.rectangle([cx - 1, 11, cx + 1, 34], fill=C((210, 225, 240))); d.line([(cx, 11), (cx, 33)], fill=C((255, 255, 255)))
    d.point((cx, 35), fill=C((210, 225, 240)))
    return outline(im)

def hourglass(sand=0.0):
    """sand: 0 all on top .. 1 all at bottom"""
    im, d = canvas(26, 40); G, S, GL = (255, 200, 60), (240, 200, 120), (180, 210, 240)
    d.rectangle([0, 0, 25, 3], fill=C(G)); d.rectangle([0, 36, 25, 39], fill=C(G))
    d.rectangle([1, 4, 2, 35], fill=C((150, 100, 30))); d.rectangle([23, 4, 24, 35], fill=C((150, 100, 30)))
    d.polygon([(4, 4), (21, 4), (14, 19), (14, 21), (21, 35), (4, 35), (11, 21), (11, 19)], fill=C(GL, 200))
    top = 1 - sand
    if top > 0.02:
        y0 = 4 + int(13 * (1 - top)); d.polygon([(4 + (y0 - 4) * 7 // 15, y0), (21 - (y0 - 4) * 7 // 15, y0), (13, 18)], fill=C(S))
    if sand > 0.02:
        y1 = 35 - int(13 * sand); w = (35 - y1) * 7 // 15
        d.polygon([(4, 35), (21, 35), (21 - (35 - y1) * 0, 35), (13 + w, y1), (12 - w, y1)], fill=C(S))
    if 0.02 < sand < 0.98: d.line([(12, 19), (12, 34)], fill=C(S))
    return outline(im)

def fireball(f, r=9):
    im, d = canvas(r * 2 + 6, r * 2 + 6); c = r + 3; j = (f % 2)
    d.ellipse([c - r, c - r + j, c + r, c + r - j], fill=C((230, 60, 30)))
    r2 = max(1, r - 3); r3 = max(0, r - 6)
    d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=C((255, 150, 30)))
    if r3 > 0: d.ellipse([c - r3, c - r3, c + r3, c + r3], fill=C((255, 230, 120)))
    return im

def preview(path):
    items = [cauldron(), book(1, 0, 0.5), book(0.6, 0.8), potion(), potion((230, 60, 60)), owl(0), owl(1), owl(2),
             frog(), frog(True), crystal_ball(), stone(), sword(), hourglass(0.3), hourglass(0.8), fireball(0)]
    W = sum(i.width + 4 for i in items); H = max(i.height for i in items)
    pv = Image.new('RGBA', (W + 4, H + 4), (25, 15, 40, 255)); x = 2
    for i in items: pv.alpha_composite(i, (x, H + 2 - i.height)); x += i.width + 4
    pv.resize((pv.width * 4, pv.height * 4), Image.NEAREST).save(path)
if __name__ == '__main__':
    preview('/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/props_preview.png')
