'use strict';
// 4 · Ship Mods: which N64 game a port archive, mod or texture folder belongs to.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const shipid = core('shipid'), rtz = core('rtz'), o2r = core('o2r'), png = core('png'), tasks = core('tasks');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64s-'));
const quietCtx = () => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: () => {}, progress: () => {} });
// The "version" file Torch / Shipwright write: endianness byte (0 little, 1 big) + the ROM's CRC1.
const version = (crc, big = true) => { const b = Buffer.alloc(5); b[0] = big ? 1 : 0; if (big) b.writeUInt32BE(crc, 1); else b.writeUInt32LE(crc, 1); return b; };
function archive(file, entries) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const zip = new rtz.ZipWriter(file);
  for (const [name, buf] of Object.entries(entries)) zip.add(name, buf, 0, zlib.crc32(buf), buf.length, Date.now());
  zip.close();
  return file;
}
const tex = () => o2r.resource({ type: 2, width: 8, height: 8, data: Buffer.alloc(128, 0x42) });

test('the version file names the game, whatever the archive is called', () => {
  const d = tmpDir();
  // Ghostship's archive, renamed: still Super Mario 64 (US CRC1 635A2BFF), read big-endian.
  const a = shipid.identify(archive(path.join(d, 'whatever.o2r'), { version: version(0x635a2bff), 'textures/x': tex() }));
  assert.equal(a.crc, '635A2BFF'); assert.equal(a.key, 'NSM'); assert.equal(a.game.title, 'Super Mario 64');
  assert.equal(a.port.name, 'Ghostship'); assert.equal(a.kind, 'game'); assert.match(a.source, /version file/);
  assert.match(a.rom, /Super Mario 64 \(U\)/);
  // Little-endian too (Shipwright): Ocarina of Time US 1.0.
  const b = shipid.identify(archive(path.join(d, 'x.o2r'), { version: version(0xec7011b7, false) }));
  assert.equal(b.key, 'CZL'); assert.equal(b.port.name, 'Ship of Harkinian');
  // GameCube discs the ports accept: Majora's Mask (USA, GameCube) is 2Ship.
  const c = shipid.identify(archive(path.join(d, 'y.o2r'), { version: version(0xb443eb08) }));
  assert.equal(c.key, 'NZS'); assert.equal(c.port.name, '2 Ship 2 Harkinian');
  // Mario Kart 64 and Star Fox 64.
  assert.equal(shipid.identify(archive(path.join(d, 'k.o2r'), { version: version(0x3e5055b6) })).port.name, 'SpaghettiKart');
  assert.equal(shipid.identify(archive(path.join(d, 's.o2r'), { version: version(0xa7d015f8) })).port.name, 'Starship');
});

test('a new port nobody has heard of still finds its game', () => {
  // Paper Mario US CRC1 from an archive with no known name: the game comes from the CRC alone.
  const crc = Object.entries(shipid.crcTable()).find(([, v]) => v[0] === 'NMQ')[0];
  const a = shipid.identify(archive(path.join(tmpDir(), 'brand-new-port.o2r'), { version: version(parseInt(crc, 16)) }));
  assert.equal(a.game.title, 'Paper Mario'); assert.equal(a.port.name, 'Paperboat');
  // A game with no port in ports.json: the game is still found, the port is just unknown.
  const blast = Object.entries(shipid.crcTable()).find(([, v]) => v[0] === 'NBC')[0];
  const b = shipid.identify(archive(path.join(tmpDir(), 'bc.o2r'), { version: version(parseInt(blast, 16)) }));
  assert.equal(b.game.title, 'Blast Corps'); assert.equal(b.port, null);
});

test('manifest.json game_version, and the port’s own archive', () => {
  const d = tmpDir();
  const m = shipid.identify(archive(path.join(d, 'm.o2r'), { 'manifest.json': Buffer.from(JSON.stringify({ name: 'Cool Mod', game_version: 0x5354631c })) }));
  assert.equal(m.key, 'NZS'); assert.match(m.source, /manifest/);
  const p = shipid.identify(archive(path.join(d, '2ship.o2r'), { portVersion: Buffer.from([1, 0, 0, 5, 0, 0, 0, 0]) }));
  assert.equal(p.kind, 'port'); assert.equal(p.key, 'NZS'); assert.match(p.source, /file name/);
});

test('names and folders only when the file says nothing; unknown stays unknown', () => {
  const d = tmpDir();
  assert.equal(shipid.identify(archive(path.join(d, 'sf64.o2r'), { a: tex() })).port.name, 'Starship');
  assert.equal(shipid.identify(archive(path.join(d, 'Ghostship', 'mods', 'My HD pack.o2r'), { a: tex() })).key, 'NSM');
  const u = shipid.identify(archive(path.join(d, 'mystery.o2r'), { version: version(0x12345678) }));
  assert.equal(u.crc, '12345678'); assert.equal(u.key, ''); assert.equal(u.game, null);
  assert.equal(shipid.identify(path.join(d, 'missing.o2r')).game, null);
  assert.equal(shipid.readVersion(Buffer.from('1.0')), null, 'too short to be a version file');
});

test('Extract Textures and Create HD Texture Pack carry the game along', async () => {
  const d = tmpDir();
  const base = archive(path.join(d, 'renamed.o2r'), { version: version(0x635a2bff), 'textures/castle/gWall': tex() });
  const got = path.join(d, 'got');
  await tasks.o2rExtractTask({ archive: base, output: got }, quietCtx());
  const folder = shipid.identify(got);
  assert.equal(folder.key, 'NSM'); assert.equal(folder.kind, 'folder'); assert.match(folder.source, /texture list/);
  // An HD texture and the mod built from it: the mod remembers its game.
  const hd = path.join(d, 'hd', 'textures', 'castle'); fs.mkdirSync(hd, { recursive: true });
  const img = { width: 32, height: 32, data: new Uint8Array(32 * 32 * 4).fill(200) };
  fs.writeFileSync(path.join(hd, 'gWall.png'), png.encodePNG(img));
  const mod = path.join(d, 'out', 'HD.o2r');
  await tasks.o2rBuildTask({ input: path.join(d, 'hd'), base, output: mod, alt: true }, quietCtx());
  const names = rtz.readEntries(mod).map((e) => e.name);
  assert.ok(names.includes('r64texhd.json') && names.includes('alt/textures/castle/gWall'));
  const m = shipid.identify(mod);
  assert.equal(m.key, 'NSM'); assert.equal(m.kind, 'mod'); assert.match(m.source, /note/);
  tasks.closePreview();
});
