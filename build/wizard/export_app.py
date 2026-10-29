"""Exports the footer scenes for the app (app/assets/scenes):
  stage.png      the footer as the scenes were drawn on it (pipe, Quit and Save removed: the real buttons sit
                 on top), with the bar dimmed to 30% (idle); bar_full.png the bar at full strength (filled
                 segments are cut from it)
  poses.png/json wizard sprites for the live endings (run, flying kick, uppercut; robed walk)
  <clip>/        per clip: atlas_N.webp (lossless) + clip.json: per frame the world and sprite layer pieces,
                 the wizard / opponent boxes (for pokes and bursts), events (hits, K.O., burn...) and, for
                 fights, where the actors stand (for the instant exit)
  index.json     every clip with what the director needs to pick it
Everything is 1x (one pixel of the 890 x 100 footer). Scene band = rows 0..92 of the stage.
    python3 export_app.py <app assets dir> [group ...]     groups: stage fights classics extras trips clips"""
import os, sys, json, hashlib, glob
import numpy as np
from PIL import Image
from scipy import ndimage as nd
import lib, layers
import fights, elf_fight, clips, s11, scenes2, scenes3, scenes4, elf2
import review_build as RB
import martial as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(sys.argv[1], 'scenes'); os.makedirs(OUT, exist_ok=True)
GROUPS = sys.argv[2:] or ['stage', 'fights', 'classics', 'extras', 'trips', 'clips']
T2, B2 = lib.SAFE, lib.BOTTOM                       # scene band in 2x rows
STAGE_TOP = T2 // 2                                 # 108: screenshot row where the footer stage starts
STAGE_H = 100

def to1x(a): return a[::2, ::2]

# ------------------------------------------------------------------ the stage
def stage():
    bg = np.array(lib.BG_NOPIPE.convert('RGB'))[::2, ::2][STAGE_TOP:STAGE_TOP + STAGE_H].copy()
    dark = np.array(lib.DARK, np.uint8)
    q = lib.QUIT_HOME; qm = np.array(lib.QUIT)[::2, ::2, 3] > 0
    qy, qx = q[1] // 2 - STAGE_TOP, q[0] // 2
    reg = bg[qy:qy + qm.shape[0], qx:qx + qm.shape[1]]; reg[qm[:reg.shape[0], :reg.shape[1]]] = dark
    bg[:, 884:] = dark                                                     # Save's edge
    bg[(B2 - T2) // 2:] = dark                                             # the screenshot's window edge under the band
    bg[:, 736:] = np.where((np.abs(bg[:, 736:].astype(int) - dark).sum(-1) < 40)[..., None], dark, bg[:, 736:])
    full = to1x(RB.FULLb); barm = to1x(RB.BARb); mag = to1x(RB.MAGb)
    pad = np.zeros((STAGE_H - full.shape[0],) + full.shape[1:], full.dtype)
    full = np.concatenate([full, pad]); barm = np.concatenate([barm, np.zeros((STAGE_H - barm.shape[0], barm.shape[1]), bool)])
    mag = np.concatenate([mag, np.zeros((STAGE_H - mag.shape[0], mag.shape[1]), bool)])
    dim = bg.astype(float); d = dark.astype(float); dim[mag] = d + (dim[mag] - d) * 0.3
    Image.fromarray(dim.astype(np.uint8)).save(os.path.join(OUT, 'stage.png'))
    fa = np.zeros(full.shape[:2] + (4,), np.uint8); fa[barm, :3] = full[barm]; fa[barm, 3] = 255
    Image.fromarray(fa).save(os.path.join(OUT, 'bar_full.png'))
    # wizard sprites for the live endings (1x, facing left, feet at the bottom)
    poses = {}
    for name, (pose, kw) in {'run1': ('run1', {}), 'run2': ('run2', {}), 'fly': ('fly', {}), 'up': ('st_up', {})}.items():
        im, ox, oy, fy = M.rig(pose, False, 'hero', True); poses[name] = (im, ox, oy, fy)
    for k in range(4):
        im, b = lib.run_frame(k); poses[f'robe{k}'] = (im, im.width // 2, 0, im.height)
    atlas, meta, x = [], {}, 0
    H = max(p[0].height for p in poses.values()) // 2 + 2
    W = sum(p[0].width // 2 + 2 for p in poses.values())
    sheet = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for name, (im, ox, oy, fy) in poses.items():
        s = im.resize((im.width // 2, im.height // 2), Image.NEAREST); sheet.paste(s, (x, 0))
        meta[name] = dict(x=x, y=0, w=s.width, h=s.height, hipx=ox // 2, hipy=oy // 2, foot=fy // 2); x += s.width + 2
    sheet.save(os.path.join(OUT, 'poses.png'))
    hf = M.hip_floor('st_stance') // 2 - STAGE_TOP; air = (fights.AIR) // 2 - STAGE_TOP
    json.dump(dict(poses=meta, floor=lib.FLOOR // 2 - STAGE_TOP, hipFloor=hf, air=air, mouth=lib.MOUTH // 2, sx=lib.SX // 2,
                   bar=dict(x0=RB.BAR_X0 // 2, x1=RB.BAR_X1 // 2, seg=RB.SEG // 2), quit=[qx, qy, 130, 50],
                   pipe=[16, 14, 69, 69], stageH=STAGE_H, bandH=(B2 - T2) // 2),
              open(os.path.join(OUT, 'stage.json'), 'w'), indent=1)
    print('stage', flush=True)

# ------------------------------------------------------------------ renders on the dimmed footer
# The app shows the idle bar at 30%; scenes are rendered on that so their world layer (tints) matches it.
def _dim(img):
    a = np.array(img.convert('RGB')).astype(float); m = RB.MAG; d = np.array(lib.DARK, float)
    a[m] = d + (a[m] - d) * 0.3; return Image.fromarray(a.astype(np.uint8))
BG_D, BG_NOPIPE_D = _dim(lib.BG), _dim(lib.BG_NOPIPE)
_px, _py = lib.PIPE_HOME; PIPE_R = (_px, _py - T2, _px + lib.PIPE.width, _py - T2 + lib.PIPE.height)
_qx, _qy = lib.QUIT_HOME; QUIT_R = (_qx, _qy - T2, _qx + lib.QUIT.width, _qy - T2 + lib.QUIT.height)
def _no_buttons(bg_band):
    """the band with the pipe and Quit taken out (the real buttons are on top in the app)"""
    a = bg_band.copy(); dark = np.array(lib.DARK, np.uint8)
    for (r, im) in ((PIPE_R, lib.PIPE), (QUIT_R, lib.QUIT)):
        m = np.array(im)[..., 3] > 0; reg = a[r[1]:r[3], r[0]:r[2]]; reg[m[:reg.shape[0], :reg.shape[1]]] = dark
    return a
STAGE2 = _no_buttons(np.array(BG_D)[T2:B2])
def buttons(a, ref, w, s, nob, thr=0):
    """a scene that moves or recolours the pipe / Quit: the real one hides for that frame and the scene's copy
    (all of it) goes in the sprite layer. -> (pipe hidden, quit hidden)"""
    out = []
    for r in (PIPE_R, QUIT_R):
        reg = (slice(r[1], r[3]), slice(r[0], r[2]))
        moved = (np.abs(a[reg].astype(int) - ref[reg].astype(int)).max(-1) > thr).any()
        if moved:
            m = np.abs(a[reg].astype(int) - nob[reg].astype(int)).max(-1) > thr
            s[reg][m, :3] = a[reg][m]; s[reg][m, 3] = 255; w[reg][m, 3] = 0
        out.append(bool(moved))
    return out
def scene_layers(fn):
    """two renders (dimmed footer A, scrambled B) -> yields (world, sprite, (pipe hidden, quit hidden)) per frame"""
    A0, N0 = lib.BG, lib.BG_NOPIPE
    try:
        layers._swap(BG_D, BG_NOPIPE_D); fa = [np.array(f.convert('RGB'))[T2:B2] for f in fn()]
        layers._swap(layers._scrambled(BG_D), layers._scrambled(BG_NOPIPE_D)); fb = [np.array(f.convert('RGB'))[T2:B2] for f in fn()]
    finally:
        layers._swap(A0, N0)
    bg = np.array(BG_D)[T2:B2]
    for i in range(len(fa)):
        a, b = fa[i], fb[i]; fa[i] = fb[i] = None
        same = (a == b).all(-1); ch = (a != bg).any(-1)
        w = np.zeros(a.shape[:2] + (4,), np.uint8); s = np.zeros_like(w)
        wm = ~same & ch; sm = same & ch
        w[wm, :3] = a[wm]; w[wm, 3] = 255; s[sm, :3] = a[sm]; s[sm, 3] = 255
        yield w, s, buttons(a, bg, w, s, STAGE2)
def gif_layers(path):
    """a finished GIF (the approved classic scenes): what changed from its first frame is sprite"""
    im = Image.open(path); im.seek(0); f0 = np.array(im.convert('RGB'))[T2:B2]
    nob = _no_buttons(f0)
    for i in range(im.n_frames):
        im.seek(i); a = np.array(im.convert('RGB'))[T2:B2]
        m = np.abs(a.astype(int) - f0.astype(int)).max(2) > 24
        s = np.zeros(a.shape[:2] + (4,), np.uint8); s[m, :3] = a[m]; s[m, 3] = 255; w = np.zeros_like(s)
        yield w, s, buttons(a, f0, w, s, nob, thr=24)
def runs(flags):
    """[[start, end), ...] of the frames where a flag is set"""
    out, st = [], None
    for i, f in enumerate(flags + [False]):
        if f and st is None: st = i
        if not f and st is not None: out.append([st, i]); st = None
    return out

# ------------------------------------------------------------------ packing
class Packer:
    """shelf packer into atlases of width W, new atlas past H_MAX"""
    def __init__(self, W=1024, H_MAX=4096): self.W, self.H_MAX = W, H_MAX; self.atlases = []; self._new()
    def _new(self): self.atlases.append([]); self.x = self.y = self.row = 0
    def add(self, img):
        h, w = img.shape[:2]
        if w > self.W: raise ValueError('piece wider than the atlas')
        if self.x + w > self.W: self.x = 0; self.y += self.row; self.row = 0
        if self.y + h > self.H_MAX: self._new()
        pos = (len(self.atlases) - 1, self.x, self.y); self.atlases[-1].append((self.x, self.y, img))
        self.x += w; self.row = max(self.row, h)
        return pos
    def save(self, d):
        names = []
        for i, pieces in enumerate(self.atlases):
            H = max([y + p.shape[0] for x, y, p in pieces] + [1]); im = np.zeros((H, self.W, 4), np.uint8)
            for x, y, p in pieces: im[y:y + p.shape[0], x:x + p.shape[1]] = p
            n = f'atlas_{i}.webp'; Image.fromarray(im).save(os.path.join(d, n), 'WEBP', lossless=True, quality=100, method=4); names.append(n)
        return names

def crop(a):
    m = a[..., 3] > 0
    if not m.any(): return None
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    return a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1], int(xs[0]), int(ys[0])

def blobs(alpha):
    lab, n = nd.label(nd.binary_dilation(alpha, iterations=2) & True)
    out = []
    for i, sl in enumerate(nd.find_objects(lab), 1):
        if sl is None: continue
        m = (lab[sl] == i) & alpha[sl]; c = int(m.sum())
        if c < 12: continue
        out.append(dict(x=sl[1].start, y=sl[0].start, w=sl[1].stop - sl[1].start, h=sl[0].stop - sl[0].start, n=c))
    return out
def pick(bl, near=None, feet=True):
    """the wizard (or opponent): nearest blob to an x, or the biggest one standing near the floor"""
    cand = [b for b in bl if b['x'] + b['w'] > 92 and (not feet or b['y'] + b['h'] >= 50)]
    if not cand: return None
    if near is not None: b = min(cand, key=lambda b: abs(b['x'] + b['w'] / 2 - near) - b['n'] * 0.002)
    else: b = max(cand, key=lambda b: b['n'])
    return [b['x'], b['y'], b['w'], b['h']]

def export_clip(cid, it, meta, actors=None):
    """it yields (world, sprite) 2x band arrays; actors(i) -> (wizard x, opponent x) in 2x or None"""
    d = os.path.join(OUT, cid); os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, '*')): os.remove(f)
    pk = Packer(); seen = {}; W, S, wiz, opp, hp, hq = [], [], [], [], [], []
    for i, (w2, s2, fl) in enumerate(it):
        hp.append(fl[0]); hq.append(fl[1])
        w, s = to1x(w2), to1x(s2)
        row = []
        for lay, out in ((w, W), (s, S)):
            c = crop(lay)
            if c is None: out.append(None); continue
            img, x, y = c; h = hashlib.md5(img.tobytes() + bytes([img.shape[0] % 256, img.shape[1] % 256])).hexdigest()
            if h not in seen: seen[h] = pk.add(img)
            a, ax, ay = seen[h]; out.append([a, ax, ay, img.shape[1], img.shape[0], x, y])
        bl = blobs(s[..., 3] > 0)
        wx = ox = None
        if actors:
            r = actors(i)
            if r: wx, ox = r[0] / 2, r[1] / 2
        wiz.append(pick(bl, wx)); opp.append(pick(bl, ox) if ox is not None else None)
    meta = dict(meta, id=cid, frames=len(W), atlases=pk.save(d), world=W, sprite=S, wizard=wiz, opponent=opp if actors else None, hidePipe=runs(hp), hideQuit=runs(hq))
    json.dump(meta, open(os.path.join(d, 'clip.json'), 'w'), separators=(',', ':'))
    print(cid, len(W), 'frames', len(seen), 'pieces', len(pk.atlases), 'atlases', flush=True)
    return {k: v for k, v in meta.items() if k not in ('world', 'sprite', 'wizard', 'opponent', 'actors', 'events')} | {'events': meta.get('events', {})}

def save_index(entries, group):
    """one index file per group (groups can export in parallel); merge_index() joins them into index.json"""
    json.dump({e['id']: e for e in entries}, open(os.path.join(OUT, f'index_{group}.json'), 'w'), indent=1)
def merge_index():
    idx = {}
    for f in sorted(glob.glob(os.path.join(OUT, 'index_*.json'))): idx.update(json.load(open(f)))
    json.dump(idx, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)

# ------------------------------------------------------------------ fights
FIGHTS = []
for name in ('goblin', 'golem', 'robot', 'twin', 'car', 'elf'):
    for robed in (True, False):
        variants = [{}]
        if name in ('golem', 'robot'): variants = [{}, {'odd_hit': True}]
        if name == 'twin': variants = [{}, {'twin_wins_r1': True}]
        for v in variants: FIGHTS.append((name, robed, v))

def fight(name, robed, v):
    sc = fights.SCENES[name](robed=robed, **v); trace = []
    frames = fights.assemble(sc, trace=trace)
    n = len(frames); del frames
    hits = sorted({s for (s, d_, p, h, l) in sc.C.steps if h}) if getattr(sc, 'C', None) else []
    first = {}
    for i, t in enumerate(trace):
        if t and t[0] == 'base' and t[1] not in first: first[t[1]] = i
    ev = {'hit': [first[c] for c in hits if c in first], 'impact': [first[c] for c in sc.impacts if c in first],
          'ko': [first[sc.impacts[0]]] if sc.impacts and sc.impacts[0] in first else []}
    if sc.V0 is not None: ev['vs'] = [i for i, t in enumerate(trace) if t and t[0] == 'vs' and t[2] == 0][:1]
    if robed and sc.B0 in first: ev['burn'] = [first[sc.B0]]
    if name == 'car': ev['honk'] = [first[c] for c in (30, 44, 58) if c in first]
    combo = [first.get(sc.combo[0]), first.get(sc.combo[1])]
    robed_until = first.get(sc.B0 + 18, 0) if robed else 0
    cid = f'fight_{name}_{"robed" if robed else "gi"}' + ''.join('_' + k for k in v)
    acts = [sc.actors(t[1])[:2] if t else None for t in trace]
    imgs = sc.actors(sc.combo[0])[2]; Image.fromarray(np.array(imgs)[::2, ::2]).save('/tmp/_opp.png')
    meta = dict(kind='fight', opponent=name, robed=robed, oddHit=bool(v.get('odd_hit')), twinWinsR1=bool(v.get('twin_wins_r1')),
                psychedelic=name == 'elf', bonus=name == 'car', events=ev, combo=combo, robedUntil=robed_until, endsRobed=False,
                actors=[[a[0] / 2, a[1] / 2] if a else None for a in acts])
    e = export_clip(cid, scene_layers(lambda: fights.assemble(fights.SCENES[name](robed=robed, **v))), meta, actors=lambda i: acts[i])
    os.replace('/tmp/_opp.png', os.path.join(OUT, cid, 'opponent.png'))
    j = json.load(open(os.path.join(OUT, cid, 'clip.json'))); j['actors'] = meta['actors']; json.dump(j, open(os.path.join(OUT, cid, 'clip.json'), 'w'), separators=(',', ':'))
    return dict(e, combo=combo, robedUntil=robed_until)

def do_fights():
    save_index([fight(*f) for f in FIGHTS], 'fights')

# ------------------------------------------------------------------ the rest
APPROVED = os.path.join(HERE, 'assets', 'approved')
def do_classics():
    out = []
    for g in sorted(glob.glob(os.path.join(APPROVED, '*.gif'))):
        base = os.path.basename(g)[:-4]
        if base.startswith('11_'): continue                                  # the peek is re-rendered (clips)
        out.append(export_clip('classic_' + base, gif_layers(g), dict(kind='classic', endsRobed=True, robed=True)))
    save_index(out, 'classics')
def do_extras():
    out = []
    for i in (18, 20, 21):                                                   # the owner's picks from 12-21
        name, fn = scenes2.SCENES[i]
        out.append(export_clip('classic_' + name, scene_layers(fn), dict(kind='classic', endsRobed=True, robed=True)))
    save_index(out, 'extras')
def do_trips():
    out = []
    for mod in (scenes3, scenes4):
        for i, (name, fn) in mod.SCENES.items():
            out.append(export_clip('trip_' + name, scene_layers(fn), dict(kind='trip', psychedelic=True, endsRobed=True, robed=True, set='LSD' if mod is scenes3 else 'DMT')))
    out.append(export_clip('trip_43_dmt_machine_elf_sacred_warp', scene_layers(elf2.scene), dict(kind='trip', psychedelic=True, endsRobed=True, robed=True, set='DMT')))
    save_index(out, 'trips')
def do_clips():
    out = [export_clip('busy_11_peek_buffering', scene_layers(s11.s11), dict(kind='busy', robed=True, endsRobed=True)),
           export_clip('rerobe', scene_layers(clips.rerobe), dict(kind='rerobe', robed=False, endsRobed=True))]
    for k, p in enumerate(clips.PHRASES):
        out.append(export_clip(f'peek_{k + 1:02d}', scene_layers(lambda p=p: clips.idle_peek(p)), dict(kind='peek', phrase=p, robed=True, endsRobed=True)))
    save_index(out, 'clips')

FN = dict(stage=stage, fights=do_fights, classics=do_classics, extras=do_extras, trips=do_trips, clips=do_clips)
for g in GROUPS: FN[g]()
merge_index()
