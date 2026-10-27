'use strict';
// Real ROM Tools data for the UI previews and screenshots (mock-htk.js reads window.__ROMS).
//
//   node build/ui-preview/make-rom-preview-data.js <folder of N64 ROMs>
//
// Made from free homebrew test ROMs (PeterLemon/N64), so every value on the screenshots,
// hashes included, is what the app really shows for that file. One ROM is also saved
// byte-swapped (.v64) and one zipped, to show those formats.
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
const out = path.join(__dirname, 'rom-preview-data.js');
fs.writeFileSync(out, `// Made by make-rom-preview-data.js from homebrew test ROMs.\nwindow.__ROMS = ${JSON.stringify({ folder: WIN, list, info })};\n`);
fs.rmSync(lib, { recursive: true, force: true });
console.log(`${list.length} ROMs -> ${out}`);
