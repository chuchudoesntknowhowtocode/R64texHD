"""Original fighting-game assets (1x pixel art): goblin brawler, boxy car with damage, call-out font, arena props."""
from PIL import Image, ImageDraw
import numpy as np, math, random, os
from props import outline, canvas, C
from lib import U, D, px, rect, snap, FW, SAFE

# ---------------- call-out font (original 5x7) ----------------
F5 = {
 'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"], 'B': ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
 'C': ["01111", "10000", "10000", "10000", "10000", "10000", "01111"], 'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
 'E': ["11111", "10000", "11110", "10000", "10000", "10000", "11111"], 'F': ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
 'G': ["01111", "10000", "10000", "10011", "10001", "10001", "01111"], 'H': ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
 'I': ["11111", "00100", "00100", "00100", "00100", "00100", "11111"], 'K': ["10001", "10010", "11100", "11000", "10100", "10010", "10001"],
 'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"], 'M': ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
 'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"], 'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
 'P': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"], 'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
 'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"], 'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
 'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"], 'W': ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
 'X': ["10001", "01010", "00100", "00100", "01010", "10001", "10001"], 'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
 '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"], '2': ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
 '3': ["11110", "00001", "00001", "01110", "00001", "00001", "11110"], '!': ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
 '.': ["00000", "00000", "00000", "00000", "00000", "00000", "00100"], ' ': ["00000"] * 7, '?': ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
}
F5.update({
 '0': ["01110", "10011", "10101", "10101", "11001", "10001", "01110"], '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
 '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"], '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
 '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"], '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
 '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"]})
# letters the arcade set lacked (same 5x7 style): VS banners and the idle speech-bubble phrases
F5.update({
 'J': ["00111", "00010", "00010", "00010", "00010", "10010", "01100"], 'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
 'V': ["10001", "10001", "10001", "01010", "01010", "00100", "00100"], 'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
 ',': ["00000", "00000", "00000", "00000", "00110", "00100", "01000"], "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
 '-': ["00000", "00000", "00000", "11111", "00000", "00000", "00000"], ':': ["00000", "00100", "00000", "00000", "00000", "00100", "00000"]})
GRAD = [(255, 255, 230), (255, 240, 120), (255, 210, 60), (255, 170, 40), (255, 120, 30), (230, 70, 30), (190, 40, 40)]
def callout(fr, text, cx, cy, s=6, a=255, pop=1.0, grad=GRAD):
    """big outlined arcade call-out. s = size of one font pixel in 2x px (even). pop scales it (bounce-in)."""
    a = int(max(0, min(255, a))); s = max(2, int(round(s * pop / 2)) * 2)
    w = len(text) * 6 * s - s; h = 7 * s
    x0 = snap(cx - w / 2); y0 = snap(cy - h / 2)
    d = D(fr)
    cells = [(x0 + i * 6 * s + c * s, y0 + r * s, r) for i, ch in enumerate(text) for r, row in enumerate(F5[ch]) for c, v in enumerate(row) if v == '1']
    o = max(2, s // 3 * 2 // 2 * 2) if s >= 6 else 2
    for (x, y, r) in cells: d.rectangle([x + o, y + o, x + s - 1 + o * 2, y + s - 1 + o * 2], fill=(20, 8, 30, int(a * 0.8)))   # drop shadow
    for (x, y, r) in cells: d.rectangle([x - o, y - o, x + s - 1 + o, y + s - 1 + o], fill=(10, 8, 24, a))                    # outline
    for (x, y, r) in cells: d.rectangle([x, y, x + s - 1, y + s - 1], fill=grad[r] + (a,))
    for (x, y, r) in cells:
        if r == 0: d.rectangle([x, y, x + s // 2 - 1, y + s // 2 - 1], fill=(255, 255, 255, a))

# ---------------- goblin street brawler (faces right) ----------------
GS, GSD, GL = (110, 190, 70), (70, 135, 45), (165, 225, 110)
BAND, VEST, PANT, WRAP, OUT = (215, 50, 55), (120, 75, 45), (60, 55, 85), (235, 220, 190), (10, 14, 42)
def goblin(pose='stance', f=0):
    im, d = canvas(46, 50)
    bob = 1 if pose == 'stance' and (f // 6) % 2 else 0
    # legs
    if pose == 'jump':
        d.polygon([(14, 32), (20, 32), (16, 40), (10, 38)], fill=C(PANT)); d.polygon([(22, 32), (28, 32), (30, 40), (24, 41)], fill=C(PANT))
        d.rectangle([8, 38, 14, 41], fill=C((70, 45, 30))); d.rectangle([25, 40, 32, 43], fill=C((70, 45, 30)))
    elif pose == 'ko':
        pass
    else:
        sp = 3 if pose == 'punch' else 0
        d.polygon([(13, 33), (19, 33), (16 - sp, 46), (10 - sp, 46)], fill=C(PANT)); d.polygon([(21, 33), (27, 33), (30 + sp, 46), (24 + sp, 46)], fill=C(PANT))
        d.rectangle([7 - sp, 45, 16 - sp, 49], fill=C((70, 45, 30))); d.rectangle([24 + sp, 45, 33 + sp, 49], fill=C((70, 45, 30)))
    if pose == 'ko':
        im2, d2 = canvas(54, 24)                                                                   # lying flat, dazed
        d2.rectangle([10, 12, 40, 20], fill=C(VEST)); d2.rectangle([38, 13, 52, 19], fill=C(PANT)); d2.rectangle([50, 11, 53, 21], fill=C((70, 45, 30)))
        d2.ellipse([0, 6, 16, 22], fill=C(GS)); d2.polygon([(4, 8), (0, 0), (8, 7)], fill=C(GS)); d2.rectangle([2, 7, 14, 10], fill=C(BAND))
        d2.line([(5, 14), (7, 16)], fill=C(OUT)); d2.line([(7, 14), (5, 16)], fill=C(OUT)); d2.line([(10, 14), (12, 16)], fill=C(OUT)); d2.line([(12, 14), (10, 16)], fill=C(OUT))
        d2.rectangle([16, 20, 28, 22], fill=C(GS))
        return outline(im2)
    y = bob
    # torso + vest
    d.rectangle([12, 20 + y, 28, 34 + y], fill=C(GS)); d.polygon([(12, 20 + y), (18, 20 + y), (17, 34 + y), (12, 34 + y)], fill=C(VEST))
    d.polygon([(22, 20 + y), (28, 20 + y), (28, 34 + y), (23, 34 + y)], fill=C(VEST)); d.line([(12, 33 + y), (28, 33 + y)], fill=C((60, 40, 30)))
    # head
    hx = 20 + (2 if pose == 'punch' else 0) - (3 if pose == 'hit' else 0); hy = 3 + y + (1 if pose == 'hit' else 0)
    d.polygon([(hx - 7, hy + 8), (hx - 17, hy + 2), (hx - 8, hy + 12)], fill=C(GS)); d.polygon([(hx + 7, hy + 8), (hx + 17, hy + 2), (hx + 8, hy + 12)], fill=C(GS))  # ears
    d.point((hx - 15, hy + 3), fill=C(GL)); d.point((hx + 15, hy + 3), fill=C(GL))
    d.ellipse([hx - 9, hy, hx + 9, hy + 18], fill=C(GS)); d.ellipse([hx - 6, hy + 2, hx + 1, hy + 7], fill=C(GL))
    d.rectangle([hx - 9, hy + 1, hx + 9, hy + 4], fill=C(BAND)); d.polygon([(hx - 9, hy + 2), (hx - 15, hy - 1), (hx - 14, hy + 5)], fill=C(BAND))  # bandana + tail
    if pose == 'hit':
        d.line([(hx + 1, hy + 7), (hx + 3, hy + 9)], fill=C(OUT)); d.line([(hx + 3, hy + 7), (hx + 1, hy + 9)], fill=C(OUT))
        d.line([(hx + 5, hy + 7), (hx + 7, hy + 9)], fill=C(OUT)); d.line([(hx + 7, hy + 7), (hx + 5, hy + 9)], fill=C(OUT))
        d.ellipse([hx + 2, hy + 12, hx + 6, hy + 16], fill=C(OUT))
    else:
        d.rectangle([hx + 1, hy + 7, hx + 3, hy + 9], fill=C((255, 230, 60))); d.rectangle([hx + 5, hy + 7, hx + 7, hy + 9], fill=C((255, 230, 60)))
        d.point((hx + 3, hy + 8), fill=C(OUT)); d.point((hx + 7, hy + 8), fill=C(OUT))
        d.line([(hx - 1, hy + 6), (hx + 3, hy + 7)], fill=C(GSD)); d.line([(hx + 5, hy + 7), (hx + 8, hy + 6)], fill=C(GSD))   # angry brows
        d.rectangle([hx, hy + 12, hx + 7, hy + 14], fill=C((60, 20, 30))); d.point((hx + 1, hy + 12), fill=C(WRAP)); d.point((hx + 4, hy + 12), fill=C(WRAP)); d.point((hx + 6, hy + 14), fill=C(WRAP))
    # arms + wrapped fists
    if pose == 'punch':
        d.rectangle([24, 22, 40, 25], fill=C(GS)); d.rectangle([39, 20, 45, 27], fill=C(WRAP)); d.line([(41, 20), (41, 27)], fill=C((190, 170, 140)))
        d.polygon([(13, 22), (8, 27), (12, 29), (16, 25)], fill=C(GS)); d.rectangle([6, 26, 11, 31], fill=C(WRAP))
    elif pose == 'hit':
        d.polygon([(26, 22), (34, 16), (36, 19), (28, 25)], fill=C(GS)); d.rectangle([33, 12, 38, 17], fill=C(WRAP))
        d.polygon([(13, 22), (6, 16), (4, 19), (11, 25)], fill=C(GS)); d.rectangle([2, 12, 7, 17], fill=C(WRAP))
    elif pose == 'throw':
        d.polygon([(26, 21), (30, 10), (33, 12), (29, 23)], fill=C(GS)); d.rectangle([29, 5, 35, 11], fill=C(WRAP))
        d.polygon([(13, 22), (8, 27), (12, 29), (16, 25)], fill=C(GS)); d.rectangle([6, 26, 11, 31], fill=C(WRAP))
    else:
        d.polygon([(26, 22), (33, 26), (31, 29), (25, 26)], fill=C(GS)); d.rectangle([31, 22 + y, 37, 28 + y], fill=C(WRAP))
        d.polygon([(14, 22), (20, 27), (19, 30), (13, 26)], fill=C(GS)); d.rectangle([18, 24 + y, 24, 30 + y], fill=C(WRAP))
    return outline(im)

# ---------------- original boxy little car with damage states ----------------
def car(dmg=0, seed=0):
    """dmg 0..5. 0 = shiny, 5 = flattened wreck. faces left."""
    rng = random.Random(seed)
    if dmg >= 5:
        im, d = canvas(84, 22)
        d.polygon([(2, 21), (6, 12), (24, 9), (40, 13), (60, 10), (80, 14), (83, 21)], fill=C((70, 160, 150)))
        for _ in range(14): x = rng.randint(6, 78); d.line([(x, 12), (x + rng.randint(-4, 4), 20)], fill=C((40, 100, 95)))
        d.ellipse([8, 15, 18, 22], fill=C((30, 30, 36))); d.ellipse([64, 16, 72, 22], fill=C((30, 30, 36)))
        d.polygon([(30, 10), (42, 4), (50, 9)], fill=C((150, 200, 230))); d.line([(34, 8), (44, 6)], fill=C((240, 250, 255)))
        return outline(im)
    im, d = canvas(84, 40)
    BODY, BODY_D, BODY_L = (80, 190, 175), (45, 125, 115), (150, 235, 220)
    yoff = 2 if dmg >= 4 else 0
    d.rectangle([2, 16 + yoff, 82, 31], fill=C(BODY)); d.rectangle([2, 26, 82, 31], fill=C(BODY_D))          # lower body
    roof = [(16, 16 + yoff), (24, 3 + yoff * 2), (60, 3 + yoff * 2), (70, 16 + yoff)] if dmg < 4 else [(16, 17), (26, 10), (58, 9), (70, 17)]
    d.polygon(roof, fill=C(BODY))
    glass = (150, 200, 230) if dmg < 2 else (120, 160, 190)
    d.polygon([(20, 15 + yoff), (26, 6 + yoff * 2), (41, 6 + yoff * 2), (41, 15 + yoff)], fill=C(glass)); d.polygon([(45, 15 + yoff), (45, 6 + yoff * 2), (58, 6 + yoff * 2), (65, 15 + yoff)], fill=C(glass))
    if dmg < 2: d.line([(28, 7), (24, 13)], fill=C((240, 250, 255))); d.line([(50, 7), (47, 12)], fill=C((240, 250, 255)))
    d.line([(43, 16 + yoff), (43, 30)], fill=C(BODY_D)); d.rectangle([36, 19 + yoff, 40, 20 + yoff], fill=C(BODY_D))   # door line + handle
    d.rectangle([2, 17 + yoff, 4, 22 + yoff], fill=C((255, 240, 160))); d.rectangle([80, 17 + yoff, 82, 21 + yoff], fill=C((220, 50, 50)))  # lights
    d.rectangle([0, 27, 6, 30], fill=C((180, 185, 195))); d.rectangle([78, 27, 84, 30], fill=C((180, 185, 195)))         # bumpers
    d.line([(6, 20 + yoff), (78, 20 + yoff)], fill=C(BODY_L))
    wl = [(10, 26, 24, 39), (60, 26, 74, 39)]
    for k, (x0, y0, x1, y1) in enumerate(wl):
        if dmg >= 3 and k == 0: continue                                                              # front wheel knocked off
        d.ellipse([x0, y0, x1, y1], fill=C((30, 30, 36))); d.ellipse([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=C((170, 175, 185)))
    if dmg >= 1:                                                                                      # dents
        for _ in range(2 + dmg * 3):
            x, y = rng.randint(6, 76), rng.randint(17, 28); d.ellipse([x, y, x + rng.randint(3, 6), y + rng.randint(2, 4)], fill=C(BODY_D))
    if dmg >= 2:                                                                                      # cracked glass
        for cx_ in (32, 53):
            for _ in range(5): d.line([(cx_, 10 + yoff), (cx_ + rng.randint(-8, 8), 10 + yoff + rng.randint(-5, 5))], fill=C((235, 245, 255)))
    if dmg >= 3:
        d.polygon([(2, 16), (14, 8), (20, 16)], fill=C(BODY))                                         # popped hood
        d.rectangle([12, 33, 22, 38], fill=C((20, 18, 24)))                                            # axle stub
    if dmg >= 4:
        d.rectangle([44, 16, 66, 30], fill=C((40, 36, 44)))                                           # door gone
        d.line([(46, 18), (64, 28)], fill=C((70, 66, 76)))
    return outline(im)

# ---------------- arena props ----------------
def torch(f):
    im, d = canvas(14, 46)
    d.rectangle([5, 14, 8, 45], fill=C((90, 60, 40))); d.rectangle([2, 10, 11, 15], fill=C((70, 70, 80))); d.rectangle([2, 10, 11, 11], fill=C((120, 120, 130)))
    rng = random.Random(f // 2)
    for k, (col, w, h) in enumerate([((230, 60, 30), 5, 10), ((255, 150, 30), 4, 8), ((255, 230, 120), 2, 5)]):
        sway = rng.randint(-1, 1); d.polygon([(7 - w + sway, 10), (7 + sway + rng.randint(-1, 1), 10 - h), (7 + w + sway, 10)], fill=C(col))
    return outline(im)
def crowd(f, n=26, seed=0):
    """row of cheering silhouettes, 1x, width n*9"""
    rng = random.Random(seed); im, d = canvas(n * 9 + 4, 22)
    for i in range(n):
        h = rng.randint(0, 3); cheer = (f // 4 + i) % 3 == 0
        x = 2 + i * 9; y = 8 + h - (2 if cheer else 0)
        col = rng.choice([(50, 30, 75), (60, 36, 88), (42, 26, 66)])
        d.ellipse([x + 1, y, x + 7, y + 6], fill=C(col)); d.rectangle([x, y + 6, x + 8, 21], fill=C(col))
        if cheer: d.line([(x, y + 7), (x - 2, y + 1)], fill=C(col)); d.line([(x + 8, y + 7), (x + 10, y + 1)], fill=C(col))
    return im

if __name__ == '__main__':
    import lib
    fr = lib.new(); lib.D(fr)
    items = [goblin(p) for p in ('stance', 'punch', 'hit', 'jump', 'throw', 'ko')] + [car(k) for k in range(6)] + [torch(0), torch(3)]
    x = 200
    for it in items:
        im = U(it); fr.paste(im, (x, 372 - im.height), im); x += im.width + 10
    c = U(crowd(0, 20)); fr.paste(c, (200, 250), c)
    callout(fr, 'ROUND 1', 1100, 262, s=6); callout(fr, 'K.O.', 600, 262, s=8)
    fr = lib.finish(fr); fr.crop((180, 200, 1780, 416)).save(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fight_preview.png'))
