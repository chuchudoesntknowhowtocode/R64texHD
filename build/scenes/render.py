"""Plays a detected scene for a given pipe / Quit position (what the app will do) and saves an
animated WebP, for reviewing the splits.   render.py <scenes .npz dir> <plan.json> <bg dir> <out dir>"""
import json, sys, os
import numpy as np
from PIL import Image
PIPE_X, QUIT_X, PIPE_ZONE, QUIT_ZONE = 18, 742, 92, 736
src_dir, plan_file, bg_dir, out_dir = sys.argv[1:5]
plan = json.load(open(plan_file)); pos = json.load(open(os.path.join(bg_dir, 'pos.json')))
os.makedirs(out_dir, exist_ok=True)
TOP = 51                                              # scene rows shown: 51..211

def stat_dx(x, pipeX, quitX):                         # where a still blob goes
    if x < PIPE_ZONE: return pipeX - PIPE_X
    if x >= QUIT_ZONE: return quitX - QUIT_X
    t = (x - PIPE_X) / (QUIT_X - PIPE_X)
    return pipeX + t * (quitX - pipeX) - x

def timeline(p, pipeX, quitX):
    """[(source frame, {blob index: dx})] for this bar length."""
    steps, f, runs = [], 0, {t['from']: t for t in p['travel']}
    mapx = lambda x: x + stat_dx(x, pipeX, quitX)
    while f < p['frames']:
        t = runs.get(f)
        if t:
            a, b, k, v = t['from'], t['to'], max(1, t['cycle']), t['speed']
            x0, x1 = mapx(t['startX']), mapx(t['endX'])
            d = 1 if x1 >= x0 else -1
            n = max(1, round(abs(x1 - x0) / v))
            for j in range(n):
                src = a + (j % k)
                cEst = t['startX'] + t['dir'] * v * (src - a)
                wdx = x0 + d * v * j - cEst
                dxs = {}
                for i, bl in enumerate(p['blobs'][src]):
                    near = PIPE_ZONE <= bl['cx'] < QUIT_ZONE and abs(bl['cx'] - cEst) < 90
                    dxs[i] = wdx if near else stat_dx(bl['cx'], pipeX, quitX)
                steps.append((src, dxs))
            f = b + 1
        else:
            steps.append((f, {i: stat_dx(bl['cx'], pipeX, quitX) for i, bl in enumerate(p['blobs'][f])}))
            f += 1
    return steps

for name, p in plan.items():
    d = np.load(os.path.join(src_dir, name + '.npz')); fr, mask = d['fr'], d['mask']
    for w, ps in pos.items():
        pipeX, quitX, off = ps['pipeX'], ps['quitX'], ps['pipeTop'] + 2 - 124   # app y = scene y + off
        bg = Image.open(os.path.join(bg_dir, f'{w}.png')).convert('RGB')
        W = min(bg.width, quitX + 300)
        base = Image.new('RGB', (W, 160), bg.getpixel((W // 2, bg.height - 2)))
        base.paste(bg.crop((0, TOP + off, W, min(bg.height, TOP + off + 160))), (0, 0))
        steps = timeline(p, pipeX, quitX); frames = []
        for src, dxs in steps:
            im = base.copy()
            for i, bl in enumerate(p['blobs'][src]):
                sl = (slice(bl['y0'], bl['y1']), slice(bl['x0'], bl['x1']))
                rgba = np.dstack([fr[src][sl], (mask[src][sl] * 255).astype(np.uint8)])
                im.paste(Image.fromarray(rgba, 'RGBA'), (int(round(bl['x0'] + dxs[i])), bl['y0'] - TOP), Image.fromarray(rgba[..., 3]))
            frames.append(im)
        frames[0].save(os.path.join(out_dir, f'{name}-{w}.webp'), save_all=True, append_images=frames[1:], duration=33, loop=0, lossless=True, method=4)
        print(name, w, len(steps), 'frames')
