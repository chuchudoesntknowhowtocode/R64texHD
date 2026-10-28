'use strict';
// Step 3: Ship port archives (.o2r) - read, Extract Textures, Create HD Texture Pack.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const o2r = core('o2r'), rtz = core('rtz'), png = core('png'), tasks = core('tasks');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64o-'));
const img = (w, h, fn) => { const d = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set(fn(x, y), (y * w + x) * 4); return { width: w, height: h, data: d }; };
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });

// A small game archive: RGBA16, CI4, I8, IA8 and IA4 textures, plus a non-texture resource and a plain file.
const RGBA16 = img(16, 16, (x, y) => [(x * 16) & 0xf8, (y * 16) & 0xf8, 0x80, x < 12 ? 255 : 0]);
function gameArchive(file) {
  const zip = new rtz.ZipWriter(file);
  const add = (name, buf) => zip.add(name, zlib.deflateRawSync(buf), 8, zlib.crc32(buf), buf.length, Date.now());
  add('objects/gameplay_keep/gBrickTex', o2r.resource({ type: 2, width: 16, height: 16, data: o2r.encodePixels(RGBA16, 2) }));
  add('objects/gameplay_keep/gGrassCITex', o2r.resource({ type: 3, width: 8, height: 8, data: Buffer.alloc(32, 0x1f) }));
  add('textures/skybox/gCloudsTex', o2r.resource({ type: 6, width: 8, height: 4, data: Buffer.from([...Array(32).keys()].map((i) => i * 8)) }));
  add('textures/nes_font_static/gMsgCharA', o2r.resource({ type: 8, width: 8, height: 8, data: Buffer.alloc(64, 0xf8) }));
  add('textures/icons/gArrowTex', o2r.resource({ type: 7, width: 4, height: 2, data: Buffer.from([0xff, 0x0e, 0xe0, 0x11]) }));
  const blob = Buffer.alloc(80); blob.writeUInt32LE(0x4f424c42, 4);            // 'OBLB': not a texture
  add('scenes/test/gSceneBlob', blob);
  add('version', Buffer.from('1.0'));
  zip.close();
  return file;
}

test('reads every texture in an .o2r and skips other resources', () => {
  const arc = gameArchive(path.join(tmpDir(), 'mm.o2r'));
  const list = o2r.listTextures(arc);
  assert.deepEqual(list.map((t) => `${t.name} ${o2r.TYPES[t.type].name} ${t.width}x${t.height}`).sort(), [
    'objects/gameplay_keep/gBrickTex RGBA16 16x16', 'objects/gameplay_keep/gGrassCITex CI4 8x8',
    'textures/icons/gArrowTex IA4 4x2', 'textures/nes_font_static/gMsgCharA IA8 8x8', 'textures/skybox/gCloudsTex I8 8x4']);
  assert.equal(o2r.gameOf(arc), '2 Ship 2 Harkinian');
});

test('RGBA16 decode / encode round trip is exact', () => {
  const t = o2r.parseTexture(o2r.resource({ type: 2, width: 16, height: 16, data: o2r.encodePixels(RGBA16, 2) }));
  const back = o2r.decodeTexture(t);
  for (let i = 0; i < 16 * 16; i++) {
    assert.equal(back.data[i * 4 + 3], RGBA16.data[i * 4 + 3]);
    if (RGBA16.data[i * 4 + 3]) assert.equal(back.data[i * 4] >> 3, RGBA16.data[i * 4] >> 3);
  }
});

test('IA4 / IA8 / I8 decode', () => {
  const ia4 = o2r.decodeTexture(o2r.parseTexture(o2r.resource({ type: 7, width: 2, height: 1, data: Buffer.from([0xf0]) })));
  assert.deepEqual([...ia4.data], [255, 255, 255, 255, 0, 0, 0, 0]);
  const ia8 = o2r.decodeTexture(o2r.parseTexture(o2r.resource({ type: 8, width: 1, height: 1, data: Buffer.from([0xf8]) })));
  assert.deepEqual([...ia8.data], [255, 255, 255, 136]);
});

test('Extract Textures: PNGs in the same folders, plus the texture list', () => {
  const arc = gameArchive(path.join(tmpDir(), 'mm.o2r')), out = tmpDir();
  const r = o2r.extract(arc, out);
  assert.equal(r.textures, 5); assert.equal(r.written, 5); assert.equal(r.palette, 1);
  const brick = png.decodePNG(fs.readFileSync(path.join(out, 'objects/gameplay_keep/gBrickTex.png')));
  assert.equal(brick.width, 16);
  const info = JSON.parse(fs.readFileSync(path.join(out, o2r.INFO_FILE), 'utf8'));
  assert.ok(info.textures.find((t) => t.path.endsWith('gGrassCITex')).palette);
});

test('Create HD Texture Pack: RGBA32 raw at a whole multiple, Retro scales, alt/ paths', () => {
  const arc = gameArchive(path.join(tmpDir(), 'mm.o2r')), hd = tmpDir(), mod = path.join(tmpDir(), 'mods', 'HD.o2r');
  const put = (rel, im) => { fs.mkdirSync(path.dirname(path.join(hd, rel)), { recursive: true }); fs.writeFileSync(path.join(hd, rel), png.encodePNG(im)); };
  put('objects/gameplay_keep/gBrickTex.png', img(64, 64, () => [200, 100, 50, 255]));       // 4x RGBA16
  put('objects/gameplay_keep/gGrassCITex.png', img(32, 32, () => [10, 200, 10, 255]));       // 4x CI4
  put('textures/skybox/gCloudsTex.png', img(8, 4, () => [128, 128, 128, 255]));              // same size I8
  put('textures/nes_font_static/gMsgCharA.png', img(30, 30, () => [255, 255, 255, 200]));    // not a whole multiple
  put('textures/not_in_game.png', img(8, 8, () => [0, 0, 0, 255]));
  const r = o2r.build(hd, arc, mod, { alt: true });
  assert.equal(r.written, 4);
  assert.deepEqual(r.unmatched, ['textures/not_in_game.png']);
  assert.equal(r.resized.length, 1);
  const entries = rtz.readEntries(mod);
  assert.ok(entries.every((e) => e.name.startsWith('alt/')));
  const get = (name) => o2r.parseTexture(rtz.readEntry(mod, entries.find((e) => e.name === 'alt/' + name)));

  const brick = get('objects/gameplay_keep/gBrickTex');
  assert.equal(brick.version, 1); assert.equal(brick.type, 1); assert.equal(brick.flags, o2r.LOAD_AS_RAW);
  assert.equal(brick.width, 64); assert.equal(brick.height, 64);
  assert.equal(brick.hScale, 4 * (4 / 2)); assert.equal(brick.vScale, 4);
  assert.equal(brick.size, 64 * 64 * 4);

  const ci = get('objects/gameplay_keep/gGrassCITex');
  assert.equal(ci.type, 1); assert.equal(ci.hScale, 4 * (4 / 0.5)); assert.equal(ci.vScale, 4);

  const sky = get('textures/skybox/gCloudsTex');
  assert.equal(sky.type, 6); assert.equal(sky.version, 0); assert.equal(sky.width, 8);

  const font = get('textures/nes_font_static/gMsgCharA');
  assert.equal(font.width, 32); assert.equal(font.height, 32, 'fitted to 4x of 8x8');
});

test('Build without the switch writes the original paths; the game archive is never changed', () => {
  const arc = gameArchive(path.join(tmpDir(), 'mm.o2r')), hd = tmpDir(), mod = path.join(tmpDir(), 'HD.o2r');
  const before = fs.readFileSync(arc);
  fs.mkdirSync(path.join(hd, 'objects/gameplay_keep'), { recursive: true });
  fs.writeFileSync(path.join(hd, 'objects/gameplay_keep/gBrickTex.png'), png.encodePNG(img(32, 32, () => [1, 2, 3, 255])));
  o2r.build(hd, arc, mod, { alt: false, compression: 'deflate' });
  assert.deepEqual(rtz.readEntries(mod).map((e) => e.name), ['objects/gameplay_keep/gBrickTex']);
  assert.deepEqual(fs.readFileSync(arc), before);
});

test('older MPQ .otr archives get a clear message', () => {
  const f = path.join(tmpDir(), 'oot.otr');
  fs.writeFileSync(f, Buffer.concat([Buffer.from('MPQ\x1a', 'latin1'), Buffer.alloc(64)]));
  assert.throws(() => o2r.listTextures(f), /older \.otr archive/);
});

test('whole flow through the app tasks: Extract Textures -> Upscale (PNG) -> Create HD Texture Pack', async () => {
  const arc = gameArchive(path.join(tmpDir(), 'mm.o2r')), got = path.join(tmpDir(), 'mm-textures'), up = path.join(tmpDir(), 'up'), mod = path.join(tmpDir(), 'Majora HD.o2r');
  const g = await tasks.o2rExtractTask({ archive: arc, output: got }, quietCtx());
  assert.equal(g.written, 5); assert.ok(g.upscalable);
  const u = await tasks.upscaleTask({ inputs: [got], output: up, size: 4, method: 'standard', sharpness: 'normal', edges: 'auto', format: 'png', hardAlpha: true }, quietCtx(), {});
  assert.equal(u.written, 5); assert.ok(u.fromO2r, 'Upscale knows these came from a Ship archive');
  const log = [];
  const b = await tasks.o2rBuildTask({ input: up, base: arc, output: mod, alt: true }, quietCtx(log));
  assert.equal(b.written, 5);
  assert.ok(log.some((l) => /mods folder/.test(l)));
  await assert.rejects(tasks.o2rBuildTask({ input: up, base: arc, output: arc }, quietCtx()), /not over the game archive/);
});
