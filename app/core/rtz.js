'use strict';
// .rtz texture packs: RT64's zip layout (texture_packer) with zstd / deflate / store, zip64 and the low-mip cache.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { parseHeader } = require('./dds');
const { Database, listFiles, databaseFromFiles, detectHashVersion, fwd, DATABASE, LOW_MIP_CACHE } = require('./rt64db');
const recomp = require('./recomp');

const STORE = 0, DEFLATE = 8, ZSTD = 93;
const ZSTD_LEVELS = { fast: 3, balanced: 12, max: 22 };

class Cancelled extends Error { constructor() { super('Cancelled'); this.cancelled = true; } }

// ------------------------------------------------------------ low-mip cache
const align = (v, a) => (v % a ? v + (a - (v % a)) : v);

function lowMipEntry(folder, rel) {
  const data = fs.readFileSync(path.join(folder, rel));
  const info = parseHeader(data.subarray(0, 148));
  if (!info || info.unsupported) return null;
  let start = 0;
  while (start < info.mips - 1) {
    if ((info.width >> start) * (info.height >> start) <= 96 * 96) break;
    start++;
  }
  let w = Math.max(info.width >> start, 1), h = Math.max(info.height >> start, 1);
  const count = info.mips - start;
  if (w % info.block || h % info.block) { w = Math.ceil(w / info.block) * info.block; h = Math.ceil(h / info.block) * info.block; }
  const sizes = [], pitches = [], aligned = [], rows = [];
  for (let i = 0; i < count; i++) {
    const mh = Math.max(h >> i, 1), pitch = info.rowPitch(start + i), ap = align(pitch, 256), rc = Math.ceil(mh / info.block);
    sizes.push(rc * ap); pitches.push(pitch); aligned.push(ap); rows.push(rc);
  }
  return { data, info, start, w, h, count, sizes, pitches, aligned, rows, pathBytes: Buffer.from(rel, 'utf8') };
}

function appendLowMips(chunks, state, e) {
  const push = (b) => { chunks.push(b); state.pos += b.length; };
  const head = Buffer.alloc(28);
  [0x434d4f4c, 3, e.w, e.h, e.info.dxgi, e.count, e.pathBytes.length].forEach((v, i) => head.writeUInt32LE(v, i * 4));
  push(head);
  const arr = (a) => { const b = Buffer.alloc(a.length * 4); a.forEach((v, i) => b.writeUInt32LE(v, i * 4)); return b; };
  push(arr(e.sizes)); push(arr(e.aligned)); push(e.pathBytes);
  const read = (off, n) => { const b = Buffer.alloc(n); e.data.copy(b, 0, Math.min(off, e.data.length), Math.min(off + n, e.data.length)); return b; };
  for (let i = 0; i < e.count; i++) {
    if (state.pos % 512) push(Buffer.alloc(512 - (state.pos % 512)));
    const base = e.info.headerSize + e.info.offset(e.start + i);
    if (e.aligned[i] > e.pitches[i]) {
      const pad = Buffer.alloc(e.aligned[i] - e.pitches[i]);
      for (let j = 0; j < e.rows[i]; j++) { push(read(base + j * e.pitches[i], e.pitches[i])); push(pad); }
    } else push(read(base, e.sizes[i]));
  }
}

// ------------------------------------------------------------ zip writer
function dosTime(ms) {
  const d = new Date(Math.max(ms, 315532800000));
  return [(d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()];
}

class ZipWriter {
  constructor(file, forceZip64 = false) { this.fd = fs.openSync(file, 'w'); this.pos = 0; this.entries = []; this.force = forceZip64; }
  write(b) { fs.writeSync(this.fd, b); this.pos += b.length; }
  add(name, payload, method, crc, size, mtime) {
    const nameB = Buffer.from(name, 'utf8');
    const flags = /[^\x00-\x7f]/.test(name) ? 0x800 : 0;
    const [t, d] = dosTime(mtime ?? Date.now());
    const offset = this.pos;
    const z64 = this.force || size >= 0xffffffff || payload.length >= 0xffffffff;
    const version = method === ZSTD ? 63 : (z64 ? 45 : 20);
    let extra = Buffer.alloc(0);
    if (z64) { extra = Buffer.alloc(20); extra.writeUInt16LE(1, 0); extra.writeUInt16LE(16, 2); extra.writeBigUInt64LE(BigInt(size), 4); extra.writeBigUInt64LE(BigInt(payload.length), 12); }
    const h = Buffer.alloc(30);
    h.writeUInt32LE(0x04034b50, 0); h.writeUInt16LE(version, 4); h.writeUInt16LE(flags, 6); h.writeUInt16LE(method, 8);
    h.writeUInt16LE(t, 10); h.writeUInt16LE(d, 12); h.writeUInt32LE(crc >>> 0, 14);
    h.writeUInt32LE(z64 ? 0xffffffff : payload.length, 18); h.writeUInt32LE(z64 ? 0xffffffff : size, 22);
    h.writeUInt16LE(nameB.length, 26); h.writeUInt16LE(extra.length, 28);
    this.write(h); this.write(nameB); this.write(extra); this.write(payload);
    this.entries.push({ nameB, flags, method, t, d, crc, csize: payload.length, usize: size, offset, version });
  }
  close() {
    const cdStart = this.pos;
    for (const e of this.entries) {
      const big = this.force;
      const fields = [];
      if (big || e.usize >= 0xffffffff) fields.push(e.usize);
      if (big || e.csize >= 0xffffffff) fields.push(e.csize);
      if (big || e.offset >= 0xffffffff) fields.push(e.offset);
      let extra = Buffer.alloc(0);
      if (fields.length) { extra = Buffer.alloc(4 + 8 * fields.length); extra.writeUInt16LE(1, 0); extra.writeUInt16LE(8 * fields.length, 2); fields.forEach((v, i) => extra.writeBigUInt64LE(BigInt(v), 4 + 8 * i)); }
      const c = Buffer.alloc(46);
      c.writeUInt32LE(0x02014b50, 0); c.writeUInt16LE((3 << 8) | e.version, 4); c.writeUInt16LE(e.version, 6); c.writeUInt16LE(e.flags, 8);
      c.writeUInt16LE(e.method, 10); c.writeUInt16LE(e.t, 12); c.writeUInt16LE(e.d, 14); c.writeUInt32LE(e.crc >>> 0, 16);
      c.writeUInt32LE(big || e.csize >= 0xffffffff ? 0xffffffff : e.csize, 20); c.writeUInt32LE(big || e.usize >= 0xffffffff ? 0xffffffff : e.usize, 24);
      c.writeUInt16LE(e.nameB.length, 28); c.writeUInt16LE(extra.length, 30); c.writeUInt32LE((0o100644 << 16) >>> 0, 38);
      c.writeUInt32LE(big || e.offset >= 0xffffffff ? 0xffffffff : e.offset, 42);
      this.write(c); this.write(e.nameB); this.write(extra);
    }
    const cdEnd = this.pos, n = this.entries.length, cdSize = cdEnd - cdStart;
    if (this.force || n >= 0xffff || cdStart >= 0xffffffff || cdSize >= 0xffffffff) {
      const z = Buffer.alloc(56);
      z.writeUInt32LE(0x06064b50, 0); z.writeBigUInt64LE(44n, 4); z.writeUInt16LE(45, 12); z.writeUInt16LE(45, 14);
      z.writeBigUInt64LE(BigInt(n), 24); z.writeBigUInt64LE(BigInt(n), 32); z.writeBigUInt64LE(BigInt(cdSize), 40); z.writeBigUInt64LE(BigInt(cdStart), 48);
      const l = Buffer.alloc(20);
      l.writeUInt32LE(0x07064b50, 0); l.writeBigUInt64LE(BigInt(cdEnd), 8); l.writeUInt32LE(1, 16);
      this.write(z); this.write(l);
    }
    const eocd = Buffer.alloc(22);
    eocd.writeUInt32LE(0x06054b50, 0); eocd.writeUInt16LE(Math.min(n, 0xffff), 8); eocd.writeUInt16LE(Math.min(n, 0xffff), 10);
    eocd.writeUInt32LE(Math.min(cdSize, 0xffffffff), 12); eocd.writeUInt32LE(Math.min(cdStart, 0xffffffff), 16);
    this.write(eocd);
    fs.closeSync(this.fd);
  }
  abort() { try { fs.closeSync(this.fd); } catch { /* already closed */ } }
}

function compress(data, compression, level) {
  let out, method;
  if (compression === 'zstd') {
    out = zlib.zstdCompressSync(data, { params: { [zlib.constants.ZSTD_c_compressionLevel]: level } });
    method = ZSTD;
  } else if (compression === 'deflate') {
    out = zlib.deflateRawSync(data, { level: Math.min(Math.max(level, 1), 9) });
    method = DEFLATE;
  } else return { payload: data, method: STORE };
  if (out.length >= data.length) return { payload: data, method: STORE };
  return { payload: out, method };
}

// ------------------------------------------------------------ packing
function prepareDatabase(folder, files) {
  const notes = [];
  if (fs.existsSync(path.join(folder, DATABASE))) return { db: Database.load(path.join(folder, DATABASE)), generated: false, notes };
  const version = detectHashVersion(files) || 5;
  const { db, skipped } = databaseFromFiles(files, version);
  if (skipped.length) notes.push(`${skipped.length} image(s) without an RT64 hash in the file name were left out (for example ${skipped[0]}).`);
  if (!db.textures.length) throw new Error('This folder has no rt64.json and no hash-named textures (<16 hex digits>.png / .dds).');
  notes.push(`No rt64.json found, so one was created for ${db.textures.length} hash-named texture(s).`);
  return { db, generated: true, notes };
}

const byteOrder = (a, b) => Buffer.compare(Buffer.from(a, 'utf8'), Buffer.from(b, 'utf8'));

// opts: { compression, level, lowMipCache, forceZip64, recomp: { name, author, version, description, game, thumb, toggle } | null,
//        progress(done,total,name), cancelled() }
function packFolder(folder, outFile, opts = {}) {
  const compression = opts.compression || 'zstd';
  const level = compression === 'zstd' ? (ZSTD_LEVELS[opts.level] ?? 12) : (opts.level === 'max' ? 9 : opts.level === 'fast' ? 1 : 6);
  const progress = opts.progress || (() => {});
  const cancelled = opts.cancelled || (() => false);
  const files = listFiles(folder).filter((f) => !/\.(rtz|part)$/i.test(f));
  const { db, generated, notes } = prepareDatabase(folder, files);
  const { resolved, missing } = db.resolvePaths(files);
  if (missing.length) notes.push(`${missing.length} texture(s) listed in rt64.json have no file and were skipped.`);
  for (const t of db.textures) { const r = resolved.get((t.hashes.rt64 || '').toLowerCase()); if (t.path && r) t.path = r.rel; }
  const textureFiles = [...new Set([...resolved.values()].map((r) => r.rel))].sort(byteOrder);

  let cache = null, cacheEntries = 0;
  if (opts.lowMipCache !== false) {
    const { resolved: dds } = db.resolvePaths(files, true);
    const stream = [...new Set([...dds.values()].filter((r) => r.operation === 'stream').map((r) => r.rel))].sort(byteOrder);
    if (stream.length) {
      const chunks = [], state = { pos: 0 };
      stream.forEach((rel, i) => {
        if (cancelled()) throw new Cancelled();
        const e = lowMipEntry(folder, rel);
        if (e) { appendLowMips(chunks, state, e); cacheEntries++; } else notes.push(`Low-mip cache skipped ${rel} (unsupported DDS format).`);
        if (i % 50 === 0) progress(0, 1, `Building low-mip cache (${i + 1}/${stream.length})`);
      });
      cache = Buffer.concat(chunks);
    }
  }
  const jobs = textureFiles.map((f) => ({ name: f, file: path.join(folder, f) }));
  for (const f of db.extraFiles) if (fs.existsSync(path.join(folder, f))) jobs.push({ name: fwd(f), file: path.join(folder, f), deflate: true });
  jobs.push({ name: DATABASE, data: Buffer.from(db.text()) });
  // Recomp mod info: a new mod.json (and picture) from the options, or the folder's own if it has them.
  let recompInfo = null;
  if (opts.recomp) {
    const m = recomp.manifest(opts.recomp);
    jobs.push({ name: recomp.MANIFEST, data: Buffer.from(JSON.stringify(m, null, 4) + '\n'), deflate: true });
    recompInfo = m;
    const thumb = opts.recomp.thumb;
    if (thumb) {
      const b = fs.existsSync(thumb) ? fs.readFileSync(thumb) : null;
      if (b && b.length > 8 && b[0] === 0x89 && b.toString('latin1', 1, 4) === 'PNG') jobs.push({ name: recomp.THUMB, data: b });
      else notes.push('The Recomp picture was left out: it must be a PNG file.');
    }
    notes.push(`Recomp mod info: “${m.display_name}” v${m.version} by ${m.authors.join(', ')}${m.config_schema ? ', with an on / off switch' : ''}.`);
  } else {
    for (const extra of [recomp.MANIFEST, recomp.THUMB, 'thumb.dds']) {
      if (fs.existsSync(path.join(folder, extra))) jobs.push({ name: extra, file: path.join(folder, extra), deflate: extra === recomp.MANIFEST });
    }
  }
  if (cache) jobs.push({ name: LOW_MIP_CACHE, data: cache });

  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  const part = outFile + '.part';
  const zip = new ZipWriter(part, opts.forceZip64);
  let bytesIn = 0;
  try {
    jobs.forEach((j, i) => {
      if (cancelled()) throw new Cancelled();
      const data = j.data || fs.readFileSync(j.file);
      const mtime = j.file ? fs.statSync(j.file).mtimeMs : Date.now();
      const comp = j.deflate && compression === 'zstd' ? 'deflate' : compression;
      const { payload, method } = compress(data, comp, comp === 'deflate' && compression === 'zstd' ? 9 : level);
      zip.add(j.name, payload, method, zlib.crc32(data), data.length, mtime);
      bytesIn += data.length;
      progress(i + 1, jobs.length, j.name);
    });
    zip.close();
    fs.renameSync(part, outFile);
  } catch (e) {
    zip.abort();
    fs.rmSync(part, { force: true });
    throw e;
  }
  return { file: outFile, textures: textureFiles.length, files: jobs.length, bytesIn, bytesOut: fs.statSync(outFile).size, cacheEntries, generated, notes, recomp: recompInfo };
}

// ------------------------------------------------------------ reading
function readEntries(file) {
  const fd = fs.openSync(file, 'r');
  try {
    const size = fs.fstatSync(fd).size;
    const tailLen = Math.min(size, 65557);
    const tail = Buffer.alloc(tailLen);
    fs.readSync(fd, tail, 0, tailLen, size - tailLen);
    let e = -1;
    for (let i = tailLen - 22; i >= 0; i--) if (tail.readUInt32LE(i) === 0x06054b50) { e = i; break; }
    if (e < 0) throw new Error('Not a zip / .rtz file');
    let count = tail.readUInt16LE(e + 10), cdSize = tail.readUInt32LE(e + 12), cdOff = tail.readUInt32LE(e + 16);
    if (e >= 20 && tail.readUInt32LE(e - 20) === 0x07064b50) {
      const z64Off = Number(tail.readBigUInt64LE(e - 20 + 8));
      const z = Buffer.alloc(56); fs.readSync(fd, z, 0, 56, z64Off);
      if (z.readUInt32LE(0) === 0x06064b50) { count = Number(z.readBigUInt64LE(32)); cdSize = Number(z.readBigUInt64LE(40)); cdOff = Number(z.readBigUInt64LE(48)); }
    }
    const cd = Buffer.alloc(cdSize); fs.readSync(fd, cd, 0, cdSize, cdOff);
    const entries = [];
    let p = 0;
    for (let i = 0; i < count; i++) {
      if (cd.readUInt32LE(p) !== 0x02014b50) throw new Error('Corrupt zip directory');
      const method = cd.readUInt16LE(p + 10), crc = cd.readUInt32LE(p + 16);
      let csize = cd.readUInt32LE(p + 20), usize = cd.readUInt32LE(p + 24);
      const nl = cd.readUInt16LE(p + 28), xl = cd.readUInt16LE(p + 30), cl = cd.readUInt16LE(p + 32);
      let offset = cd.readUInt32LE(p + 42);
      const name = cd.toString('utf8', p + 46, p + 46 + nl);
      let x = p + 46 + nl;
      const xEnd = x + xl;
      while (x + 4 <= xEnd) {
        const id = cd.readUInt16LE(x), len = cd.readUInt16LE(x + 2);
        if (id === 1) {
          let q = x + 4;
          if (usize === 0xffffffff) { usize = Number(cd.readBigUInt64LE(q)); q += 8; }
          if (csize === 0xffffffff) { csize = Number(cd.readBigUInt64LE(q)); q += 8; }
          if (offset === 0xffffffff) { offset = Number(cd.readBigUInt64LE(q)); q += 8; }
        }
        x += 4 + len;
      }
      p = xEnd + cl;
      if (!name.endsWith('/')) entries.push({ name, method, crc, csize, usize, offset });
    }
    return entries;
  } finally { fs.closeSync(fd); }
}

function readEntry(file, e, fd) {
  const own = fd === undefined;
  if (own) fd = fs.openSync(file, 'r');
  try {
    const h = Buffer.alloc(30); fs.readSync(fd, h, 0, 30, e.offset);
    if (h.readUInt32LE(0) !== 0x04034b50) throw new Error(e.name + ': bad local header');
    const raw = Buffer.alloc(e.csize);
    fs.readSync(fd, raw, 0, e.csize, e.offset + 30 + h.readUInt16LE(26) + h.readUInt16LE(28));
    let data;
    if (e.method === STORE) data = raw;
    else if (e.method === DEFLATE) data = zlib.inflateRawSync(raw);
    else if (e.method === ZSTD) data = zlib.zstdDecompressSync(raw);
    else throw new Error(`${e.name}: unsupported compression method ${e.method}`);
    if (data.length !== e.usize || (zlib.crc32(data) >>> 0) !== (e.crc >>> 0)) throw new Error(`${e.name}: data is corrupt`);
    return data;
  } finally { if (own) fs.closeSync(fd); }
}

function unpack(file, outFolder, { keepCache = false, progress = () => {}, cancelled = () => false } = {}) {
  const entries = readEntries(file).filter((e) => keepCache || e.name !== LOW_MIP_CACHE);
  const root = path.resolve(outFolder);
  fs.mkdirSync(root, { recursive: true });
  const fd = fs.openSync(file, 'r');
  try {
    entries.forEach((e, i) => {
      if (cancelled()) throw new Cancelled();
      const target = path.resolve(root, e.name);
      if (target !== root && !target.startsWith(root + path.sep)) throw new Error(`${e.name}: refuses to write outside the output folder`);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target + '.part', readEntry(file, e, fd));
      fs.renameSync(target + '.part', target);
      progress(i + 1, entries.length, e.name);
    });
  } finally { fs.closeSync(fd); }
  return entries.length;
}

function inspect(file) {
  const entries = readEntries(file);
  const names = entries.map((e) => e.name.toLowerCase());
  const methods = {};
  for (const e of entries) { const k = { 0: 'store', 8: 'deflate', 93: 'zstd' }[e.method] || String(e.method); methods[k] = (methods[k] || 0) + 1; }
  return {
    files: entries.length, textures: names.filter((n) => n.endsWith('.png') || n.endsWith('.dds')).length,
    dds: names.filter((n) => n.endsWith('.dds')).length, png: names.filter((n) => n.endsWith('.png')).length,
    size: entries.reduce((s, e) => s + e.usize, 0), methods, hasDatabase: names.includes(DATABASE), hasCache: names.includes(LOW_MIP_CACHE),
    hasRecomp: names.includes(recomp.MANIFEST),
  };
}

module.exports = { packFolder, unpack, inspect, readEntries, readEntry, Cancelled, ZSTD_LEVELS };
