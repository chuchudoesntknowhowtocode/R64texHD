'use strict';
// Reads MPQ archives: the older .otr format Ship ports (Ship of Harkinian and friends) used before
// .o2r. Made with StormLib as MPQ v2 with a (listfile), each file split into sectors and compressed
// with zlib (Torch's SWrapper / Shipwright's exporter). Read only.
//
// Format: header 'MPQ\x1A' (maybe after a 'MPQ\x1B' user-data header), an encrypted hash table
// (name hashes -> block index) and block table (file position, sizes, flags), an optional hi-block
// table for archives over 4 GB. Names come from (listfile). A compressed file starts with a
// sector offset table; each sector that is smaller than its full size starts with a compression
// byte (0x02 = zlib, 0x10 = bzip2, 0x08 = PKWARE implode).
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const MAGIC = 0x1a51504d, USER_DATA = 0x1b51504d;
const F = { IMPLODE: 0x100, COMPRESS: 0x200, ENCRYPTED: 0x10000, FIX_KEY: 0x20000, PATCH: 0x100000, SINGLE: 0x1000000, DELETE: 0x2000000, CRC: 0x4000000, EXISTS: 0x80000000 };

const CRYPT = (() => {
  const t = new Uint32Array(0x500);
  let seed = 0x00100001;
  for (let i1 = 0; i1 < 0x100; i1++) for (let i2 = i1, k = 0; k < 5; k++, i2 += 0x100) {
    seed = (seed * 125 + 3) % 0x2aaaab; const a = (seed & 0xffff) << 16;
    seed = (seed * 125 + 3) % 0x2aaaab; const b = seed & 0xffff;
    t[i2] = (a | b) >>> 0;
  }
  return t;
})();

// StormLib's name hash: upper-case; older StormLib (what the Ship ports shipped) also counts '/' as
// '\', newer StormLib keeps '/' (keepSlash). Archives in the wild can be either, so lookups try both.
function hash(name, type, keepSlash = false) {
  let s1 = 0x7fed7fed, s2 = 0xeeeeeeee;
  for (let i = 0; i < name.length; i++) {
    let c = name.charCodeAt(i) & 0xff;
    if (c === 0x2f && !keepSlash) c = 0x5c; else if (c >= 0x61 && c <= 0x7a) c -= 0x20;
    s1 = (CRYPT[type * 0x100 + c] ^ ((s1 + s2) >>> 0)) >>> 0;
    s2 = (c + s1 + s2 + ((s2 << 5) >>> 0) + 3) >>> 0;
  }
  return s1;
}

function decrypt(buf, key) {            // in place, whole dwords
  let s2 = 0xeeeeeeee;
  for (let o = 0; o + 4 <= buf.length; o += 4) {
    s2 = (s2 + CRYPT[0x400 + (key & 0xff)]) >>> 0;
    const v = (buf.readUInt32LE(o) ^ ((key + s2) >>> 0)) >>> 0;
    key = ((((~key) << 21) >>> 0) + 0x11111111 | (key >>> 11)) >>> 0;
    s2 = (v + s2 + ((s2 << 5) >>> 0) + 3) >>> 0;
    buf.writeUInt32LE(v, o);
  }
  return buf;
}

const readAt = (fd, len, pos) => { const b = Buffer.alloc(len); const n = fs.readSync(fd, b, 0, len, pos); return n === len ? b : b.subarray(0, n); };

function isMpq(file) {
  const fd = fs.openSync(file, 'r');
  try { const b = readAt(fd, 4, 0); return b.length === 4 && (b.readUInt32LE(0) === MAGIC || b.readUInt32LE(0) === USER_DATA); } finally { fs.closeSync(fd); }
}

function openTables(fd) {
  let base = 0, h = readAt(fd, 44, 0);
  if (h.length >= 16 && h.readUInt32LE(0) === USER_DATA) { base = h.readUInt32LE(8); h = readAt(fd, 44, base); }
  if (h.length < 32 || h.readUInt32LE(0) !== MAGIC) throw new Error('Not an MPQ (.otr) archive');
  const headerSize = h.readUInt32LE(4), version = h.readUInt16LE(12);
  if (version > 1) throw new Error(`This .otr uses MPQ version ${version + 1}, which R64texHD can’t read yet.`);
  const sector = 512 << h.readUInt16LE(14);
  let hashPos = h.readUInt32LE(16), blockPos = h.readUInt32LE(20);
  const hashN = h.readUInt32LE(24), blockN = h.readUInt32LE(28);
  let hiPos = 0;
  if (version === 1 && headerSize >= 44) {
    hiPos = Number(h.readBigUInt64LE(32));
    hashPos += h.readUInt16LE(40) * 2 ** 32; blockPos += h.readUInt16LE(42) * 2 ** 32;
  }
  const hashes = decrypt(readAt(fd, hashN * 16, base + hashPos), hash('(hash table)', 3));
  const blocks = decrypt(readAt(fd, blockN * 16, base + blockPos), hash('(block table)', 3));
  const hi = hiPos ? readAt(fd, blockN * 2, base + hiPos) : null;
  const block = (i) => ({
    pos: base + blocks.readUInt32LE(i * 16) + (hi ? hi.readUInt16LE(i * 2) * 2 ** 32 : 0), filePos: blocks.readUInt32LE(i * 16),
    csize: blocks.readUInt32LE(i * 16 + 4), usize: blocks.readUInt32LE(i * 16 + 8), flags: blocks.readUInt32LE(i * 16 + 12),
  });
  const find = (name) => findWith(name, false) >= 0 ? findWith(name, false) : name.includes('/') ? findWith(name, true) : -1;
  const findWith = (name, keepSlash) => {    // block index for a name, or -1
    if (!hashN) return -1;
    const a = hash(name, 1, keepSlash), b = hash(name, 2, keepSlash);
    let i = hash(name, 0, keepSlash) & (hashN - 1);
    for (let n = 0; n < hashN; n++, i = (i + 1) & (hashN - 1)) {
      const bi = hashes.readUInt32LE(i * 16 + 12);
      if (bi === 0xffffffff) return -1;       // empty: end of the chain
      if (bi !== 0xfffffffe && hashes.readUInt32LE(i * 16) === a && hashes.readUInt32LE(i * 16 + 4) === b && bi < blockN) return bi;
    }
    return -1;
  };
  return { sector, block, find, blockN };
}

function unpackSector(data, full, name) {
  if (data.length >= full) return data.subarray(0, full);          // stored as is
  const mask = data[0];
  if (mask === 0x02) return zlib.inflateSync(data.subarray(1));
  if (mask === 0x00) return data.subarray(1);
  const what = mask & 0x10 ? 'bzip2' : mask & 0x08 ? 'PKWARE implode' : mask & 0x01 ? 'Huffman' : `type 0x${mask.toString(16)}`;
  throw new Error(`${name}: ${what} compression in this .otr isn’t supported`);
}

// Reads one file's bytes.
function readFile(fd, t, e) {
  const b = e.mpq, { flags } = b;
  if (!(flags & F.EXISTS) || flags & (F.DELETE | F.PATCH)) throw new Error(`${e.name}: not a normal file in this archive`);
  if (!b.usize) return Buffer.alloc(0);
  let key = 0;
  if (flags & F.ENCRYPTED) {
    key = hash(path.posix.basename(e.name.replace(/\\/g, '/')), 3);
    if (flags & F.FIX_KEY) key = ((key + b.filePos) ^ b.usize) >>> 0;
  }
  if (flags & F.SINGLE || !(flags & (F.COMPRESS | F.IMPLODE))) {
    const raw = readAt(fd, b.csize, b.pos);
    if (key) decrypt(raw, key);
    if (flags & F.IMPLODE && raw.length < b.usize) throw new Error(`${e.name}: PKWARE implode compression in this .otr isn’t supported`);
    return flags & F.COMPRESS ? unpackSector(raw, b.usize, e.name) : raw.subarray(0, b.usize);
  }
  const n = Math.ceil(b.usize / t.sector), tableLen = (n + 1 + (flags & F.CRC ? 1 : 0)) * 4;
  const table = readAt(fd, tableLen, b.pos);
  if (key) decrypt(table, (key - 1) >>> 0);
  const all = readAt(fd, b.csize, b.pos), out = [];
  for (let i = 0; i < n; i++) {
    const s = table.readUInt32LE(i * 4), en = table.readUInt32LE(i * 4 + 4);
    if (en < s || en > b.csize) throw new Error(`${e.name}: damaged sector table`);
    let sec = Buffer.from(all.subarray(s, en));
    if (key) decrypt(sec, (key + i) >>> 0);
    const full = Math.min(t.sector, b.usize - i * t.sector);
    out.push(flags & F.IMPLODE && !(flags & F.COMPRESS) && sec.length < full ? (() => { throw new Error(`${e.name}: PKWARE implode compression in this .otr isn’t supported`); })() : unpackSector(sec, full, e.name));
  }
  const data = Buffer.concat(out);
  if (data.length !== b.usize) throw new Error(`${e.name}: data is corrupt`);
  return data;
}

// Every named file: [{ name, usize, csize, mpq }], like rtz.readEntries for zips.
function readEntries(file) {
  const fd = fs.openSync(file, 'r');
  try {
    const t = openTables(fd);
    const li = t.find('(listfile)');
    if (li < 0) throw new Error('This .otr has no file list, so its files can’t be named.');
    const lb = t.block(li);
    const names = readFile(fd, t, { name: '(listfile)', mpq: lb }).toString('latin1').split(/[\r\n;]+/).map((s) => s.trim()).filter(Boolean);
    const out = [], seen = new Set();
    for (const raw of names) {
      const bi = t.find(raw);
      if (bi < 0 || seen.has(bi)) continue;
      const b = t.block(bi);
      if (!(b.flags & F.EXISTS) || b.flags & F.DELETE) continue;
      seen.add(bi);
      out.push({ name: raw.replace(/\\/g, '/'), usize: b.usize, csize: b.csize, mpq: { ...b, sector: t.sector } });
    }
    return out;
  } finally { fs.closeSync(fd); }
}

function readEntry(file, e, fd) {
  const own = fd === undefined;
  if (own) fd = fs.openSync(file, 'r');
  try { return readFile(fd, { sector: e.mpq.sector }, e); } finally { if (own) fs.closeSync(fd); }
}

module.exports = { isMpq, readEntries, readEntry, hash, _test: { decrypt, CRYPT } };
