'use strict';
// R64texHD - Rice / GLideN64 texture IDs and pack files.
// Copyright (C) 2026 R64texHD contributors.
//
// This program is free software; you can redistribute it and/or modify it under the terms of the
// GNU General Public License as published by the Free Software Foundation; either version 2 of the
// License, or (at your option) any later version. This program is distributed in the hope that it
// will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
// FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
//
// The Rice ID formula (RiceCRC32 and the load size rules) is ported from RT64's texture_hasher, which
// references GLideN64 and Rice Video (GPL). The .hts / .htc layouts follow GLideN64's TxCache.cpp.
//
// A Rice ID is "<crc>#<fmt>#<siz>" plus "#<palette crc>" for palette textures, as in Rice pack file
// names (GAME#003334A1#3#0_all.png) and in rt64.json "hashes.rice". GLideN64 stores the same IDs as a
// 64-bit key: texture crc in the low half, palette crc in the high half, with format + size beside it.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const png = require('./png');

const hex8 = (v) => (v >>> 0).toString(16).padStart(8, '0');

// ---------------------------------------------------------------- the Rice CRC
// src: bytes as the game had them in RDRAM. RT64's .rice.rdram dumps keep the emulator's word order
// (read 32-bit words little-endian); texture data from a Ship .o2r is in the N64's own byte order
// (read big-endian). Both give the same words.
function riceCRC32(src, width, height, size, rowStride, bigEndian = false, offset = 0) {
  let crc = 0;
  const bytesPerLine = (width << size) >> 1;
  for (let y = height - 1, row = offset; y >= 0; y--, row += rowStride) {
    let esi = 0;
    for (let x = bytesPerLine - 4; x >= 0; x -= 4) {
      const p = row + x;
      const w = p + 4 <= src.length ? (bigEndian ? src.readUInt32BE(p) : src.readUInt32LE(p)) : 0;
      esi = (w ^ x) >>> 0;
      crc = (((crc << 4) >>> 0) + ((crc >>> 28) & 15)) >>> 0;
      crc = (crc + esi) >>> 0;
    }
    esi = (esi ^ y) >>> 0;
    crc = (crc + esi) >>> 0;
  }
  return crc >>> 0;
}

function maxCI(src, width, height, rowStride, four) {
  let v = 0;
  for (let y = 0; y < height; y++) {
    const row = rowStride * y;
    if (four) {
      for (let x = 0; x < width >> 1; x++) { const b = src[row + x] || 0; v = Math.max(v, b >> 4, b & 15); if (v === 15) return 15; }
    } else {
      for (let x = 0; x < width; x++) { v = Math.max(v, src[row + x] || 0); if (v === 255) return 255; }
    }
  }
  return v;
}

// ---------------------------------------------------------------- Rice IDs from an RT64 dump
const G_TX_CLAMP = 2;
const SIZE_BYTES = [0, 1, 2, 4];
const calculateDXT = (t) => (t === 0 ? 1 : Math.floor((2048 + t - 1) / t));
const txl2Words = (width, size) => (size === 0 ? Math.max(1, Math.floor(width / 16)) : Math.max(1, Math.floor((width * SIZE_BYTES[size]) / 8)));
function reverseDXT(val, width, size) {
  if (val === 0x800) return 1;
  let low = Math.floor(2047 / val);
  if (calculateDXT(low) > val) low++;
  const high = Math.floor(2047 / (val - 1));
  if (low === high) return low;
  for (let i = low; i <= high; i++) if (txl2Words(width, size) === i) return i;
  return Math.floor((low + high) / 2);
}

// The Rice ID for one dumped texture (<dir>/<hash>.v<N>.*), or null when the dump has no Rice data.
function riceFromDump(tmemPath) {
  const base = tmemPath.replace(/\.tmem$/i, '');
  const read = (ext) => { try { return fs.readFileSync(base + ext); } catch { return null; } };
  const tileJ = read('.tile.json'), opJ = read('.rice.json'), rdram = read('.rice.rdram');
  if (!tileJ || !opJ || !rdram) return null;
  const info = JSON.parse(tileJ.toString('utf8')), op = JSON.parse(opJ.toString('utf8'));
  const draw = num(info.tile), lt = num(op.tile), tex = num(op.texture);
  const tlut = info.tlut ?? 'None';
  let bpl, width, height;
  if (op.type === 'Tile' || op.type === 0) {
    let tileWidth = (Math.max((lt.lrs >> 2) - (lt.uls >> 2), 0) + 1) & 0x3ff;
    const tileHeight = (Math.max((lt.lrt >> 2) - (lt.ult >> 2), 0) + 1) & 0x3ff;
    tileWidth = lt.masks !== 0 ? Math.min(tileWidth, 1 << lt.masks) : tileWidth;
    bpl = (tex.width << tex.siz) >> 1;
    width = Math.min(tileWidth, tex.width);
    if (lt.siz > draw.siz) width <<= lt.siz - draw.siz;
    height = lt.maskt !== 0 ? Math.min(tileHeight, 1 << lt.maskt) : tileHeight;
  } else if (op.type === 'Block' || op.type === 1) {
    const tw = Math.max((draw.lrs >> 2) - (draw.uls >> 2), 0) + 1, th = Math.max((draw.lrt >> 2) - (draw.ult >> 2), 0) + 1;
    const mw = draw.masks === 0 ? tw : 1 << draw.masks, mh = draw.maskt === 0 ? th : 1 << draw.maskt;
    const clamps = draw.masks === 0 || (draw.cms & G_TX_CLAMP), clampt = draw.maskt === 0 || (draw.cmt & G_TX_CLAMP);
    width = clamps && tw <= 256 ? Math.min(mw, tw) : mw;
    height = (clampt && th <= 256) || mh > 256 ? Math.min(mh, th) : mh;
    if (draw.siz === 3) bpl = draw.line << 4;
    else if (lt.lrt === 0) bpl = draw.line << 3;
    else { let dxt = lt.lrt; if (dxt > 1) dxt = reverseDXT(dxt, tex.width, tex.siz); bpl = dxt << 3; }
  } else return null;
  const expected = (height - 1) * bpl + ((width << draw.siz) >> 1);
  if (expected > rdram.length || width <= 0 || height <= 0) return null;
  let id = `${hex8(riceCRC32(rdram, width, height, draw.siz, bpl))}#${draw.fmt}#${draw.siz}`;
  if (tlut !== 'None' && tlut !== 0) {
    const pal = read('.rice.palette.rdram');
    if (!pal) return null;
    const four = draw.siz === 0;
    const cimax = maxCI(rdram, width, height, bpl, four);
    id += '#' + hex8(riceCRC32(pal, cimax + 1, 1, 2, four ? 32 : 512));
  }
  return id;
}
const num = (o) => { const r = {}; for (const [k, v] of Object.entries(o || {})) r[k] = Number(v) || 0; return r; };

// ---------------------------------------------------------------- Rice IDs for Ship .o2r textures
// o2r texture type -> N64 [format, size]
const O2R_FMT = { 1: [0, 3], 2: [0, 2], 3: [2, 0], 4: [2, 1], 5: [4, 0], 6: [4, 1], 7: [3, 0], 8: [3, 1], 9: [3, 2] };
function riceForTexture(t) {
  const fs_ = O2R_FMT[t.type];
  if (!fs_) return null;
  const [fmt, siz] = fs_;
  const bits = [4, 8, 16, 32][siz];
  const rowBytes = Math.ceil((t.width * bits) / 8);
  const pitch = Math.max(8, Math.ceil((t.width * bits) / 64) * 8);
  const data = pitch === rowBytes ? t.data : padRows(t.data, rowBytes, pitch, t.height);
  return { crc: riceCRC32(Buffer.from(data.buffer, data.byteOffset, data.length), t.width, t.height, siz, pitch, true), fmt, siz };
}
function padRows(src, rowBytes, pitch, height) {
  const out = Buffer.alloc(pitch * height);
  for (let y = 0; y < height; y++) src.copy(out, y * pitch, y * rowBytes, (y + 1) * rowBytes);
  return out;
}

// ---------------------------------------------------------------- Rice IDs in file names
const RICE_NAME = /#([0-9a-f]{8})#(\d)#(\d)(?:#([0-9a-f]{8}))?_(all|rgb|a|ci|ciByRGBA|allciByRGBA)\.png$/i;
function parseRiceName(file) {
  const m = RICE_NAME.exec(path.basename(file));
  if (!m) return null;
  return { crc: parseInt(m[1], 16) >>> 0, fmt: +m[2], siz: +m[3], pal: m[4] ? parseInt(m[4], 16) >>> 0 : 0, kind: m[5].toLowerCase() };
}
const riceId = (e) => `${hex8(e.crc)}#${e.fmt}#${e.siz}${e.pal ? '#' + hex8(e.pal) : ''}`;
function parseRiceId(s) {
  const m = /^([0-9a-f]{8})#(\d)#(\d)(?:#([0-9a-f]{8}))?$/i.exec(String(s || ''));
  return m ? { crc: parseInt(m[1], 16) >>> 0, fmt: +m[2], siz: +m[3], pal: m[4] ? parseInt(m[4], 16) >>> 0 : 0 } : null;
}

// ---------------------------------------------------------------- GLideN64 .hts / .htc
const VERSION = 0x08000000;                       // TXCACHE_FORMAT_VERSION (UNDEFINED_1)
const GZ = 0x80000000;                            // GL_TEXFMT_GZ
const GL = { RGBA8: 0x8058, RGB8: 0x8051, RGBA4: 0x8056, RGB5_A1: 0x8057, RGBA: 0x1908, RGB: 0x1907,
  UNSIGNED_BYTE: 0x1401, US_565: 0x8363, US_5551: 0x8034, US_4444: 0x8033 };
// Options GLideN64 saves with hi-res caches (Rice packs, file storage, compressed, artists' freedom).
const CONFIG = 0x00020000 | 0x00800000 | 0x40000000;

function decodePixels(info, data) {
  const { width: w, height: h } = info, n = w * h, out = new Uint8Array(n * 4);
  if (data.length >= n * 4) out.set(data.subarray(0, n * 4));
  else if (data.length >= n * 3 && data.length < n * 4) for (let i = 0; i < n; i++) { out[i * 4] = data[i * 3]; out[i * 4 + 1] = data[i * 3 + 1]; out[i * 4 + 2] = data[i * 3 + 2]; out[i * 4 + 3] = 255; }
  else if (data.length >= n * 2) {
    for (let i = 0; i < n; i++) {
      const v = data.readUInt16LE(i * 2);
      if (info.pixelType === GL.US_4444) { out[i * 4] = (v >> 12) * 17; out[i * 4 + 1] = ((v >> 8) & 15) * 17; out[i * 4 + 2] = ((v >> 4) & 15) * 17; out[i * 4 + 3] = (v & 15) * 17; }
      else if (info.pixelType === GL.US_565) { out[i * 4] = ((v >> 11) * 255 / 31) | 0; out[i * 4 + 1] = (((v >> 5) & 63) * 255 / 63) | 0; out[i * 4 + 2] = ((v & 31) * 255 / 31) | 0; out[i * 4 + 3] = 255; }
      else { out[i * 4] = ((v >> 11) * 255 / 31) | 0; out[i * 4 + 1] = (((v >> 6) & 31) * 255 / 31) | 0; out[i * 4 + 2] = (((v >> 1) & 31) * 255 / 31) | 0; out[i * 4 + 3] = v & 1 ? 255 : 0; }
    }
  } else return null;
  return { width: w, height: h, data: out };
}

// One texture record (after the 64-bit key): width, height, format, texture format, pixel type,
// hi-res flag, N64 format + size, data size, data.
function readRecord(buf, o, withFormatSize = true) {
  const info = { width: buf.readUInt32LE(o), height: buf.readUInt32LE(o + 4), format: buf.readUInt32LE(o + 8),
    textureFormat: buf.readUInt16LE(o + 12), pixelType: buf.readUInt16LE(o + 14), hires: buf[o + 16] };
  o += 17;
  if (withFormatSize) { info.n64fmt = buf[o]; info.n64siz = buf[o + 1]; o += 2; }
  const size = buf.readUInt32LE(o); o += 4;
  info.data = buf.subarray(o, o + size);
  return { info, end: o + size };
}
function unpackRecord(info) {
  let data = info.data;
  if (info.format & GZ) data = zlib.inflateSync(data);
  return decodePixels(info, data);
}

// Reads a .hts (file storage) or .htc (gzip memory cache). Returns [{ crc, pal, fmt, siz, w, h, load() }].
// A .hts can be several GB, so only its index is read here; each texture is read when load() is called.
function readGlidenPack(file) {
  const out = [];
  const key = (k) => ({ crc: Number(k & 0xffffffffn) >>> 0, pal: Number(k >> 32n) >>> 0 });
  const fd = fs.openSync(file, 'r');
  const readAt = (pos, n) => { const b = Buffer.alloc(n); const got = fs.readSync(fd, b, 0, n, pos); return b.subarray(0, got); };
  try {
    const head = readAt(0, 16);
    if (head.length < 8) throw new Error('This file is too small to be a GLideN64 pack.');
    if (head[0] === 0x1f && head[1] === 0x8b) {                        // .htc: one gzip stream
      const buf = zlib.gunzipSync(fs.readFileSync(file));
      const current = buf.readInt32LE(0) === VERSION;
      let o = current ? 8 : 4;
      while (o + 8 + 21 <= buf.length) {
        const k = buf.readBigUInt64LE(o);
        const { info, end } = readRecord(buf, o + 8, current);
        out.push({ ...key(k), fmt: info.n64fmt ?? 0, siz: info.n64siz ?? 0, w: info.width, h: info.height, load: () => unpackRecord(info) });
        o = end;
      }
      return out;
    }
    const current = head.readInt32LE(0) === VERSION;
    const storagePos = Number(head.readBigInt64LE(current ? 8 : 4));
    const size = fs.fstatSync(fd).size;
    if (!(storagePos > 0 && storagePos + 4 <= size)) throw new Error('This .hts file has no texture index (it may be unfinished or damaged).');
    const count = readAt(storagePos, 4).readInt32LE(0);
    const index = readAt(storagePos + 4, count * 16);
    const recLen = current ? 23 : 21;
    for (let i = 0; i < count && (i + 1) * 16 <= index.length; i++) {
      const k = index.readBigUInt64LE(i * 16), v = index.readBigInt64LE(i * 16 + 8);
      const offset = Number(BigInt.asIntN(48, v)), fs16 = Number((v >> 48n) & 0xffffn);
      const rec = readAt(offset, recLen);
      if (rec.length < recLen) continue;
      const w = rec.readUInt32LE(0), h = rec.readUInt32LE(4), dataLen = rec.readUInt32LE(recLen - 4);
      out.push({ ...key(k), fmt: fs16 & 0xff, siz: fs16 >> 8, w, h, load: () => {
        const f2 = fs.openSync(file, 'r');
        try {
          const buf = Buffer.alloc(recLen + dataLen);
          fs.readSync(f2, buf, 0, buf.length, offset);
          return unpackRecord(readRecord(buf, 0, current).info);
        } finally { fs.closeSync(f2); }
      } });
    }
    return out;
  } finally { fs.closeSync(fd); }
}

// Writes a .hts that GLideN64 loads ("Texture Hires File Storage"). entries: [{ crc, pal, fmt, siz, img }]
function writeHts(entries, outFile, { level = 6, onEntry = () => {} } = {}) {
  fs.mkdirSync(path.dirname(path.resolve(outFile)), { recursive: true });
  const part = outFile + '.part';
  const fd = fs.openSync(part, 'w');
  let pos = 16;
  const index = [];
  try {
    const head = Buffer.alloc(16);
    head.writeInt32LE(VERSION, 0); head.writeInt32LE(CONFIG, 4);
    fs.writeSync(fd, head);
    entries.forEach((e, i) => {
      const img = typeof e.img === 'function' ? e.img() : e.img;
      const data = zlib.deflateSync(Buffer.from(img.data.buffer, img.data.byteOffset, img.data.length), { level });
      const rec = Buffer.alloc(23);                                  // record header: 23 bytes
      rec.writeUInt32LE(img.width, 0); rec.writeUInt32LE(img.height, 4); rec.writeUInt32LE((GL.RGBA8 | GZ) >>> 0, 8);
      rec.writeUInt16LE(GL.RGBA, 12); rec.writeUInt16LE(GL.UNSIGNED_BYTE, 14); rec[16] = 1;
      rec[17] = e.fmt; rec[18] = e.siz; rec.writeUInt32LE(data.length, 19);
      index.push({ key: (BigInt(e.pal >>> 0) << 32n) | BigInt(e.crc >>> 0), value: (BigInt((e.siz << 8) | e.fmt) << 48n) | BigInt(pos) });
      fs.writeSync(fd, rec); fs.writeSync(fd, data);
      pos += rec.length + data.length;
      onEntry(i + 1, entries.length);
    });
    const tail = Buffer.alloc(4 + index.length * 16);
    tail.writeInt32LE(index.length, 0);
    index.forEach((x, i) => { tail.writeBigUInt64LE(x.key, 4 + i * 16); tail.writeBigInt64LE(BigInt.asIntN(64, x.value), 12 + i * 16); });
    fs.writeSync(fd, tail);
    const p = Buffer.alloc(8); p.writeBigInt64LE(BigInt(pos)); fs.writeSync(fd, p, 0, 8, 8);
  } catch (err) { fs.closeSync(fd); fs.rmSync(part, { force: true }); throw err; }
  fs.closeSync(fd);
  fs.renameSync(part, outFile);
  return { file: outFile, textures: entries.length };
}

// ---------------------------------------------------------------- classic packs (any kind)
// A Rice texture folder, or a GLideN64 .hts / .htc. Returns [{ crc, pal, fmt, siz, rel, load() }].
function readClassicPack(input) {
  if (fs.statSync(input).isFile()) return readGlidenPack(input).map((e) => ({ ...e, rel: riceId(e) }));
  const files = [];
  const walk = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const f = path.join(d, e.name); if (e.isDirectory()) walk(f); else if (/\.png$/i.test(e.name)) files.push(f); } };
  walk(input);
  const out = [], alpha = new Map();
  for (const f of files) { const r = parseRiceName(f); if (r && r.kind === 'a') alpha.set(f.replace(/_a\.png$/i, '').toLowerCase(), f); }
  for (const f of files) {
    const r = parseRiceName(f);
    if (!r || r.kind === 'a') continue;
    const a = r.kind === 'rgb' ? alpha.get(f.replace(/_rgb\.png$/i, '').toLowerCase()) : null;
    out.push({ ...r, rel: path.relative(input, f), file: f, load: () => {
      const img = png.decodePNG(fs.readFileSync(f));
      if (!a) return img;
      const al = png.decodePNG(fs.readFileSync(a));                 // _rgb + _a: the second image's brightness is the alpha
      if (al.width === img.width && al.height === img.height) for (let i = 0; i < img.width * img.height; i++) img.data[i * 4 + 3] = al.data[i * 4];
      return img;
    } });
  }
  return out;
}

module.exports = { _test: { maxCI, reverseDXT, calculateDXT, txl2Words }, riceCRC32, riceFromDump, riceForTexture, parseRiceName, parseRiceId, riceId, readGlidenPack, writeHts, readClassicPack, hex8, VERSION, CONFIG, O2R_FMT };
