'use strict';
// N64 ROM explorer: finds ROMs in a folder and reads everything the header and boot code say.
//
// Byte orders: .z64 is big-endian (the N64's own order, first word 80 37 12 40), .v64 swaps every
// 2 bytes (37 80 40 12), .n64 reverses every 4 bytes (40 12 37 80). Everything is read in .z64 order.
// Header (0x40 bytes): 0x00 PI settings, 0x04 clock rate, 0x08 entry point, 0x0C libultra release,
// 0x10 CRC1, 0x14 CRC2, 0x20 title (20 bytes), 0x3B category, 0x3C 2-letter game ID, 0x3E region,
// 0x3F version. CIC chip: CRC32 of the boot code (0x40-0x1000). Checksum: the boot code's own sum over
// 0x1000-0x101000 (algorithm as in n64crc.c), compared with CRC1 / CRC2.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const rtz = require('./rtz');

const ROM_EXT = /\.(z64|v64|n64|rom|bin|u64|ndd|zip)$/i;
const MAGIC = { '80371240': 'z64', '37804012': 'v64', '40123780': 'n64' };
const FORMAT_NAME = { z64: 'Big-endian (.z64)', v64: 'Byte-swapped (.v64)', n64: 'Little-endian (.n64)' };

const CATEGORY = { N: 'Game Pak (cartridge)', D: '64DD disk', C: 'Cartridge for 64DD expansion', E: '64DD expansion', Z: 'Aleck64 arcade' };
const REGION = {
  '7': 'Beta', A: 'All regions', B: 'Brazil', C: 'China', D: 'Germany', E: 'North America', F: 'France', G: 'Gateway 64 (NTSC)',
  H: 'Netherlands', I: 'Italy', J: 'Japan', K: 'Korea', L: 'Gateway 64 (PAL)', N: 'Canada', P: 'Europe', S: 'Spain', U: 'Australia',
  W: 'Scandinavia', X: 'Europe', Y: 'Europe', Z: 'Europe',
};
const PAL = new Set(['D', 'F', 'H', 'I', 'L', 'P', 'S', 'U', 'W', 'X', 'Y', 'Z']);
// CIC lockout chip, from the CRC32 of the boot code, with the seed its checksum uses.
const CIC = {
  0x6170a4a1: { name: 'CIC-6101', seed: 0xf8ca4ddc, note: 'Star Fox 64 (NTSC)' },
  0x90bb6cb5: { name: 'CIC-6102 / 7101', seed: 0xf8ca4ddc, note: 'most games' },
  0x0b050ee0: { name: 'CIC-6103 / 7103', seed: 0xa3886759, note: 'e.g. Banjo-Kazooie, Paper Mario' },
  0x98bc2c86: { name: 'CIC-6105 / 7105', seed: 0xdf26f436, note: 'e.g. Zelda: Ocarina of Time, Majora\'s Mask' },
  0xacc8580a: { name: 'CIC-6106 / 7106', seed: 0x1fea617a, note: 'e.g. F-Zero X, Yoshi\'s Story' },
  0x009e9ea3: { name: 'CIC-7102', seed: null, note: 'Lylat Wars (PAL)' },
  0x0e018159: { name: 'CIC-8303', seed: null, note: '64DD' },
};

// The N64 North American library (box art + description), keyed by game ID: category letter +
// 2-letter ID, e.g. "NMQ" for NMQE Paper Mario. Any region's ROM finds the same game.
// Made by build/n64-library/make-games.py.
let LIBRARY = null;
function library() {
  if (!LIBRARY) {
    try { LIBRARY = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'assets', 'n64', 'games.json'), 'utf8')); }
    catch { LIBRARY = { count: 0, games: {} }; }
  }
  return LIBRARY;
}
const gameKey = (code) => (/^[A-Z0-9]{4}$/.test(code || '') ? code.slice(0, 3) : '');
function libraryGame(code) { const k = gameKey(code); return (k && library().games[k]) || null; }

const hex = (v, n = 8) => (v >>> 0).toString(16).toUpperCase().padStart(n, '0');

// Bytes in .z64 order (a copy for .v64 / .n64).
function toZ64(buf) {
  const fmt = MAGIC[buf.subarray(0, 4).toString('hex')];
  if (!fmt) return null;
  if (fmt === 'z64') return { data: buf, format: fmt };
  const out = Buffer.allocUnsafe(buf.length - (buf.length % 4));
  if (fmt === 'v64') for (let i = 0; i + 1 < out.length; i += 2) { out[i] = buf[i + 1]; out[i + 1] = buf[i]; }
  else for (let i = 0; i + 3 < out.length; i += 4) { out[i] = buf[i + 3]; out[i + 1] = buf[i + 2]; out[i + 2] = buf[i + 1]; out[i + 3] = buf[i]; }
  return { data: out, format: fmt };
}

// The checksum the boot code computes over 0x1000-0x101000 (n64crc.c).
function checksum(d, cicName, seed) {
  const START = 0x1000, LEN = 0x100000;
  if (d.length < START + LEN || seed == null) return null;
  let t1 = seed, t2 = seed, t3 = seed, t4 = seed, t5 = seed, t6 = seed;
  const is6105 = cicName.startsWith('CIC-6105');
  for (let i = START; i < START + LEN; i += 4) {
    const w = d.readUInt32BE(i);
    if (((t6 + w) >>> 0) < t6) t4 = (t4 + 1) >>> 0;
    t6 = (t6 + w) >>> 0;
    t3 = (t3 ^ w) >>> 0;
    const s = w & 0x1f, r = s ? ((w << s) | (w >>> (32 - s))) >>> 0 : w;
    t5 = (t5 + r) >>> 0;
    if (t2 > w) t2 = (t2 ^ r) >>> 0; else t2 = (t2 ^ t6 ^ w) >>> 0;
    if (is6105) t1 = (t1 + ((d.readUInt32BE(0x40 + 0x710 + (i & 0xff)) ^ w) >>> 0)) >>> 0;
    else t1 = (t1 + ((t5 ^ w) >>> 0)) >>> 0;
  }
  if (cicName.startsWith('CIC-6103')) return [((t6 ^ t4) + t3) >>> 0, ((t5 ^ t2) + t1) >>> 0];
  if (cicName.startsWith('CIC-6106')) return [(Math.imul(t6, t4) + t3) >>> 0, (Math.imul(t5, t2) + t1) >>> 0];
  return [(t6 ^ t4 ^ t3) >>> 0, (t5 ^ t2 ^ t1) >>> 0];
}

const text = (b) => b.toString('latin1').replace(/\0+$/, '').replace(/[^\x20-\x7e]/g, '?').trimEnd();
const ascii = (c) => (c >= 0x20 && c < 0x7f ? String.fromCharCode(c) : '');

// The header fields from the first 0x40 bytes (z64 order).
function parseHeader(h) {
  const cat = ascii(h[0x3b]), id = ascii(h[0x3c]) + ascii(h[0x3d]), reg = ascii(h[0x3e]);
  const code = cat + id + reg;
  return {
    title: text(h.subarray(0x20, 0x34)) || '(no title)',
    gameCode: code.length === 4 ? code : '',
    category: CATEGORY[cat] || (cat ? `Unknown (${cat})` : 'Not set (homebrew)'),
    gameId: id,
    region: REGION[reg] || (reg ? `Unknown (${reg})` : 'Not set'),
    regionCode: reg,
    video: reg ? (PAL.has(reg) ? 'PAL' : 'NTSC') : '',
    version: h[0x3f],
    crc1: h.readUInt32BE(0x10), crc2: h.readUInt32BE(0x14),
    clockRate: h.readUInt32BE(0x04), entryPoint: h.readUInt32BE(0x08),
    libultra: h.readUInt32BE(0x0c), piSettings: h.readUInt32BE(0x00),
  };
}

// libultra release word: e.g. 0x0000144B -> "2.0K"
function libultraVersion(v) {
  const rev = v & 0xff, major = (v >> 8) & 0xff;
  if (!major || rev < 0x41 || rev > 0x5a) return v ? hex(v) : '';
  return `${(major / 10).toFixed(1)}${String.fromCharCode(rev)}`;
}

// Zelda 64 file table (Ocarina of Time / Majora's Mask): starts with the makerom entry
// 00000000 00001060 00000000 00000000, then [vromStart, vromEnd, romStart, romEnd] per file.
function zeldaFiles(d) {
  const sig = Buffer.from('00000000000010600000000000000000', 'hex');
  let at = -1;
  for (let i = 0x1000; i < Math.min(d.length, 0x40000) - 16; i += 16) if (d.compare(sig, 0, 16, i, i + 16) === 0) { at = i; break; }
  if (at < 0) return null;
  const files = [];
  for (let p = at; p + 16 <= d.length && files.length < 4000; p += 16) {
    const vs = d.readUInt32BE(p), ve = d.readUInt32BE(p + 4), rs = d.readUInt32BE(p + 8), re = d.readUInt32BE(p + 12);
    if (!vs && !ve && !rs && !re) break;
    files.push({ vromStart: vs, vromEnd: ve, size: ve - vs, compressed: re !== 0 && rs !== 0xffffffff, missing: rs === 0xffffffff });
  }
  if (files.length < 10) return null;
  const build = d.indexOf('zelda@', 0, 'latin1');
  return {
    table: at, count: files.length,
    compressed: files.filter((f) => f.compressed).length,
    missing: files.filter((f) => f.missing).length,
    // "zelda@srd44" then the build date, each ending in a 0 byte.
    build: build >= 0 ? d.subarray(build, build + 64).toString('latin1').split(/\0+/).slice(0, 2).filter((t) => /^[\x20-\x7e]+$/.test(t)).join(' · ') : '',
    largest: [...files].map((f, i) => ({ ...f, index: i })).sort((a, b) => b.size - a.size).slice(0, 5),
  };
}

// Reads a ROM file (or the first ROM inside a .zip). Returns { data (z64 order), raw, format, inner }.
function readRom(file) {
  if (/\.zip$/i.test(file)) {
    const entries = rtz.readEntries(file).filter((e) => /\.(z64|v64|n64|rom|bin|u64)$/i.test(e.name) && e.usize >= 0x1000);
    if (!entries.length) throw new Error('No N64 ROM inside this .zip');
    const raw = rtz.readEntry(file, entries[0]);
    const r = toZ64(raw);
    if (!r) throw new Error('The file inside the .zip is not an N64 ROM');
    return { ...r, raw, inner: entries[0].name };
  }
  const raw = fs.readFileSync(file);
  const r = toZ64(raw);
  if (!r) throw new Error('Not an N64 ROM (unknown first bytes)');
  return { ...r, raw };
}

// Quick look for the list: header only.
function peek(file) {
  if (/\.zip$/i.test(file)) {
    const r = readRom(file);
    return { format: r.format, inner: r.inner, size: r.raw.length, ...parseHeader(r.data.subarray(0, 0x40)) };
  }
  const fd = fs.openSync(file, 'r');
  try {
    const head = Buffer.alloc(0x40);
    if (fs.readSync(fd, head, 0, 0x40, 0) < 0x40) return null;
    const r = toZ64(head);
    if (!r) return null;
    return { format: r.format, size: fs.fstatSync(fd).size, ...parseHeader(r.data) };
  } finally { fs.closeSync(fd); }
}

// Every ROM below a folder, with its header. Non-ROM files with ROM-like names are skipped.
function scan(folder, { progress = () => {}, limit = 20000 } = {}) {
  const root = path.resolve(folder), files = [];
  const walk = (dir, depth) => {
    let entries; try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (files.length >= limit) return;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (depth < 12 && !e.name.startsWith('.')) walk(p, depth + 1); }
      else if (ROM_EXT.test(e.name)) files.push(p);
    }
  };
  walk(root, 0);
  const roms = [];
  let skipped = 0;
  files.forEach((f, i) => {
    if (i % 25 === 0) progress(i, files.length, path.basename(f));
    let h = null;
    try { h = peek(f); } catch { h = null; }
    if (!h) { skipped++; return; }
    const lib = libraryGame(h.gameCode);
    roms.push({ path: f, rel: path.relative(root, f).split(path.sep).join('/'), folder: path.relative(root, path.dirname(f)).split(path.sep).join('/'), file: path.basename(f), ...h,
      libKey: lib ? gameKey(h.gameCode) : '', libTitle: lib ? lib.title : '' });
  });
  // Folder by folder (ROMs right in the chosen folder first), then by file name.
  const cmp = (x, y) => x.localeCompare(y, undefined, { numeric: true, sensitivity: 'base' });
  roms.sort((a, b) => (a.folder === b.folder ? cmp(a.file, b.file) : !a.folder ? -1 : !b.folder ? 1 : cmp(a.folder, b.folder)));
  const matched = new Set(roms.map((r) => r.libKey).filter(Boolean)).size;
  return { roms, skipped, truncated: files.length >= limit, matched, libraryCount: library().count };
}

// Everything about one ROM.
function info(file) {
  const st = fs.statSync(file);
  const { data, raw, format, inner } = readRom(file);
  const h = parseHeader(data.subarray(0, 0x40));
  const bootCrc = zlib.crc32(data.subarray(0x40, 0x1000)) >>> 0;
  const cic = CIC[bootCrc] || null;
  const calc = cic ? checksum(data, cic.name, cic.seed) : null;
  const sum = (alg) => crypto.createHash(alg).update(data).digest('hex').toUpperCase();
  const zelda = zeldaFiles(data);
  const mbit = data.length * 8 / 1048576;
  return {
    path: file, file: path.basename(file), folder: path.dirname(file), inner: inner || '',
    fileSize: st.size, modified: st.mtimeMs, format, formatName: FORMAT_NAME[format],
    romSize: data.length, mbit: Math.round(mbit * 10) / 10,
    ...h, crc1Hex: hex(h.crc1), crc2Hex: hex(h.crc2),
    libultraVersion: libultraVersion(h.libultra), entryHex: hex(h.entryPoint), clockHex: hex(h.clockRate), piHex: hex(h.piSettings),
    cic: cic ? cic.name : 'Unknown (custom or homebrew boot code)', cicNote: cic ? cic.note : '', bootCrc: hex(bootCrc),
    checksum: !calc ? (cic ? 'Not checked for this chip' : 'Not checked (unknown boot code)')
      : (calc[0] === h.crc1 && calc[1] === h.crc2 ? 'OK' : `Doesn't match (calculated ${hex(calc[0])} ${hex(calc[1])})`),
    checksumOk: calc ? calc[0] === h.crc1 && calc[1] === h.crc2 : null,
    crc32: hex(zlib.crc32(data) >>> 0), md5: sum('md5'), sha1: sum('sha1'),
    trailingZeros: (() => { const pad = data[data.length - 1]; if (pad !== 0 && pad !== 0xff) return 0; let n = data.length; while (n > 0x1000 && data[n - 1] === pad) n--; return data.length - n; })(),  // 00 or FF padding
    layout: [
      { name: 'Header', start: 0, end: 0x40 },
      { name: `Boot code (${cic ? cic.name : 'IPL3'})`, start: 0x40, end: 0x1000 },
      { name: 'Game code and data', start: 0x1000, end: data.length },
    ],
    zelda,
    library: libraryGame(h.gameCode),          // { title, code, art, description } or null
  };
}

module.exports = { scan, info, peek, library, libraryGame, toZ64, parseHeader, checksum, zeldaFiles, CIC, REGION, MAGIC };
