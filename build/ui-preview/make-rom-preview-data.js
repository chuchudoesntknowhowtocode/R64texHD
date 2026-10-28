'use strict';
// Real ROM Tools data for the UI previews and screenshots (mock-htk.js reads window.__ROMS).
//
//   node build/ui-preview/make-rom-preview-data.js <folder of N64 ROMs>
//
// Made from free homebrew test ROMs (PeterLemon/N64), so every value shown for them, hashes
// included, is what the app really shows for that file. One ROM is also saved byte-swapped
// (.v64) and one zipped, to show those formats. A few retail games are added from their header
// details only, to show the box art and descriptions; their hashes say "(preview)".
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const rom = require('../../app/core/rom');
const rtz = require('../../app/core/rtz');

const src = process.argv[2];
if (!src) { console.error('usage: node make-rom-preview-data.js <folder of N64 ROMs>'); process.exit(1); }
const WIN = 'D:\\N64\\ROMs';

// Copy into a small library: Demos, Tests and Tools, like a real ROM folder.
const lib = fs.mkdtempSync(path.join(os.tmpdir(), 'r64roms-'));
const files = [];
(function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { if (e.name === '.git') continue; const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (/\.(n64|z64)$/i.test(e.name)) files.push(p); } })(src);
const group = (f) => (/NICCC|Devo|Video|Sound|Fractal|GBEMU/i.test(f) ? 'Demos' : /CPUTest|CP1ABS|Input|RSP|RDP|FrameBuffer/i.test(f) ? 'Tests' : 'Homebrew');
files.sort();
files.forEach((f, i) => {
  const dir = path.join(lib, group(f)); fs.mkdirSync(dir, { recursive: true });
  const name = path.basename(f).replace(/\.n64$/i, '.z64');
  const buf = fs.readFileSync(f);
  if (i === 1) {                                     // a byte-swapped copy
    const v = Buffer.from(buf); for (let j = 0; j + 1 < v.length; j += 2) { const t = v[j]; v[j] = v[j + 1]; v[j + 1] = t; }
    fs.writeFileSync(path.join(dir, name.replace(/\.z64$/, '.v64')), v);
  } else if (i === 2) {                              // a zipped copy
    const zip = new rtz.ZipWriter(path.join(dir, name.replace(/\.z64$/, '.zip')));
    zip.add(name, zlib.deflateRawSync(buf), 8, zlib.crc32(buf), buf.length, Date.now()); zip.close();
  } else fs.writeFileSync(path.join(dir, name), buf);
});

const win = (p) => (p ? WIN + '\\' + path.relative(lib, p).split(path.sep).join('\\') : WIN).replace(/\\$/, '');
const scan = rom.scan(lib);
const list = scan.roms.map((r) => ({ ...r, path: win(r.path), folder: r.folder.split('/').join('\\'), rel: r.rel.split('/').join('\\') }));
const info = {};
for (const r of scan.roms) { const i = rom.info(r.path); i.path = win(i.path); i.folder = win(i.folder); delete i.modified; info[i.path] = i; }
// Retail games, header details only: [file, header title, game code, size in MB, CIC].
const RETAIL = [
  ['GoldenEye 007 (USA).z64', 'GOLDENEYE', 'NGEE', 12, 'CIC-6102 / 7101'], ['Banjo-Kazooie (USA).z64', 'Banjo-Kazooie', 'NBKE', 16, 'CIC-6103 / 7103'],
  ['Donkey Kong 64 (USA).z64', 'DONKEY KONG 64', 'NDOE', 32, 'CIC-6105 / 7105'], ["Legend of Zelda, The - Majora's Mask (USA).z64", "ZELDA MAJORA'S MASK", 'NZSE', 32, 'CIC-6105 / 7105'],
  ['Blast Corps (USA).v64', 'Blast Corps', 'NBCE', 8, 'CIC-6102 / 7101'], ["Conker's Bad Fur Day (USA).z64", 'CONKER BFD', 'NFUE', 64, 'CIC-6105 / 7105'],
  ['Paper Mario (USA).z64', 'PAPERMARIO', 'NMQE', 40, 'CIC-6103 / 7103'], ['Super Mario 64 (USA).z64', 'SUPER MARIO 64', 'NSME', 8, 'CIC-6102 / 7101'],
  ['Star Fox 64 (USA).z64', 'STARFOX64', 'NFXE', 12, 'CIC-6101'],
];
for (const [file, title, code, mb, cic] of RETAIL) {
  const h = Buffer.alloc(0x40); h.writeUInt32BE(0x80371240, 0); h.writeUInt32BE(0x0f, 4); h.writeUInt32BE(0x80000400, 8); h.writeUInt32BE(0x144b, 0x0c);
  h.fill(0x20, 0x20, 0x34); h.write(title, 0x20, 'latin1'); h.write(code, 0x3b, 'latin1');
  const hd = rom.parseHeader(h), lib = rom.libraryGame(code), p = WIN + '\\' + file, size = mb * 1048576;
  const format = file.endsWith('.v64') ? 'v64' : 'z64';
  list.push({ path: p, rel: file, folder: '', file, format, size, ...hd, libKey: lib ? code.slice(0, 3) : '', libTitle: lib ? lib.title : '', libArt: lib ? lib.art : '' });
  info[p] = { path: p, file, folder: WIN, inner: '', fileSize: size, format, formatName: format === 'v64' ? 'Byte-swapped (.v64)' : 'Big-endian (.z64)',
    romSize: size, mbit: mb * 8, ...hd, crc1Hex: '(preview)', crc2Hex: '', libultraVersion: '2.0K', entryHex: '80000400', clockHex: '0000000F', piHex: '80371240',
    cic, cicNote: '', bootCrc: '(preview)', checksum: 'Not checked (preview data)', checksumOk: null, crc32: '(preview)', md5: '(preview)', sha1: '(preview)',
    trailingZeros: 0, layout: [{ name: 'Header', start: 0, end: 0x40 }, { name: `Boot code (${cic})`, start: 0x40, end: 0x1000 }, { name: 'Game code and data', start: 0x1000, end: size }],
    zelda: null, library: lib };
}
list.sort((a, b) => (a.folder === b.folder ? a.file.localeCompare(b.file) : !a.folder ? -1 : !b.folder ? 1 : a.folder.localeCompare(b.folder)));
const matched = new Set(list.map((r) => r.libKey).filter(Boolean)).size;
// Ship Mods: the ports list and the games behind them, with a real CRC1 for each (from crc.json).
const shipid = require('../../app/core/shipid');
const crcOf = (key) => (Object.entries(shipid.crcTable()).find(([, v]) => v[0] === key && /\(U\)/.test(v[1])) || Object.entries(shipid.crcTable()).find(([, v]) => v[0] === key) || [''])[0];
const ship = { ports: shipid.ports(), games: {} };
for (const p of ship.ports) if (p.game) { const c = crcOf(p.game); ship.games[p.game] = { game: rom.library().games[p.game], crc: c, rom: c ? shipid.crcTable()[c][1] : '' }; }
const out = path.join(__dirname, 'rom-preview-data.js');
fs.writeFileSync(out, `// Made by make-rom-preview-data.js from homebrew test ROMs.\nwindow.__ROMS = ${JSON.stringify({ folder: WIN, list, info, matched, libraryCount: rom.library().count })};\nwindow.__SHIP = ${JSON.stringify(ship)};\n`);
fs.rmSync(lib, { recursive: true, force: true });
console.log(`${list.length} ROMs -> ${out}`);
