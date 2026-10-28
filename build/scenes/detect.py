"""Splits a footer scene into parts the app can rebuild for any bar length.

Scenes are drawn on a screenshot where the pipe is at x 18 and Quit at x 742 (1x px). Each frame is
cut into blobs (connected bits of what changed since frame 0). Then:
  - travel: stretches where the wizard (the biggest moving blob) keeps moving one way at a steady
    speed. They're stored with their speed and the length of their repeating cycle (found by
    comparing his shape frame to frame), so the app can loop or shorten them;
  - everything else stays put relative to the pipe or Quit: a blob's position is mapped by where it
    sits between the two (near the pipe -> follows the pipe, near Quit -> follows Quit).
"""
import json, sys
import numpy as np
from scipy import ndimage

PIPE_X, QUIT_X = 18, 742
PIPE_ZONE, QUIT_ZONE = 92, 736

def blobs(mask):
    lab, n = ndimage.label(ndimage.binary_dilation(mask, iterations=3))
    lab = lab * mask
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None: continue
        m = lab[sl] == i; cnt = int(m.sum())
        if cnt < 4: continue
        ys, xs = np.nonzero(m)
        out.append({'x0': sl[1].start, 'y0': sl[0].start, 'x1': sl[1].stop, 'y1': sl[0].stop, 'cx': float(xs.mean() + sl[1].start), 'n': cnt})
    return out

def detect(npz):
    d = np.load(npz); fr, mask = d['fr'], d['mask']
    per = [blobs(m) for m in mask]
    # the wizard: the biggest blob in the bar between the pipe and Quit zones
    wiz = []
    for bl in per:
        c = [b for b in bl if PIPE_ZONE <= b['cx'] < QUIT_ZONE]
        wiz.append(max(c, key=lambda b: b['n']) if c else None)
    cx = np.array([w['cx'] if w else np.nan for w in wiz])
    v = np.full(len(cx), np.nan)
    for i in range(2, len(cx) - 2):
        win = cx[i - 2:i + 3]
        if not np.isnan(win).any(): v[i] = (win[-1] - win[0]) / 4
    moving = np.abs(np.nan_to_num(v)) > 1.5
    runs, i = [], 0
    while i < len(cx):
        if moving[i]:
            j = i
            while j + 1 < len(cx) and moving[j + 1] and np.sign(v[j + 1]) == np.sign(v[i]): j += 1
            if j - i + 1 >= 12:
                a, b = i - 2, j + 2
                speed = (cx[b] - cx[a]) / (b - a)
                # cycle: the shift k where his cropped shape repeats best
                def crop(f):
                    w = wiz[f]
                    return mask[f][w['y0']:w['y1'], w['x0']:w['x1']] if w else None
                best, bk = 1e9, 0
                for k in range(3, min(25, (b - a) // 2 + 1)):
                    diffs = []
                    for f in range(a, b - k + 1):
                        p, q = crop(f), crop(f + k)
                        if p is None or q is None: continue
                        h, w_ = min(p.shape[0], q.shape[0]), min(p.shape[1], q.shape[1])
                        diffs.append((p[:h, :w_] != q[:h, :w_]).mean() + abs(p.shape[1] - q.shape[1]) * 0.01)
                    if diffs and np.mean(diffs) < best: best, bk = float(np.mean(diffs)), k
                runs.append({'from': int(a), 'to': int(b), 'speed': round(float(abs(speed)), 2), 'dir': int(np.sign(speed)),
                             'startX': round(float(cx[a]), 1), 'endX': round(float(cx[b]), 1), 'cycle': int(bk), 'cycleMatch': round(1 - best, 3)})
            i = j + 1
        else: i += 1
    return {'frames': int(len(fr)), 'durs': d['durs'].tolist(), 'travel': runs, 'blobs': per,
            'wizard': [None if np.isnan(c) else round(float(c), 1) for c in cx]}

if __name__ == '__main__':
    out = {}
    for f in sys.argv[1:-1]:
        name = f.split('/')[-1][:-4]; r = detect(f); out[name] = r
        print(f"{name:36s} {r['frames']:3d} frames  travel: " + ('; '.join(f"frames {t['from']}-{t['to']} {'<-' if t['dir'] < 0 else '->'} {t['speed']} px/f, cycle {t['cycle']} ({t['cycleMatch']:.0%})" for t in r['travel']) or 'none'))
    json.dump(out, open(sys.argv[-1], 'w'))
