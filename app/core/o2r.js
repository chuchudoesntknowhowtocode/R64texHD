'use strict';
// Ship port archives (.o2r): 2 Ship 2 Harkinian, Ship of Harkinian, Starship and other ports built on
// libultraship. An .o2r is a zip; each texture is a binary "OTEX" resource at a path with no extension
// (e.g. objects/gameplay_keep/gEffBombExplosion1Tex).
//
// Resource layout (libultraship ResourceLoader / TextureFactory; written the same way as HarbourMasters'
// Retro tool):
//   0x00 u8 byte order (0 little, 1 big)   0x04 u32 type 'OTEX' 0x4F544558   0x08 u32 resource version
//   0x0C u64 id   ...zero padding to 0x40
//   V0 body: u32 type, u32 width, u32 height, u32 size, bytes
//   V1 body: u32 type, u32 width, u32 height, u32 flags, f32 hByteScale, f32 vPixelScale, u32 size, bytes
// HD replacement (Retro): RGBA32 pixels at a whole multiple of the original size, flag LOAD_AS_RAW,
//   hByteScale = (hdWidth / width) * (4 / original bytes per pixel), vPixelScale = hdHeight / height.
// Mods go in the port's mods folder; paths starting with alt/ are used when "Use Alternate Assets" is on.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const png = require('./png');
const rtz = require('./rtz');
const { resizeRGBA } = require('./upscale');

const OTEX = 0x4f544558;
const HEADER = 0x40;
const LOAD_AS_RAW = 1;
const TYPES = {
  1: { name: 'RGBA32', bpp: 4 }, 2: { name: 'RGBA16', bpp: 2 }, 3: { name: 'CI4', bpp: 0.5, palette: true }, 4: { name: 'CI8', bpp: 1, palette: true },
  5: { name: 'I4', bpp: 0.5 }, 6: { name: 'I8', bpp: 1 }, 7: { name: 'IA4', bpp: 0.5 }, 8: { name: 'IA8', bpp: 1 }, 9: { name: 'IA16', bpp: 2 },
};
const INFO_FILE = 'r64texhd-o2r.json';
// The port (or game) an archive belongs to, for messages: read from the archive itself (see shipid.js).
const gameOf = (file) => { const id = require('./shipid').identify(file); return id.port ? id.port.name : id.game ? id.game.title : 'Ship port'; };
// What R64texHD writes into a mod so it can be recognised later: the base game's CRC1.
function modNote(baseFile) {
  const id = require('./shipid').identify(baseFile);
  return id.crc ? Buffer.from(JSON.stringify({ tool: 'R64texHD', crc: id.crc, game: id.game ? id.game.title : '', port: id.port ? id.port.name : '', base: path.basename(baseFile) }) + '\n') : null;
}

function isMpq(file) {
  const fd = fs.openSync(file, 'r');
  try { const b = Buffer.alloc(4); fs.readSync(fd, b, 0, 4, 0); return b.toString('latin1') === 'MPQ\x1a'; } finally { fs.closeSync(fd); }
}
function openArchive(file) {
  if (isMpq(file)) throw new Error('This is an older .otr archive (MPQ). R64texHD reads .o2r archives: update the port, or let it make a new .o2r from your ROM.');
  return rtz.readEntries(file);
}

// Header + texture fields of a resource, or null when it isn't a texture.
function parseTexture(buf) {
  if (buf.length < HEADER + 16) return null;
  const le = buf[0] === 0;
  const u32 = (o) => (le ? buf.readUInt32LE(o) : buf.readUInt32BE(o));
  const f32 = (o) => (le ? buf.readFloatLE(o) : buf.readFloatBE(o));
  if (u32(4) !== OTEX) return null;
  const version = u32(8);
  let o = HEADER;
  const t = { version, type: u32(o), width: u32(o + 4), height: u32(o + 8), flags: 0, hScale: 1, vScale: 1 };
  o += 12;
  if (version >= 1) { t.flags = u32(o); t.hScale = f32(o + 4); t.vScale = f32(o + 8); o += 12; }
  t.size = u32(o); o += 4;
  t.data = buf.subarray(o, o + t.size);
  if (!TYPES[t.type] || !t.width || !t.height) return null;
  return t;
}

// N64 texture data -> RGBA. Palette (CI) textures have no colours of their own: shown as grey indices.
function decodeTexture(t) {
  const { width: w, height: h, data: d } = t;
  const out = new Uint8Array(w * h * 4);
  const set = (i, r, g, b, a) => { out[i * 4] = r; out[i * 4 + 1] = g; out[i * 4 + 2] = b; out[i * 4 + 3] = a; };
  const nib = (i) => (i & 1 ? d[i >> 1] & 15 : d[i >> 1] >> 4);
  const e5 = (v) => (v << 3) | (v >> 2);
  for (let i = 0; i < w * h; i++) {
    switch (t.type) {
      case 1: set(i, d[i * 4], d[i * 4 + 1], d[i * 4 + 2], d[i * 4 + 3]); break;
      case 2: { const v = (d[i * 2] << 8) | d[i * 2 + 1]; set(i, e5(v >> 11), e5((v >> 6) & 31), e5((v >> 1) & 31), v & 1 ? 255 : 0); break; }
      case 3: { const v = nib(i) * 17; set(i, v, v, v, 255); break; }
      case 4: set(i, d[i], d[i], d[i], 255); break;
      case 5: { const v = nib(i) * 17; set(i, v, v, v, 255); break; }
      case 6: set(i, d[i], d[i], d[i], 255); break;
      case 7: { const n = nib(i), v = Math.round(((n >> 1) * 255) / 7); set(i, v, v, v, n & 1 ? 255 : 0); break; }
      case 8: { const v = (d[i] >> 4) * 17; set(i, v, v, v, (d[i] & 15) * 17); break; }
      case 9: set(i, d[i * 2], d[i * 2], d[i * 2], d[i * 2 + 1]); break;
    }
  }
  // An already-HD resource stores its pixels at its own (bigger) size: decode as RGBA32.
  return { width: w, height: h, data: out };
}

// RGBA -> N64 texture data of a given type (same-size replacements keep the original format).
function encodePixels(img, type) {
  const { width: w, height: h, data: s } = img, n = w * h;
  const lum = (i) => Math.round(0.299 * s[i * 4] + 0.587 * s[i * 4 + 1] + 0.114 * s[i * 4 + 2]);
  const out = Buffer.alloc(Math.ceil(n * TYPES[type].bpp));
  const put4 = (i, v) => { if (i & 1) out[i >> 1] |= v & 15; else out[i >> 1] = (v & 15) << 4; };
  for (let i = 0; i < n; i++) {
    switch (type) {
      case 1: out[i * 4] = s[i * 4]; out[i * 4 + 1] = s[i * 4 + 1]; out[i * 4 + 2] = s[i * 4 + 2]; out[i * 4 + 3] = s[i * 4 + 3]; break;
      case 2: { const v = ((s[i * 4] >> 3) << 11) | ((s[i * 4 + 1] >> 3) << 6) | ((s[i * 4 + 2] >> 3) << 1) | (s[i * 4 + 3] >= 128 ? 1 : 0); out[i * 2] = v >> 8; out[i * 2 + 1] = v & 255; break; }
      case 5: put4(i, lum(i) >> 4); break;
      case 6: out[i] = lum(i); break;
      case 7: put4(i, ((lum(i) >> 5) << 1) | (s[i * 4 + 3] >= 128 ? 1 : 0)); break;
      case 8: out[i] = ((lum(i) >> 4) << 4) | (s[i * 4 + 3] >> 4); break;
      case 9: out[i * 2] = lum(i); out[i * 2 + 1] = s[i * 4 + 3]; break;
      default: throw new Error('no encoder for ' + type);
    }
  }
  return out;
}

function resource({ type, width, height, flags = 0, hScale = 1, vScale = 1, data, version = flags || hScale !== 1 || vScale !== 1 ? 1 : 0 }) {
  const head = Buffer.alloc(HEADER);
  head.writeUInt32LE(OTEX, 4); head.writeUInt32LE(version, 8); head.writeBigUInt64LE(0xdeadbeefdeadbeefn, 12); head[24] = 1; // made by a tool (custom)
  const body = Buffer.alloc(version >= 1 ? 28 : 16);
  let o = 0;
  body.writeUInt32LE(type, o); body.writeUInt32LE(width, o + 4); body.writeUInt32LE(height, o + 8); o += 12;
  if (version >= 1) { body.writeUInt32LE(flags, o); body.writeFloatLE(hScale, o + 4); body.writeFloatLE(vScale, o + 8); o += 12; }
  body.writeUInt32LE(data.length, o);
  return Buffer.concat([head, body, data]);
}

// An HD replacement for base texture t from image img (the HD art, any size).
// Same size: keeps the original format (palette art becomes RGBA32 raw). Bigger: RGBA32 raw at a whole
// multiple of the original size, with the scales libultraship needs to read it.
function hdResource(t, img) {
  const meta = TYPES[t.type];
  // Grey-only art for an intensity texture: in game its alpha is its brightness.
  if ((t.type === 5 || t.type === 6) && isOpaque(img)) img = alphaFromBrightness(img);
  const kx = Math.max(1, Math.round(img.width / t.width)), ky = Math.max(1, Math.round(img.height / t.height));
  const W = kx * t.width, H = ky * t.height;
  const resized = img.width !== W || img.height !== H;
  if (resized) img = resizeRGBA(img, W, H);
  if (kx === 1 && ky === 1 && !meta.palette) return { buf: resource({ type: t.type, width: t.width, height: t.height, data: encodePixels(img, t.type) }), kx, ky, resized };
  return {
    buf: resource({ type: 1, width: W, height: H, flags: LOAD_AS_RAW, hScale: kx * (4 / meta.bpp), vScale: ky, data: encodePixels(img, 1), version: 1 }),
    kx, ky, resized,
  };
}

function isOpaque(img) { for (let i = 3; i < img.data.length; i += 4) if (img.data[i] !== 255) return false; return true; }
function alphaFromBrightness(img) {
  const d = Uint8Array.from(img.data);
  for (let i = 0; i < d.length; i += 4) d[i + 3] = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
  return { width: img.width, height: img.height, data: d };
}

// Every texture in an archive: [{ name, type, width, height, ... }] (pixel data not kept).
function listTextures(file, { progress = () => {}, cancelled = () => false } = {}) {
  const entries = openArchive(file);
  const fd = fs.openSync(file, 'r'), out = [];
  try {
    entries.forEach((e, i) => {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      if (i % 200 === 0) progress(i, entries.length, `Reading ${e.name}`);
      if (e.usize < HEADER + 16 || e.usize > 64 * 1048576) return;
      let t;
      try { t = parseTexture(rtz.readEntry(file, e, fd)); } catch { return; }
      if (t) out.push({ name: e.name, entry: e, type: t.type, width: t.width, height: t.height, flags: t.flags, hScale: t.hScale, vScale: t.vScale, version: t.version });
    });
  } finally { fs.closeSync(fd); }
  return out;
}

// Extract Textures: every texture as PNG at <out>/<path in the archive>.png, plus r64texhd-o2r.json.
function extract(file, outDir, { progress = () => {}, cancelled = () => false, skipPalette = false } = {}) {
  const list = listTextures(file, { progress: (d, t) => progress(d, t * 2, 'Finding textures'), cancelled });
  if (!list.length) throw new Error('No textures in this archive.');
  const root = path.resolve(outDir);
  fs.mkdirSync(root, { recursive: true });
  const fd = fs.openSync(file, 'r'), info = [];
  let written = 0, palette = 0;
  try {
    list.forEach((t, i) => {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      const isPal = TYPES[t.type].palette;
      if (isPal) palette++;
      info.push({ path: t.name, type: TYPES[t.type].name, width: t.width, height: t.height, ...(isPal ? { palette: true } : {}) });
      if (isPal && skipPalette) return;
      const target = path.resolve(root, t.name + '.png');
      if (!target.startsWith(root + path.sep)) return;                     // never write outside the folder
      const img = decodeTexture(parseTexture(rtz.readEntry(file, t.entry, fd)));
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target + '.part', png.encodePNG(img, 6));
      fs.renameSync(target + '.part', target);
      written++;
      if (i % 25 === 0) progress(list.length + i, list.length * 2, t.name);
    });
  } finally { fs.closeSync(fd); }
  const id = require('./shipid').identify(file);
  fs.writeFileSync(path.join(root, INFO_FILE), JSON.stringify({ version: 1, archive: path.basename(file), game: gameOf(file), crc: id.crc || undefined, textures: info }, null, 1) + '\n');
  return { textures: list.length, written, palette, game: gameOf(file) };
}

const listPngs = (dir) => {
  const out = [];
  const walk = (d, rel) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walk(path.join(d, e.name), r); else if (/\.png$/i.test(e.name)) out.push(r);
  } };
  walk(dir, '');
  return out.sort();
};

// Writes a mod from [{ t: base texture, img, label }]. Returns { written, resized, same }.
function writeMod(pairs, outFile, { alt = true, compression = 'store', progress = () => {}, cancelled = () => false, offset = 0, total = pairs.length, note = null } = {}) {
  const part = outFile + '.part';
  fs.mkdirSync(path.dirname(path.resolve(outFile)), { recursive: true });
  const zip = new rtz.ZipWriter(part);
  const resized = [], same = [];
  let written = 0;
  try {
    pairs.forEach(({ t, img, label }, i) => {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      const image = typeof img === 'function' ? img() : img;
      const r = hdResource({ ...t, data: null }, image);
      if (r.resized) resized.push(`${label || t.name} (${image.width}×${image.height} → ${t.width * r.kx}×${t.height * r.ky})`);
      if (r.kx === 1 && r.ky === 1) same.push(label || t.name);
      const { payload, method } = rtz.compress(r.buf, compression === 'deflate' ? 'deflate' : 'store', 6);
      zip.add((alt ? 'alt/' : '') + t.name, payload, method, zlib.crc32(r.buf), r.buf.length, Date.now());
      written++;
      progress(offset + i + 1, offset + total, `Adding ${t.name}`);
    });
    if (note) zip.add(require('./shipid').MOD_INFO, note, 0, zlib.crc32(note), note.length, Date.now());   // ignored by the port
    zip.close();
    fs.renameSync(part, outFile);
  } catch (e) { zip.abort(); fs.rmSync(part, { force: true }); throw e; }
  return { written, resized, same, bytesOut: fs.statSync(outFile).size };
}

// Build an HD mod: each PNG in hdDir replaces the texture at the same path in the base archive.
function build(hdDir, baseFile, outFile, { alt = true, compression = 'store', progress = () => {}, cancelled = () => false } = {}) {
  const pngs = listPngs(hdDir).filter((f) => f !== INFO_FILE);
  if (!pngs.length) throw new Error('No PNG textures in that folder. Ship mods are built from PNG: upscale with Output format PNG.');
  const base = listTextures(baseFile, { progress: (d, t) => progress(d, t * 2, 'Reading the game archive'), cancelled });
  const byName = new Map(), byLower = new Map();
  for (const t of base) { byName.set(t.name, t); byLower.set(t.name.toLowerCase(), t); }
  const unmatched = [], pairs = [], done = new Set();
  for (const rel of pngs) {
    const key = rel.replace(/\.png$/i, '').replace(/^alt\//i, '');
    const t = byName.get(key) || byLower.get(key.toLowerCase());
    if (!t) { unmatched.push(rel); continue; }
    if (done.has(t.name)) continue;                                  // alt/x.png and x.png: the first wins
    done.add(t.name);
    pairs.push({ t, label: rel, img: () => png.decodePNG(fs.readFileSync(path.join(hdDir, rel))) });
  }
  if (!pairs.length) throw new Error('None of the PNGs match a texture in the game archive. Keep the folders and names you got from “Extract Textures”.');
  const r = writeMod(pairs, outFile, { alt, compression, progress, cancelled, offset: base.length, total: base.length + pairs.length, note: modNote(baseFile) });
  return { file: outFile, written: r.written, unmatched, resized: r.resized, same: r.same, game: gameOf(baseFile), bytesOut: r.bytesOut };
}

// Every texture with its pixel data (for matching by content, e.g. Rice IDs).
function readTextures(file, { progress = () => {}, cancelled = () => false } = {}) {
  const entries = openArchive(file);
  const fd = fs.openSync(file, 'r'), out = [];
  try {
    entries.forEach((e, i) => {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      if (i % 200 === 0) progress(i, entries.length, `Reading ${e.name}`);
      if (e.usize < HEADER + 16 || e.usize > 64 * 1048576) return;
      let t;
      try { t = parseTexture(rtz.readEntry(file, e, fd)); } catch { return; }
      if (t) out.push({ ...t, name: e.name });
    });
  } finally { fs.closeSync(fd); }
  return out;
}

// Quick look for the status card: game name and entry count (no decompressing).
function inspect(file) {
  const entries = openArchive(file);
  return { game: gameOf(file), files: entries.length, size: fs.statSync(file).size };
}

module.exports = { TYPES, OTEX, LOAD_AS_RAW, INFO_FILE, modNote, parseTexture, decodeTexture, encodePixels, resource, hdResource, listTextures, readTextures, extract, build, writeMod, inspect, gameOf, isMpq, listPngs };
