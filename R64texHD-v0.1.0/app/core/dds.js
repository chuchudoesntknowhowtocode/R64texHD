'use strict';
// DDS read (top mip -> RGBA) and write (DX10 header, full mip chain).
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const bc = require('./bc');
const png = require('./png');

const DXGI = { RGBA8: 28, RGBA8_SRGB: 29, BC1: 71, BC1_SRGB: 72, BC2: 74, BC2_SRGB: 75, BC3: 77, BC3_SRGB: 78, BC4: 80, BC5: 83, BC7: 98, BC7_SRGB: 99, BGRA8: 87, BGRX8: 88 };
const BLOCK_BITS = { 70: 64, 71: 64, 72: 64, 79: 64, 80: 64, 81: 64, 73: 128, 74: 128, 75: 128, 76: 128, 77: 128, 78: 128, 82: 128, 83: 128, 84: 128, 94: 128, 95: 128, 96: 128, 97: 128, 98: 128, 99: 128 };
const PIXEL32 = new Set([27, 28, 29, 87, 88, 90, 91, 92, 93]);
const FOURCC = { DXT1: 71, DXT2: 74, DXT3: 74, DXT4: 77, DXT5: 77, ATI1: 80, BC4U: 80, ATI2: 83, BC5U: 83 };

// Header info compatible with ddspp (used by the low-mip cache too).
function parseHeader(buf) {
  if (buf.length < 128 || buf.toString('latin1', 0, 4) !== 'DDS ') return null;
  const height = buf.readUInt32LE(12) || 1, width = buf.readUInt32LE(16) || 1;
  const mips = buf.readUInt32LE(28) || 1;
  const pfFlags = buf.readUInt32LE(80);
  const fourcc = buf.toString('latin1', 84, 88);
  let headerSize = 128, dxgi = 0, masks = null, bitCount = 0;
  if ((pfFlags & 4) && fourcc === 'DX10') {
    if (buf.length < 148) return null;
    dxgi = buf.readUInt32LE(128);
    const dim = buf.readUInt32LE(132), array = buf.readUInt32LE(140);
    headerSize = 148;
    if (dim !== 3 || array > 1) return { unsupported: 'only plain 2D textures are supported' };
  } else if (pfFlags & 4) {
    dxgi = FOURCC[fourcc] || 0;
    if (!dxgi) return { unsupported: `DDS format ${fourcc} is not supported` };
  } else if (pfFlags & 0x40 || pfFlags & 0x20000 || pfFlags & 0x2) {
    bitCount = buf.readUInt32LE(88);
    masks = [buf.readUInt32LE(92), buf.readUInt32LE(96), buf.readUInt32LE(100), (pfFlags & 1) || (pfFlags & 2) ? buf.readUInt32LE(104) : 0];
    if (bitCount === 32 && masks[0] === 0xff && masks[1] === 0xff00 && masks[2] === 0xff0000 && masks[3] === 0xff000000) dxgi = 28;
    else if (bitCount === 32 && masks[0] === 0xff0000 && masks[1] === 0xff00 && masks[2] === 0xff && masks[3] === 0xff000000) dxgi = 87;
    else if (bitCount === 32 && masks[0] === 0xff0000 && masks[1] === 0xff00 && masks[2] === 0xff && masks[3] === 0) dxgi = 88;
  }
  const info = { width, height, mips, dxgi, headerSize, masks, bitCount };
  if (BLOCK_BITS[dxgi]) { info.bits = BLOCK_BITS[dxgi]; info.block = 4; }
  else if (PIXEL32.has(dxgi)) { info.bits = 32; info.block = 1; }
  else if (masks && [8, 16, 24, 32].includes(bitCount)) { info.bits = bitCount; info.block = 1; info.generic = true; }
  else return { unsupported: `DDS format ${dxgi} is not supported` };
  info.rowPitch = (mip) => ((Math.ceil(Math.max(width >> mip, 1) / info.block) * info.bits + 7) >> 3);
  info.offset = (mip) => {
    let bits = 0;
    for (let m = 0; m < mip; m++) {
      const w = Math.max(width >> m, 1), h = Math.max(height >> m, 1);
      bits += Math.ceil(w / info.block) * Math.ceil(h / info.block) * info.bits;
    }
    return bits / 8;
  };
  return info;
}

function maskShift(mask) {
  if (!mask) return [0, 0];
  let shift = 0;
  while (!((mask >>> shift) & 1)) shift++;
  let bits = 0;
  while ((mask >>> (shift + bits)) & 1) bits++;
  return [shift, bits];
}

function decodeDDS(buf) {
  buf = Buffer.isBuffer(buf) ? buf : Buffer.from(buf);
  const info = parseHeader(buf);
  if (!info) throw new Error('Not a DDS file');
  if (info.unsupported) throw new Error(info.unsupported);
  const { width, height, dxgi, headerSize } = info;
  if ([94, 95, 96].includes(dxgi)) throw new Error('BC6H (HDR) DDS textures are not supported');
  const out = new Uint8Array(width * height * 4);
  if (info.block === 4) {
    const dec = { 70: bc.decodeBC1, 71: bc.decodeBC1, 72: bc.decodeBC1, 73: bc.decodeBC2, 74: bc.decodeBC2, 75: bc.decodeBC2,
      76: bc.decodeBC3, 77: bc.decodeBC3, 78: bc.decodeBC3, 79: bc.decodeBC4, 80: bc.decodeBC4, 81: bc.decodeBC4,
      82: bc.decodeBC5, 83: bc.decodeBC5, 84: bc.decodeBC5, 97: bc.decodeBC7, 98: bc.decodeBC7, 99: bc.decodeBC7 }[dxgi];
    if (!dec) throw new Error(`DDS format ${dxgi} is not supported`);
    const bytes = info.bits / 8, bw = Math.ceil(width / 4), bh = Math.ceil(height / 4);
    if (headerSize + bw * bh * bytes > buf.length) throw new Error('DDS file is truncated');
    const px = new Uint8Array(64);
    for (let by = 0; by < bh; by++) {
      for (let bx = 0; bx < bw; bx++) {
        dec(buf, headerSize + (by * bw + bx) * bytes, px);
        for (let y = 0; y < 4; y++) {
          const yy = by * 4 + y;
          if (yy >= height) break;
          for (let x = 0; x < 4; x++) {
            const xx = bx * 4 + x;
            if (xx >= width) break;
            out.set(px.subarray((y * 4 + x) * 4, (y * 4 + x) * 4 + 4), (yy * width + xx) * 4);
          }
        }
      }
    }
    return { width, height, data: out };
  }
  const bpp = info.bits / 8, pitch = info.rowPitch(0);
  if (headerSize + pitch * height > buf.length) throw new Error('DDS file is truncated');
  let masks = info.masks;
  if (!info.generic) {
    masks = dxgi === 87 ? [0xff0000, 0xff00, 0xff, 0xff000000] : dxgi === 88 ? [0xff0000, 0xff00, 0xff, 0] : [0xff, 0xff00, 0xff0000, 0xff000000];
  }
  const sh = masks.map(maskShift);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const o = headerSize + y * pitch + x * bpp;
      let v = 0;
      for (let k = 0; k < bpp; k++) v += buf[o + k] * 2 ** (8 * k);
      const d = (y * width + x) * 4;
      for (let c = 0; c < 4; c++) {
        const [s, n] = sh[c];
        if (!n) { out[d + c] = c === 3 ? 255 : (c > 0 && !masks[1] && !masks[2] ? out[d] : 0); continue; }
        const raw = Math.floor(v / 2 ** s) % (2 ** n);
        out[d + c] = Math.round(raw * 255 / (2 ** n - 1));
      }
    }
  }
  return { width, height, data: out };
}

// ------------------------------------------------------------------ writing
function mipChain(img) {
  const levels = [img];
  let { width: w, height: h } = img;
  let cur = new Float32Array(img.data.length);
  for (let i = 0; i < img.data.length; i += 4) {
    const a = img.data[i + 3] / 255;
    cur[i] = img.data[i] / 255 * a; cur[i + 1] = img.data[i + 1] / 255 * a; cur[i + 2] = img.data[i + 2] / 255 * a; cur[i + 3] = a;
  }
  while (w > 1 || h > 1) {
    const nw = Math.max(w >> 1, 1), nh = Math.max(h >> 1, 1);
    const sx = w > 1 ? 2 : 1, sy = h > 1 ? 2 : 1;
    const next = new Float32Array(nw * nh * 4);
    const data = new Uint8Array(nw * nh * 4);
    for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
      const d = (y * nw + x) * 4;
      for (let dy = 0; dy < sy; dy++) for (let dx = 0; dx < sx; dx++) {
        const s = ((y * sy + dy) * w + (x * sx + dx)) * 4;
        for (let c = 0; c < 4; c++) next[d + c] += cur[s + c];
      }
      const n = sx * sy;
      for (let c = 0; c < 4; c++) next[d + c] /= n;
      const a = next[d + 3];
      for (let c = 0; c < 3; c++) data[d + c] = a > 1e-6 ? Math.max(0, Math.min(255, Math.round(next[d + c] / a * 255))) : 0;
      data[d + 3] = Math.max(0, Math.min(255, Math.round(a * 255)));
    }
    levels.push({ width: nw, height: nh, data });
    cur = next; w = nw; h = nh;
  }
  return levels;
}

function header(width, height, mips, dxgi) {
  const h = Buffer.alloc(148);
  const blockBytes = BLOCK_BITS[dxgi] ? BLOCK_BITS[dxgi] / 8 : 0;
  let flags = 0x1 | 0x2 | 0x4 | 0x1000 | (mips > 1 ? 0x20000 : 0);
  let pitch;
  if (blockBytes) { flags |= 0x80000; pitch = Math.max(1, Math.ceil(width / 4)) * Math.max(1, Math.ceil(height / 4)) * blockBytes; }
  else { flags |= 0x8; pitch = width * 4; }
  h.write('DDS ', 0, 'latin1');
  h.writeUInt32LE(124, 4); h.writeUInt32LE(flags, 8); h.writeUInt32LE(height, 12); h.writeUInt32LE(width, 16);
  h.writeUInt32LE(pitch, 20); h.writeUInt32LE(mips, 28);
  h.writeUInt32LE(32, 76); h.writeUInt32LE(4, 80); h.write('DX10', 84, 'latin1');
  h.writeUInt32LE(0x1000 | (mips > 1 ? 0x400008 : 0), 108);
  h.writeUInt32LE(dxgi, 128); h.writeUInt32LE(3, 132); h.writeUInt32LE(1, 140);
  return h;
}

function encodeBlocks(level, encode, blockBytes) {
  const { width, height, data } = level;
  const bw = Math.ceil(width / 4), bh = Math.ceil(height / 4);
  const out = Buffer.alloc(bw * bh * blockBytes);
  const px = new Uint8Array(64);
  for (let by = 0; by < bh; by++) for (let bx = 0; bx < bw; bx++) {
    for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
      const xx = Math.min(bx * 4 + x, width - 1), yy = Math.min(by * 4 + y, height - 1); // edge pixels repeat
      const s = (yy * width + xx) * 4, d = (y * 4 + x) * 4;
      px[d] = data[s]; px[d + 1] = data[s + 1]; px[d + 2] = data[s + 2]; px[d + 3] = data[s + 3];
    }
    encode(px, out, (by * bw + bx) * blockBytes);
  }
  return out;
}

function hasAlpha(img) {
  for (let i = 3; i < img.data.length; i += 4) if (img.data[i] !== 255) return true;
  return false;
}

// format: auto | bc7 | bc3 | bc1 | rgba8
function encodeDDS(img, format = 'auto', { mipmaps = true, texconv = null } = {}) {
  let dxgi;
  if (format === 'rgba8') dxgi = DXGI.RGBA8;
  else if (format === 'bc1') dxgi = DXGI.BC1;
  else if (format === 'bc3') dxgi = DXGI.BC3;
  else if (format === 'bc7' && texconv) return encodeTexconv(img, mipmaps, texconv);
  else dxgi = hasAlpha(img) ? DXGI.BC3 : DXGI.BC1;
  const levels = mipmaps ? mipChain(img) : [img];
  const parts = [header(img.width, img.height, levels.length, dxgi)];
  for (const level of levels) {
    if (dxgi === DXGI.RGBA8) parts.push(Buffer.from(level.data.buffer, level.data.byteOffset, level.data.length));
    else if (dxgi === DXGI.BC1) parts.push(encodeBlocks(level, bc.encodeBC1, 8));
    else parts.push(encodeBlocks(level, bc.encodeBC3, 16));
  }
  return Buffer.concat(parts);
}

function encodeTexconv(img, mipmaps, texconv) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'htk-'));
  try {
    const src = path.join(dir, 'tex.png');
    fs.writeFileSync(src, png.encodePNG(img, 1));
    const r = spawnSync(texconv, ['-nologo', '-y', '-f', 'BC7_UNORM', '-m', mipmaps ? '0' : '1', '-dx10', '-o', dir, src], { windowsHide: true, encoding: 'utf8' });
    const out = path.join(dir, 'tex.dds');
    if (r.status !== 0 || !fs.existsSync(out)) throw new Error('texconv failed: ' + ((r.stdout || '') + (r.stderr || '') || String(r.error)).trim().slice(-300));
    return fs.readFileSync(out);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { parseHeader, decodeDDS, encodeDDS, mipChain, hasAlpha, DXGI };
