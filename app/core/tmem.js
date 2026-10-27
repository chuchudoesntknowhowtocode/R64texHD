'use strict';
// RT64 texture dumps (<hash>.v<N>.tmem + .tile.json) -> RGBA.
// A direct port of RT64's shaders/TextureDecoder.hlsli (sampleTMEM), so images match what RT64 shows.
const fs = require('fs');
const path = require('path');

const TMEM_BYTES = 0x1000, TMEM_PALETTE = 0x800, MASK8 = 0xfff, MASK16 = 0x7ff;
const FMT = { RGBA: 0, YUV: 1, CI: 2, IA: 3, I: 4 };
const TLUT = { None: 0, RGBA16: 0x8000, IA16: 0xc000 };
const DUMP_RE = /^([0-9a-fA-F]{16})\.v(\d+)\.tmem$/;

const e5 = (v) => (v << 3) | (v >> 2);

function decodeTMEM(tmem, { fmt, siz, tmemAddress, line, width, height, tlut = 0, palette = 0 }) {
  const t = new Uint8Array(TMEM_BYTES);
  t.set(tmem.subarray ? tmem.subarray(0, TMEM_BYTES) : tmem.slice(0, TMEM_BYTES));
  const address = tmemAddress << 3, stride = line << 3;
  const isRgba32 = fmt === FMT.RGBA && siz === 3;
  const usesTlut = tlut !== 0;
  const shift = isRgba32 ? 2 : siz;
  const mask = (isRgba32 || usesTlut) ? MASK16 : MASK8;
  const out = new Uint8Array(width * height * 4);

  for (let y = 0; y < height; y++) {
    const oddRow = (y & 1) === 1;
    const load = (rel, m, orA) => {
      let final;
      if (oddRow) {
        const rowStart = stride > 0 ? Math.floor(rel / stride) * stride : 0;
        const word = Math.floor((rel - rowStart) / 4);
        final = address + rowStart + ((word ^ 1) * 4) + (rel & 3);
      } else final = address + rel;
      return t[((final & m) | orA) & MASK8];
    };
    for (let x = 0; x < width; x++) {
      const oddCol = (x & 1) === 1;
      const pa = y * stride + ((x << shift) >> 1);
      const p0 = load(pa, mask, 0), p1 = load(pa + 1, mask, 0);
      const v4 = (p0 >> (oddCol ? 0 : 4)) & 0xf;
      let r = 0, g = 0, b = 0, a = 255;
      if (usesTlut) {
        const pal = siz === 0 ? TMEM_PALETTE + (palette << 7) + (v4 << 3) : TMEM_PALETTE + (p0 << 3);
        const v = t[(pal + 1) & MASK8] | (t[pal & MASK8] << 8);
        if (tlut === TLUT.RGBA16) { r = e5((v >> 11) & 31); g = e5((v >> 6) & 31); b = e5((v >> 1) & 31); a = v & 1 ? 255 : 0; }
        else if (tlut === TLUT.IA16) { r = g = b = (v >> 8) & 0xff; a = v & 0xff; }
      } else {
        const pa2 = isRgba32 ? pa : pa + 2;
        const orA = isRgba32 ? TMEM_BYTES >> 1 : 0;
        const p2 = load(pa2, mask, orA), p3 = load(pa2 + 1, mask, orA);
        if (siz === 0) {
          if (fmt === FMT.CI) { r = g = b = a = (palette << 4) | v4; }
          else if (fmt === FMT.IA) { let i = v4 & 0b1110; i = (i << 4) | (i << 1) | (i >> 2); r = g = b = i; a = v4 & 1 ? 255 : 0; }
          else if (fmt === FMT.I || fmt === FMT.RGBA) { r = g = b = a = (v4 << 4) | v4; }
        } else if (siz === 1) {
          if (fmt === FMT.IA) { const i = (p0 >> 4) & 0xf, al = p0 & 0xf; r = g = b = (i << 4) | i; a = (al << 4) | al; }
          else if (fmt === FMT.I || fmt === FMT.RGBA || fmt === FMT.CI) { r = g = b = a = p0; }
        } else if (siz === 2) {
          const v = p1 | (p0 << 8);
          if (fmt === FMT.RGBA) { r = e5((v >> 11) & 31); g = e5((v >> 6) & 31); b = e5((v >> 1) & 31); a = v & 1 ? 255 : 0; }
          else if (fmt === FMT.IA) { r = g = b = (v >> 8) & 0xff; a = v & 0xff; }
          else if (fmt === FMT.CI || fmt === FMT.I) { r = p0; g = p1; b = p0; a = p1; }
        } else if (siz === 3) {
          if (fmt === FMT.RGBA) { r = p0; g = p1; b = p2; a = p3; }
          else if (fmt === FMT.CI || fmt === FMT.IA || fmt === FMT.I) {
            if (oddCol) { r = p0; g = p1; b = p0; a = p1; } else { r = p2; g = p3; b = p2; a = p3; }
          }
        }
      }
      const o = (y * width + x) * 4;
      out[o] = r; out[o + 1] = g; out[o + 2] = b; out[o + 3] = a;
    }
  }
  return { width, height, data: out };
}

function loadDump(tmemPath) {
  const m = DUMP_RE.exec(path.basename(tmemPath));
  if (!m) throw new Error(path.basename(tmemPath) + ' is not an RT64 texture dump');
  const tilePath = tmemPath.slice(0, -'.tmem'.length) + '.tile.json';
  const info = JSON.parse(fs.readFileSync(tilePath, 'utf8'));
  const tile = info.tile || {};
  let tlut = info.tlut ?? 'None';
  tlut = typeof tlut === 'string' ? (TLUT[tlut] ?? 0) : Number(tlut);
  // How the texture repeats on each axis. No mask means it never wraps; the clamp bit wins over mirror.
  const wrap = (cm, mask) => (cm & 2 || !mask ? 'clamp' : (cm & 1 ? 'mirror' : 'wrap'));
  return {
    hash: m[1].toLowerCase(), version: Number(m[2]), tmemPath, tilePath,
    width: Number(info.width || 0), height: Number(info.height || 0), tlut, tile,
    edges: [wrap(Number(tile.cms || 0), Number(tile.masks || 0)), wrap(Number(tile.cmt || 0), Number(tile.maskt || 0))],
    decode() {
      return decodeTMEM(fs.readFileSync(tmemPath), {
        fmt: Number(tile.fmt || 0), siz: Number(tile.siz || 0), tmemAddress: Number(tile.tmem || 0), line: Number(tile.line || 0),
        width: this.width, height: this.height, tlut, palette: Number(tile.palette || 0),
      });
    },
  };
}

// Recursively lists .tmem files that have their .tile.json. Returns { files, problems }.
function findDumps(folder, limit = Infinity) {
  const files = [], problems = [];
  const walk = (dir) => {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    const names = new Set(entries.map((e) => e.name));
    for (const e of entries) {
      if (files.length >= limit) return;
      if (e.isDirectory()) walk(path.join(dir, e.name));
      else if (DUMP_RE.test(e.name)) {
        const tile = e.name.slice(0, -'.tmem'.length) + '.tile.json';
        if (names.has(tile)) files.push(path.join(dir, e.name)); else problems.push(`${e.name}: missing ${tile}`);
      }
    }
  };
  walk(folder);
  files.sort((a, b) => path.basename(a).localeCompare(path.basename(b)));
  return { files, problems };
}

module.exports = { decodeTMEM, loadDump, findDumps, DUMP_RE, TLUT };
