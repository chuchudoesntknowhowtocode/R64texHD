'use strict';
// Step 2: Recomp mod info in .rtz packs, Check a pack, and the "Make them DDS" fix.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const png = core('png'), dds = core('dds'), rtz = core('rtz'), recomp = core('recomp'), check = core('check'), tasks = core('tasks');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64c-'));
const img = (w, h, fn) => { const d = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set(fn(x, y), (y * w + x) * 4); return { width: w, height: h, data: d }; };
const tex = (n = 32) => img(n, n, (x, y) => [x * 7, y * 7, 90, 255]);
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });
const titles = (r) => r.checks.map((c) => `${c.level}: ${c.title}`);

// A pack folder: 2 DDS (with mips), 1 PNG, and rt64.json for the three.
function packFolder() {
  const dir = tmpDir();
  fs.mkdirSync(path.join(dir, 'textures'));
  fs.writeFileSync(path.join(dir, 'textures', '1111111111111111.dds'), dds.encodeDDS(tex(), 'bc1'));
  fs.writeFileSync(path.join(dir, 'textures', '2222222222222222.dds'), dds.encodeDDS(tex(), 'bc1'));
  fs.writeFileSync(path.join(dir, 'textures', '3333333333333333.png'), png.encodePNG(tex()));
  return dir;
}

test('Recomp manifest follows the Recomp rules', () => {
  const m = recomp.manifest({ name: 'Majora HD Reimagined', author: 'chuchu, friend', version: '1.0.0', description: 'HD', game: 'mm' });
  assert.equal(m.game_id, 'mm'); assert.equal(m.id, 'majora_hd_reimagined'); assert.equal(m.display_name, 'Majora HD Reimagined');
  assert.deepEqual(m.authors, ['chuchu', 'friend']); assert.equal(m.minimum_recomp_version, '1.2.0');
  const opt = m.config_schema.options[0];
  assert.equal(opt.id, '_recomp_texture_pack_enabled'); assert.equal(opt.type, 'Enum'); assert.deepEqual(opt.options, ['Off', 'On']); assert.equal(opt.default, 'On');
  assert.equal(recomp.validate(JSON.stringify(m)).ok, true);
  assert.equal(recomp.manifest({ toggle: false }).config_schema, undefined);
  assert.throws(() => recomp.manifest({ version: '1.0' }), /like 1\.0\.0/);
  assert.equal(recomp.validate('{"id":"x"}').ok, false);
});

test('Packing with Recomp info puts mod.json and thumb.png in the .rtz', () => {
  const dir = packFolder(), thumb = path.join(tmpDir(), 'thumb.png'), out = path.join(tmpDir(), 'Majora HD.rtz');
  fs.writeFileSync(thumb, png.encodePNG(tex(64)));
  const r = rtz.packFolder(dir, out, { compression: 'zstd', level: 'fast', recomp: { name: 'Majora HD', author: 'chuchu', version: '1.2.3', thumb } });
  assert.equal(r.recomp.display_name, 'Majora HD');
  const names = rtz.readEntries(out).map((e) => e.name);
  assert.ok(names.includes('mod.json') && names.includes('thumb.png') && names.includes('rt64.json'));
  const e = rtz.readEntries(out).find((x) => x.name === 'mod.json');
  assert.equal(JSON.parse(rtz.readEntry(out, e)).version, '1.2.3');
  // Unpacked and packed again without new info: the mod.json and picture come along.
  const back = tmpDir(), again = path.join(tmpDir(), 'again.rtz');
  rtz.unpack(out, back, {});
  rtz.packFolder(back, again, { compression: 'store' });
  assert.ok(rtz.readEntries(again).some((x) => x.name === 'mod.json'));
});

test('Check a pack: a good DDS pack with Recomp info', () => {
  const dir = packFolder();
  fs.rmSync(path.join(dir, 'textures', '3333333333333333.png'));
  const out = path.join(tmpDir(), 'good.rtz');
  rtz.packFolder(dir, out, { compression: 'zstd', level: 'fast', lowMipCache: true, recomp: { name: 'Good Pack', author: 'me', version: '1.0.0' } });
  const r = check.checkPack(out);
  assert.ok(r.checks.every((c) => c.level === 'ok'), titles(r).join('\n'));
  assert.ok(titles(r).includes('ok: All textures are DDS'));
  assert.ok(titles(r).some((t) => /Recomp mod info found/.test(t)));
  assert.match(r.summary, /good\.rtz · 2 textures/);
});

test('Check a pack: PNG left, no mipmaps, missing file, unused image, bad mod.json', () => {
  const dir = packFolder();
  fs.writeFileSync(path.join(dir, 'textures', '4444444444444444.dds'), dds.encodeDDS(tex(), 'bc1', { mipmaps: false }));
  fs.writeFileSync(path.join(dir, 'textures', 'notes-sketch.png'), png.encodePNG(tex(8)));
  const out = path.join(tmpDir(), 'messy.rtz');
  rtz.packFolder(dir, out, { compression: 'deflate', level: 'fast', lowMipCache: false });
  // Folder version: add an rt64.json entry with no file, and a broken mod.json.
  rtz.unpack(out, dir, {});
  const db = JSON.parse(fs.readFileSync(path.join(dir, 'rt64.json'), 'utf8'));
  db.textures.push({ path: 'textures/5555555555555555', hashes: { rt64: '5555555555555555', rice: '' } });
  fs.writeFileSync(path.join(dir, 'rt64.json'), JSON.stringify(db));
  fs.writeFileSync(path.join(dir, 'mod.json'), JSON.stringify({ id: 'x', display_name: 'X', version: '1.0' }));
  const r = check.checkPack(dir);
  const t = titles(r).join('\n');
  assert.match(t, /bad: 1 texture in rt64\.json has no file/);
  assert.match(t, /bad: 1 texture is still PNG/);
  assert.match(t, /warn: 1 DDS texture has no mipmaps/);
  assert.match(t, /warn: 1 image isn’t used by rt64\.json/);
  assert.match(t, /bad: Recomp mod info has a problem/);
  assert.equal(r.checks[0].level, 'bad', 'problems are listed first');
  assert.equal(r.checks.find((c) => /still PNG/.test(c.title)).fix, 'png-to-dds');
});

test('Make them DDS: writes a fixed copy, the original is untouched', async () => {
  const dir = packFolder(), out = path.join(tmpDir(), 'Pack.rtz');
  rtz.packFolder(dir, out, { compression: 'zstd', level: 'fast', recomp: { name: 'Pack', author: 'me', version: '1.0.0' } });
  const before = fs.readFileSync(out);
  const log = [];
  const r = await tasks.fixTask({ kind: 'png-to-dds', input: out }, quietCtx(log), {});
  assert.equal(r.written, 1);
  assert.equal(path.basename(r.output), 'Pack-fixed.rtz');
  assert.deepEqual(fs.readFileSync(out), before, 'original pack unchanged');
  const c = check.checkPack(r.output);
  assert.ok(titles(c).includes('ok: All textures are DDS'), titles(c).join('\n'));
  assert.ok(titles(c).some((x) => /Recomp mod info found/.test(x)), 'mod.json kept');
  assert.ok(rtz.readEntries(r.output).some((e) => e.name === 'rt64-low-mip-cache.bin'), 'low-mip cache rebuilt');
  // Fixing a folder works too and leaves the folder alone.
  const r2 = await tasks.fixTask({ kind: 'png-to-dds', input: dir }, quietCtx(), {});
  assert.ok(fs.existsSync(path.join(dir, 'textures', '3333333333333333.png')));
  assert.ok(check.checkPack(r2.output).checks.every((x) => x.level === 'ok'));
});

test('Check task reports through the app task runner', async () => {
  const dir = packFolder();
  const log = [];
  const r = await tasks.checkTask({ input: dir }, quietCtx(log));
  assert.equal(r.title, 'Checked');
  assert.ok(log.some((l) => /still PNG/.test(l)));
});
