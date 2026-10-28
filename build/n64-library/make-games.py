"""Builds app/assets/n64/games.json: N64 game ID -> box art file + description, for 6 · ROM Tools.

    python3 build/n64-library/make-games.py <box art folder> <descriptions .txt> <libretro serial .dat> <libretro no-intro .dat>

The box art (Kondorito's N64 3D boxes, via EmuMovies) is named by No-Intro title, so each title
is looked up in the libretro N64 databases to find its game code (e.g. NMQE = Paper Mario).
Games are keyed by the first 3 letters of the code (category + 2-letter game ID), so a ROM from
any region finds the same box. Descriptions come from the N64 North American library text.
"""
import json, re, sys, unicodedata
from pathlib import Path

art_dir, desc_file, serial_dat, nointro_dat = map(Path, sys.argv[1:5])
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app' / 'assets' / 'n64'

def norm(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'\([^)]*\)', '', t).replace('&', 'and')
    t = re.sub(r'^the |, the\b|^sesame street - ', '', t.strip())
    return re.sub(r'[^a-z0-9]', '', t)

# Title -> code. The No-Intro database first (its codes are read from the ROM headers), then the
# libretro serial list for titles it lacks. USA entries win when a name matches several.
codes = {}
for m in re.finditer(r'game \(\s*name "([^"]+)"(.*?)\n\)', nointro_dat.read_text(encoding='utf-8'), re.S):
    s = re.search(r'serial "([A-Z0-9]{4})"', m.group(2))
    if s: codes.setdefault(m.group(1), s.group(1))
for m in re.finditer(r'comment "([^"]+)"\s*serial "NUS-([A-Z0-9]{4})-', serial_dat.read_text(encoding='utf-8')):
    codes.setdefault(m.group(1), m.group(2))
by_norm = {}
for name, code in codes.items():
    by_norm.setdefault(norm(name), []).append((0 if 'USA' in name else 1, code))

# Box art names that are spelt differently in the databases (each code checked against them).
ALIAS = {
    '007 - GoldenEye (USA)': 'NGEE', 'Air Boarder 64 (Europe)': 'NABP', 'Toy Story 2 (USA)': 'NTHE',
    "Kobe Bryant's NBA Courtside (USA)": 'NNBE', "Midway's Greatest Arcade Hits Vol. 1 (USA)": 'NAIE',
    'NFL Quarterback Club 2001 (USA)': 'NQCE', "Olympic Hockey Nagano '98 (USA)": 'NHNE', 'Quake 64 (USA)': 'NQKE',
    'Roadsters Trophy (USA) (En,Fr,Es)': 'NRRE', 'Wave Race 64 (USA) (Rev A)': 'NWRE', 'Superman (USA) (En,Fr,Es)': 'NSPE',
    'Centre Court Tennis (Europe)': 'NTSP', 'Premier Manager 64 (Europe)': 'NPMP', 'Rakuga Kids (Europe)': 'NKRP',
}
# Description titles that are written differently from the box art names.
DESC_ALIAS = {
    "A Bug's Life": "Bug's Life, A (USA)", "Charlie's Blast Territory": "Charlie Blast's Territory (USA)",
    'Daikatana': "John Romero's Daikatana (USA)", 'Donald Duck: Quack Attack': "Donald Duck - Goin' Quackers (USA) (En,Fr,De,Es,It)",
    'Extreme-G 2': 'Extreme-G XG2 (USA)', 'GoldenEye 007': '007 - GoldenEye (USA)', 'Kobe Bryant in NBA Courtside': "Kobe Bryant's NBA Courtside (USA)",
    "Midway's Greatest Arcade Hits: Volume 1": "Midway's Greatest Arcade Hits Vol. 1 (USA)", 'NFL QB Club 2001': 'NFL Quarterback Club 2001 (USA)',
    "Olympic Hockey '98": "Olympic Hockey Nagano '98 (USA)", 'PGA European Tour Golf': 'PGA European Tour (USA)',
    'Ridge Racer 64': 'RR64 - Ridge Racer 64 (USA)', 'Roadsters': 'Roadsters Trophy (USA) (En,Fr,Es)',
    'Superman: The New Superman Adventures': 'Superman (USA) (En,Fr,Es)', 'Toy Story 2: Buzz Lightyear to the Rescue!': 'Toy Story 2 (USA)',
    'Bass Hunter 64': 'In-Fisherman - Bass Hunter 64 (USA)', '007: The World Is Not Enough': '007 - The World Is Not Enough (USA)',
    "G.A.S.P!! Fighters' NEXTream": 'Deadly Arts (USA)',
    "Donald Duck: Quack Attack / Goin' Quackers": "Donald Duck - Goin' Quackers (USA) (En,Fr,De,Es,It)",
}

def code_of(name):
    if name in ALIAS: return ALIAS[name]
    if name in codes: return codes[name]
    c = sorted(by_norm.get(norm(name), []))
    return c[0][1] if c else None

def title_of(name):  # "Legend of Zelda, The - Ocarina of Time (USA) (Rev B)" -> "The Legend of Zelda: Ocarina of Time"
    t = re.sub(r'\s*\([^)]*\)', '', name).strip()
    m = re.match(r'^(.*), (The|A|An)( - .*)?$', t)
    if m: t = f'{m.group(2)} {m.group(1)}{m.group(3) or ""}'
    return t.replace(' - ', ': ')

txt = desc_file.read_text(encoding='utf-8')
straight = lambda t: t.replace('\u2019', "'").replace('\u2018', "'")   # the list may use curly apostrophes
descs = {straight(m.group(1).strip()): ' '.join(l.strip() for l in m.group(2).splitlines())
         for m in re.finditer(r'^\d{3}\. (.+)\n((?:     .+\n?)+)', txt, re.M)}

games, problems = {}, []
images = sorted(p for p in art_dir.glob('*.png') if p.name != 'Cover.png')
for p in images:
    code = code_of(p.stem)
    if not code: problems.append(f'no game code: {p.name}'); continue
    key = code[:3]
    if key in games: problems.append(f'two boxes for {key}: {games[key]["art"]} and {p.name}'); continue
    games[key] = {'title': title_of(p.stem), 'code': code[:3] + 'E', 'art': p.name, 'description': ''}
by_art = {g['art'][:-4]: g for g in games.values()}
art_norm = {norm(k): g for k, g in by_art.items()}
for title, text in descs.items():
    g = by_art.get(DESC_ALIAS.get(title, '')) or art_norm.get(norm(title))
    if g: g['description'] = text; g['title'] = title
    else: problems.append(f'description with no box art: {title}')
for g in games.values():
    if not g['description']: problems.append(f'box art with no description: {g["art"]}')

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'games.json').write_text(json.dumps({
    'about': 'N64 North American library for ROM Tools. Key: game ID (category letter + 2-letter ID). Box art: Kondorito (EmuMovies).',
    'count': len(games), 'games': dict(sorted(games.items())),
}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'{len(games)} games, {sum(1 for g in games.values() if g["description"])} with descriptions -> {OUT / "games.json"}')
print('\n'.join(problems))
