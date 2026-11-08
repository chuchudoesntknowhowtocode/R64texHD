"""Converts ESRGAN (RRDBNet, 4x) .pth models to the ncnn .param/.bin pair Real-ESRGAN-ncnn-vulkan loads.

    python3 build/models/convert.py                    (the whole pack: build/models/src/*.pth -> build/models/out)
    python3 build/models/convert.py <model.pth> <out/name>

No PyTorch needed: the .pth is read with a small unpickler (both the zip format and the legacy format), and the
ncnn graph is written directly. Weights are stored as fp16 (half the size), biases as fp32, like ncnn's own tools.
Only the standard ESRGAN layout is accepted (old "model.N" keys or BasicSR "conv_first / body" keys, any nf/nb,
growth 32, 4x); anything else stops with an error rather than producing a broken model.
"""
import collections, io, pickle, struct, sys, zipfile
from pathlib import Path
import numpy as np

DTYPES = {'FloatStorage': np.float32, 'HalfStorage': np.float16, 'DoubleStorage': np.float64, 'BFloat16Storage': None}

class _Storage:
    def __init__(self, name): self.name = name

def _rebuild_tensor(storage, offset, size, stride, *_):
    arr, = storage
    n = int(np.prod(size)) if size else 1
    flat = arr[offset:offset + (sum((s - 1) * st for s, st in zip(size, stride)) + 1 if size else 1)]
    if size and list(stride) != [int(np.prod(size[i + 1:])) for i in range(len(size))]:
        return np.lib.stride_tricks.as_strided(flat, shape=size, strides=[s * flat.itemsize for s in stride]).copy()
    return flat[:n].reshape(size).copy()

class _Unpickler(pickle.Unpickler):
    dry = False
    def __init__(self, f, load_storage):
        super().__init__(f); self.load_storage = load_storage
    def find_class(self, module, name):
        if self.dry and module == 'torch._utils' and name.startswith('_rebuild'): return lambda *a: None
        if module in ('collections', 'typing') and name == 'OrderedDict': return collections.OrderedDict
        if module == 'torch._utils' and name in ('_rebuild_tensor_v2', '_rebuild_tensor'): return _rebuild_tensor
        if module == 'torch' and name in DTYPES: return _Storage(name)
        if module == 'torch._utils' and name == '_rebuild_parameter': return lambda data, *a: data
        raise pickle.UnpicklingError(f'unexpected object in the model file: {module}.{name}')
    def persistent_load(self, pid):
        # zip: ('storage', type, key, location, numel); legacy: ('storage', type, key, location, size, view)
        typ, key = pid[1], pid[2]
        dt = DTYPES.get(typ.name)
        if dt is None: raise ValueError(f'unsupported weight type {typ.name}')
        return (self.load_storage(key, dt),)

def load_pth(path):
    data = Path(path).read_bytes()
    if data[:2] == b'PK':
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist(); root = names[0].split('/')[0]
        pkl = next(n for n in names if n.endswith('data.pkl'))
        cache = {}
        def st(key, dt):
            if key not in cache: cache[key] = np.frombuffer(z.read(f'{root}/data/{key}'), dtype=dt)
            return cache[key]
        obj = _Unpickler(io.BytesIO(z.read(pkl)), st).load()
    else:   # legacy format: magic, protocol, sys info, the object, the storage keys, then each storage's bytes
        f = io.BytesIO(data)
        for _ in range(3): pickle.load(f)
        start, dts = f.tell(), {}
        dry = _Unpickler(f, lambda key, dt: dts.setdefault(key, dt)); dry.dry = True; dry.load()   # pass 1: storage types
        storages = {}
        for key in pickle.load(f):
            n, = struct.unpack('<q', f.read(8))
            storages[key] = np.frombuffer(f.read(n * np.dtype(dts[key]).itemsize), dtype=dts[key])
        f.seek(start)
        obj = _Unpickler(f, lambda key, dt: storages[key]).load()                                   # pass 2: real weights
    if isinstance(obj, dict):
        for k in ('params_ema', 'params', 'state_dict'):
            if k in obj and isinstance(obj[k], dict): obj = obj[k]; break
    return {k: np.asarray(v, dtype=np.float32) for k, v in obj.items()}

def to_new_keys(sd):
    """Old ESRGAN keys -> BasicSR names (conv_first, body.i.rdbj.convk, conv_body, conv_up1/2, conv_hr, conv_last)."""
    if 'conv_first.weight' in sd: return sd
    if 'model.0.weight' not in sd: raise ValueError('not an ESRGAN model (no model.0 / conv_first)')
    out = {}
    for k, v in sd.items():
        p = k.split('.')
        if p[1] == '0': n = 'conv_first.' + p[-1]
        elif p[1] == '1':
            if len(p) == 5: n = 'conv_body.' + p[-1]                       # model.1.sub.<nb>.weight: the trunk conv
            else: n = f'body.{p[3]}.{p[4].lower()}.{p[5]}.{p[-1]}'
        else: n = {'3': 'conv_up1', '6': 'conv_up2', '8': 'conv_hr', '10': 'conv_last'}.get(p[1], 'x' + p[1]) + '.' + p[-1]
        out[n] = v
    return out

def shape_of(sd):
    nf = sd['conv_first.weight'].shape[0]
    nb = 1 + max(int(k.split('.')[1]) for k in sd if k.startswith('body.'))
    gc = sd['body.0.rdb1.conv1.weight'].shape[0]
    if sd['conv_first.weight'].shape[1] != 3 or sd['conv_last.weight'].shape[0] != 3: raise ValueError('needs 3-channel input and output')
    if 'conv_up2.weight' not in sd or any(k.startswith('x') for k in sd): raise ValueError('only 4x ESRGAN models are supported')
    return nf, nb, gc

class Graph:
    def __init__(self): self.layers = []; self.weights = []; self.n = 0
    def blob(self): self.n += 1; return f'b{self.n}'
    def add(self, typ, ins, params='', weights=None):
        out = self.blob(); self.layers.append([typ, f'{typ.lower()}{len(self.layers)}', list(ins), [out], params])
        if weights: self.weights.append((len(self.layers) - 1, weights))
        return out
    def conv(self, x, sd, name, act=False):
        w, b = sd[name + '.weight'], sd[name + '.bias']
        y = self.add('Convolution', [x], f'0={w.shape[0]} 1={w.shape[2]} 3=1 4={w.shape[2] // 2} 5=1 6={w.size}', (w, b))
        return self.add('ReLU', [y], '0=2.000000e-01') if act else y
    def text(self):
        # ncnn wants one consumer per blob: fan out with Split layers.
        uses = collections.Counter(b for l in self.layers for b in l[2])
        layers, made = [], collections.defaultdict(list)
        produced = {b: i for i, l in enumerate(self.layers) for b in l[3]}
        for l in self.layers:
            for j, b in enumerate(l[2]):
                if uses[b] > 1: l[2][j] = made[b].pop(0)
            layers.append(l)
            for b in l[3]:
                if uses[b] > 1:
                    outs = [f'{b}_{k}' for k in range(uses[b])]; made[b] = list(outs)
                    layers.append(['Split', f'split_{b}', [b], outs, ''])
        blobs = {b for l in layers for b in l[3]}
        lines = ['7767517', f'{len(layers)} {len(blobs)}']
        for typ, name, ins, outs, params in layers:
            lines.append(f'{typ:<16} {name:<20} {len(ins)} {len(outs)} ' + ' '.join(ins + outs) + (' ' + params if params else ''))
        return '\n'.join(lines) + '\n'

def build(sd):
    nf, nb, gc = shape_of(sd)
    g = Graph()
    g.layers.append(['Input', 'input', [], ['data'], '']); x = 'data'
    fea = g.conv(x, sd, 'conv_first')
    h = fea
    for i in range(nb):
        r = h
        for j in (1, 2, 3):
            t = r; feats = [t]
            for k in (1, 2, 3, 4):
                inp = feats[0] if len(feats) == 1 else g.add('Concat', feats, '0=0')
                feats.append(g.conv(inp, sd, f'body.{i}.rdb{j}.conv{k}', act=True))
            x5 = g.conv(g.add('Concat', feats, '0=0'), sd, f'body.{i}.rdb{j}.conv5')
            r = g.add('BinaryOp', [g.add('BinaryOp', [x5], '0=2 1=1 2=2.000000e-01'), t], '0=0')
        h = g.add('BinaryOp', [g.add('BinaryOp', [r], '0=2 1=1 2=2.000000e-01'), h], '0=0')
    h = g.add('BinaryOp', [fea, g.conv(h, sd, 'conv_body')], '0=0')
    for n in ('conv_up1', 'conv_up2'):
        h = g.conv(g.add('Interp', [h], '0=1 1=2.000000e+00 2=2.000000e+00'), sd, n, act=True)
    out = g.conv(g.conv(h, sd, 'conv_hr', act=True), sd, 'conv_last')
    g.layers[-1][3] = ['output']
    return g, (nf, nb, gc)

def write(sd, out_stem):
    g, shape = build(sd)
    out_stem = Path(out_stem); out_stem.parent.mkdir(parents=True, exist_ok=True)
    out_stem.with_suffix('.param').write_text(g.text(), newline='\n')
    with open(out_stem.with_suffix('.bin'), 'wb') as f:
        for _, (w, b) in g.weights:
            f.write(struct.pack('<I', 0x01306B47)); f.write(w.astype('<f2').tobytes())      # fp16 weights, tagged
            f.write(b.astype('<f4').tobytes())                                               # fp32 bias
    return shape

# The pack: source file pattern (in build/models/src) -> model name Real-ESRGAN is given with -n.
PACK = [('*HDCube*.pth', 'hdcube-x4'), ('*GameAI*2*.pth', 'gameai2-x4'), ('*PixelPerfect*4*.pth', 'pixelperfect4-x4')]

if __name__ == '__main__' and len(sys.argv) == 1:      # no arguments: convert the whole pack into build/models/out
    here = Path(__file__).parent
    for pattern, name in PACK:
        found = sorted((here / 'src').glob(pattern), key=lambda p: p.name.lower())
        if not found: sys.exit(f'missing: build/models/src/{pattern}')
        sd = to_new_keys(load_pth(found[0])); nf, nb, gc = write(sd, here / 'out' / name)
        print(f'{found[0].name} -> out/{name}.param/.bin  (ESRGAN {nf}nf {nb}nb, 4x)')
    sys.exit(0)

if __name__ == '__main__':
    src, stem = sys.argv[1], sys.argv[2]
    sd = to_new_keys(load_pth(src))
    nf, nb, gc = write(sd, stem)
    print(f'{Path(src).name} -> {stem}.param/.bin  (ESRGAN {nf}nf {nb}nb gc{gc}, 4x)')
