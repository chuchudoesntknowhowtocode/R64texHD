'use strict';
// 6 · ROM Tools: finding N64 ROMs, reading headers, CIC, checksum, file table.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const rom = core('rom'), rtz = core('rtz'), tasks = core('tasks');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64rom-'));
const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });
const hex = (v) => (v >>> 0).toString(16).toUpperCase().padStart(8, '0');

// A made-up 1 MB + 4 KB ROM in .z64 order: a known header, then filler bytes from a simple LCG.
function makeRom({ title = 'TEST CART', code = 'NTSE', version = 1, size = 0x101000 } = {}) {
  const d = Buffer.alloc(size);
  for (let i = 0; i < size; i++) d[i] = ((Math.imul(i, 1103515245) + 12345) >>> 16) & 255;
  d.writeUInt32BE(0x80371240, 0); d.writeUInt32BE(0x0000000f, 4); d.writeUInt32BE(0x80000400, 8); d.writeUInt32BE(0x0000144b, 0x0c);
  d.fill(0, 0x18, 0x40);
  d.write(title.padEnd(20, ' '), 0x20, 'latin1');
  d.write(code, 0x3b, 'latin1'); d[0x3f] = version;
  return d;
}
const swap2 = (b) => { const o = Buffer.from(b); for (let i = 0; i < o.length; i += 2) { o[i] = b[i + 1]; o[i + 1] = b[i]; } return o; };
const swap4 = (b) => { const o = Buffer.from(b); for (let i = 0; i < o.length; i += 4) { o[i] = b[i + 3]; o[i + 1] = b[i + 2]; o[i + 2] = b[i + 1]; o[i + 3] = b[i]; } return o; };
// Teach rom.js this ROM's (made-up) boot code as a CIC, and write the right CRC1 / CRC2.
function sign(d, name = 'CIC-6102 / 7101') {
  const real = Object.values(rom.CIC).find((c) => c.name === name);
  rom.CIC[zlib.crc32(d.subarray(0x40, 0x1000)) >>> 0] = { name, seed: real.seed, note: 'test' };
  const [c1, c2] = rom.checksum(d, name, real.seed);
  d.writeUInt32BE(c1, 0x10); d.writeUInt32BE(c2, 0x14);
  return d;
}

test('checksum matches a separate port of n64crc.c for every chip', () => {
  // Expected values come from a straight Python port of n64crc.c run on the same bytes.
  const d = Buffer.alloc(0x101000);
  for (let i = 0; i < d.length; i++) d[i] = ((Math.imul(i, 1103515245) + 12345) >>> 16) & 255;
  const want = {
    'CIC-6102 / 7101': ['798F2EBB', '35A6AE34'], 'CIC-6103 / 7103': ['2B35883A', '8B3C290C'],
    'CIC-6105 / 7105': ['602BD415', '3FD88873'], 'CIC-6106 / 7106': ['4B7537EA', '6DDF4E18'],
  };
  for (const [name, crc] of Object.entries(want)) {
    const seed = Object.values(rom.CIC).find((c) => c.name === name).seed;
    assert.deepEqual(rom.checksum(d, name, seed).map(hex), crc, name);
  }
  assert.equal(rom.checksum(d.subarray(0, 0x2000), 'CIC-6102 / 7101', 0xf8ca4ddc), null, 'too small to check');
});

test('header fields', () => {
  const h = rom.parseHeader(makeRom({ title: 'SUPER TEST 64', code: 'NTSP', version: 2 }));
  assert.equal(h.title, 'SUPER TEST 64');
  assert.deepEqual([h.gameCode, h.category, h.gameId, h.region, h.video, h.version], ['NTSP', 'Game Pak (cartridge)', 'TS', 'Europe', 'PAL', 2]);
  assert.equal(h.entryPoint, 0x80000400);
  const hb = rom.parseHeader(makeRom({ code: '\0\0\0\0' }));
  assert.deepEqual([hb.gameCode, hb.category, hb.region, hb.video], ['', 'Not set (homebrew)', 'Not set', '']);
});

test('.z64, .v64 and .n64 give the same answers; checksum OK, then wrong after a change', () => {
  const dir = tmpDir();
  const z = sign(makeRom());
  fs.writeFileSync(path.join(dir, 'a.z64'), z);
  fs.writeFileSync(path.join(dir, 'a.v64'), swap2(z));
  fs.writeFileSync(path.join(dir, 'a.n64'), swap4(z));
  const [iz, iv, in_] = ['a.z64', 'a.v64', 'a.n64'].map((f) => rom.info(path.join(dir, f)));
  assert.deepEqual([iz.format, iv.format, in_.format], ['z64', 'v64', 'n64']);
  for (const i of [iz, iv, in_]) {
    assert.equal(i.title, 'TEST CART'); assert.equal(i.gameCode, 'NTSE'); assert.equal(i.region, 'North America');
    assert.equal(i.checksum, 'OK'); assert.equal(i.checksumOk, true); assert.equal(i.cic, 'CIC-6102 / 7101');
    assert.equal(i.md5, iz.md5, 'hashes are of the .z64 order');
  }
  assert.equal(iz.libultraVersion, '2.0K'); assert.equal(iz.mbit, 8);
  const bad = Buffer.from(z); bad[0x5000] ^= 1;
  fs.writeFileSync(path.join(dir, 'bad.z64'), bad);
  const ib = rom.info(path.join(dir, 'bad.z64'));
  assert.equal(ib.checksumOk, false); assert.match(ib.checksum, /^Doesn't match \(calculated [0-9A-F]{8} [0-9A-F]{8}\)$/);
});

test('unknown boot code is reported, not guessed', () => {
  const f = path.join(tmpDir(), 'x.z64');
  const d = makeRom(); d[0x80] ^= 0x5a;                  // boot code nobody knows
  fs.writeFileSync(f, d);
  const i = rom.info(f);
  assert.match(i.cic, /^Unknown/); assert.equal(i.checksumOk, null); assert.match(i.checksum, /^Not checked/);
});

test('a ROM inside a .zip, and padding at the end', () => {
  const dir = tmpDir();
  const d = Buffer.concat([sign(makeRom({ title: 'ZIPPED' })), Buffer.alloc(0x20000, 0xff)]);
  const zip = new rtz.ZipWriter(path.join(dir, 'game.zip'));
  zip.add('readme.txt', Buffer.from('hi'), 0, zlib.crc32(Buffer.from('hi')), 2, Date.now());
  zip.add('Game (USA).z64', zlib.deflateRawSync(d), 8, zlib.crc32(d), d.length, Date.now());
  zip.close();
  const i = rom.info(path.join(dir, 'game.zip'));
  assert.equal(i.title, 'ZIPPED'); assert.equal(i.inner, 'Game (USA).z64'); assert.equal(i.checksum, 'OK');
  assert.equal(i.trailingZeros, 0x20000);
  assert.ok(i.fileSize < i.romSize);
});

test('Zelda 64 file table is found and counted', () => {
  const d = makeRom({ size: 0x200000 });
  const at = 0x12f70;                                    // where Ocarina of Time keeps it
  const ent = (n, vs, ve, rs, re) => { const p = at + n * 16; d.writeUInt32BE(vs, p); d.writeUInt32BE(ve, p + 4); d.writeUInt32BE(rs, p + 8); d.writeUInt32BE(re, p + 12); };
  ent(0, 0, 0x1060, 0, 0);
  for (let n = 1; n < 30; n++) ent(n, n * 0x1000, n * 0x1000 + 0x800, n * 0x1000, n % 3 ? n * 0x1000 + 0x400 : 0);
  ent(30, 0x40000, 0x41000, 0xffffffff, 0xffffffff);
  d.fill(0, at + 31 * 16, at + 32 * 16);
  d.write('zelda@srd44\x0098-10-21 04:56:31\x00', 0x7310, 'latin1');
  const z = rom.zeldaFiles(d);
  assert.equal(z.table, at); assert.equal(z.count, 31);
  assert.equal(z.compressed, 20); assert.equal(z.missing, 1);
  assert.equal(z.build, 'zelda@srd44 · 98-10-21 04:56:31');
  assert.equal(rom.zeldaFiles(makeRom()), null);
});

test('scan finds ROMs in subfolders, skips look-alikes, and the app task reports it', async () => {
  const dir = tmpDir();
  fs.mkdirSync(path.join(dir, 'USA'));
  fs.mkdirSync(path.join(dir, 'Japan', 'Hacks'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'USA', 'b.z64'), makeRom({ title: 'BETA' }).subarray(0, 0x2000));
  fs.writeFileSync(path.join(dir, 'USA', 'a.v64'), swap2(makeRom({ title: 'ALPHA' }).subarray(0, 0x2000)));
  fs.writeFileSync(path.join(dir, 'Japan', 'Hacks', 'c.n64'), swap4(makeRom({ title: 'GAMMA', code: 'NGMJ' }).subarray(0, 0x2000)));
  fs.writeFileSync(path.join(dir, 'firmware.bin'), Buffer.alloc(0x2000, 7));   // .bin but not a ROM
  fs.writeFileSync(path.join(dir, 'notes.txt'), 'x');
  const r = rom.scan(dir);
  assert.deepEqual(r.roms.map((x) => [x.rel.split(path.sep).join('/'), x.title, x.format]),
    [['Japan/Hacks/c.n64', 'GAMMA', 'n64'], ['USA/a.v64', 'ALPHA', 'v64'], ['USA/b.z64', 'BETA', 'z64']]);
  assert.equal(r.skipped, 1);
  assert.equal(r.roms[0].region, 'Japan');

  const log = [];
  const t = await tasks.romsTask({ folder: dir }, quietCtx(log));
  assert.equal(t.count, 3); assert.equal(t.folders, 2);
  assert.ok(log.some((l) => /Found 3 N64 ROM/.test(l)));
  const info = await tasks.romInfo(path.join(dir, 'USA', 'b.z64'));
  assert.equal(info.title, 'BETA');
  assert.equal((await tasks.inspect('roms', dir)).state, 'ready');
  assert.equal((await tasks.inspect('roms', tmpDir())).state, 'error');
  await assert.rejects(tasks.romsTask({ folder: '' }, quietCtx()), /folder/i);
  tasks.closePreview();
});

test('N64 library: box art and description by game ID, any region', () => {
  const lib = rom.library();
  assert.equal(lib.count, 303);
  assert.equal(Object.keys(lib.games).length, 303);
  for (const [key, g] of Object.entries(lib.games)) {
    assert.match(key, /^[A-Z0-9]{3}$/);
    assert.ok(fs.existsSync(path.join(__dirname, '..', 'app', 'assets', 'n64', 'boxart', g.art)), `box art for ${key}: ${g.art}`);
  }
  const pm = rom.libraryGame('NMQE');
  assert.equal(pm.title, 'Paper Mario'); assert.equal(pm.art, 'Paper Mario (USA).webp'); assert.match(pm.description, /paper-styled/);
  assert.equal(rom.libraryGame('NMQJ'), pm, 'a Japanese copy finds the same game');
  assert.equal(rom.libraryGame('NG5E').title, 'Mystical Ninja Starring Goemon');
  assert.equal(rom.libraryGame('NGME').title, "Goemon's Great Adventure");
  assert.equal(rom.libraryGame('CZLE').title, 'The Legend of Zelda: Ocarina of Time');
  assert.equal(rom.libraryGame(''), null); assert.equal(rom.libraryGame('ZZZE'), null);
});

test('scan counts library titles once, however many copies', () => {
  const dir = tmpDir();
  fs.writeFileSync(path.join(dir, 'pm-us.z64'), makeRom({ title: 'PAPERMARIO', code: 'NMQE' }).subarray(0, 0x2000));
  fs.writeFileSync(path.join(dir, 'pm-jp.z64'), makeRom({ title: 'MARIO STORY', code: 'NMQJ' }).subarray(0, 0x2000));
  fs.writeFileSync(path.join(dir, 'sm64.z64'), makeRom({ title: 'SUPER MARIO 64', code: 'NSME' }).subarray(0, 0x2000));
  fs.writeFileSync(path.join(dir, 'home.z64'), makeRom({ title: 'HOMEBREW', code: '\0\0\0\0' }).subarray(0, 0x2000));
  const r = rom.scan(dir);
  assert.equal(r.roms.length, 4); assert.equal(r.matched, 2); assert.equal(r.libraryCount, 303);
  assert.deepEqual(r.roms.map((x) => [x.file, x.libKey]), [['home.z64', ''], ['pm-jp.z64', 'NMQ'], ['pm-us.z64', 'NMQ'], ['sm64.z64', 'NSM']]);
  assert.equal(r.roms.find((x) => x.file === 'home.z64').libKey, '');
  const f = path.join(dir, 'full.z64'); fs.writeFileSync(f, makeRom({ code: 'NSME' }));
  assert.equal(rom.info(f).library.title, 'Super Mario 64');
});
