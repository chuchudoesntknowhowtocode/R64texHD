'use strict';
// PNG decode (all colour types, bit depths, palettes, tRNS, Adam7 interlace) and RGBA8 encode.
// Images are { width, height, data: Uint8Array RGBA }.

const zlib = require('zlib');

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function paeth(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  return pb <= pc ? b : c;
}

function unfilter(data, offset, width, height, bpp, rowBytes, out) {
  // Returns the offset after this (sub)image's scanlines; `out` receives unfiltered rows.
  let prev = new Uint8Array(rowBytes);
  for (let y = 0; y < height; y++) {
    const type = data[offset++];
    const row = out.subarray(y * rowBytes, (y + 1) * rowBytes);
    for (let i = 0; i < rowBytes; i++) {
      const x = data[offset + i];
      const a = i >= bpp ? row[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      let v;
      switch (type) {
        case 0: v = x; break;
        case 1: v = x + a; break;
        case 2: v = x + b; break;
        case 3: v = x + ((a + b) >> 1); break;
        case 4: v = x + paeth(a, b, c); break;
        default: throw new Error('PNG: bad filter type ' + type);
      }
      row[i] = v & 0xff;
    }
    offset += rowBytes;
    prev = row;
  }
  return offset;
}

function decodePNG(buf) {
  buf = Buffer.isBuffer(buf) ? buf : Buffer.from(buf);
  if (buf.length < 8 || !buf.subarray(0, 8).equals(SIGNATURE)) throw new Error('Not a PNG file');
  let pos = 8;
  let width = 0, height = 0, depth = 0, colorType = 0, interlace = 0;
  let palette = null, trns = null;
  const idat = [];
  while (pos + 8 <= buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString('latin1', pos + 4, pos + 8);
    const body = buf.subarray(pos + 8, pos + 8 + len);
    pos += 12 + len;
    if (type === 'IHDR') {
      width = body.readUInt32BE(0); height = body.readUInt32BE(4);
      depth = body[8]; colorType = body[9]; interlace = body[12];
    } else if (type === 'PLTE') palette = body;
    else if (type === 'tRNS') trns = body;
    else if (type === 'IDAT') idat.push(body);
    else if (type === 'IEND') break;
  }
  if (!width || !height) throw new Error('PNG: missing header');
  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[colorType];
  if (!channels) throw new Error('PNG: unsupported colour type ' + colorType);
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const bitsPerPixel = channels * depth;
  const bpp = Math.max(1, bitsPerPixel >> 3);
  const out = new Uint8Array(width * height * 4);

  const passes = interlace
    ? [[0, 0, 8, 8], [4, 0, 8, 8], [0, 4, 4, 8], [2, 0, 4, 4], [0, 2, 2, 4], [1, 0, 2, 2], [0, 1, 1, 2]]
    : [[0, 0, 1, 1]];
  let offset = 0;
  const maxGray = (1 << depth) - 1;
  let trnsGray = -1, trnsR = -1, trnsG = -1, trnsB = -1;
  if (trns && colorType === 0) trnsGray = trns.readUInt16BE(0);
  if (trns && colorType === 2) { trnsR = trns.readUInt16BE(0); trnsG = trns.readUInt16BE(2); trnsB = trns.readUInt16BE(4); }

  for (const [x0, y0, dx, dy] of passes) {
    const pw = Math.ceil((width - x0) / dx), ph = Math.ceil((height - y0) / dy);
    if (pw <= 0 || ph <= 0) continue;
    const rowBytes = Math.ceil(pw * bitsPerPixel / 8);
    const rows = new Uint8Array(rowBytes * ph);
    offset = unfilter(raw, offset, pw, ph, bpp, rowBytes, rows);
    for (let y = 0; y < ph; y++) {
      const row = rows.subarray(y * rowBytes);
      for (let x = 0; x < pw; x++) {
        const o = (((y0 + y * dy) * width) + (x0 + x * dx)) * 4;
        let r, g, b, a = 255;
        if (depth < 8) {
          const bit = x * depth;
          const v = (row[bit >> 3] >> (8 - depth - (bit & 7))) & maxGray;
          if (colorType === 3) {
            r = palette[v * 3]; g = palette[v * 3 + 1]; b = palette[v * 3 + 2];
            a = trns && v < trns.length ? trns[v] : 255;
          } else {
            r = g = b = Math.round(v * 255 / maxGray);
            if (v === trnsGray) a = 0;
          }
        } else if (depth === 8) {
          const i = x * channels;
          switch (colorType) {
            case 0: r = g = b = row[i]; if (row[i] === trnsGray) a = 0; break;
            case 2: r = row[i]; g = row[i + 1]; b = row[i + 2]; if (r === trnsR && g === trnsG && b === trnsB) a = 0; break;
            case 3: { const v = row[i]; r = palette[v * 3]; g = palette[v * 3 + 1]; b = palette[v * 3 + 2]; a = trns && v < trns.length ? trns[v] : 255; break; }
            case 4: r = g = b = row[i]; a = row[i + 1]; break;
            default: r = row[i]; g = row[i + 1]; b = row[i + 2]; a = row[i + 3];
          }
        } else { // 16-bit
          const i = x * channels * 2;
          const s = (k) => (row[i + k * 2] << 8) | row[i + k * 2 + 1];
          switch (colorType) {
            case 0: { const v = s(0); r = g = b = row[i]; if (v === trnsGray) a = 0; break; }
            case 2: { r = row[i]; g = row[i + 2]; b = row[i + 4]; if (s(0) === trnsR && s(1) === trnsG && s(2) === trnsB) a = 0; break; }
            case 4: r = g = b = row[i]; a = row[i + 2]; break;
            default: r = row[i]; g = row[i + 2]; b = row[i + 4]; a = row[i + 6];
          }
        }
        out[o] = r; out[o + 1] = g; out[o + 2] = b; out[o + 3] = a;
      }
    }
  }
  return { width, height, data: out };
}

function chunk(type, body) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(body.length, 0);
  head.write(type, 4, 'latin1');
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(zlib.crc32(Buffer.concat([head.subarray(4), body])) >>> 0, 0);
  return Buffer.concat([head, body, crc]);
}

// RGBA8 (or RGB8 when every pixel is opaque) with adaptive per-row filtering.
function encodePNG(img, level = 6) {
  const { width, height, data } = img;
  let opaque = true;
  for (let i = 3; i < data.length; i += 4) if (data[i] !== 255) { opaque = false; break; }
  const ch = opaque ? 3 : 4;
  const rowBytes = width * ch;
  const raw = Buffer.alloc((rowBytes + 1) * height);
  let prev = new Uint8Array(rowBytes);
  const cur = new Uint8Array(rowBytes);
  const cand = [0, 1, 2, 3, 4].map(() => new Uint8Array(rowBytes));
  for (let y = 0; y < height; y++) {
    for (let x = 0, s = y * width * 4, d = 0; x < width; x++, s += 4) {
      cur[d++] = data[s]; cur[d++] = data[s + 1]; cur[d++] = data[s + 2];
      if (ch === 4) cur[d++] = data[s + 3];
    }
    let best = 0, bestScore = Infinity;
    for (let t = 0; t < 5; t++) {
      const c = cand[t];
      let score = 0;
      for (let i = 0; i < rowBytes; i++) {
        const a = i >= ch ? cur[i - ch] : 0, b = prev[i], cc = i >= ch ? prev[i - ch] : 0;
        let v;
        switch (t) {
          case 0: v = cur[i]; break;
          case 1: v = cur[i] - a; break;
          case 2: v = cur[i] - b; break;
          case 3: v = cur[i] - ((a + b) >> 1); break;
          default: v = cur[i] - paeth(a, b, cc);
        }
        v &= 0xff;
        c[i] = v;
        score += v < 128 ? v : 256 - v;
      }
      if (score < bestScore) { bestScore = score; best = t; }
    }
    const o = y * (rowBytes + 1);
    raw[o] = best;
    raw.set(cand[best], o + 1);
    prev = Uint8Array.from(cur);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; ihdr[9] = ch === 4 ? 6 : 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([SIGNATURE, chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level })), chunk('IEND', Buffer.alloc(0))]);
}

module.exports = { decodePNG, encodePNG };
