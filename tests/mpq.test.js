'use strict';
// Older Ship port archives (.otr, MPQ): read, identify, extract, and use as the base for a pack.
// tests/fixtures/oot-test.otr was made by StormLib the way Torch / Shipwright made .otr files
// (MPQ v2, listfile, zlib sectors): three textures (one over a sector) and an OoT version file.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const mpq = core('mpq'), o2r = core('o2r'), shipid = core('shipid'), tasks = core('tasks'), rtz = core('rtz'), png = core('png');
const OTR = path.join(__dirname, 'fixtures', 'oot-test.otr');
const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64m-'));
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });

test('MPQ hashing matches the known table keys', () => {
  assert.equal(mpq.hash('(hash table)', 3), 0xc3af3770);
  assert.equal(mpq.hash('(block table)', 3), 0xec83b3a3);
  assert.equal(mpq.hash('a/b', 1), mpq.hash('A\\B', 1), 'slash and case don’t matter by default');
});

test('reads every file in a StormLib .otr, byte for byte', () => {
  assert.equal(mpq.isMpq(OTR), true);
  const es = mpq.readEntries(OTR), names = es.map((e) => e.name).sort();
  assert.deepEqual(names.filter((n) => !n.startsWith('(')), ['objects/gameplay_keep/gBrickTex', 'textures/icons/gArrowTex', 'textures/skybox/gCloudsTex', 'version']);
  const clouds = o2r.parseTexture(mpq.readEntry(OTR, es.find((e) => e.name.endsWith('gCloudsTex'))));
  assert.equal(clouds.width, 64);
  assert.deepEqual([...clouds.data], [...Array(4096).keys()].map((i) => (i * 37) & 255), 'multi-sector file intact');
  const ver = mpq.readEntry(OTR, es.find((e) => e.name === 'version'));
  assert.equal(ver.readUInt32LE(1), 0xec7011b7);
});

test('a .otr is recognised: Ocarina of Time, Ship of Harkinian', async () => {
  const id = shipid.identify(OTR);
  assert.equal(id.key, 'CZL'); assert.equal(id.port.name, 'Ship of Harkinian'); assert.match(id.source, /version file/);
  const r = await tasks.inspect('o2rExtract', OTR);
  assert.equal(r.state, 'ready'); assert.match(r.text, /Ship of Harkinian game archive: \d+ files/);
});

test('Extract Textures from a .otr, then Create HD Texture Pack with it as the base', async () => {
  const out = path.join(tmpDir(), 'got');
  const g = await tasks.o2rExtractTask({ archive: OTR, output: out }, quietCtx());
  assert.equal(g.written, 3);
  assert.equal(png.decodePNG(fs.readFileSync(path.join(out, 'textures/skybox/gCloudsTex.png'))).width, 64);
  assert.equal(shipid.identify(out).key, 'CZL', 'the texture folder remembers the game');
  const hd = tmpDir(); fs.mkdirSync(path.join(hd, 'objects/gameplay_keep'), { recursive: true });
  fs.writeFileSync(path.join(hd, 'objects/gameplay_keep/gBrickTex.png'), png.encodePNG({ width: 64, height: 64, data: new Uint8Array(64 * 64 * 4).fill(200) }));
  const mod = path.join(tmpDir(), 'HD.o2r');
  const b = await tasks.o2rBuildTask({ input: hd, base: OTR, output: mod, alt: true }, quietCtx());
  assert.equal(b.written, 1);
  assert.ok(rtz.readEntries(mod).some((e) => e.name === 'alt/objects/gameplay_keep/gBrickTex'));
  tasks.closePreview();
});

test('damaged or unnamed .otr archives fail with a clear message', () => {
  const f = path.join(tmpDir(), 'bad.otr');
  fs.writeFileSync(f, Buffer.concat([Buffer.from('MPQ\x1a', 'latin1'), Buffer.alloc(64)]));
  assert.throws(() => o2r.listTextures(f), /no file list/);
});
