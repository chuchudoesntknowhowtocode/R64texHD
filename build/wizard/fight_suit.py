import os, sys
from PIL import Image
import numpy as np
import lib
HERE = os.path.dirname(os.path.abspath(__file__))
for n in 'RECFBIDH': lib.P1[n] = Image.open(os.path.join(HERE, f'px_suit_{n}.png'))
lib._cache.clear()
import fight
for i, (name, fn) in fight.EX.items():
    frames = fn()
    out = lib.write_gif(frames, name.replace('sf_example', 'sf_red_gi_example'), outdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'fighter'))
    frames[[60, 120, 130][i - 1]].crop((0, 208, lib.FW, 404)).save(os.path.join(HERE, f'redgi_{i}.png'))
    print(out, len(frames), flush=True)
