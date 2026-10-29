"""Recolour the wizard's robe into a red fighting gi with black trim and a black belt (hat, beard, staff untouched)."""
from PIL import Image
import numpy as np, scipy.ndimage as nd, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = np.array([10, 14, 42])
REDMAP = {(8, 29, 78): (196, 32, 36), (6, 16, 57): (128, 16, 26), (8, 43, 97): (232, 64, 56),
          (17, 84, 129): (160, 24, 30), (36, 46, 81): (96, 14, 22)}
BLACK, BLACK_HI = (26, 22, 30), (64, 58, 70)

def is_navy(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (b > r + 30) & (b > g + 20) & (r + g + b < 260) & ~((np.abs(a[..., :3].astype(int) - OUT).sum(-1)) < 6)
def is_cyan(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (b > 150) & (g > 110) & (r < 80)

def suit(name):
    a = np.array(Image.open(os.path.join(HERE, f'px_{name}.png'))).copy(); H, W = a.shape[:2]
    navy, cyan = is_navy(a), is_cyan(a)
    blue = navy | cyan
    lab, n = nd.label(blue)
    # hat = blue component holding the topmost blue pixel
    ys, xs = np.nonzero(blue); top = ys.argmin(); hat = lab == lab[ys[top], xs[top]]
    if hat.sum() > blue.sum() * 0.6:            # fused with the robe: fall back to everything above the face
        r_, g_, b_ = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
        skin = (r_ > 200) & (g_ > 130) & (g_ < 200) & (b_ < 140); skin[int(H * 0.5):] = False; skin[:, :int(W * 0.3)] = False; skin[:, int(W * 0.7):] = False
        hat = blue.copy(); hat[np.nonzero(skin.any(1))[0].min():] = False; hat[:, :int(W * 0.2)] = False; hat[:, int(W * 0.8):] = False
    # staff orb = small cyan blobs touching a near-white pixel
    bright = (a[..., :3].astype(int).sum(-1) > 620) & (a[..., 2] > 200)
    clab, cn = nd.label(cyan | bright)
    orb = np.zeros_like(cyan)
    for i in range(1, cn + 1):
        m = clab == i
        if (m & bright).any() and m.sum() < 60: orb |= m
    robe = blue & ~hat & ~nd.binary_dilation(orb, iterations=4)
    out = a.copy()
    for (src, dst) in REDMAP.items():
        m = robe & (np.abs(a[..., :3].astype(int) - np.array(src)).sum(-1) < 4); out[m, :3] = dst
    rest = robe & navy & ~np.isin(np.arange(1), [0])                       # any other navy shade
    leftover = rest & ~np.isin(out[..., 0], [196, 128, 232, 160, 96])
    out[leftover, :3] = (176, 26, 32)
    trim = robe & cyan
    light = trim & (a[..., 1] > 190); out[trim, :3] = BLACK; out[light, :3] = BLACK_HI
    # belt: the buckle is the most square cyan blob near the middle -> band across the robe + knot tails
    tl, tn = nd.label(trim); best = None
    for i in range(1, tn + 1):
        m = tl == i; yy, xx = np.nonzero(m); h_, w_ = np.ptp(yy) + 1, np.ptp(xx) + 1
        if 3 <= h_ <= 7 and 3 <= w_ <= 9 and 0.4 * H < yy.mean() < 0.7 * H:
            sc = abs(h_ - w_ * 0.7) + abs(yy.mean() - 0.62 * H) * 0.2
            if best is None or sc < best[0]: best = (sc, yy.min(), yy.max(), xx.min(), xx.max())
    if best:
        _, y0, y1, x0, x1 = best
        band = np.zeros_like(robe); cx_ = (x0 + x1) // 2; hw_ = max(6, int(W * 0.24)); band[y0:y1 + 1, max(0, cx_ - hw_):cx_ + hw_ + 1] = True; band &= (robe | (np.abs(out[..., :3].astype(int) - np.array(BLACK)).sum(-1) < 4))
        out[band, :3] = BLACK; out[band & (np.arange(H)[:, None] == y0), :3] = BLACK_HI
        cx = (x0 + x1) // 2
        for k, dx in enumerate((-1, 1)):                                    # knot tails
            for j in range(1, 6):
                yy_, xx_ = y1 + j, cx + dx * (1 + j // 2)
                if 0 <= yy_ < H and 0 <= xx_ < W and out[yy_, xx_, 3] > 0 and not (np.abs(out[yy_, xx_, :3].astype(int) - OUT).sum() < 6 and j > 4):
                    out[yy_, xx_, :3] = BLACK if j < 5 else BLACK_HI
    Image.fromarray(out).save(os.path.join(HERE, f'px_suit_{name}.png'))
    return Image.fromarray(out)

if __name__ == '__main__':
    names = 'RCIFBHEDG'
    ims = [Image.open(os.path.join(HERE, f'px_{n}.png')) for n in names] + [suit(n) for n in names]
    W = sum(i.width + 4 for i in ims[:9]) + 4; Hh = max(i.height for i in ims) + 4
    pv = Image.new('RGBA', (W, Hh * 2), (25, 15, 40, 255))
    for row in range(2):
        x = 2
        for i in ims[row * 9:(row + 1) * 9]: pv.alpha_composite(i, (x, row * Hh + Hh - 2 - i.height)); x += i.width + 4
    pv.resize((pv.width * 3, pv.height * 3), Image.NEAREST).save(os.path.join(HERE, 'suit_preview.png'))
