"""Original opponents (1x pixel art, face right): stone golem, clockwork ninja robot; plus projectiles & debris."""
from PIL import Image, ImageDraw, ImageOps
import numpy as np, math, random, os
from props import outline, canvas, C
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- stone golem ----------------
ST, ST_D, ST_L, MOSS, EYE = (124, 116, 108), (84, 78, 74), (164, 156, 144), (92, 146, 64), (255, 170, 50)
def _block(d, box, col=ST):
    x0, y0, x1, y1 = box; d.rectangle(box, fill=C(col)); d.line([(x0, y0), (x1, y0)], fill=C(ST_L)); d.line([(x0, y1), (x1, y1)], fill=C(ST_D))
def golem(pose='stance', f=0):
    im, d = canvas(64, 74); bob = 1 if pose == 'stance' and (f // 8) % 2 else 0
    crouch = 6 if pose == 'pound' else 0
    # legs
    _block(d, (16, 54, 26, 73), ST_D); _block(d, (34, 54, 44, 73), ST_D)
    d.rectangle([14, 70, 28, 73], fill=C((70, 64, 60))); d.rectangle([32, 70, 46, 73], fill=C((70, 64, 60)))
    y = bob + crouch
    _block(d, (10, 22 + y, 50, 56), ST)                                          # torso
    for (a, b_) in [((16, 30 + y), (24, 40 + y)), ((38, 26 + y), (32, 36 + y)), ((22, 46), (30, 50))]: d.line([a, b_], fill=C(ST_D))   # cracks
    d.ellipse([12, 22 + y, 22, 28 + y], fill=C(MOSS)); d.rectangle([40, 50, 48, 53], fill=C(MOSS))
    d.ellipse([26, 34 + y, 34, 42 + y], fill=C((255, 120, 30))); d.ellipse([28, 36 + y, 32, 40 + y], fill=C(EYE))   # glowing core
    _block(d, (21, 6 + y, 41, 24 + y), ST)                                      # head
    d.rectangle([21, 6 + y, 41, 9 + y], fill=C(ST_D))
    if pose == 'hit': d.line([(29, 14 + y), (33, 18 + y)], fill=C(EYE)); d.line([(33, 14 + y), (29, 18 + y)], fill=C(EYE)); d.line([(36, 14 + y), (40, 18 + y)], fill=C(EYE)); d.line([(40, 14 + y), (36, 18 + y)], fill=C(EYE))
    else: d.rectangle([29, 14 + y, 32, 16 + y], fill=C(EYE)); d.rectangle([36, 14 + y, 39, 16 + y], fill=C(EYE)); d.line([(28, 12 + y), (33, 13 + y)], fill=C(ST_D)); d.line([(35, 13 + y), (40, 12 + y)], fill=C(ST_D))
    d.rectangle([30, 20 + y, 39, 21 + y], fill=C((50, 44, 44)))
    # arms
    if pose in ('raise', 'throw'):
        _block(d, (2, 0, 12, 26 + y)); _block(d, (48, 0, 58, 26 + y)) if pose == 'raise' else _block(d, (50, 18 + y, 60, 46 + y))
        d.rectangle([0, 0, 14, 8], fill=C(ST_D)) if pose == 'raise' else None
        if pose == 'raise': d.rectangle([46, 0, 60, 8], fill=C(ST_D))
    elif pose == 'pound':
        _block(d, (0, 30 + y, 12, 62)); _block(d, (48, 30 + y, 62, 62)); d.rectangle([0, 60, 14, 67], fill=C(ST_D)); d.rectangle([46, 60, 62, 67], fill=C(ST_D))
    elif pose == 'hit':
        _block(d, (2, 14, 12, 40)); _block(d, (48, 10, 58, 36))
    else:
        _block(d, (2, 22 + y, 12, 52 + y)); _block(d, (48, 22 + y, 60, 52 + y)); d.rectangle([0, 50 + y, 14, 58 + y], fill=C(ST_D)); d.rectangle([46, 50 + y, 62, 58 + y], fill=C(ST_D))
    return outline(im)
def boulder(f=0):
    im, d = canvas(16, 14); d.polygon([(2, 4), (6, 0), (12, 1), (15, 6), (13, 12), (6, 13), (0, 9)], fill=C(ST)); d.line([(4, 3), (8, 2)], fill=C(ST_L)); d.line([(6, 8), (10, 10)], fill=C(ST_D))
    im = outline(im); return im.rotate((f * 45) % 360, expand=True, resample=Image.NEAREST) if f else im

# ---------------- clockwork ninja robot ----------------
BR, BR_D, BR_L, STL, STL_D, HOOD, SCARF, VIS = (200, 150, 60), (130, 90, 40), (240, 200, 110), (150, 156, 168), (96, 100, 112), (30, 28, 40), (210, 40, 50), (255, 60, 60)
def _gear(d, cx, cy, r, col=BR, teeth=8):
    for k in range(teeth):
        a = k / teeth * 6.283; d.rectangle([cx + (r + 1) * math.cos(a) - 1, cy + (r + 1) * math.sin(a) - 1, cx + (r + 1) * math.cos(a), cy + (r + 1) * math.sin(a)], fill=C(col))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C(col)); d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=C(BR_D))
def robot(pose='stance', f=0, fist=True):
    im, d = canvas(58, 62); lean = 6 if pose in ('dash', 'punch', 'throw') else (-4 if pose == 'hit' else 0)
    sc = (f // 2) % 3
    # scarf tails flow behind (left)
    d.polygon([(14 + lean, 16), (2, 14 + sc * 2), (0, 20 + sc), (14 + lean, 20)], fill=C(SCARF))
    # legs
    if pose == 'dash':
        d.line([(22, 40), (14, 50), (6, 58)], fill=C(STL), width=4); d.line([(28, 40), (36, 50), (40, 60)], fill=C(STL), width=4)
        d.rectangle([2, 57, 10, 60], fill=C(STL_D)); d.rectangle([37, 58, 45, 61], fill=C(STL_D))
    else:
        d.line([(22, 40), (18, 50), (16, 60)], fill=C(STL), width=4); d.line([(30, 40), (34, 50), (36, 60)], fill=C(STL), width=4)
        d.ellipse([16, 47, 22, 53], fill=C(BR)); d.ellipse([31, 47, 37, 53], fill=C(BR))
        d.rectangle([12, 58, 21, 61], fill=C(STL_D)); d.rectangle([32, 58, 41, 61], fill=C(STL_D))
    # torso (brass) with chest gear
    d.polygon([(16 + lean, 18), (34 + lean, 18), (32, 40), (18, 40)], fill=C(BR)); d.line([(17 + lean, 19), (33 + lean, 19)], fill=C(BR_L))
    _gear(d, 25 + lean // 2, 28, 4, BR_L, teeth=8)
    for k in range(3): d.point((19 + k * 5, 37), fill=C(BR_D))
    # head: hood + visor
    hx = 25 + lean
    d.ellipse([hx - 9, 2, hx + 9, 20], fill=C(HOOD)); d.rectangle([hx - 1, 9, hx + 9, 12], fill=C((60, 10, 14)))
    d.rectangle([hx + 1, 10, hx + 8, 11], fill=C(VIS if (f // 6) % 4 else (255, 200, 200)))
    d.rectangle([hx - 9, 15, hx + 9, 18], fill=C(SCARF))
    # arms
    sh = (30 + lean, 21)
    if pose == 'punch':
        d.line([sh, (46, 20)], fill=C(STL), width=4)
        if fist: d.rectangle([46, 16, 53, 24], fill=C(BR)); d.rectangle([47, 17, 52, 18], fill=C(BR_L))
        else: d.rectangle([45, 18, 48, 22], fill=C(BR_D))
    elif pose == 'throw':
        d.line([sh, (44, 14)], fill=C(STL), width=4); d.rectangle([43, 10, 48, 15], fill=C(BR))
    elif pose == 'hit':
        d.line([sh, (36, 6)], fill=C(STL), width=4); d.rectangle([34, 2, 39, 7], fill=C(BR))
    else:
        d.line([sh, (38, 28), (42, 22)], fill=C(STL), width=4); d.rectangle([40, 18, 45, 23], fill=C(BR))
    d.line([(18 + lean, 22), (12, 30), (16, 34)], fill=C(STL_D), width=4); d.rectangle([13, 32, 18, 37], fill=C(BR_D))
    im = outline(im)
    return im
def rocket_fist():
    im, d = canvas(14, 10); d.rectangle([4, 0, 13, 9], fill=C(BR)); d.rectangle([5, 1, 12, 2], fill=C(BR_L)); d.rectangle([0, 3, 4, 6], fill=C(STL_D))
    return outline(im)
def shuriken(f=0):
    im, d = canvas(11, 11); c = 5
    d.polygon([(c, 0), (c + 2, c - 2), (10, c), (c + 2, c + 2), (c, 10), (c - 2, c + 2), (0, c), (c - 2, c - 2)], fill=C(STL)); d.point((c, c), fill=C((20, 20, 30)))
    d.line([(c, 1), (c, 3)], fill=C((220, 225, 235)))
    im = outline(im); return im.rotate(45 if f % 2 else 0, expand=False, resample=Image.NEAREST)
def gear_piece(k):
    im, d = canvas(12, 12)
    if k % 3 == 2: d.line([(1, 2), (10, 4), (1, 6), (10, 8), (1, 10)], fill=C(STL), width=1)       # spring
    else: _gear(d, 6, 6, 3 + k % 2, BR if k % 2 else BR_L, teeth=7)
    return outline(im)

# ---------------- robed sprites for the robe-burn (front view) ----------------
def robe_pair(scheme='hero'):
    """(robed front sprite, gi front sprite) at 1x, same size/alignment"""
    import martial as M
    robed = np.array(Image.open(os.path.join(HERE, 'px_R.png'))); gi = np.array(Image.open(os.path.join(HERE, 'px_suit_R.png')))
    if scheme == 'dark': robed = M.dark_recolor_arr(robed); gi = M.dark_recolor_arr(gi)
    return Image.fromarray(robed), Image.fromarray(gi)

if __name__ == '__main__':
    import lib
    fr = lib.new(); x = 220
    items = [golem(p) for p in ('stance', 'raise', 'pound', 'throw', 'hit')] + [boulder(), boulder(2)] + [robot(p) for p in ('stance', 'dash', 'punch', 'throw', 'hit')] + [robot('punch', fist=False), rocket_fist(), shuriken(0), shuriken(1)] + [gear_piece(k) for k in range(3)]
    for a, b in [robe_pair('hero'), robe_pair('dark')]: items += [a, b]
    for it in items:
        im = lib.U(it); fr.paste(im, (x, 372 - im.height), im); x += im.width + 6
    lib.finish(fr).crop((200, 216, 1780, 404)).save(os.path.join(HERE, 'opp_preview.png'))
