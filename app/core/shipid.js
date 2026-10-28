'use strict';
// Which N64 game a Ship port file belongs to, so 4 · Ship Mods can show its box art.
//
// Read from the file itself first, so new ports work without updates:
//   1. "version" inside the .o2r: an endianness byte (0 little, 1 big) then the ROM's CRC1 (header
//      0x10). Torch and Shipwright's exporter both write it into every archive made from a ROM.
//   2. manifest.json "game_version": the same CRC1, in newer archives.
//   3. r64texhd.json: written by R64texHD into the HD mods it builds (the base game's CRC1).
//   4. For a texture folder: r64texhd-o2r.json, written when R64texHD got the textures out.
// Then, only if those say nothing, the file name (mm.o2r, sm64.o2r...) or a port's folder in the
// path (...\Ghostship\mods\...). CRC1 -> game is app/assets/n64/crc.json (see build/n64-library).
const fs = require('fs');
const path = require('path');
const archive = require('./archive');
const rom = require('./rom');

const ASSETS = path.join(__dirname, '..', 'assets', 'n64');
const MOD_INFO = 'r64texhd.json';
const FOLDER_INFO = 'r64texhd-o2r.json';
let CRC = null, PORTS = null;
const load = (f, fallback) => { try { return JSON.parse(fs.readFileSync(path.join(ASSETS, f), 'utf8')); } catch { return fallback; } };
const crcTable = () => (CRC = CRC || load('crc.json', { crc: {} }).crc);
const ports = () => (PORTS = PORTS || load('ports.json', { ports: [] }).ports);
const hex = (v) => (v >>> 0).toString(16).toUpperCase().padStart(8, '0');
const squash = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

// The "version" entry: [endianness][uint32 CRC1].
function readVersion(buf) {
  if (!buf || buf.length < 5) return null;
  const v = buf[0] === 0 ? buf.readUInt32LE(1) : buf.readUInt32BE(1);
  return v === 0 || v === 0xffffffff ? null : v >>> 0;
}

// What the archive's own entries say: { crc, source, port archive?, name }.
function readArchive(file) {
  const out = { crc: null, source: '', portArchive: false, manifestName: '' };
  let entries;
  try { entries = archive.entries(file); } catch { return out; }        // .o2r or the older .otr
  const get = (name) => { const e = entries.find((x) => x.name === name); try { return e ? archive.read(file, e) : null; } catch { return null; } };
  const v = readVersion(get('version'));
  if (v != null) { out.crc = v; out.source = 'the archive’s version file'; }
  const man = get('manifest.json');
  if (man) {
    try {
      const j = JSON.parse(man.toString('utf8'));
      out.manifestName = j.name || '';
      const gv = Number(j.game_version);
      if (out.crc == null && Number.isFinite(gv) && gv > 0 && gv !== 0xffffffff) { out.crc = gv >>> 0; out.source = 'the archive’s manifest'; }
    } catch { /* not JSON */ }
  }
  const mine = get(MOD_INFO);
  if (mine && out.crc == null) {
    try { const j = JSON.parse(mine.toString('utf8')); if (j.crc) { out.crc = parseInt(j.crc, 16) >>> 0; out.source = 'R64texHD’s note in the mod'; } } catch { /* ignore */ }
  }
  out.portArchive = entries.some((e) => e.name === 'portVersion');
  return out;
}

// A port by its archive file name (mm.o2r) or by a folder in the path (...\2ship\...).
function portByName(file) {
  const base = path.basename(file).toLowerCase().replace(/\.(o2r|otr)$/, '');
  for (const p of ports()) if (p.archives.includes(base)) return { port: p, by: 'file' };
  const parts = path.resolve(file).split(/[\\/]+/).map(squash);
  for (const p of ports()) {
    const names = [squash(p.name), squash(p.repo.split('/').pop() || '')].filter((n) => n.length > 3);
    if (parts.some((x) => names.includes(x))) return { port: p, by: 'folder' };
  }
  return null;
}

// Everything known about a Ship file or folder. Never throws.
function identify(target) {
  const r = { file: target, crc: '', rom: '', source: '', key: '', game: null, port: null, kind: '' };
  if (!target) return r;
  let st; try { st = fs.statSync(target); } catch { return r; }
  let crc = null;
  if (st.isDirectory()) {
    r.kind = 'folder';
    try {
      const j = JSON.parse(fs.readFileSync(path.join(target, FOLDER_INFO), 'utf8'));
      if (j.crc) { crc = parseInt(j.crc, 16) >>> 0; r.source = 'the texture list R64texHD saved here'; }
      if (j.archive && !crc) { const byName = portByName(j.archive); if (byName) { r.port = byName.port; r.source = 'the archive name in the texture list'; } }
    } catch { /* not one of ours */ }
  } else {
    const a = readArchive(target);
    crc = a.crc; r.source = a.source;
    r.kind = a.portArchive ? 'port' : a.crc != null && a.source.includes('version') ? 'game' : 'mod';
  }
  if (crc != null) {
    r.crc = hex(crc);
    const hit = crcTable()[r.crc];
    if (hit) { r.key = hit[0]; r.rom = hit[1]; }
  }
  const byName = portByName(target);
  if (!r.key && !r.port && byName) { r.port = byName.port; r.source = byName.by === 'file' ? 'the file name' : 'the port’s folder name'; }
  if (r.key && !r.port) r.port = ports().find((p) => p.game === r.key) || null;
  if (!r.key && r.port && r.port.game) r.key = r.port.game;
  r.game = r.key ? rom.library().games[r.key] || null : null;
  return r;
}

module.exports = { identify, readVersion, portByName, MOD_INFO, FOLDER_INFO, crcTable, ports };
