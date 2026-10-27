'use strict';
// Step 4: Rice IDs, GLideN64 .hts / .htc, classic packs into RT64 / GLideN64 / Ship ports.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const rice = core('rice'), legacy = core('legacy'), o2r = core('o2r'), rtz = core('rtz'), png = core('png'), tasks = core('tasks');
const { Database } = core('rt64db');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64r-'));
const img = (w, h, fn) => { const d = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set(fn(x, y), (y * w + x) * 4); return { width: w, height: h, data: d }; };
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });

test('Rice formula gives the same results as RT64 texture_hasher’s own C++', () => {
  const ref = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'rice-reference.json'), 'utf8'));
  for (const c of ref.crc) {
    const buf = Buffer.from(c.bytes, 'hex');
    assert.equal(rice.riceCRC32(buf, c.width, c.height, c.size, c.stride), c.crc);
    assert.equal(rice._test.maxCI(buf, c.width, c.height, c.stride, true), c.max4);
    assert.equal(rice._test.maxCI(buf, c.width, c.height, c.stride, false), c.max8);
  }
  for (const [v, w, s, want] of ref.reverseDXT) assert.equal(rice._test.reverseDXT(v, w, s), want);
});

test('Rice names and IDs', () => {
  const r = rice.parseRiceName('THE LEGEND OF ZELDA#003334A1#3#0_all.png');
  assert.deepEqual([r.crc, r.fmt, r.siz, r.pal, r.kind], [0x003334a1, 3, 0, 0, 'all']);
  const c = rice.parseRiceName('GAME#1A2B3C4D#2#1#DEADBEEF_ciByRGBA.png');
  assert.equal(rice.riceId(c), '1a2b3c4d#2#1#deadbeef');
  assert.deepEqual(rice.parseRiceId('1A2B3C4D#2#1#DEADBEEF'), { crc: 0x1a2b3c4d, fmt: 2, siz: 1, pal: 0xdeadbeef });
  assert.equal(rice.parseRiceName('notes.png'), null);
});

// An RT64 dump texture with its Rice files (a "Tile" load of a 16x8 RGBA16 texture).
function dumpWithRice(dir, hash, { tlut = 'None' } = {}) {
  const rdram = Buffer.alloc(16 * 8 * 2); for (let i = 0; i < rdram.length; i++) rdram[i] = (i * 37 + hash.charCodeAt(0)) & 255;
  fs.writeFileSync(path.join(dir, `${hash}.v5.tmem`), Buffer.alloc(4096, 0x55));
  fs.writeFileSync(path.join(dir, `${hash}.v5.tile.json`), JSON.stringify({ width: 16, height: 8, tlut,
    tile: { fmt: 0, siz: 2, line: 4, tmem: 0, cms: 0, cmt: 0, masks: 4, maskt: 3, uls: 0, ult: 0, lrs: 60, lrt: 28 } }));
  fs.writeFileSync(path.join(dir, `${hash}.v5.rice.json`), JSON.stringify({ type: 'Tile',
    tile: { fmt: 0, siz: 2, uls: 0, ult: 0, lrs: 60, lrt: 28, masks: 0, maskt: 0 }, texture: { address: 0x80100000, fmt: 0, siz: 2, width: 16 } }));
  fs.writeFileSync(path.join(dir, `${hash}.v5.rice.rdram`), rdram);
  return rice.hex8(rice.riceCRC32(rdram, 16, 8, 2, 32)) + '#0#2';
}

test('Rice ID from an RT64 dump, and Convert writes it to rt64.json', async () => {
  const dump = tmpDir(), out = path.join(tmpDir(), 'conv');
  const want = dumpWithRice(dump, 'aaaaaaaaaaaaaaaa');
  assert.equal(rice.riceFromDump(path.join(dump, 'aaaaaaaaaaaaaaaa.v5.tmem')), want);
  const log = [];
  await tasks.convertTask({ input: dump, output: out, format: 'png', rice: true }, quietCtx(log), {});
  const db = Database.load(path.join(out, 'rt64.json'));
  assert.equal(db.textures[0].hashes.rice, want);
  assert.ok(log.some((l) => /Added Rice IDs for 1/.test(l)));
});

test('GLideN64 .hts: write then read back keys, format / size and pixels', () => {
  const file = path.join(tmpDir(), 'GAME_HIRESTEXTURES.hts');
  const a = img(8, 4, (x, y) => [x * 30, y * 60, 77, 255]), b = img(4, 4, () => [1, 2, 3, 128]);
  rice.writeHts([{ crc: 0x11223344, pal: 0, fmt: 0, siz: 2, img: a }, { crc: 0xaabbccdd, pal: 0x01020304, fmt: 2, siz: 1, img: () => b }], file);
  const raw = fs.readFileSync(file);
  assert.equal(raw.readInt32LE(0), rice.VERSION);
  const list = rice.readGlidenPack(file).sort((x, y) => x.crc - y.crc);
  assert.deepEqual(list.map((e) => [e.crc, e.pal, e.fmt, e.siz, e.w, e.h]), [[0x11223344, 0, 0, 2, 8, 4], [0xaabbccdd, 0x01020304, 2, 1, 4, 4]]);
  assert.deepEqual(Buffer.from(list[0].load().data), Buffer.from(a.data));
  assert.deepEqual(Buffer.from(list[1].load().data), Buffer.from(b.data));
});

test('GLideN64 .htc (gzip cache) is read too', () => {
  const file = path.join(tmpDir(), 'GAME_HIRESTEXTURES.htc');
  const px = Buffer.from(img(2, 2, () => [9, 8, 7, 255]).data);
  const body = zlib.deflateSync(px);
  const rec = Buffer.alloc(8 + 23);
  rec.writeBigUInt64LE(0x0000000055667788n, 0);
  rec.writeUInt32LE(2, 8); rec.writeUInt32LE(2, 12); rec.writeUInt32LE((0x8058 | 0x80000000) >>> 0, 16); rec.writeUInt16LE(0x1908, 20); rec.writeUInt16LE(0x1401, 22);
  rec[24] = 1; rec[25] = 4; rec[26] = 1; rec.writeUInt32LE(body.length, 27);
  const head = Buffer.alloc(8); head.writeInt32LE(rice.VERSION, 0); head.writeInt32LE(rice.CONFIG, 4);
  fs.writeFileSync(file, zlib.gzipSync(Buffer.concat([head, rec, body])));
  const [e] = rice.readGlidenPack(file);
  assert.deepEqual([e.crc, e.fmt, e.siz, e.w], [0x55667788, 4, 1, 2]);
  assert.deepEqual(Buffer.from(e.load().data), px);
});

test('Use in RT64: a Rice pack matched through the converted dump', async () => {
  const dump = tmpDir(), conv = path.join(tmpDir(), 'conv'), pack = tmpDir(), out = path.join(tmpDir(), 'imported');
  const idA = dumpWithRice(dump, 'aaaaaaaaaaaaaaaa'), idB = dumpWithRice(dump, 'bbbbbbbbbbbbbbbb');
  await tasks.convertTask({ input: dump, output: conv, format: 'png', rice: true }, quietCtx(), {});
  const name = (id) => `GAME#${id.split('#')[0].toUpperCase()}#0#2_all.png`;
  fs.writeFileSync(path.join(pack, name(idA)), png.encodePNG(img(64, 32, () => [255, 0, 0, 255])));
  fs.writeFileSync(path.join(pack, name(idB)), png.encodePNG(img(64, 32, () => [0, 0, 255, 255])));
  fs.writeFileSync(path.join(pack, 'GAME#99999999#0#2_all.png'), png.encodePNG(img(8, 8, () => [0, 0, 0, 255])));  // not in the dump
  const log = [];
  const r = await tasks.legacyImportTask({ input: pack, dumpDb: conv, output: out }, quietCtx(log));
  assert.equal(r.written, 2);
  assert.ok(log.some((l) => /2 of the pack’s 3 textures match/.test(l)));
  const db = Database.load(path.join(out, 'rt64.json'));
  assert.deepEqual(db.textures.map((t) => t.path).sort(), ['textures/aaaaaaaaaaaaaaaa.png', 'textures/bbbbbbbbbbbbbbbb.png']);
  assert.equal(png.decodePNG(fs.readFileSync(path.join(out, 'textures/aaaaaaaaaaaaaaaa.png'))).width, 64);
  // ...and it packs into an .rtz like any other folder.
  assert.equal(rtz.packFolder(out, path.join(tmpDir(), 'p.rtz'), { compression: 'store' }).textures, 2);
});

test('Make GLideN64 pack from a folder with Rice IDs in rt64.json', async () => {
  const dump = tmpDir(), conv = path.join(tmpDir(), 'conv');
  const idA = dumpWithRice(dump, 'aaaaaaaaaaaaaaaa');
  await tasks.convertTask({ input: dump, output: conv, format: 'png', rice: true }, quietCtx(), {});
  const out = path.join(tmpDir(), 'ZELDA MAJORA\'S MASK_HIRESTEXTURES.hts');
  const r = await tasks.legacyHtsTask({ input: conv, name: 'ZELDA MAJORA\'S MASK', output: out }, quietCtx());
  assert.equal(r.written, 1);
  const [e] = rice.readGlidenPack(out);
  assert.equal(rice.riceId(e), idA);
  await assert.rejects(tasks.legacyHtsTask({ input: conv, name: '' }, quietCtx()), /game name/);
});

test('Use in a Ship port: Rice pack matched to .o2r textures by Rice ID', async () => {
  const arcFile = path.join(tmpDir(), 'mm.o2r');
  const zip = new rtz.ZipWriter(arcFile);
  const tex = img(16, 16, (x, y) => [x * 16, y * 16, 0, 255]);
  const data = o2r.encodePixels(tex, 2);
  const res = o2r.resource({ type: 2, width: 16, height: 16, data });
  for (const name of ['objects/a/gTexA', 'objects/b/gSameTexB']) zip.add(name, res, 0, zlib.crc32(res), res.length, Date.now());
  zip.close();
  const r = rice.riceForTexture({ type: 2, width: 16, height: 16, data });
  assert.equal(r.crc, rice.riceCRC32(data, 16, 16, 2, 32, true));
  const pack = tmpDir();
  fs.writeFileSync(path.join(pack, `MM#${rice.hex8(r.crc).toUpperCase()}#0#2_all.png`), png.encodePNG(img(64, 64, () => [5, 200, 5, 255])));
  const mod = path.join(tmpDir(), 'Celda.o2r');
  const log = [];
  const b = await tasks.riceToO2rTask({ input: pack, base: arcFile, output: mod, alt: true }, quietCtx(log));
  assert.equal(b.written, 2, 'both archive textures with that data are replaced');
  const names = rtz.readEntries(mod).map((e) => e.name).sort();
  assert.deepEqual(names, ['alt/objects/a/gTexA', 'alt/objects/b/gSameTexB']);
  const t = o2r.parseTexture(rtz.readEntry(mod, rtz.readEntries(mod)[0]));
  assert.deepEqual([t.width, t.hScale, t.vScale, t.flags], [64, 8, 4, 1]);
});
