"""Builds the review videos for the Wizard Scene Review page: every new clip, and the chained runs that show
how the director strings them together on a real job (progress bar included).

The footer is drawn the way the app will: idle bar dim (30%), filled segments bright from the right toward
the pipe; scene tints/warps under the segments and behind Quit; characters and call-outs on top.
    python3 review_build.py <out dir> [only ...]"""
import os, sys, json, subprocess, shutil, math
import numpy as np
from PIL import Image
import lib
from lib import SAFE, BOTTOM, FW, FH, DARK
import layers

HERE = os.path.dirname(os.path.abspath(__file__))
BGA = np.array(lib.BG.convert('RGB'))
BAR_X0, BAR_X1 = 176, 1456
SEG = 32                                                                       # one bar segment (2x px)
_r, _g, _b = [BGA[..., i].astype(int) for i in range(3)]
_mag = (_r > _g + 22) & (_b >= _g) & (_r > 40); _mag[:SAFE] = False; _mag[BOTTOM:] = False; _mag[:, :BAR_X0] = False; _mag[:, BAR_X1:] = False
MAG = _mag
QUITM = np.zeros(BGA.shape[:2], bool)
_q = np.array(lib.QUIT)[..., 3] > 0; qx, qy = lib.QUIT_HOME; QUITM[qy:qy + _q.shape[0], qx:qx + _q.shape[1]] = _q
FPS = 30

# everything below works on the scene band only (rows SAFE..BOTTOM); videos show the footer
T, B = SAFE, BOTTOM
BGb = BGA[T:B]; MAGb = MAG[T:B]; QUITb = QUITM[T:B]
# the bar at full strength everywhere: the densest stretch of the fade (next to the pipe), repeated along the bar
_ys = np.nonzero(MAGb.any(1))[0]; BARb = np.zeros_like(MAGb); BARb[_ys.min():_ys.max() + 1, BAR_X0:BAR_X1] = True
FULLb = BGb.copy()
for _x in range(BAR_X0, BAR_X1): FULLb[:, _x] = BGb[:, BAR_X0 + 8 + (_x - BAR_X0) % 64]
CROP = (196, 416)                                                              # rows shown in the videos

# ------------------------------------------------------------------ the bar
def bar(p, state='run', k=0):
    """footer band with the progress bar at p (0..1). state: 'idle', 'run', 'fail' (k = frames since it failed)"""
    out = BGb.copy().astype(float); d = np.array(DARK, float)
    if state == 'idle': p = 0
    fill_x = BAR_X1 - round(p * (BAR_X1 - BAR_X0) / SEG) * SEG
    xs = np.arange(FW)[None, :].repeat(B - T, 0)
    filled = BARb & (xs >= fill_x); unf = MAGb & ~filled
    out[unf] = d + (out[unf] - d) * 0.3
    out[filled] = FULLb[filled]                                                # filled segments: the bar at full strength
    front = filled & (xs < fill_x + SEG)
    out[front] = np.minimum(255, out[front] * 1.25 + 10)
    if state == 'fail' and k < 16 and (k // 4) % 2 == 0:
        out[filled] = out[filled] * 0.4 + np.array([255, 40, 50]) * 0.6
    return out.clip(0, 255).astype(np.uint8), filled

# ------------------------------------------------------------------ layers of a clip
def from_scene(fn):
    """toolkit clip -> iterator of (world, sprite) band arrays via the two-background render"""
    return layers.render_iter(fn)
def from_gif(path):
    """a finished GIF (classic scenes, old tests): everything that changed from its first frame is sprite"""
    im = Image.open(path); im.seek(0); f0 = np.array(im.convert('RGB')).astype(int)[T:B]
    for i in range(im.n_frames):
        im.seek(i); a = np.array(im.convert('RGB'))[T:B]
        m = np.abs(a.astype(int) - f0).max(2) > 24
        sp = np.zeros(a.shape[:2] + (4,), np.uint8); sp[m, :3] = a[m]; sp[m, 3] = 255
        yield np.zeros_like(sp), sp
def gif_len(path): return Image.open(path).n_frames

def compose(world, sprite, p, state='run', k=0):
    base, filled = bar(p, state, k)
    out = base.copy()
    wm = (world[..., 3] > 0) & ~QUITb                                          # scene tints: behind Quit
    out[wm] = world[wm, :3]
    fm = filled & wm                                                           # the fill stays readable through tints
    out[fm] = (base[fm].astype(int) * 0.75 + world[fm, :3].astype(int) * 0.25).astype(np.uint8)
    sm = sprite[..., 3] > 0
    out[sm] = sprite[sm, :3]
    out[QUITb] = BGb[QUITb]                                                    # the real button stays on top
    full = BGA.copy(); full[T:B] = out
    return full[CROP[0]:CROP[1]]

# ------------------------------------------------------------------ a run: segments on a job timeline, written as they go
EMPTY = None
class Run:
    def __init__(self, out_dir):
        self.dir = out_dir; shutil.rmtree(out_dir, ignore_errors=True); os.makedirs(out_dir); self.n = 0; self.marks = []
    def _put(self, a): Image.fromarray(a).save(os.path.join(self.dir, f'{self.n:05d}.png'), compress_level=1); self.n += 1
    def add(self, layers_iter, prog, state='run', label=None):
        if label: self.marks.append((self.n, label))
        for i, (w, s) in enumerate(layers_iter):
            st = state(i) if callable(state) else state
            self._put(compose(w, s, prog(self.n), st[0] if isinstance(st, tuple) else st, st[1] if isinstance(st, tuple) else i))
    def gap(self, n, prog, label=None, state='run'):
        global EMPTY
        if EMPTY is None: EMPTY = np.zeros(BGb.shape[:2] + (4,), np.uint8)
        self.add(((EMPTY, EMPTY) for _ in range(n)), prog, state, label)
    def encode(self, out_mp4, poster=None):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(self.dir, '%05d.png'),
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_mp4], check=True)
        if poster: shutil.copy(os.path.join(self.dir, f'{self.n // 3:05d}.png'), poster)
        shutil.rmtree(self.dir)

def gap_len(rate_per_frame, blocks=2, max_s=3.0, min_s=1.0):
    """wait 3 s, or until 2 more segments fill if that's sooner (at least 1 s)"""
    seg_p = SEG / (BAR_X1 - BAR_X0)
    t_blocks = (blocks * seg_p / rate_per_frame) if rate_per_frame > 0 else 1e9
    return int(round(max(min_s * FPS, min(max_s * FPS, t_blocks))))
