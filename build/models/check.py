"""Checks a converted model: runs it with ncnn (CPU) and with a plain NumPy ESRGAN on the same small image,
using the same weights, and reports the largest difference (0-1 scale). Needs: pip install ncnn

    python3 build/models/check.py build/models/src/4x_HDCube.pth build/models/out/hdcube-x4
    python3 build/models/check.py --random            (self-test on a random small network)
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import convert

def conv(x, w, b):
    c, h, wd = x.shape; k = w.shape[2]; p = k // 2
    xp = np.pad(x, ((0, 0), (p, p), (p, p)))
    cols = np.stack([xp[:, i:i + h, j:j + wd] for i in range(k) for j in range(k)], axis=1)   # c, k*k, h, w
    return np.tensordot(w.reshape(w.shape[0], -1), cols.reshape(c * k * k, h * wd), axes=1).reshape(w.shape[0], h, wd) + b[:, None, None]

lrelu = lambda x: np.where(x > 0, x, 0.2 * x)
up2 = lambda x: x.repeat(2, axis=1).repeat(2, axis=2)

def forward(sd, x, nb):
    c = lambda n, t: conv(t, sd[n + '.weight'], sd[n + '.bias'])
    fea = c('conv_first', x); h = fea
    for i in range(nb):
        r = h
        for j in (1, 2, 3):
            feats = [r]
            for k in (1, 2, 3, 4): feats.append(lrelu(c(f'body.{i}.rdb{j}.conv{k}', np.concatenate(feats))))
            r = c(f'body.{i}.rdb{j}.conv5', np.concatenate(feats)) * 0.2 + feats[0]
        h = r * 0.2 + h
    h = fea + c('conv_body', h)
    h = lrelu(c('conv_up1', up2(h))); h = lrelu(c('conv_up2', up2(h)))
    return c('conv_last', lrelu(c('conv_hr', h)))

def run_ncnn(stem, x):
    import ncnn
    net = ncnn.Net(); net.opt.use_vulkan_compute = False; net.opt.use_fp16_storage = False; net.opt.use_fp16_arithmetic = False; net.opt.use_fp16_packed = False
    assert net.load_param(str(stem) + '.param') == 0 and net.load_model(str(stem) + '.bin') == 0
    ex = net.create_extractor(); ex.input('data', ncnn.Mat(np.ascontiguousarray(x, dtype=np.float32)))
    _, out = ex.extract('output')
    return np.array(out)

def random_sd(nf=8, nb=2, gc=4, seed=1):
    g = np.random.default_rng(seed); sd = {}
    def mk(n, o, i): sd[n + '.weight'] = (g.standard_normal((o, i, 3, 3)) * (0.5 / np.sqrt(i * 9))).astype(np.float32); sd[n + '.bias'] = (g.standard_normal(o) * 0.01).astype(np.float32)
    mk('conv_first', nf, 3)
    for i in range(nb):
        for j in (1, 2, 3):
            for k in (1, 2, 3, 4): mk(f'body.{i}.rdb{j}.conv{k}', gc, nf + (k - 1) * gc)
            mk(f'body.{i}.rdb{j}.conv5', nf, nf + 4 * gc)
    for n in ('conv_body', 'conv_up1', 'conv_up2', 'conv_hr'): mk(n, nf, nf)
    mk('conv_last', 3, nf)
    return sd

if __name__ == '__main__':
    if sys.argv[1] == '--random':
        sd = random_sd(); stem = Path(__file__).parent / 'out' / '_selftest'
    else:
        sd = convert.to_new_keys(convert.load_pth(sys.argv[1])); stem = Path(sys.argv[2])
    nf, nb, gc = convert.write(sd, stem)
    sdw = {k: (v.astype(np.float16).astype(np.float32) if k.endswith('weight') else v) for k, v in sd.items()}   # what the .bin holds
    x = np.random.default_rng(7).random((3, 12, 10), dtype=np.float32)
    a, b = forward(sdw, x, nb), run_ncnn(stem, x)
    d = float(np.abs(a - b).max())
    print(f'{stem.name}: {nf}nf {nb}nb, output {b.shape}, max difference NumPy vs ncnn {d:.2e}', 'OK' if a.shape == b.shape and d < 2e-3 else 'MISMATCH')
    if sys.argv[1] == '--random':
        for s in ('.param', '.bin'): stem.with_suffix(s).unlink()
