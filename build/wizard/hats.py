"""Hatless versions of the wizard sprites (his hat burns up with the robe). The hat is everything above
the top of his face; a bald skin dome with white side hair is drawn in its place."""
import numpy as np
from PIL import Image
OUTL = (10, 14, 42); SKIN = (239, 172, 104); SKIN_D = (195, 145, 96); HAIR = (226, 230, 240); HAIR_D = (170, 176, 196)

def _skin(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (a[..., 3] > 0) & (r > 170) & (g > 110) & (g < 200) & (b < 140) & (r > b + 60)

def _brim(a, top, cx):
    """columns of the hat brim: the solid run through cx on the rows just above the face"""
    best = (cx, cx)
    for y in range(max(0, top - 3), top):
        row = a[y, :, 3] > 0
        if not row[cx]: continue
        x0 = cx
        while x0 > 0 and row[x0 - 1]: x0 -= 1
        x1 = cx
        while x1 < len(row) - 1 and row[x1 + 1]: x1 += 1
        if x1 - x0 > best[1] - best[0]: best = (x0, x1)
    # the brim never reaches the staff: stop at a gap of see-through pixels in rows above
    return best

def remove_hat(img):
    a = np.array(img.convert('RGBA')).copy(); sk = _skin(a)
    rows = np.nonzero(sk.any(1))[0]
    if not len(rows): return img
    top = rows[0]                                   # first row with face skin
    cols = np.nonzero(sk[top:top + 3].any(0))[0]; c0, c1 = cols.min(), cols.max()
    # beard/hair at the face sides on the face's top rows tells how wide the head is
    hair = (a[..., 3] > 0) & (a[..., 0] > 150) & (a[..., 1] > 150) & (a[..., 2] > 160)
    hc = np.nonzero((hair[top:top + 6] | sk[top:top + 6]).any(0))[0]
    h0, h1 = (min(c0, hc.min()), max(c1, hc.max())) if len(hc) else (c0, c1)
    b0, b1 = _brim(a, top, (h0 + h1) // 2)
    a[:top, b0:b1 + 1] = 0                          # the hat (only its columns: the staff orb stays)
    # clear brim leftovers on the face's first rows outside the head
    for x in list(range(b0, h0)) + list(range(h1 + 1, b1 + 1)):
        for y in range(top, top + 2):
            if not sk[y, x] and not hair[y, x]: a[y, x] = 0
    # thin brim lines left on the face's first rows (one pixel tall, nothing above or below)
    for _ in range(2):
        al = a[..., 3] > 0
        for y in range(max(1, top - 1), min(a.shape[0] - 1, top + 3)):
            for x in list(range(max(0, b0 - 6), h0 - 1)) + list(range(h1 + 2, min(a.shape[1], b1 + 7))):
                if al[y, x] and not sk[y, x] and not hair[y, x] and not al[y - 1, x] and not al[y + 1, x]: a[y, x] = 0
    # dome: 3 rows of skin, narrowing, with white hair at the sides and an outline
    w = h1 - h0 + 1
    for k, inset in enumerate((2, 1, 0)):
        y = top - 3 + k
        if y < 0: continue
        for x in range(h0 + inset, h1 - inset + 1): a[y, x] = SKIN + (255,) if k < 2 else SKIN + (255,)
        a[y, h0 + inset] = HAIR + (255,) if k > 0 else SKIN_D + (255,); a[y, h1 - inset] = HAIR + (255,) if k > 0 else SKIN_D + (255,)
    for y in range(top - 1, top + 3):              # side hair tufts
        for x in (h0, h1):
            if 0 <= y < a.shape[0]: a[y, x] = HAIR + (255,)
    px = top - 2
    if px >= 0: a[px, h0 + (w // 2) - 2: h0 + (w // 2)] = SKIN_D + (255,)   # a little shine shadow
    # outline everything that is new
    m = a[..., 3] > 0; out = a.copy()
    for y in range(max(0, top - 5), top + 1):
        for x in range(a.shape[1]):
            if m[y, x]: continue
            nb = [(y + dy, x + dx) for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))]
            if any(0 <= yy < a.shape[0] and 0 <= xx < a.shape[1] and m[yy, xx] for yy, xx in nb): out[y, x] = OUTL + (255,)
    import scipy.ndimage as nd                      # drop stray bits left from the brim
    lab, n = nd.label(out[..., 3] > 0, structure=np.ones((3, 3)))
    if n > 1:
        sz = nd.sum(out[..., 3] > 0, lab, range(1, n + 1))
        for k, z in enumerate(sz, 1):
            if z < 6: out[lab == k] = 0
    return Image.fromarray(out)

def hat_only(img):
    """the hat pixels (to fly off in flames)"""
    a = np.array(img.convert('RGBA')).copy(); sk = _skin(a); rows = np.nonzero(sk.any(1))[0]
    if not len(rows): return img
    top = rows[0]; cols = np.nonzero(sk[top:top + 3].any(0))[0]
    b0, b1 = _brim(a, top, (cols.min() + cols.max()) // 2)
    out = np.zeros_like(a); out[:top, b0:b1 + 1] = a[:top, b0:b1 + 1]
    return Image.fromarray(out)
