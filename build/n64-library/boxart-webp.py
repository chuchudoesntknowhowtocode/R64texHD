"""Shrinks the ROM Tools box art: app/assets/n64/boxart/*.png -> .webp (392 px wide, lossy, quality 80), and points
games.json at the new files. Run after make-games.py.

    python3 build/n64-library/boxart-webp.py
"""
import json, os, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / 'app' / 'assets' / 'n64'
ART, GAMES = ROOT / 'boxart', ROOT / 'games.json'
Q = int(sys.argv[1]) if len(sys.argv) > 1 else 80
W = 392

before = after = 0
for png in sorted(ART.glob('*.png')):
    im = Image.open(png).convert('RGBA')
    if im.width > W:                                    # shown at most 196 px wide: 2x that covers high-DPI screens
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    webp = png.with_suffix('.webp')
    im.save(webp, 'WEBP', quality=Q, method=6, alpha_quality=60)
    before += png.stat().st_size; after += webp.stat().st_size
    png.unlink()
games = json.loads(GAMES.read_text(encoding='utf-8'))
n = 0
for g in games['games'].values():
    if isinstance(g, dict) and str(g.get('art', '')).endswith('.png'):
        g['art'] = g['art'][:-4] + '.webp'; n += 1
GAMES.write_text(json.dumps(games, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'{n} entries updated; box art {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB')
