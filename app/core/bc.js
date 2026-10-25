'use strict';
// Block compression: decoders for BC1-BC5 and BC7 (exact ports of bcdec), and BC1 / BC3 encoders.
// Blocks decode into / encode from 16 RGBA pixels (64 bytes, row-major).

const { P2, P3 } = require('./bc7tables');

// ---------------------------------------------------------------- decoders
function expand565(c) {
  const r = (c >> 11) & 31, g = (c >> 5) & 63, b = c & 31;
  return [r, g, b];
}

function decodeColorBlock(src, o, out, onlyOpaque) {
  const c0 = src[o] | (src[o + 1] << 8), c1 = src[o + 2] | (src[o + 3] << 8);
  const [r0, g0, b0] = expand565(c0), [r1, g1, b1] = expand565(c1);
  const pal = new Uint8Array(16);
  pal[0] = (r0 * 527 + 23) >> 6; pal[1] = (g0 * 259 + 33) >> 6; pal[2] = (b0 * 527 + 23) >> 6; pal[3] = 255;
  pal[4] = (r1 * 527 + 23) >> 6; pal[5] = (g1 * 259 + 33) >> 6; pal[6] = (b1 * 527 + 23) >> 6; pal[7] = 255;
  if (c0 > c1 || onlyOpaque) {
    pal[8] = ((2 * r0 + r1) * 351 + 61) >> 7; pal[9] = ((2 * g0 + g1) * 2763 + 1039) >> 11; pal[10] = ((2 * b0 + b1) * 351 + 61) >> 7; pal[11] = 255;
    pal[12] = ((r0 + r1 * 2) * 351 + 61) >> 7; pal[13] = ((g0 + g1 * 2) * 2763 + 1039) >> 11; pal[14] = ((b0 + b1 * 2) * 351 + 61) >> 7; pal[15] = 255;
  } else {
    pal[8] = ((r0 + r1) * 1053 + 125) >> 8; pal[9] = ((g0 + g1) * 4145 + 1019) >> 11; pal[10] = ((b0 + b1) * 1053 + 125) >> 8; pal[11] = 255;
    pal[12] = pal[13] = pal[14] = pal[15] = 0;
  }
  let idx = (src[o + 4] | (src[o + 5] << 8) | (src[o + 6] << 16) | (src[o + 7] << 24)) >>> 0;
  for (let p = 0; p < 16; p++, idx >>>= 2) {
    const k = (idx & 3) * 4;
    out[p * 4] = pal[k]; out[p * 4 + 1] = pal[k + 1]; out[p * 4 + 2] = pal[k + 2]; out[p * 4 + 3] = pal[k + 3];
  }
}

function decodeSmoothAlpha(src, o, out, channel, stride) {
  const a = new Uint8Array(8);
  a[0] = src[o]; a[1] = src[o + 1];
  if (a[0] > a[1]) {
    for (let i = 1; i <= 6; i++) a[i + 1] = Math.floor(((7 - i) * a[0] + i * a[1]) / 7);
  } else {
    for (let i = 1; i <= 4; i++) a[i + 1] = Math.floor(((5 - i) * a[0] + i * a[1]) / 5);
    a[6] = 0; a[7] = 255;
  }
  // 48 bits of 3-bit indices
  let lo = (src[o + 2] | (src[o + 3] << 8) | (src[o + 4] << 16)) >>> 0;
  let hi = (src[o + 5] | (src[o + 6] << 8) | (src[o + 7] << 16)) >>> 0;
  for (let p = 0; p < 16; p++) {
    const v = p < 8 ? (lo >> (3 * p)) & 7 : (hi >> (3 * (p - 8))) & 7;
    out[p * stride + channel] = a[v];
  }
}

function decodeBC1(src, o, out) { decodeColorBlock(src, o, out, false); }
function decodeBC2(src, o, out) {
  decodeColorBlock(src, o + 8, out, true);
  for (let p = 0; p < 16; p++) out[p * 4 + 3] = ((src[o + (p >> 1)] >> ((p & 1) * 4)) & 15) * 17;
}
function decodeBC3(src, o, out) { decodeColorBlock(src, o + 8, out, true); decodeSmoothAlpha(src, o, out, 3, 4); }
function decodeBC4(src, o, out) {
  decodeSmoothAlpha(src, o, out, 0, 4);
  for (let p = 0; p < 16; p++) { out[p * 4 + 1] = out[p * 4 + 2] = out[p * 4]; out[p * 4 + 3] = 255; }
}
function decodeBC5(src, o, out) {
  decodeSmoothAlpha(src, o, out, 0, 4);
  decodeSmoothAlpha(src, o + 8, out, 1, 4);
  for (let p = 0; p < 16; p++) { out[p * 4 + 2] = 0; out[p * 4 + 3] = 255; }
}

const W2 = [0, 21, 43, 64], W3 = [0, 9, 18, 27, 37, 46, 55, 64], W4 = [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64];
const BITS = [[4, 6, 5, 7, 5, 7, 7, 5], [0, 0, 0, 0, 6, 8, 7, 5]];
const HAS_PBITS = 0b11001011;

function decodeBC7(src, o, out) {
  let pos = 0;
  const read = (n) => {
    let v = 0;
    for (let i = 0; i < n; i++, pos++) v |= ((src[o + (pos >> 3)] >> (pos & 7)) & 1) << i;
    return v;
  };
  let mode = 0;
  while (mode < 8 && read(1) === 0) mode++;
  if (mode >= 8) { out.fill(0, 0, 64); return; }
  let partition = 0, parts = 1, rotation = 0, isb = 0;
  if (mode === 0 || mode === 1 || mode === 2 || mode === 3 || mode === 7) {
    parts = (mode === 0 || mode === 2) ? 3 : 2;
    partition = read(mode === 0 ? 4 : 6);
  }
  const ne = parts * 2;
  if (mode === 4 || mode === 5) { rotation = read(2); if (mode === 4) isb = read(1); }
  const ep = [0, 1, 2, 3, 4, 5].map(() => [0, 0, 0, 0]);
  for (let c = 0; c < 3; c++) for (let j = 0; j < ne; j++) ep[j][c] = read(BITS[0][mode]);
  if (BITS[1][mode] > 0) for (let j = 0; j < ne; j++) ep[j][3] = read(BITS[1][mode]);
  if (mode === 0 || mode === 1 || mode === 3 || mode === 6 || mode === 7) {
    for (let i = 0; i < ne; i++) for (let c = 0; c < 4; c++) ep[i][c] <<= 1;
    if (mode === 1) {
      const i = read(1), j = read(1);
      for (let c = 0; c < 3; c++) { ep[0][c] |= i; ep[1][c] |= i; ep[2][c] |= j; ep[3][c] |= j; }
    } else if (HAS_PBITS & (1 << mode)) {
      for (let i = 0; i < ne; i++) { const j = read(1); for (let c = 0; c < 4; c++) ep[i][c] |= j; }
    }
  }
  for (let i = 0; i < ne; i++) {
    let j = BITS[0][mode] + ((HAS_PBITS >> mode) & 1);
    for (let c = 0; c < 3; c++) { ep[i][c] = (ep[i][c] << (8 - j)) & 0xffff; ep[i][c] |= ep[i][c] >> j; ep[i][c] &= 0xff; }
    j = BITS[1][mode] + ((HAS_PBITS >> mode) & 1);
    ep[i][3] = (ep[i][3] << (8 - j)) & 0xffff; ep[i][3] |= ep[i][3] >> j; ep[i][3] &= 0xff;
  }
  if (!BITS[1][mode]) for (let j = 0; j < ne; j++) ep[j][3] = 255;
  const ib = (mode === 0 || mode === 1) ? 3 : (mode === 6 ? 4 : 2);
  const ib2 = mode === 4 ? 3 : (mode === 5 ? 2 : 0);
  const w = ib === 2 ? W2 : (ib === 3 ? W3 : W4);
  const w2 = ib2 === 2 ? W2 : W3;
  const set = (p) => parts === 1 ? (p ? 0 : 128) : (parts === 2 ? P2 : P3)[partition * 16 + p];
  const idx = new Uint8Array(16);
  for (let p = 0; p < 16; p++) idx[p] = read((set(p) & 0x80) ? ib - 1 : ib);
  const interp = (a, b, wt, i) => (a * (64 - wt[i]) + b * wt[i] + 32) >> 6;
  for (let p = 0; p < 16; p++) {
    const s = set(p) & 3;
    const e0 = ep[s * 2], e1 = ep[s * 2 + 1];
    const i = idx[p];
    let r, g, b, a;
    if (!ib2) {
      r = interp(e0[0], e1[0], w, i); g = interp(e0[1], e1[1], w, i); b = interp(e0[2], e1[2], w, i); a = interp(e0[3], e1[3], w, i);
    } else {
      const i2 = read(p ? ib2 : ib2 - 1);
      if (!isb) {
        r = interp(e0[0], e1[0], w, i); g = interp(e0[1], e1[1], w, i); b = interp(e0[2], e1[2], w, i); a = interp(e0[3], e1[3], w2, i2);
      } else {
        r = interp(e0[0], e1[0], w2, i2); g = interp(e0[1], e1[1], w2, i2); b = interp(e0[2], e1[2], w2, i2); a = interp(e0[3], e1[3], w, i);
      }
    }
    if (rotation === 1) [a, r] = [r, a];
    else if (rotation === 2) [a, g] = [g, a];
    else if (rotation === 3) [a, b] = [b, a];
    out[p * 4] = r; out[p * 4 + 1] = g; out[p * 4 + 2] = b; out[p * 4 + 3] = a;
  }
}

// ---------------------------------------------------------------- encoders
const to565 = (r, g, b) => ((Math.max(0, Math.min(31, Math.round(r * 31 / 255))) << 11) |
  (Math.max(0, Math.min(63, Math.round(g * 63 / 255))) << 5) | Math.max(0, Math.min(31, Math.round(b * 31 / 255))));

function palette4(c0, c1) {
  const tmp = new Uint8Array(64);
  const blk = new Uint8Array([c0 & 255, c0 >> 8, c1 & 255, c1 >> 8, 0xe4, 0, 0, 0]); // indices 0,1,2,3 in first row
  decodeColorBlock(blk, 0, tmp, true);
  return [[tmp[0], tmp[1], tmp[2]], [tmp[4], tmp[5], tmp[6]], [tmp[8], tmp[9], tmp[10]], [tmp[12], tmp[13], tmp[14]]];
}

function fitIndices(px, pal) {
  const idx = new Uint8Array(16);
  let err = 0;
  for (let p = 0; p < 16; p++) {
    let best = 0, bd = Infinity;
    for (let k = 0; k < 4; k++) {
      const dr = px[p * 4] - pal[k][0], dg = px[p * 4 + 1] - pal[k][1], db = px[p * 4 + 2] - pal[k][2];
      const d = dr * dr * 2 + dg * dg * 4 + db * db; // rough luminance weighting
      if (d < bd) { bd = d; best = k; }
    }
    idx[p] = best;
    err += bd;
  }
  return { idx, err };
}

// Least squares endpoints for fixed indices (weights for palette slots 0,1,2,3).
function refine(px, idx) {
  const wt = [1, 0, 2 / 3, 1 / 3];
  let aa = 0, bb = 0, ab = 0;
  const ax = [0, 0, 0], bx = [0, 0, 0];
  for (let p = 0; p < 16; p++) {
    const a = wt[idx[p]], b = 1 - a;
    aa += a * a; bb += b * b; ab += a * b;
    for (let c = 0; c < 3; c++) { ax[c] += a * px[p * 4 + c]; bx[c] += b * px[p * 4 + c]; }
  }
  const det = aa * bb - ab * ab;
  if (Math.abs(det) < 1e-8) return null;
  const e0 = [0, 0, 0], e1 = [0, 0, 0];
  for (let c = 0; c < 3; c++) {
    e0[c] = (ax[c] * bb - bx[c] * ab) / det;
    e1[c] = (bx[c] * aa - ax[c] * ab) / det;
  }
  return [e0, e1];
}

function writeColorBlock(out, o, c0, c1, idx) {
  // 4-colour mode requires c0 > c1.
  if (c0 < c1) {
    [c0, c1] = [c1, c0];
    idx = idx.map((i) => [1, 0, 3, 2][i]);
  } else if (c0 === c1) {
    idx = idx.map(() => 0);
  }
  out[o] = c0 & 255; out[o + 1] = c0 >> 8; out[o + 2] = c1 & 255; out[o + 3] = c1 >> 8;
  let bits = 0;
  for (let p = 15; p >= 0; p--) bits = (bits * 4) + idx[p];
  out[o + 4] = bits & 255; out[o + 5] = (bits >>> 8) & 255; out[o + 6] = (bits >>> 16) & 255; out[o + 7] = (bits >>> 24) & 255;
}

function encodeColorBlock(px, out, o) {
  // Principal axis of the block's colours.
  let mr = 0, mg = 0, mb = 0;
  for (let p = 0; p < 16; p++) { mr += px[p * 4]; mg += px[p * 4 + 1]; mb += px[p * 4 + 2]; }
  mr /= 16; mg /= 16; mb /= 16;
  let crr = 0, cgg = 0, cbb = 0, crg = 0, crb = 0, cgb = 0;
  for (let p = 0; p < 16; p++) {
    const r = px[p * 4] - mr, g = px[p * 4 + 1] - mg, b = px[p * 4 + 2] - mb;
    crr += r * r; cgg += g * g; cbb += b * b; crg += r * g; crb += r * b; cgb += g * b;
  }
  if (crr + cgg + cbb < 1e-3) { // solid colour
    const c = to565(mr, mg, mb);
    writeColorBlock(out, o, c, c, new Uint8Array(16));
    return;
  }
  let vr = 1, vg = 1, vb = 1;
  for (let it = 0; it < 6; it++) {
    const nr = crr * vr + crg * vg + crb * vb, ng = crg * vr + cgg * vg + cgb * vb, nb = crb * vr + cgb * vg + cbb * vb;
    const len = Math.hypot(nr, ng, nb) || 1;
    vr = nr / len; vg = ng / len; vb = nb / len;
  }
  let lo = Infinity, hi = -Infinity, loP = 0, hiP = 0;
  for (let p = 0; p < 16; p++) {
    const d = (px[p * 4] - mr) * vr + (px[p * 4 + 1] - mg) * vg + (px[p * 4 + 2] - mb) * vb;
    if (d < lo) { lo = d; loP = p; }
    if (d > hi) { hi = d; hiP = p; }
  }
  let e0 = [px[hiP * 4], px[hiP * 4 + 1], px[hiP * 4 + 2]], e1 = [px[loP * 4], px[loP * 4 + 1], px[loP * 4 + 2]];
  let bestErr = Infinity, best = null;
  for (let it = 0; it < 3; it++) {
    const c0 = to565(...e0), c1 = to565(...e1);
    const pal = palette4(c0, c1);
    const { idx, err } = fitIndices(px, pal);
    if (err < bestErr) { bestErr = err; best = [c0, c1, idx]; }
    const r = refine(px, idx);
    if (!r) break;
    [e0, e1] = r;
  }
  writeColorBlock(out, o, best[0], best[1], best[2]);
}

function alphaPalette(a0, a1) {
  const a = [a0, a1];
  if (a0 > a1) for (let i = 1; i <= 6; i++) a.push(Math.floor(((7 - i) * a0 + i * a1) / 7));
  else { for (let i = 1; i <= 4; i++) a.push(Math.floor(((5 - i) * a0 + i * a1) / 5)); a.push(0, 255); }
  return a;
}

function encodeAlphaBlock(px, out, o, channel = 3) {
  let mn = 255, mx = 0, mn2 = 255, mx2 = 0;
  for (let p = 0; p < 16; p++) {
    const v = px[p * 4 + channel];
    if (v < mn) mn = v; if (v > mx) mx = v;
    if (v !== 0 && v !== 255) { if (v < mn2) mn2 = v; if (v > mx2) mx2 = v; }
  }
  const tryPal = (a0, a1) => {
    const pal = alphaPalette(a0, a1);
    const idx = new Uint8Array(16);
    let err = 0;
    for (let p = 0; p < 16; p++) {
      const v = px[p * 4 + channel];
      let best = 0, bd = Infinity;
      for (let k = 0; k < 8; k++) { const d = Math.abs(v - pal[k]); if (d < bd) { bd = d; best = k; } }
      idx[p] = best; err += bd * bd;
    }
    return { a0, a1, idx, err };
  };
  let res = tryPal(mx, mn); // 8-value mode when mx > mn (all equal: every index 0 is exact)
  if (mn2 <= mx2 && (mn === 0 || mx === 255)) {
    const alt = tryPal(mn2, mx2); // 6-value mode (a0 <= a1) keeps exact 0 and 255
    if (alt.err < res.err) res = alt;
  }
  out[o] = res.a0; out[o + 1] = res.a1;
  let lo = 0, hi = 0;
  for (let p = 0; p < 8; p++) lo |= res.idx[p] << (3 * p);
  for (let p = 8; p < 16; p++) hi |= res.idx[p] << (3 * (p - 8));
  out[o + 2] = lo & 255; out[o + 3] = (lo >>> 8) & 255; out[o + 4] = (lo >>> 16) & 255;
  out[o + 5] = hi & 255; out[o + 6] = (hi >>> 8) & 255; out[o + 7] = (hi >>> 16) & 255;
}

function encodeBC1(px, out, o) { encodeColorBlock(px, out, o); }
function encodeBC3(px, out, o) { encodeAlphaBlock(px, out, o); encodeColorBlock(px, out, o + 8); }

module.exports = { decodeBC1, decodeBC2, decodeBC3, decodeBC4, decodeBC5, decodeBC7, encodeBC1, encodeBC3 };
