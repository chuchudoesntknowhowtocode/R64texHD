"""Builds the folded-menu icons: app/assets/nav/<name>.png, 32 x 32 RGBA.

    python3 build/nav_icons.py

rt64, classic (G64) and ship come from the owner's images in build/nav-src (white background removed, scaled down).
The rest are drawn here pixel by pixel.
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'app', 'assets', 'nav')
os.makedirs(OUT, exist_ok=True)
N = 32
K = (12, 6, 24, 255)            # outline


def new():
    return Image.new('RGBA', (N, N), (0, 0, 0, 0))


def px(im, x, y, c):
    if 0 <= x < N and 0 <= y < N:
        im.putpixel((x, y), c)


def rect(im, x0, y0, x1, y1, c):
    ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], fill=c)


def outline(im, col=K):
    """1-px dark outline around everything drawn (pixel-art look on any background)."""
    a = im.split()[3].load()
    out = im.copy()
    for y in range(N):
        for x in range(N):
            if a[x, y]:
                continue
            if any(0 <= x + dx < N and 0 <= y + dy < N and a[x + dx, y + dy] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), col)
    return out


# 3x5 pixel font for the .rtz label
F3 = {'o': ['000', '010', '101', '101', '010'], '2': ['110', '001', '010', '100', '111'],
      '.': ['000', '000', '000', '000', '010'], 'r': ['000', '101', '110', '100', '100'],
      't': ['010', '111', '010', '010', '011'], 'z': ['000', '111', '001', '010', '111']}


def text3(im, s, x, y, c):
    for ch in s:
        for r, row in enumerate(F3[ch]):
            for cc, v in enumerate(row):
                if v == '1':
                    px(im, x + cc, y + r, c)
        x += 4


def upscale():
    """a bar graph climbing, with an arrow going up and to the right"""
    im = new()
    rect(im, 2, 3, 3, 28, (185, 166, 214, 255)); rect(im, 2, 27, 29, 28, (185, 166, 214, 255))        # axes
    bars = [(6, 21), (11, 16), (16, 11), (21, 6)]
    cols = [((255, 209, 102), (184, 134, 46)), ((255, 154, 106), (200, 87, 74)), ((255, 106, 213), (168, 63, 140)), ((196, 140, 255), (123, 85, 179))]
    for (x, top), (c, d) in zip(bars, cols):
        rect(im, x, top, x + 3, 26, c + (255,))
        rect(im, x + 3, top, x + 3, 26, d + (255,))                     # shade
        rect(im, x, top, x + 3, top, (255, 255, 255, 255))             # cap highlight
    # arrow: zigzag line over the bars, head at top right
    pts = [(5, 19), (10, 14), (14, 16), (21, 7), (26, 3)]
    d = ImageDraw.Draw(im)
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=(63, 207, 122, 255), width=2)
    for (x, y) in [(22, 2), (23, 2), (24, 2), (25, 2), (26, 2), (27, 2), (27, 3), (27, 4), (27, 5), (27, 6), (27, 7), (26, 3), (26, 4)]:
        px(im, x, y, (63, 207, 122, 255))
    return outline(im)


def rtz():
    """a zip file with a zipper and a .rtz label"""
    im = new()
    body, shade, fold = (255, 209, 102, 255), (184, 134, 46, 255), (255, 236, 180, 255)
    # page with a folded corner
    rect(im, 5, 2, 26, 29, body)
    for i in range(6):                                   # folded corner, top right
        for j in range(6 - i):
            px(im, 26 - j, 2 + i, (0, 0, 0, 0))
    for i in range(6):
        for j in range(i + 1):
            px(im, 21 + j, 2 + i, fold)
    rect(im, 26, 8, 26, 29, shade); rect(im, 5, 29, 26, 29, shade)
    # zipper: a dark track with big silver teeth, then a large pull tab
    rect(im, 12, 2, 18, 15, (60, 40, 20, 255))
    for y in range(2, 15, 2):
        rect(im, 12, y, 14, y, (230, 234, 245, 255)); rect(im, 16, y + 1, 18, y + 1, (230, 234, 245, 255))
    rect(im, 11, 15, 19, 21, (154, 163, 181, 255)); rect(im, 11, 15, 19, 15, (230, 234, 245, 255)); rect(im, 19, 16, 19, 21, (91, 98, 116, 255))
    rect(im, 14, 17, 16, 19, (40, 30, 50, 255))
    # .rtz label
    rect(im, 3, 22, 28, 29, (242, 112, 107, 255)); rect(im, 3, 29, 28, 29, (168, 50, 60, 255))
    text3(im, '.rtz', 8, 23, (255, 255, 255, 255))
    return outline(im)


def ship():
    """a little sailing ship on the waves"""
    im = new()
    white, sh = (241, 228, 255, 255), (185, 166, 214, 255)
    rect(im, 15, 2, 15, 22, (138, 90, 59, 255))                         # main mast
    rect(im, 22, 8, 22, 22, (138, 90, 59, 255))                         # rear mast
    for i, (x, y) in enumerate([(16, 2), (17, 2), (18, 3), (16, 3), (17, 3)]):
        px(im, x, y, (255, 100, 100, 255))                              # pennant
    for y in range(5, 19):                                              # main sail (left of the mast)
        w = (y - 4) * 10 // 14
        rect(im, 14 - w, y, 14, y, white); px(im, 14 - w, y, sh)
    for y in range(10, 20):                                             # rear sail
        w = (y - 9) * 5 // 10
        rect(im, 16, y, 16 + w, y, white); px(im, 16 + w, y, sh)
    for y in range(11, 20):
        w = (y - 10) * 5 // 9
        rect(im, 23, y, 23 + w, y, white)
    # hull
    rect(im, 3, 21, 29, 22, (138, 90, 59, 255)); rect(im, 5, 23, 27, 24, (110, 70, 45, 255)); rect(im, 7, 25, 25, 25, (90, 58, 38, 255))
    rect(im, 3, 21, 29, 21, (190, 130, 85, 255))
    for x in range(6, 26, 4):
        px(im, x, 22, (255, 209, 102, 255))                             # portholes
    # waves
    for x in range(1, 31):
        y = 27 + (1 if (x // 3) % 2 else 0)
        px(im, x, y, (108, 198, 255, 255)); px(im, x, y + 1, (47, 127, 184, 255))
    return outline(im)


def roms():
    """a cartridge under a magnifying glass"""
    im = new()
    g, dg, lg = (154, 163, 181, 255), (91, 98, 116, 255), (200, 206, 220, 255)
    rect(im, 3, 2, 22, 24, g); rect(im, 3, 2, 22, 3, lg); rect(im, 21, 4, 22, 24, dg)
    rect(im, 6, 5, 19, 13, (108, 198, 255, 255)); rect(im, 6, 5, 19, 6, (190, 230, 255, 255)); rect(im, 8, 9, 17, 10, (47, 127, 184, 255))   # label
    for x in range(5, 21, 3):
        rect(im, x, 16, x, 22, dg)                                       # grip ridges
    rect(im, 6, 24, 19, 26, dg)                                          # connector
    # magnifier
    d = ImageDraw.Draw(im)
    d.ellipse([13, 11, 27, 25], fill=(180, 230, 255, 150), outline=(241, 228, 255, 255), width=2)
    px(im, 17, 14, (255, 255, 255, 255)); px(im, 16, 15, (255, 255, 255, 255)); px(im, 16, 16, (255, 255, 255, 255))
    d.line([(25, 23), (30, 28)], fill=(138, 90, 59, 255), width=3)
    return outline(im)


def settings():
    im = new()
    d = ImageDraw.Draw(im)
    c, s = (241, 228, 255, 255), (185, 166, 214, 255)
    import math
    for k in range(8):
        a = k * math.pi / 4
        cx, cy = 16 + 11 * math.cos(a), 16 + 11 * math.sin(a)
        d.rectangle([round(cx) - 2, round(cy) - 2, round(cx) + 2, round(cy) + 2], fill=c)
    d.ellipse([6, 6, 26, 26], fill=c)
    d.ellipse([11, 11, 21, 21], fill=s)
    d.ellipse([13, 13, 19, 19], fill=(0, 0, 0, 0))
    return outline(im)


def about():
    im = new()
    v, dv, w = (196, 140, 255, 255), (123, 85, 179, 255), (255, 255, 255, 255)
    rect(im, 3, 3, 28, 23, v); rect(im, 2, 5, 29, 21, v)
    rect(im, 4, 22, 28, 23, dv); rect(im, 28, 5, 29, 21, dv)
    for i in range(5):
        rect(im, 6, 24 + i, 10 - i, 24 + i, v)                           # tail
    rect(im, 14, 6, 17, 9, w)
    rect(im, 12, 11, 17, 12, w); rect(im, 14, 13, 17, 18, w); rect(im, 12, 19, 19, 20, w)
    return outline(im)


def queue():
    """a list with a play arrow: jobs lined up"""
    im = new()
    rows = [(4, (255, 154, 106)), (12, (196, 140, 255)), (20, (196, 140, 255))]
    for y, c in rows:
        rect(im, 2, y, 5, y + 4, c + (255,)); rect(im, 8, y + 1, 22, y + 3, (241, 228, 255, 255)); rect(im, 8, y + 3, 22, y + 3, (185, 166, 214, 255))
    for i in range(7):                                                     # play arrow, right
        rect(im, 24, 9 + i, 24 + min(i, 6 - i), 9 + i, (63, 207, 122, 255))
    return outline(im)


def cutout(im, step=22):
    """removes the background: everything joined to the border by small colour steps (flat white, or a soft gradient)"""
    from collections import deque
    W, H = im.size; p = im.load()
    seen = [[False] * W for _ in range(H)]
    q = deque((x, y) for x in range(W) for y in (0, H - 1)); q.extend((x, y) for y in range(H) for x in (0, W - 1))
    for x, y in q: seen[y][x] = True
    bg = []
    while q:
        x, y = q.popleft(); bg.append((x, y)); c = p[x, y]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx]:
                n = p[nx, ny]
                if abs(n[0] - c[0]) + abs(n[1] - c[1]) + abs(n[2] - c[2]) <= step:
                    seen[ny][nx] = True; q.append((nx, ny))
    for x, y in bg: p[x, y] = (0, 0, 0, 0)
    return im


def cutout_hue(im, lo=42, hi=150, smin=0.22, vmin=0.4):
    """removes a green-to-yellow background (and its soft glow) by colour: those hues go, the ship stays"""
    import colorsys
    p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            h, sat, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if lo <= h * 360 <= hi and sat >= smin and v >= vmin:
                p[x, y] = (0, 0, 0, 0)
    return im


def from_image(src, label=None, step=22, crop_top=0):
    """the owner's image: background removed, cropped, scaled to 32 x 32 (optional label on top)"""
    im = Image.open(os.path.join(HERE, 'nav-src', src)).convert('RGBA')
    im = cutout_hue(im) if step == 'hue' else cutout(im, step)
    im = im.crop(im.getbbox())
    if crop_top:                                                         # e.g. the ship's flag pole, so the ship itself can be bigger
        im = im.crop((0, round(im.height * crop_top), im.width, im.height)); im = im.crop(im.getbbox())
    bw, bh = (32, 31) if label else (30, 30)                          # with a label: leave room for it at the bottom
    s = min(bw / im.width, bh / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    if crop_top:                                                         # small photo-like art: crisper and punchier at 32 px
        from PIL import ImageEnhance, ImageFilter
        a_ = im.split()[3]; rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1, percent=70, threshold=2))
        rgb = ImageEnhance.Contrast(ImageEnhance.Color(rgb).enhance(1.15)).enhance(1.1)
        im = rgb.convert('RGBA'); im.putalpha(a_)
    out = new(); out.alpha_composite(im, ((N - im.width) // 2 - (2 if label else 0), 0 if label else (N - im.height) // 2))
    if label:                                                            # e.g. .o2r, like the .rtz icon
        lab = new()
        rect(lab, 13, 24, 30, 30, (196, 140, 255, 255)); rect(lab, 13, 30, 30, 30, (123, 85, 179, 255))   # small tag, bottom right
        text3(lab, label, 15, 25, (255, 255, 255, 255))
        out.alpha_composite(outline(lab))
    return out


ICONS = {'queue': queue, 'upscale': upscale, 'rtz': rtz, 'roms': roms, 'settings': settings, 'about': about,
         'rt64': lambda: from_image('rt64-source.png'), 'classic': lambda: from_image('g64-source.png'),
         'ship': lambda: from_image('ship-source.png', '.o2r', step='hue', crop_top=0.16)}

if __name__ == '__main__':
    for name, fn in ICONS.items():
        fn().save(os.path.join(OUT, name + '.png'))
        print(name)
