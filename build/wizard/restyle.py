"""Moves every wizard sprite to the owner's new style sheet (assets/style/wizard_style_sheet.png, 2026-10-28):
  - the red front figure becomes the after-burn front sprite (px_suit_R), and, recoloured blue, the robed
    front sprite (px_R), so the robe burn reveals exactly the same silhouette;
  - the new front head (hat, face with eye whites and brows, moustache, beard) replaces the head on every
    front-facing pose; the side-view head replaces it on the side poses;
  - the side-view heads (with hat / bald) become the fight rig's heads (martial.py).
Everything is scaled to the sprites' current size and snapped to one palette taken from the sheet.
The old sprites are kept in px_old/.      python3 restyle.py  [preview.png]"""
import os, sys, shutil
import numpy as np
from PIL import Image
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, 'assets', 'style', 'wizard_style_sheet.png')
OUTL = (10, 14, 42)

# ------------------------------------------------------------------ cut the sheet
def cut_sheet():
    a = np.array(Image.open(SHEET).convert('RGB')).astype(int)
    bgc = np.median(a[40:60, 900:1300].reshape(-1, 3), 0)                  # the dark purple ground
    fg = np.abs(a - bgc).sum(2) > 46
    fg[:4] = fg[-4:] = False; fg[:, :4] = fg[:, -4:] = False                 # the sheet's own border
    fg = nd.binary_opening(fg, iterations=1)
    lab, n = nd.label(nd.binary_dilation(fg, iterations=5))
    objs = []
    for i, sl in enumerate(nd.find_objects(lab), 1):
        m = nd.binary_fill_holes((lab[sl] == i) & fg[sl])                    # dark straps match the ground: keep them
        if m.sum() < 1500: continue
        rgba = np.zeros(m.shape + (4,), np.uint8); rgba[..., :3] = a[sl]; rgba[..., 3] = m * 255
        objs.append((sl[1].start, Image.fromarray(rgba)))
    objs.sort(key=lambda o: o[0])
    return [o for _, o in objs]

def down(img, h=None, scale=None):
    """BOX downscale to the 1x grid, hard alpha"""
    bb = img.getbbox(); img = img.crop(bb)
    if scale is None: scale = h / img.height
    w2, h2 = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    a = np.array(img.resize((w2, h2), Image.BOX)); a[..., 3] = np.where(a[..., 3] > 120, 255, 0)
    return Image.fromarray(a)

# ------------------------------------------------------------------ one palette for everything
def kmeans(px, k, it=12, seed=0):
    rng = np.random.default_rng(seed); c = px[rng.choice(len(px), k, replace=False)].astype(float)
    for _ in range(it):
        d = ((px[:, None, :] - c[None]) ** 2).sum(-1); lab = d.argmin(1)
        for j in range(k):
            sel = px[lab == j]
            if len(sel): c[j] = sel.mean(0)
    return c.round().astype(int)
def snap(img, pal):
    a = np.array(img).copy(); m = a[..., 3] > 0; px = a[m][:, :3].astype(int)
    d = ((px[:, None, :] - pal[None]) ** 2).sum(-1); a[m, :3] = pal[d.argmin(1)]
    return Image.fromarray(a)
def outline(img):
    a = np.array(img); m = a[..., 3] > 0; H, W = m.shape
    o = np.zeros((H + 2, W + 2, 4), np.uint8); o[1:-1, 1:-1] = a; mm = np.zeros((H + 2, W + 2), bool); mm[1:-1, 1:-1] = m
    ring = nd.binary_dilation(mm) & ~mm; o[ring, :3] = OUTL; o[ring, 3] = 255
    return Image.fromarray(o)
def clean(img, pal):
    """snap, drop specks, outline"""
    a = np.array(snap(img, pal)); m = a[..., 3] > 0
    lab, n = nd.label(m, structure=np.ones((3, 3)))
    if n > 1:
        sz = nd.sum(m, lab, range(1, n + 1))
        for k, z in enumerate(sz, 1):
            if z < 5: a[lab == k] = 0
    return outline(Image.fromarray(a))

# ------------------------------------------------------------------ colour helpers
def masks(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]; al = a[..., 3] > 0
    skin = al & (r > 150) & (g > 95) & (b < 150) & (r > b + 45) & (g > b + 10)
    hair = al & (r > 140) & (g > 140) & (b > 150) & (np.abs(r - g) < 30)
    navy = al & (b > r + 25) & (b > g + 10)
    red = al & (r > g + 50) & (r > b + 40) & ~skin
    return skin, hair, navy, red

def blue_robe(img):
    """the red figure, recoloured into his blue robe: reds -> navy shades, dark straps -> cyan trim"""
    a = np.array(img).copy(); skin, hair, navy, red = masks(a)
    r, g, b = [a[..., i].astype(float) for i in range(3)]; al = a[..., 3] > 0
    L = (0.5 * r + 0.3 * g + 0.2 * b)
    lo, hi = np.array([10, 22, 70]), np.array([40, 86, 190])                   # navy ramp of the old robe
    t = np.clip((L - 40) / 110, 0, 1)[..., None]
    a[red, :3] = (lo + (hi - lo) * t)[red].astype(np.uint8)
    # straps and the belt: dark, unsaturated pixels below the beard
    lab, n = nd.label(skin)                                                    # chin = bottom of the face (hands are skin too)
    blobs = [nd.find_objects(lab)[k][0] for k in range(n) if (lab == k + 1).sum() >= 6]
    chin = min(blobs, key=lambda sl: sl.start).stop if blobs else 0
    L0 = 0.5 * r + 0.3 * g + 0.2 * b
    dark = al & ~skin & ~hair & (L0 < 48) & nd.binary_erosion(al, iterations=2)
    yy = np.arange(a.shape[0])[:, None]
    straps = dark & (yy > chin - 4)
    wid = al.any(0).sum()
    belt_rows = dark.sum(1) > wid * 0.35                                       # the wide belt stays dark
    straps &= ~belt_rows[:, None]
    # thin vertical straps become the cyan trim; the belt keeps a cyan buckle
    lab, n = nd.label(straps)
    for i, sl in enumerate(nd.find_objects(lab), 1):
        m = lab[sl] == i; h, w = m.shape
        if h >= 3 and h > w * 1.5: a[sl][m, :3] = (32, 200, 240)
    grey = al & ~hair & (np.abs(r - g) < 20) & (np.abs(g - b) < 25) & (r > 90) & (r < 150) & (yy > chin)
    a[grey, :3] = (40, 215, 245)                                               # buckle
    return Image.fromarray(a)

# ------------------------------------------------------------------ heads
def head_part(img, front=True):
    """hat + face + beard + hair of a figure (no staff, no clothes)"""
    a = np.array(img).copy(); skin, hair, navy, red = masks(a)
    rows = np.nonzero(skin.any(1))[0]; cols = np.nonzero(skin.any(0))[0]
    if not len(rows): return img
    cx = int(cols.mean())
    lab, n = nd.label(skin)                                                    # the face: the topmost big skin blob (not the hands)
    blobs = [(nd.find_objects(lab)[k][0].start, k + 1) for k in range(n) if (lab == k + 1).sum() >= 6]
    face = lab == min(blobs)[1] if blobs else skin
    rows = np.nonzero(face.any(1))[0]; cols = np.nonzero(face.any(0))[0]; cx = int(cols.mean())
    keep = face.copy()
    near = nd.binary_dilation(face, iterations=6)
    lab, n = nd.label(hair, structure=np.ones((3, 3)))
    ids = set(lab[near].ravel()) - {0}
    keep |= np.isin(lab, list(ids))                                            # beard and hair touching the face
    # the hat: navy/blue pixels in the rows above the face, connected through the column over the face
    hatz = navy.copy(); hatz[rows.min() + 2:] = False
    lab, n = nd.label(hatz, structure=np.ones((3, 3)))
    ids = set(lab[:rows.min() + 2, max(0, cx - 4):cx + 5].ravel()) - {0}
    keep |= np.isin(lab, list(ids))
    keep = nd.binary_closing(keep, iterations=2) & (a[..., 3] > 0)
    keep |= nd.binary_dilation(keep, iterations=1) & (a[..., 3] > 0) & (a[..., :3].sum(-1) < 150)   # its outline / eyes
    out = np.zeros_like(a); out[keep] = a[keep]
    bb = Image.fromarray(out).getbbox()
    return Image.fromarray(out).crop(bb)

def face_box(a):
    skin = masks(a)[0]; ys, xs = np.nonzero(skin)
    return (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None

def transplant(old, head, pal, flip=False):
    """put the new head on an old pose (same scale: both are this character at 1x). The old hat, face and
    beard are cleared first; the new head is lined up on the old face."""
    a = np.array(old).copy(); skin, hair, navy, red = masks(a)
    r, g, b = [a[..., k].astype(int) for k in range(3)]; al = a[..., 3] > 0
    cyan = al & (b > 150) & (g > 120) & (r < 120)
    fb = face_box(a)
    if fb is None: return old
    hs = np.array(head)
    if flip: hs = hs[:, ::-1].copy()
    hfb = face_box(hs)
    # old face = the biggest skin blob (hands are skin too)
    lab, n = nd.label(skin); sz = nd.sum(skin, lab, range(1, n + 1)); face = lab == (np.argmax(sz) + 1)
    ys, xs = np.nonzero(face); fb = (xs.min(), ys.min(), xs.max(), ys.max())
    cx = (fb[0] + fb[2]) // 2
    # old hat: blue/cyan pixels above the face, connected to the column over the face
    hatz = (navy | cyan).copy(); hatz[fb[1] + 1:] = False
    lab, n = nd.label(hatz); ids = set(lab[:fb[1] + 1, max(0, cx - 2):cx + 3].ravel()) - {0}
    hat = np.isin(lab, list(ids))
    lim = np.zeros_like(hat); w = fb[2] - fb[0] + 1
    lim[:, max(0, fb[0] - int(w * 0.8)):fb[2] + int(w * 0.8) + 1] = True
    hat &= lim                                                                 # raised arms next to the hat stay
    # old beard / hair: light pixels touching the face
    lab, n = nd.label(hair, structure=np.ones((3, 3))); near = nd.binary_dilation(face, iterations=2)
    ids = set(lab[near].ravel()) - {0}; beard = np.isin(lab, list(ids))
    oldhead = hat | face | beard
    ring = nd.binary_dilation(oldhead, iterations=1) & al & (r + g + b < 120) & ~nd.binary_dilation(al & ~oldhead & (r + g + b >= 120), iterations=1)
    robe_px = a[al & navy & ~hat][:, :3]
    robe = np.median(robe_px, 0).astype(np.uint8) if len(robe_px) else np.array((20, 34, 90), np.uint8)
    below = beard & (np.arange(a.shape[0])[:, None] > fb[3])
    a[(hat | face | ring | beard) & ~below] = 0
    a[below, :3] = robe
    # paste the new head, lined up on the old face (centre x, top of the face)
    dx = int(round((fb[0] + fb[2]) / 2 - (hfb[0] + hfb[2]) / 2)); dy = int(fb[1] - hfb[1])
    H, W = a.shape[:2]; h2, w2 = hs.shape[:2]
    pad_t = max(0, -dy); pad_l = max(0, -dx); pad_r = max(0, dx + w2 - W); pad_b = max(0, dy + h2 - H)
    if pad_t or pad_l or pad_r or pad_b:
        a = np.pad(a, ((pad_t, pad_b), (pad_l, pad_r), (0, 0))); dx += pad_l; dy += pad_t
    reg = a[dy:dy + h2, dx:dx + w2]; m = hs[..., 3] > 0; reg[m] = hs[m]
    im = Image.fromarray(a); a = np.array(im.crop(im.getbbox()))
    ol = (np.abs(a[..., :3].astype(int) - np.array(OUTL)).sum(-1) < 30) & (a[..., 3] > 0)
    a[ol & ~nd.binary_erosion(a[..., 3] > 0)] = 0                                # the outline is redrawn by clean()
    return clean(Image.fromarray(a), pal)

FRONT = 'RBHEDGI'          # faces the viewer (I: three-quarter, gets the front head)
SIDE = 'CF'                 # side view, facing right

def build(preview=None):
    objs = cut_sheet()
    red_front, red_hook, orb, hat, side_hat, side_bald = objs[:6]
    old = {n: Image.open(os.path.join(HERE, f'px_{n}.png')) for n in 'RCIFBHEDG'}
    old_dir = os.path.join(HERE, 'px_old')
    if not os.path.isdir(old_dir):
        os.makedirs(old_dir)
        for n in 'RCIFBHEDG': shutil.copy(os.path.join(HERE, f'px_{n}.png'), old_dir)
        shutil.copy(os.path.join(HERE, 'px_suit_R.png'), old_dir); shutil.copy(os.path.join(HERE, 'px_suit_C.png'), old_dir)
    else:
        old = {n: Image.open(os.path.join(old_dir, f'px_{n}.png')) for n in 'RCIFBHEDG'}
    H_R = old['R'].height - 2                                                   # without the outline ring
    fr = down(red_front, H_R)
    sc = H_R / red_front.crop(red_front.getbbox()).height
    blue = blue_robe(fr)
    sh = down(side_hat, scale=sc); sb = down(side_bald, scale=sc)
    px = []
    for im in (fr, blue, sh, sb): a = np.array(im); px.append(a[a[..., 3] > 0][:, :3])
    for n in 'RCIFBHEDG': a = np.array(old[n]); px.append(a[a[..., 3] > 0][:, :3])
    pal = kmeans(np.concatenate(px).astype(float), 30)
    pal = np.vstack([pal, [OUTL]])
    out = {}
    out['suit_R'] = clean(fr, pal); out['R'] = clean(blue, pal)
    fhead = head_part(blue)                                                     # the 1x front head (blue hat)
    shead = head_part(sh)
    for n in FRONT:
        if n == 'R': continue
        out[n] = transplant(old[n], fhead, pal)
    for n in SIDE: out[n] = transplant(old[n], shead, pal, flip=True)
    out['head_side_hat'] = clean(shead, pal); out['head_side_bald'] = clean(head_part(sb), pal)
    for k, im in out.items(): im.save(os.path.join(HERE, f'px_{k}.png'))
    if preview:
        ims = [out[k] for k in ['R', 'suit_R'] + list('CIFBHEDG') + ['head_side_hat', 'head_side_bald']]
        olds = [old[k] for k in 'R'] + [Image.open(os.path.join(old_dir, 'px_suit_R.png'))] + [old[k] for k in 'CIFBHEDG']
        W = sum(i.width for i in ims) + 10 * len(ims); Hh = max(i.height for i in ims)
        o = Image.new('RGBA', (W, Hh * 2 + 10), (40, 30, 60, 255)); x = 0
        for i, im in enumerate(ims):
            o.paste(im, (x, Hh - im.height), im)
            if i < len(olds): o.paste(olds[i], (x, Hh * 2 + 10 - olds[i].height), olds[i])
            x += im.width + 10
        o.resize((o.width * 4, o.height * 4), Image.NEAREST).save(preview)
    return out

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else None)
