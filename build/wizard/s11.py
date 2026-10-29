import math, numpy as np
from PIL import Image
from lib import *
from scenes import cloud

# ---- head cut from the front pose (hat, face, top of beard; no staff) ----
a = np.array(P1['R']); rgb = a[..., :3].astype(int)
skin = (rgb[..., 0] > 200) & (rgb[..., 1] > 130) & (rgb[..., 1] < 200) & (rgb[..., 2] < 140) & (a[..., 3] > 0)
skin[int(a.shape[0] * 0.5):] = False
sy, sx_ = np.nonzero(skin)
face_top, face_bot = sy.min(), sy.max()
HEAD_ROWS = face_bot + 9
head = a[:HEAD_ROWS, 12:].copy()
lab, n = __import__('scipy.ndimage', fromlist=['label']).label(head[..., 3] > 0)
keep = lab == np.bincount(lab[lab > 0]).argmax()
head[~keep] = 0
# close the beard bottom with an outline row
ys, xs = np.nonzero(head[..., 3] > 0)
head = head[:, xs.min():xs.max() + 1]
HEAD1 = Image.fromarray(head)
# blink version: dark eye pixels inside the face area become skin
hb = head.copy(); hr = hb[..., :3].astype(int)
fs = (hr[..., 0] > 200) & (hr[..., 1] > 130) & (hr[..., 1] < 200) & (hr[..., 2] < 140)
fy, fx = np.nonzero(fs); skin_col = np.median(hr[fs], 0).astype(np.uint8)
eye = (hr.sum(2) < 150) & (hb[..., 3] > 0)
eye[:fy.min()] = False; eye[fy.min() + 5:] = False; eye[:, :fx.min()] = False; eye[:, fx.max() + 1:] = False
hb[eye, :3] = skin_col
HEADB1 = Image.fromarray(hb)
BASE_TILT = -12
HEAD, HEADB = [U(h.rotate(BASE_TILT, expand=True, resample=Image.NEAREST)) for h in (HEAD1, HEADB1)]

# ---- buffer wheel: 8 pixel spokes, drawn on a cell grid ----
SPOKES = [  # clockwise from top, cells on an 11x11 grid
    [(5, 0), (5, 1), (5, 2)],
    [(9, 1), (8, 1), (8, 2), (7, 2), (7, 3)],
    [(8, 5), (9, 5), (10, 5)],
    [(9, 9), (8, 9), (8, 8), (7, 8), (7, 7)],
    [(5, 8), (5, 9), (5, 10)],
    [(1, 9), (2, 9), (2, 8), (3, 8), (3, 7)],
    [(0, 5), (1, 5), (2, 5)],
    [(1, 1), (2, 1), (2, 2), (3, 2), (3, 3)],
]
SHADES = [(28, 20, 58), (55, 44, 92), (85, 74, 122), (112, 102, 150), (135, 125, 172), (150, 140, 186), (150, 140, 186), (150, 140, 186)]
def wheel(fr, cx, cy, f, cell=4, a=255):
    lead = (f // 3) % 8
    for i, cells in enumerate(SPOKES):
        col = SHADES[(lead - i) % 8]
        for (gx, gy) in cells:
            x0 = snap(cx) + (gx - 5) * cell - cell // 2; y0 = snap(cy) + (gy - 5) * cell - cell // 2
            D(fr).rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1], fill=col + (int(a),))

def s11():
    out = []; N = 138
    HW = HEAD.width; CY = MOUTH_Y + 8          # head centre height in the opening
    CLX, CLY = MOUTH + 196, 272
    for f in range(N):
        fr = new()
        # pipe wiggle before he peeks, and a small hop when he ducks back
        dy = 0
        if 6 <= f < 14: dy = -2 if f % 2 else 0
        dy = min(dy, pipe_bounce(f - 128))
        # head position: how far it sticks out of the opening
        if f < 14: out_ = 0
        elif f < 26: out_ = HW * 0.92 * ease_back((f - 14) / 12, 2.2)
        elif f < 118: out_ = HW * 0.92 + (2 if (f // 10) % 4 == 1 else 0)
        elif f < 126: out_ = HW * 0.92 * (1 - ease_in((f - 118) / 8))
        else: out_ = 0
        tilt = 0
        if 26 <= f < 40: tilt = [0, 4, 4, 4, 0, -4, -4, -4, 0, 0, 0, 0, 0, 0][f - 26]
        blink = f in (34, 35, 82, 83, 104, 105)
        if out_ > 1:
            im = HEADB if blink else HEAD
            if tilt: im = U((HEADB1 if blink else HEAD1).rotate(BASE_TILT + tilt, expand=True, resample=Image.NEAREST))
            cx = MOUTH + out_ - HW / 2
            place(fr, im, cx, 0, cy=CY + dy, clip_x=MOUTH)
        # thought bubbles + cloud with spinning wheel
        al = 255 if f < 112 else 255 * (1 - clamp((f - 112) / 6))
        if 40 <= f < 118:
            for i, (dx, ddy, r, st) in enumerate([(84, -40, 4, 40), (108, -54, 7, 44)]):
                if f >= st: px(fr, MOUTH + dx - r, CY + ddy - r, r * 2, (225, 215, 245), al)
            s = ease_back((f - 47) / 9, 2.0) if f >= 47 else 0
            if f >= 112: s = 1 + 0.15 * (f - 112) / 6
            if s > 0:
                cloud(fr, CLX, CLY, 0.95 * s, al)
                if f >= 54 and f < 112: wheel(fr, CLX - 2, CLY - 2, f - 54, cell=6)
        if 112 <= f < 120: burst(fr, CLX, CLY, (f - 112) / 8, n=12, speed=90, cols=((225, 215, 245), WHITE), seed=4)
        draw_pipe(fr, 0, dy)
        # the pipe lip covers the head edge: redraw the rim over the head
        out.append(finish(fr))
    return out

if __name__ == '__main__':
    frames = s11()
    sheet = Image.new('RGB', (1200, 4 * 150))
    for k, p in enumerate([10, 20, 30, 36, 50, 60, 66, 83, 100, 114, 122, 130]):
        sheet.paste(frames[p].crop((0, 216, 600, 416)).resize((400, 133)), ((k % 3) * 400, (k // 3) * 150))
    sheet.save('/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/sheet_11.png')
    frames[66].crop((100, 216, 500, 380)).resize((800, 328), Image.NEAREST).save('/tmp/claude-0/-home-claude/6d8aaa48-7e39-5aa3-b065-e4dbb89d71cf/scratchpad/v2/zoom_11.png')
    print(write_gif(frames, '11_peek_buffering'), len(frames))
