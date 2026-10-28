"""Builds app/assets/n64/crc.json: ROM header CRC1 -> N64 library game, for Ship port archives.

    python3 build/n64-library/make-ship-ids.py <mupen64plus.ini> <libretro no-intro N64 .dat>

Every libultraship .o2r made from a ROM carries a "version" file: one endianness byte, then the
ROM's CRC1 (header offset 0x10). Torch (Ghostship, Starship, SpaghettiKart...) and Shipwright's
exporter (Ship of Harkinian, 2Ship) both write it, and newer archives may also put it in
manifest.json as "game_version". So any port, including ones not out yet, can be matched to its
game: CRC1 -> ROM dump (mupen64plus.ini, by MD5) -> game code (No-Intro, by MD5) -> library game.
GameCube disc versions that the ports accept are added from the ports' own source.
"""
import json, re, sys
from pathlib import Path

ini_file, dat_file = map(Path, sys.argv[1:3])
ROOT = Path(__file__).resolve().parents[2]
games = json.loads((ROOT / 'app' / 'assets' / 'n64' / 'games.json').read_text(encoding='utf-8'))['games']

dumps = {}   # CRC1 -> [(md5, GoodName)]
ini = ini_file.read_text(encoding='utf-8', errors='replace')
for m in re.finditer(r'^\[([0-9A-F]{32})\]\s*\n(.*?)(?=^\[|\Z)', ini, re.M | re.S):
    crc = re.search(r'^CRC=([0-9A-F]{8}) [0-9A-F]{8}', m.group(2), re.M)
    name = re.search(r'^GoodName=(.*)$', m.group(2), re.M)
    if crc: dumps.setdefault(crc.group(1), []).append((m.group(1), name.group(1).strip() if name else ''))
serial = {m.group(1): m.group(2) for m in re.finditer(r'md5 ([0-9A-F]{32})[^)]*?serial "([A-Z0-9]{4})"', dat_file.read_text(encoding='utf-8'))}

def label(names):  # the cleanest dump name: a verified [!] one, without the [..] tags
    region = lambda n: next((i for i, r in enumerate(('(U)', '(E)', '(J)')) if r in n), 3)   # US name first when releases share a CRC
    best = sorted(names, key=lambda n: (0 if '[!]' in n else 1, '[' in n.replace('[!]', ''), region(n), len(n)))[0]
    return re.sub(r'\s*\[[^\]]*\]', '', best).strip()

table = {}
for crc, lst in dumps.items():
    keys = {serial[md5][:3] for md5, _ in lst if md5 in serial} & games.keys()
    if len(keys) == 1:
        key = keys.pop()
        table[crc] = [key, label([n for md5, n in lst if md5 in serial and serial[md5][:3] == key] or [n for _, n in lst])]

# GameCube discs the ports accept (Shipwright soh/GameVersions.h, 2ship2harkinian mm/2s2h/BenPort.h).
EXTRA = {
    'F7F52DB8': ['CZL', 'Ocarina of Time (Japan) (GameCube, Collector\'s Edition)'], 'F611F4BA': ['CZL', 'Ocarina of Time (Japan) (GameCube)'],
    'F3DD35BA': ['CZL', 'Ocarina of Time (USA) (GameCube)'], '09465AC3': ['CZL', 'Ocarina of Time (Europe) (GameCube)'],
    'F43B45BA': ['CZL', 'Ocarina of Time Master Quest (Japan) (GameCube)'], 'F034001A': ['CZL', 'Ocarina of Time Master Quest (USA) (GameCube)'],
    '1D4136F3': ['CZL', 'Ocarina of Time Master Quest (Europe) (GameCube)'], '871E1C92': ['CZL', 'Ocarina of Time (GameCube debug, 2002-03-21)'],
    '87121EFE': ['CZL', 'Ocarina of Time (GameCube debug, 2002-03-13)'], '917D18F6': ['CZL', 'Ocarina of Time Master Quest (GameCube debug)'],
    '3D81FB3E': ['CZL', 'Ocarina of Time (iQue, Taiwan)'], 'B1E1E07B': ['CZL', 'Ocarina of Time (iQue, China)'],
    'B443EB08': ['NZS', "Majora's Mask (USA) (GameCube)"],
}
for crc, v in EXTRA.items(): table.setdefault(crc, v)

out = ROOT / 'app' / 'assets' / 'n64' / 'crc.json'
out.write_text(json.dumps({'about': 'ROM header CRC1 -> [game ID, ROM name]. Made by build/n64-library/make-ship-ids.py.',
                           'crc': dict(sorted(table.items()))}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(f'{len(table)} CRC1 values for {len({v[0] for v in table.values()})} of {len(games)} games -> {out}')
