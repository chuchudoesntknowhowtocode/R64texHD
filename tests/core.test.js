'use strict';
// Core tests: run with `node --test tests/` (Node 22.15 or newer, same as Electron 38's Node).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const png = core('png'), dds = core('dds'), rtz = core('rtz'), tiling = core('tiling'), tasks = core('tasks');
const { Database } = core('rt64db');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64t-'));
const img = (w, h, fn) => { const d = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set(fn(x, y), (y * w + x) * 4); return { width: w, height: h, data: d }; };
const fence = (n = 256) => img(n, n, (x, y) => [40, 160, 40, (x % 8 < 2 || y % 8 < 2) ? 255 : 0]);
const coverageOf = (l) => { let c = 0; for (let i = 3; i < l.data.length; i += 4) if (l.data[i] >= 128) c++; return c / (l.width * l.height); };
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });

// ---------------------------------------------------------------- image formats
test('PNG round trip keeps every pixel', () => {
  const a = img(13, 7, (x, y) => [x * 19, y * 33, (x + y) * 7, 255 - x]);
  const b = png.decodePNG(png.encodePNG(a));
  assert.equal(b.width, 13); assert.equal(b.height, 7);
  assert.deepEqual(Buffer.from(b.data), Buffer.from(a.data));
});

test('DDS BC1 / BC3 / uncompressed decode close to the original', () => {
  // A smooth gradient, like most real textures; BC3 also carries a cut-out alpha.
  const a = img(16, 16, (x, y) => [x * 16, x * 12 + 20, 200 - x * 8, y < 8 ? 255 : 0]);
  for (const f of ['bc1', 'bc3', 'rgba8']) {
    const b = dds.decodeDDS(dds.encodeDDS(a, f, { mipmaps: true }));
    assert.equal(b.width, 16);
    let err = 0, n = 0;
    for (let i = 0; i < a.data.length; i += 4) if (a.data[i + 3] === 255) { for (let c = 0; c < 3; c++) err += Math.abs(a.data[i + c] - b.data[i + c]); n += 3; }
    assert.ok(err / n < 6, `${f} average error ${err / n}`);
    if (f !== 'bc1') assert.equal(b.data[15 * 64 + 3], 0, `${f} keeps the see-through half`);
  }
});

// ---------------------------------------------------------------- mipmaps
test('fences far away: coverage is kept in every mip level', () => {
  const plain = dds.mipChain(fence(), { keepCoverage: false });
  const kept = dds.mipChain(fence(), { keepCoverage: true });
  assert.equal(coverageOf(plain[3]), 0, 'without the fix the fence vanishes by the 4th level');
  for (const l of kept.slice(1)) assert.ok(coverageOf(l) >= coverageOf(kept[0]) - 0.02, `level ${l.width}px coverage ${coverageOf(l)}`);
});

test('keep coverage leaves soft-alpha textures (smoke, glass) alone', () => {
  const smoke = img(64, 64, (x, y) => [200, 200, 200, Math.round((x / 63) * 255)]);
  assert.equal(dds.isCutout(smoke), false);
  const a = dds.mipChain(smoke, { keepCoverage: true }), b = dds.mipChain(smoke, { keepCoverage: false });
  assert.deepEqual(Buffer.from(a[2].data), Buffer.from(b[2].data));
});

test('odd-sized mipmaps keep the last row and column', () => {
  const chain = dds.mipChain(img(5, 3, () => [255, 255, 255, 255]));
  assert.deepEqual(chain.map((l) => `${l.width}x${l.height}`), ['5x3', '2x1', '1x1']);
  const row = dds.mipChain(img(3, 1, (x) => [[0, 128, 255][x], 0, 0, 255]))[1];
  assert.equal(row.data[0], 128, 'all three pixels are averaged');
});

// ---------------------------------------------------------------- RT64 tiling (Edges: Auto)
test('tile.json wrap modes: mask 0 or clamp bit = clamp, mirror bit = mirror, else wrap', () => {
  const dir = tmpDir();
  const make = (name, tile) => {
    fs.writeFileSync(path.join(dir, `${name}.v5.tmem`), Buffer.alloc(4096));
    fs.writeFileSync(path.join(dir, `${name}.v5.tile.json`), JSON.stringify({ width: 4, height: 4, tlut: 'None', tile: { fmt: 0, siz: 2, line: 1, ...tile } }));
    return core('tmem').loadDump(path.join(dir, `${name}.v5.tmem`)).edges;
  };
  assert.deepEqual(make('0000000000000001', { cms: 0, cmt: 0, masks: 2, maskt: 2 }), ['wrap', 'wrap']);
  assert.deepEqual(make('0000000000000002', { cms: 1, cmt: 2, masks: 2, maskt: 2 }), ['mirror', 'clamp']);
  assert.deepEqual(make('0000000000000003', { cms: 0, cmt: 0, masks: 0, maskt: 0 }), ['clamp', 'clamp']);
});

test('tiling file: saved, found from a subfolder, and used by Edges: Auto', () => {
  const dir = tmpDir();
  tiling.save(dir, new Map([['0123456789abcdef', ['wrap', 'mirror']]]));
  const map = tiling.loadFor([path.join(dir, 'textures')].map((p) => (fs.mkdirSync(p, { recursive: true }), p)));
  assert.deepEqual(tiling.edgesFor('textures/0123456789ABCDEF.png', 'auto', map), ['wrap', 'mirror']);
  assert.deepEqual(tiling.edgesFor('textures/ffffffffffffffff.png', 'auto', map), ['clamp', 'clamp']);
  assert.deepEqual(tiling.edgesFor('anything.png', 'wrap', map), ['wrap', 'wrap']);
});

// A tiny RT64 dump: two RGBA16 4x4 textures, one repeating and one not.
function fakeDump(dir) {
  const tmem = Buffer.alloc(4096);
  for (let i = 0; i < 32; i += 2) tmem.writeUInt16BE(0xf801 | (i << 5), i);
  const write = (hash, tile) => {
    fs.writeFileSync(path.join(dir, `${hash}.v5.tmem`), tmem);
    fs.writeFileSync(path.join(dir, `${hash}.v5.tile.json`), JSON.stringify({ width: 4, height: 4, tlut: 'None', tile: { fmt: 0, siz: 2, line: 1, tmem: 0, ...tile } }));
  };
  write('aaaaaaaaaaaaaaaa', { cms: 0, cmt: 0, masks: 2, maskt: 2 });
  write('bbbbbbbbbbbbbbbb', { cms: 2, cmt: 2, masks: 0, maskt: 0 });
}

test('Convert writes rt64.json and the tiling file; Only new skips done textures', async () => {
  const dump = tmpDir(), out = path.join(tmpDir(), 'out');
  fakeDump(dump);
  const r1 = await tasks.convertTask({ input: dump, output: out, format: 'png', wrapInfo: true }, quietCtx(), {});
  assert.equal(r1.written, 2);
  const db = Database.load(path.join(out, 'rt64.json'));
  assert.equal(db.textures.length, 2);
  const t = tiling.load(path.join(out, tiling.TILING));
  assert.deepEqual(t.get('aaaaaaaaaaaaaaaa'), ['wrap', 'wrap']);
  assert.deepEqual(t.get('bbbbbbbbbbbbbbbb'), ['clamp', 'clamp']);

  const log = [];
  const r2 = await tasks.convertTask({ input: dump, output: out, format: 'png', wrapInfo: true, onlyNew: true }, quietCtx(log), {});
  assert.equal(r2.written, 0);
  assert.ok(log.some((l) => /already converted/.test(l)));
  assert.equal(Database.load(path.join(out, 'rt64.json')).textures.length, 2, 'rt64.json still lists both');
});

test('Upscale with Edges: Auto uses the dump tiling', async () => {
  const dump = tmpDir(), conv = path.join(tmpDir(), 'conv'), up = path.join(tmpDir(), 'up');
  fakeDump(dump);
  await tasks.convertTask({ input: dump, output: conv, format: 'png', wrapInfo: true }, quietCtx(), {});
  const log = [];
  const r = await tasks.upscaleTask({ inputs: [path.join(conv, 'textures')], output: up, size: 2, method: 'standard', sharpness: 'normal',
    edges: 'auto', format: 'same', hardAlpha: true, keepCoverage: true }, quietCtx(log), {});
  assert.equal(r.written, 2);
  assert.ok(log.some((l) => /tiling known for 2 of 2/.test(l)), log.join('\n'));
  const p = await tasks.preview({ src: path.join(conv, 'textures', 'aaaaaaaaaaaaaaaa.png'), edges: 'auto', size: 2, method: 'standard', format: 'png' }, {});
  await tasks.closePreview();
  assert.equal(p.edges, 'tile × tile (from dump)');
});

// ---------------------------------------------------------------- .rtz packs
test('.rtz pack and unpack round trip (zstd, rt64.json, low-mip cache)', () => {
  const src = tmpDir(), out = path.join(tmpDir(), 'pack.rtz'), back = tmpDir();
  fs.mkdirSync(path.join(src, 'textures'));
  fs.writeFileSync(path.join(src, 'textures', '0123456789abcdef.dds'), dds.encodeDDS(fence(128), 'bc3', { keepCoverage: true }));
  fs.writeFileSync(path.join(src, 'textures', 'fedcba9876543210.png'), png.encodePNG(fence(16)));
  tiling.save(src, new Map([['0123456789abcdef', ['wrap', 'wrap']]]));
  const r = rtz.packFolder(src, out, { compression: 'zstd', level: 'fast', lowMipCache: true });
  assert.equal(r.textures, 2); assert.equal(r.cacheEntries, 1);
  const info = rtz.inspect(out);
  assert.ok(info.hasDatabase && info.hasCache);
  assert.equal(rtz.readEntries(out).some((e) => e.name === tiling.TILING), false, 'tiling file stays out of packs');
  rtz.unpack(out, back, {});
  assert.deepEqual(fs.readFileSync(path.join(back, 'textures', '0123456789abcdef.dds')), fs.readFileSync(path.join(src, 'textures', '0123456789abcdef.dds')));
});

test('.rtz unpack refuses paths that escape the output folder', () => {
  const zip = path.join(tmpDir(), 'evil.rtz');
  // A minimal stored zip with one entry named ../evil.txt
  const name = Buffer.from('../evil.txt'), data = Buffer.from('x'), crc = require('zlib').crc32(data) >>> 0;
  const lh = Buffer.alloc(30); lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt32LE(crc, 14); lh.writeUInt32LE(1, 18); lh.writeUInt32LE(1, 22); lh.writeUInt16LE(name.length, 26);
  const cd = Buffer.alloc(46); cd.writeUInt32LE(0x02014b50, 0); cd.writeUInt16LE(20, 4); cd.writeUInt16LE(20, 6); cd.writeUInt32LE(crc, 16); cd.writeUInt32LE(1, 20); cd.writeUInt32LE(1, 24); cd.writeUInt16LE(name.length, 28);
  const cdOff = 30 + name.length + 1;
  const eo = Buffer.alloc(22); eo.writeUInt32LE(0x06054b50, 0); eo.writeUInt16LE(1, 8); eo.writeUInt16LE(1, 10); eo.writeUInt32LE(46 + name.length, 12); eo.writeUInt32LE(cdOff, 16);
  fs.writeFileSync(zip, Buffer.concat([lh, name, data, cd, name, eo]));
  assert.throws(() => rtz.unpack(zip, tmpDir(), {}), /outside the output folder/);
});

// ---------------------------------------------------------------- AI options
test('Real-ESRGAN gets the chosen graphics card and memory use', () => {
  assert.deepEqual(tasks.aiArgs('i', 'o', { realesrganModel: 'realesr-animevideov3', aiGpu: '1', aiTile: '128' }),
    ['-i', 'i', '-o', 'o', '-n', 'realesr-animevideov3', '-s', '4', '-f', 'png', '-g', '1', '-t', '128']);
  assert.deepEqual(tasks.aiArgs('i', 'o', { aiGpu: 'auto', aiTile: 'auto' }).slice(-2), ['-f', 'png']);
});

// ---------------------------------------------------------------- Make an HD Pack (Welcome)
test('Make an HD Pack: dump -> convert -> upscale -> .rtz in one job, then only the new textures', async () => {
  const dump = tmpDir(), out = path.join(tmpDir(), 'majora-hd.rtz');
  fakeDump(dump);
  const log = [], steps = [];
  const ctx = { ...quietCtx(log), progress: (d, t, m) => steps.push([d, t, m]) };
  const r = await tasks.pipelineTask({ input: dump, output: out, method: 'standard', size: 2, sharpness: 'normal', edges: 'auto', hardAlpha: true,
    format: 'dds', ddsFormat: 'auto', keepCoverage: true, recomp: false, keep: true, maxSize: 4096 }, ctx, {});
  assert.equal(r.written, 2);
  assert.ok(fs.existsSync(out));
  assert.ok(fs.existsSync(out.replace(/\.rtz$/, '-textures')) && fs.existsSync(out.replace(/\.rtz$/, '-upscaled')));
  assert.ok(log.some((l) => /^1\/3 Convert:/.test(l)) && log.some((l) => /^2\/3 Upscale:/.test(l)) && log.some((l) => /^3\/3 Pack:/.test(l)), log.join('\n'));
  assert.ok(steps.every(([, t]) => t === 1000) && steps.some(([, , m]) => /Step 2 of 3 · Upscale/.test(m)));
  const back = tmpDir(); rtz.unpack(out, back, {});
  assert.equal(fs.readdirSync(path.join(back, 'textures')).filter((f) => f.endsWith('.dds')).length, 2);
  // again, with nothing new: convert skips both, upscale skips both, the pack is rebuilt
  const log2 = [];
  const r2 = await tasks.pipelineTask({ input: dump, output: out, method: 'standard', size: 2, sharpness: 'normal', format: 'dds', ddsFormat: 'auto', keep: false, maxSize: 4096 }, quietCtx(log2), {});
  assert.equal(r2.written, 2);
  assert.ok(log2.some((l) => /Nothing new to convert/.test(l)) && log2.some((l) => /Skipping 2 image/.test(l)), log2.join('\n'));
  assert.ok(!fs.existsSync(out.replace(/\.rtz$/, '-textures')), 'keep: false removes the in-between folders');
});

test('Watch mode: converts (and upscales) dumps as they arrive, repacks when stopped', async () => {
  const dump = tmpDir(), out = path.join(tmpDir(), 'conv'), pack = path.join(tmpDir(), 'live.rtz');
  fakeDump(dump);
  const extra = tmpDir(); fakeDump(extra);                      // the same two dumps, renamed below to look new
  const log = []; let stop = false;
  const ctx = { workers: 2, cancelled: () => stop, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} };
  const run = tasks.watchTask({ input: dump, output: out, mode: 'upscale', intervalMs: 300, repack: true, packOutput: pack, presetName: 'HD 4×', maxSize: 4096,
    upscale: { method: 'standard', size: 2, sharpness: 'normal', edges: 'auto', hardAlpha: true, format: 'png' } }, ctx, {});
  await new Promise((r) => setTimeout(r, 900));
  assert.ok(log.some((l) => /Started watching/.test(l)), log.join('\n'));
  for (const f of fs.readdirSync(extra)) fs.copyFileSync(path.join(extra, f), path.join(dump, f.replace(/^aaaa/, 'cccc').replace(/^bbbb/, 'dddd')));
  for (let i = 0; i < 60 && !log.some((l) => /\+2 /.test(l)); i++) await new Promise((r) => setTimeout(r, 200));
  stop = true;
  const r = await run;
  assert.ok(log.some((l) => /\+2 .*→ upscaled \(HD 4×\)/.test(l)), log.join('\n'));
  assert.equal(r.written, 2);
  assert.ok(fs.existsSync(pack) && /Watched/.test(r.title));
  assert.equal(fs.readdirSync(path.join(out + '-upscaled', 'textures')).length, 4);
  assert.equal(Database.load(path.join(out + '-upscaled', 'rt64.json')).textures.length, 4);
});
