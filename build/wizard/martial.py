"""Jointed martial-arts rig for the wizard (1x pixel art, faces left). Head = his real hat/face/beard pixels,
body = red gi with black trim + black belt, poses defined by joint angles."""
from PIL import Image, ImageDraw, ImageOps
import numpy as np, scipy.ndimage as nd, math, os
from lib import U, snap, FLOOR
HERE = os.path.dirname(os.path.abspath(__file__))
OUTL = (10, 14, 42); RED, RED_D, RED_L = (154, 16, 25), (97, 12, 22), (196, 40, 44)   # the style sheet's reds
BLK, BLK_H = (26, 22, 30), (64, 58, 70); SKIN, SKIN_D = (232, 151, 88), (177, 108, 67); SHOE, SHOE_D = (8, 29, 78), (6, 16, 57)

def _head():
    a = np.array(Image.open(os.path.join(HERE, 'px_suit_C.png'))).astype(int); H, W = a.shape[:2]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3] > 0
    outl = (np.abs(a[..., :3] - np.array(OUTL)).sum(-1) < 8) & al
    red = (r > 110) & (g < 80) & (b < 80); dred = (r > 45) & (r < 150) & (g < 40) & (b < 50)
    blk = (r < 75) & (g < 65) & (b < 75) & (np.abs(r - b) < 25) & ~outl
    yy, xx = np.mgrid[:H, :W]
    keep = al & ~outl & ~red & ~dred & ~blk & (yy < 41) & (xx < 35)
    lab, n = nd.label(keep); sz = nd.sum(keep, lab, range(1, n + 1)); keep = np.isin(lab, 1 + np.nonzero(sz > 8)[0])
    ol = outl & nd.binary_dilation(keep, structure=np.ones((3, 3))) & (yy < 42) & (xx < 36)
    m = keep | ol; out = np.zeros_like(a); out[m] = a[m]
    img = Image.fromarray(out.astype(np.uint8)); bb = img.getbbox(); img = ImageOps.mirror(img.crop(bb))
    anchor = (bb[2] - 1 - 18, 27 - bb[1])                       # neck point (C coords x=18,y=27) after crop+mirror
    return img, anchor
HEAD_OLD, HEAD_OLD_A = _head()
# The owner's 2026-10-28 style: side-view heads cut from the style sheet by restyle.py (they face left, like the rig).
def _side_heads():
    hat = Image.open(os.path.join(HERE, 'px_head_side_hat.png')); bald = Image.open(os.path.join(HERE, 'px_head_side_bald.png'))
    def marks(im):
        a = np.array(im).astype(int); al = a[..., 3] > 0
        skin = al & (a[..., 0] > 150) & (a[..., 1] > 95) & (a[..., 2] < 150) & (a[..., 0] > a[..., 2] + 45)
        ys, xs = np.nonzero(skin); return xs.min(), ys.min(), xs.max(), ys.max(), np.nonzero(al.any(1))[0].max()
    x0, y0, x1, y1, bot = marks(hat)
    anchor = ((x0 + x1) // 2 + 2, y1 - 1)                                  # where the neck meets the head
    bx0, by0, bx1, by1, bbot = marks(bald)
    banchor = (anchor[0] - x0 + bx0, anchor[1] - bot + bbot)            # same nose and beard tip as the hat head
    return hat, anchor, bald, banchor
HEAD, HEAD_A, HEAD_BALD, HEAD_BALD_A = _side_heads()
# After the robe burns, his hat is gone too. Old test scenes set NOHAT = False to keep it.
NOHAT = True
def _head_img():
    return (HEAD_BALD, HEAD_BALD_A) if NOHAT else (HEAD, HEAD_A)

STAFF_L = 40
ORB = [(22, 206, 245), (240, 252, 255)]
ORB_HOT = [(255, 160, 40), (255, 240, 170)]
ORB_COOL = [(22, 206, 245), (240, 252, 255)]
def dark_recolor_arr(a):
    """hero palette -> dark twin palette (black/purple gi, purple hat, magenta glow, greyer beard)"""
    a = a.copy(); r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int); al = a[..., 3] > 0
    outl = (np.abs(a[..., :3].astype(int) - np.array(OUTL)).sum(-1) < 8)
    red = al & (r > 70) & (g < 90) & (b < 90) & (r > g + 45)
    blk = al & ~outl & (r < 75) & (g < 65) & (b < 75) & (np.abs(r - b) < 25)
    navy = al & ~outl & (b > r + 30) & (b > g + 20) & (r + g + b < 260)
    cyan = al & (b > 150) & (g > 110) & (r < 80)
    hot = al & (r > 240) & (g > 140) & (b < 80)
    grey = al & (r > 110) & (g > 110) & (b > 110) & (np.abs(r - g) < 30) & ~cyan
    out = a.copy()
    out[red, 0] = (r * 0.22 + 14)[red]; out[red, 1] = (r * 0.12 + 8)[red]; out[red, 2] = (r * 0.3 + 24)[red]
    out[blk, :3] = (150, 60, 200); out[navy, 0] = (b * 0.45)[navy]; out[navy, 1] = (b * 0.12)[navy]; out[navy, 2] = (b * 0.55)[navy]
    out[cyan, 0] = g[cyan]; out[cyan, 1] = (r * 0.4)[cyan]; out[cyan, 2] = b[cyan]
    out[hot, :3] = (210, 70, 255)
    out[grey, 0] = (r * 0.62)[grey]; out[grey, 1] = (g * 0.6)[grey]; out[grey, 2] = (b * 0.66)[grey]
    return out
RED_EYES = True
def red_eyes_arr(a):
    """the dark twin's eyes glow red: the dark pixels in the top half of his face"""
    import scipy.ndimage as nd
    a = a.copy(); r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int); al = a[..., 3] > 0
    skin = al & (r > 150) & (g > 90) & (b < 140) & (r > b + 50)
    if not skin.any(): return a
    lab, n = nd.label(skin); big = np.argmax(nd.sum(skin, lab, range(1, n + 1))) + 1; face = lab == big
    ys, xs = np.nonzero(face); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    zone = np.zeros_like(face); zone[y0:y0 + max(2, (y1 - y0) // 2 + 1), x0:x1 + 1] = True
    eyes = zone & al & ~skin & (r + g + b < 200) & nd.binary_fill_holes(face | (al & ~(r + g + b < 200) & zone))
    a[eyes, :3] = (255, 46, 40)
    return a
STAFF_DEF = {'fly': ('ba', 255, 0.5), 'bow': ('ba', 182, 0.5), 'hit': ('ba', 210, 0.5), 'sweep': ('ba', 230, 0.5)}
def draw_staff(d, hand, ang, grip):
    def dv(th, L): return (-math.sin(math.radians(th)) * L, math.cos(math.radians(th)) * L)
    lo = (hand[0] - dv(ang, STAFF_L * grip)[0], hand[1] - dv(ang, STAFF_L * grip)[1]); hi = (hand[0] + dv(ang, STAFF_L * (1 - grip))[0], hand[1] + dv(ang, STAFF_L * (1 - grip))[1])
    d.line([lo, hi], fill=OUTL + (255,), width=4); d.line([lo, hi], fill=(72, 36, 28, 255), width=2)
    mid = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2); d.line([lo, mid], fill=(110, 64, 44, 255), width=1)
    d.ellipse([hi[0] - 4, hi[1] - 4, hi[0] + 4, hi[1] + 4], fill=OUTL + (255,)); d.ellipse([hi[0] - 3, hi[1] - 3, hi[0] + 3, hi[1] + 3], fill=ORB[0] + (255,))
    d.rectangle([hi[0] - 1, hi[1] - 1, hi[0], hi[1]], fill=ORB[1] + (255,))
def dvec(th, L): return (-math.sin(math.radians(th)) * L, math.cos(math.radians(th)) * L)
def _limb(d, p0, th1, th2, L1, L2, w1, w2, col, end, endcol, endsz):
    k = (p0[0] + dvec(th1, L1)[0], p0[1] + dvec(th1, L1)[1]); e = (k[0] + dvec(th2, L2)[0], k[1] + dvec(th2, L2)[1])
    for w, c in ((w1 + 2, OUTL), (w1, col)):
        d.line([p0, k], fill=c + (255,), width=w); d.ellipse([k[0] - w / 2, k[1] - w / 2, k[0] + w / 2, k[1] + w / 2], fill=c + (255,))
    for w, c in ((w2 + 2, OUTL), (w2, col)): d.line([k, e], fill=c + (255,), width=w)
    if end == 'fist':
        s = endsz; d.rectangle([e[0] - s / 2 - 1, e[1] - s / 2 - 1, e[0] + s / 2 + 1, e[1] + s / 2 + 1], fill=OUTL + (255,)); d.rectangle([e[0] - s / 2, e[1] - s / 2, e[0] + s / 2, e[1] + s / 2], fill=endcol + (255,))
    else:                                                        # foot: toe points 90deg forward of the shin
        t = (e[0] + dvec(th2 + 90, 5)[0], e[1] + dvec(th2 + 90, 5)[1])
        d.line([e, t], fill=OUTL + (255,), width=6); d.line([e, t], fill=endcol + (255,), width=4)
    return e

STANCE = dict(lean=5, fl=(25, 5), bl=(-25, -8), fa=(55, 145), ba=(25, 135))
POSES = {
    'stance': STANCE,
    'stance2': dict(lean=7, fl=(28, 8), bl=(-22, -6), fa=(60, 150), ba=(30, 140)),
    'bow': dict(lean=35, fl=(4, 0), bl=(-4, 0), fa=(10, 5), ba=(-5, 0)),
    'punch': dict(lean=15, fl=(35, 15), bl=(-35, -30), fa=(90, 90), ba=(30, 145)),
    'punch2': dict(lean=15, fl=(35, 15), bl=(-35, -30), fa=(40, 150), ba=(88, 90)),
    'death': dict(lean=22, fl=(48, 25), bl=(-45, -40), fa=(92, 92), ba=(-40, 30), big=True),
    'fly': dict(lean=-35, fl=(97, 94), bl=(35, -60), fa=(60, 150), ba=(-20, 60)),
    'tuck': dict(lean=10, fl=(80, -20), bl=(60, -40), fa=(70, 150), ba=(40, 140)),
    'high': dict(lean=-22, fl=(132, 128), bl=(-8, -4), fa=(70, 150), ba=(-30, 40)),
    'mid': dict(lean=-12, fl=(95, 93), bl=(-14, -6), fa=(65, 150), ba=(-20, 50)),
    'low': dict(lean=0, fl=(62, 72), bl=(-20, -10), fa=(60, 150), ba=(20, 130)),
    'sweep': dict(lean=35, fl=(88, 92), bl=(-55, 55), fa=(45, 70), ba=(-25, 20), crouch=9),
    'upper': dict(lean=8, fl=(20, 0), bl=(-35, -15), fa=(165, 178), ba=(30, 140)),
    'crouch': dict(lean=20, fl=(65, -15), bl=(-10, -70), fa=(60, 150), ba=(30, 140), crouch=7),
    'hit': dict(lean=-25, fl=(15, -5), bl=(-30, -25), fa=(-30, 20), ba=(-60, 0)),
    'win': dict(lean=0, fl=(15, 0), bl=(-15, 0), fa=(150, 175), ba=(-40, 10)),
    'run1': dict(lean=18, fl=(50, 20), bl=(-45, -80), fa=(-30, 60), ba=(60, 140)),
    'run2': dict(lean=18, fl=(-40, -75), bl=(45, 15), fa=(60, 140), ba=(-30, 60)),
    'charge': dict(lean=-5, fl=(30, 10), bl=(-30, -15), fa=(-35, 80), ba=(40, 150)),
    'knee': dict(lean=-10, fl=(115, 10), bl=(-20, -10), fa=(70, 150), ba=(-30, 50)),
    'st_stance': dict(lean=5, fl=(25, 5), bl=(-25, -8), fa=(55, 110), ba=(25, 135), staff=('fa', 168, 0.4)),
    'st_stance2': dict(lean=7, fl=(28, 8), bl=(-22, -6), fa=(58, 114), ba=(30, 140), staff=('fa', 172, 0.4)),
    'st_thrust': dict(lean=18, fl=(40, 20), bl=(-40, -35), fa=(90, 90), ba=(45, 120), staff=('fa', 92, 0.15)),
    'st_thrust2': dict(lean=12, fl=(38, 18), bl=(-38, -30), fa=(70, 115), ba=(40, 130), staff=('fa', 95, 0.3)),
    'st_death': dict(lean=24, fl=(50, 26), bl=(-46, -42), fa=(92, 92), ba=(-40, 30), staff=('fa', 91, 0.1), big=True),
    'st_over': dict(lean=-10, fl=(25, 8), bl=(-25, -10), fa=(150, 190), ba=(140, 185), staff=('fa', 255, 0.35)),
    'st_smash': dict(lean=26, fl=(46, 26), bl=(-42, -36), fa=(98, 72), ba=(80, 74), staff=('fa', 58, 0.25)),
    'st_sweep': dict(lean=32, fl=(82, 95), bl=(-55, 55), fa=(70, 92), ba=(40, 80), staff=('fa', 96, 0.2), crouch=9),
    'st_up': dict(lean=6, fl=(22, 2), bl=(-34, -14), fa=(140, 150), ba=(30, 140), staff=('fa', 145, 0.3)),
    'st_win': dict(lean=0, fl=(15, 0), bl=(-15, 0), fa=(120, 160), ba=(-40, 10), staff=('fa', 150, 0.45)),
    'st_charge': dict(lean=-5, fl=(30, 10), bl=(-30, -15), fa=(30, 60), ba=(40, 150), staff=('fa', 120, 0.5)),
}
def spin_pose(k):
    return dict(lean=6, fl=(28, 8), bl=(-28, -10), fa=(105, 125), ba=(30, 140), staff=('fa', (k * 45) % 360, 0.5))
def staff_tip(pose, flip=False):
    P = POSES[pose] if isinstance(pose, str) else pose
    stf = P.get('staff', STAFF_DEF.get(pose if isinstance(pose, str) else '', ('ba', 195, 0.45)))
    lean = P['lean']; S = (-math.sin(math.radians(lean)) * 17, -math.cos(math.radians(lean)) * 17)
    b0 = (S[0] - 1, S[1] + 2) if stf[0] == 'fa' else (S[0] + 2, S[1] + 2); a1, a2 = P[stf[0]]
    h = (b0[0] + dvec(a1, 8)[0] + dvec(a2, 8)[0], b0[1] + dvec(a1, 8)[1] + dvec(a2, 8)[1] + P.get('crouch', 0))
    t = (h[0] + dvec(stf[1], STAFF_L * (1 - stf[2]))[0], h[1] + dvec(stf[1], STAFF_L * (1 - stf[2]))[1])
    return (-t[0] * 2 if flip else t[0] * 2, t[1] * 2)
def eff(pose, limb, flip=False):
    """2x offset of a fist ('fa','ba') or foot ('fl','bl') from the hip"""
    P = POSES[pose]; lean = P['lean']
    if limb in ('fa', 'ba'):
        b = (-math.sin(math.radians(lean)) * 17 - 1, -math.cos(math.radians(lean)) * 17 + 2); L = 8
    else: b = (-1 if limb == 'fl' else 2, 0); L = 11
    a1, a2 = P[limb]; x = b[0] + dvec(a1, L)[0] + dvec(a2, L)[0]; y = b[1] + dvec(a1, L)[1] + dvec(a2, L)[1]
    return (-x * 2 if flip else x * 2, y * 2)
_cache = {}
def rig(pose, flip=False, scheme='hero', hot=False):
    """returns (2x image, hip x, hip y, foot-bottom y) in 2x px inside the image"""
    key = (pose if isinstance(pose, str) else tuple(sorted((k, str(v)) for k, v in pose.items())), flip, scheme, hot, NOHAT, RED_EYES)
    if key in _cache: return _cache[key]
    ORB[:] = ORB_HOT if hot else ORB_COOL
    P = POSES[pose] if isinstance(pose, str) else pose
    im = Image.new('RGBA', (170, 140), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    hip = (85, 84 + P.get('crouch', 0)); lean = P['lean']
    stf = P.get('staff', STAFF_DEF.get(pose if isinstance(pose, str) else '', ('ba', 195, 0.45)))
    S = (hip[0] - math.sin(math.radians(lean)) * 17, hip[1] - math.cos(math.radians(lean)) * 17)
    e1 = _limb(d, (hip[0] + 2, hip[1]), *P['bl'], 11, 11, 7, 6, RED_D, 'foot', SHOE_D, 0)            # back leg
    eb = _limb(d, (S[0] + 2, S[1] + 2), *P['ba'], 8, 8, 6, 5, RED_D, 'fist', SKIN_D, 4)              # back arm
    if stf and stf[0] == 'ba': draw_staff(d, eb, stf[1], stf[2])
    perp = (math.cos(math.radians(lean)), -math.sin(math.radians(lean)))                              # torso
    tor = [(S[0] - perp[0] * 6, S[1] - perp[1] * 6), (S[0] + perp[0] * 6, S[1] + perp[1] * 6),
           (hip[0] + perp[0] * 6, hip[1] + perp[1] * 6), (hip[0] - perp[0] * 6, hip[1] - perp[1] * 6)]
    d.polygon(tor, fill=RED + (255,), outline=OUTL + (255,))
    d.line([(S[0] - perp[0] * 3, S[1]), (hip[0] - perp[0] * 1, hip[1] - 4)], fill=BLK + (255,), width=1)  # lapel
    bl = [(hip[0] - perp[0] * 7, hip[1] - 3), (hip[0] + perp[0] * 7, hip[1] - 3)]
    d.line(bl, fill=BLK + (255,), width=3); d.line([(bl[0][0], bl[0][1] - 1), (bl[1][0], bl[1][1] - 1)], fill=BLK_H + (255,), width=1)
    d.line([(hip[0] - 3, hip[1] - 2), (hip[0] - 6, hip[1] + 4)], fill=BLK + (255,), width=2)          # belt tails
    d.line([(hip[0] - 1, hip[1] - 2), (hip[0] - 2, hip[1] + 5)], fill=BLK + (255,), width=2)
    e2 = _limb(d, (hip[0] - 1, hip[1]), *P['fl'], 11, 11, 7, 6, RED, 'foot', SHOE, 0)                 # front leg
    foot_b = max(e1[1], e2[1]) + 3
    H0, (ax, ay) = _head_img()
    h = H0 if abs(lean) < 8 else H0.rotate(int(round(lean / 15)) * 15 if abs(lean) >= 8 else 0, expand=True, resample=Image.NEAREST)
    if h is not H0:                                                                                    # anchor after rotation
        c = (H0.width / 2, H0.height / 2); ang = math.radians(int(round(lean / 15)) * 15)
        dx, dy = ax - c[0], ay - c[1]; ax = dx * math.cos(ang) + dy * math.sin(ang) + h.width / 2; ay = -dx * math.sin(ang) + dy * math.cos(ang) + h.height / 2
    im.alpha_composite(h, (int(round(S[0] - ax)), int(round(S[1] - ay))))
    if stf and stf[0] == 'fa':
        b0 = (S[0] - 1, S[1] + 2); a1, a2 = P['fa']; ef = (b0[0] + dvec(a1, 8)[0] + dvec(a2, 8)[0], b0[1] + dvec(a1, 8)[1] + dvec(a2, 8)[1])
        draw_staff(d, ef, stf[1], stf[2])
    _limb(d, (S[0] - 1, S[1] + 2), *P['fa'], 8, 8, 6, 5, RED, 'fist', SKIN, 5 if P.get('big') else 4)  # front arm
    a = np.array(im); a[..., 3] = np.where(a[..., 3] > 127, 255, 0)
    if scheme == 'dark':
        a = dark_recolor_arr(a)
        if RED_EYES: a = red_eyes_arr(a)
    im = Image.fromarray(a)
    from props import outline
    bb = im.getbbox(); im = outline(im.crop(bb)); hx, hy = hip[0] - bb[0] + 1, hip[1] - bb[1] + 1; fy = foot_b - bb[1] + 1
    if flip: im = ImageOps.mirror(im); hx = im.width - 1 - hx
    res = (U(im), hx * 2, hy * 2, int(round(fy)) * 2); _cache[key] = res; return res

def fplace(fr, pose, hx, hy=None, flip=False, clip_x=None, img_fn=None, alpha=None, scheme='hero', hot=False, clip_xmax=None):
    """hy=None -> feet on the floor. Otherwise hy is the hip height (2x px)."""
    im, ox, oy, fy = rig(pose, flip, scheme, hot)
    if img_fn: im = img_fn(im)
    x = snap(hx - ox); y = snap(FLOOR - fy) if hy is None else snap(hy - oy)
    if clip_xmax is not None and x + im.width > clip_xmax:
        if clip_xmax - x <= 0: return
        im = im.crop((0, 0, clip_xmax - x, im.height))
    l = 0
    if clip_x is not None and x < clip_x: l = clip_x - x
    if l >= im.width: return
    if l: im = im.crop((l, 0, im.width, im.height))
    fr.paste(im, (x + l, y), im)
def hip_floor(pose, scheme='hero'):
    im, ox, oy, fy = rig(pose, False, scheme); return FLOOR - fy + oy

if __name__ == '__main__':
    import lib
    fr = lib.new(); x = 260
    for p in ['stance', 'bow', 'punch', 'punch2', 'death', 'fly', 'tuck', 'high', 'mid', 'low', 'sweep', 'upper', 'crouch', 'hit', 'win']:
        im, ox, oy, fy = rig(p); fplace(fr, p, x + ox); x += im.width + 8
    lib.finish(fr).crop((240, 216, 1780, 404)).resize((1540 * 1, 188 * 1)).save(os.path.join(HERE, 'rig_preview.png'))
    print(HEAD.size, HEAD_A)
