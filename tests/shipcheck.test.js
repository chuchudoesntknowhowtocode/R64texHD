'use strict';
// 4 · Ship Mods: is the port's game archive made yet, and is it from the port build that's installed?
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const sc = core('shipcheck'), shipfind = core('shipfind'), rtz = core('rtz');
const OTR = path.join(__dirname, 'fixtures', 'oot-test.otr');

const tmpDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'r64c-'));
const version = (crc) => { const b = Buffer.alloc(5); b[0] = 1; b.writeUInt32BE(crc, 1); return b; };
// portVersion as Torch writes it: endianness byte (1 = big) + u16 major, minor, patch.
const pv = (major, minor = 0, patch = 0) => { const b = Buffer.alloc(7); b[0] = 1; b.writeUInt16BE(major, 1); b.writeUInt16BE(minor, 3); b.writeUInt16BE(patch, 5); return b; };
function archive(file, entries) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const zip = new rtz.ZipWriter(file);
  for (const [name, buf] of Object.entries(entries)) zip.add(name, buf, 0, zlib.crc32(buf), buf.length, Date.now());
  zip.close();
  return file;
}
const touch = (f, data = 'x') => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, data); return f; };
const OOT = 0xec7011b7, MM = 0x5354631c;
const port = (name) => core('shipid').ports().find((p) => p.name === name);

// A tiny Windows program with only a version resource (VS_FIXEDFILEINFO), like a port's .exe.
function exe(file, major, minor, patch) {
  const b = Buffer.alloc(0x600);
  b.write('MZ', 0, 'latin1'); b.writeUInt32LE(0x40, 0x3c);
  b.writeUInt32LE(0x4550, 0x40);                       // PE\0\0
  b.writeUInt16LE(1, 0x40 + 6);                        // one section
  b.writeUInt16LE(224, 0x40 + 20);                     // PE32 optional header
  const opt = 0x40 + 24;
  b.writeUInt16LE(0x10b, opt);
  b.writeUInt32LE(0x1000, opt + 96 + 16); b.writeUInt32LE(0x100, opt + 96 + 20);   // resources at RVA 0x1000
  const sec = opt + 224;
  b.write('.rsrc', sec, 'latin1'); b.writeUInt32LE(0x100, sec + 8); b.writeUInt32LE(0x1000, sec + 12);
  b.writeUInt32LE(0x200, sec + 16); b.writeUInt32LE(0x400, sec + 20);
  const fi = 0x400 + 0x40;
  b.writeUInt32LE(0xfeef04bd, fi); b.writeUInt32LE(0x10000, fi + 4);
  b.writeUInt32LE((major << 16) | minor, fi + 8); b.writeUInt32LE(patch << 16, fi + 12);
  return touch(file, b);
}

test('portVersion: with and without the endianness byte; INT16_MAX means none', () => {
  assert.deepEqual(sc.readPortVersion(pv(9, 0, 2)), { major: 9, minor: 0, patch: 2, text: '9.0.2' });
  const le = Buffer.from([0, 3, 0, 1, 0, 4, 0]);
  assert.equal(sc.readPortVersion(le).text, '3.1.4');
  assert.equal(sc.readPortVersion(Buffer.from([0, 2, 0, 5, 0, 1])).text, '2.5.1', '6 bytes: big-endian, no endianness byte');
  assert.equal(sc.readPortVersion(pv(0x7fff)), null);
  assert.equal(sc.readPortVersion(Buffer.from([1, 2])), null);
});

test('a port’s build comes from its own archive, or from its program', () => {
  const d = tmpDir();
  archive(path.join(d, 'soh.o2r'), { portVersion: pv(9, 1, 0) });
  assert.equal(sc.checkPort(port('Ship of Harkinian'), d).build.text, '9.1.0');
  const e = tmpDir();
  exe(path.join(e, '2ship.exe'), 2, 3, 1);
  assert.equal(sc.exeVersion(path.join(e, '2ship.exe')).text, '2.3.1');
  const r = sc.checkPort(port('2 Ship 2 Harkinian'), e);
  assert.equal(r.installed, true); assert.equal(r.build.text, '2.3.1'); assert.equal(r.buildFrom, '2ship.exe');
  assert.equal(sc.exeVersion(touch(path.join(e, 'not.exe'), 'hello')), null);
});

test('not made yet, then made, then outdated after the port updates', () => {
  const d = tmpDir();
  touch(path.join(d, 'soh.exe'));
  archive(path.join(d, 'soh.o2r'), { portVersion: pv(9, 0, 2) });
  const p = port('Ship of Harkinian');
  let r = sc.checkPort(p, d);
  assert.equal(r.installed, true); assert.equal(r.generated, false); assert.equal(r.state, 'not-generated'); assert.equal(r.archive, '');
  assert.match(r.message, /run it once/);
  // The player runs the port: it makes oot.o2r with its build in it.
  archive(path.join(d, 'oot.o2r'), { version: version(OOT), portVersion: pv(9, 0, 2) });
  r = sc.checkPort(p, d);
  assert.equal(r.state, 'ready'); assert.equal(r.generated, true); assert.equal(r.archive, path.join(d, 'oot.o2r')); assert.equal(r.version.text, '9.0.2');
  // A new minor build is fine (Ship of Harkinian only compares majors)...
  archive(path.join(d, 'soh.o2r'), { portVersion: pv(9, 1, 0) });
  assert.equal(sc.checkPort(p, d).state, 'ready');
  // ...a new major isn't: the game archive has to be made again.
  archive(path.join(d, 'soh.o2r'), { portVersion: pv(10, 0, 0) });
  r = sc.checkPort(p, d);
  assert.equal(r.state, 'outdated'); assert.match(r.message, /made by Ship of Harkinian 9\.0\.2, but version 10\.0\.0 is installed/);
});

test('an archive with no portVersion, like an old .otr, is outdated for a versioned port', () => {
  const d = tmpDir();
  archive(path.join(d, 'soh.o2r'), { portVersion: pv(9) });
  fs.copyFileSync(OTR, path.join(d, 'oot.otr'));
  const r = sc.checkPort(port('Ship of Harkinian'), d);
  assert.equal(r.archive, path.join(d, 'oot.otr')); assert.equal(r.state, 'outdated'); assert.match(r.message, /an older build/);
  // Without a known build there's nothing to compare with: it's just there.
  const e = tmpDir(); fs.copyFileSync(OTR, path.join(e, 'oot.otr'));
  assert.equal(sc.checkTarget(path.join(e, 'oot.otr')).state, 'ready');
});

test('checking again follows the PC as it is now', () => {
  const d = tmpDir(), soh = path.join(d, 'SoH'), mm = path.join(d, '2Ship');
  touch(path.join(soh, 'soh.exe')); archive(path.join(soh, 'soh.o2r'), { portVersion: pv(9) });
  archive(path.join(soh, 'oot.o2r'), { version: version(OOT), portVersion: pv(9) });
  touch(path.join(mm, '2ship.exe'));
  const found = [
    { name: 'Ship of Harkinian', installed: true, dir: soh, exe: path.join(soh, 'soh.exe'), archive: path.join(soh, 'oot.o2r'), archives: [path.join(soh, 'oot.o2r')] },
    { name: '2 Ship 2 Harkinian', installed: true, dir: mm, exe: path.join(mm, '2ship.exe'), archive: '', archives: [] },
  ];
  let r = sc.checkPorts(found);
  const by = (n) => r.find((x) => x.name === n);
  assert.equal(by('Ship of Harkinian').state, 'ready');
  assert.equal(by('2 Ship 2 Harkinian').state, 'not-generated');
  assert.equal(by('Ghostship').installed, false);
  // 2Ship is run (game archive appears) and SoH is deleted.
  archive(path.join(mm, 'mm.o2r'), { version: version(MM) });
  fs.rmSync(soh, { recursive: true });
  r = sc.checkPorts(r);
  assert.equal(by('2 Ship 2 Harkinian').state, 'ready'); assert.equal(by('2 Ship 2 Harkinian').archive, path.join(mm, 'mm.o2r'));
  assert.equal(by('Ship of Harkinian').installed, false);
});

test('the chosen archive is checked against the installed build, even kept elsewhere', () => {
  const d = tmpDir(), soh = path.join(d, 'SoH');
  touch(path.join(soh, 'soh.exe')); archive(path.join(soh, 'soh.o2r'), { portVersion: pv(10) });
  const here = archive(path.join(soh, 'oot.o2r'), { version: version(OOT), portVersion: pv(9) });
  let t = sc.checkTarget(here);
  assert.equal(t.state, 'outdated'); assert.equal(t.id.key, 'CZL'); assert.equal(t.build.text, '10.0.0');
  const copy = archive(path.join(d, 'backup', 'oot.o2r'), { version: version(OOT), portVersion: pv(10) });
  assert.match(sc.checkTarget(copy).message, /no installed Ship of Harkinian build/);
  t = sc.checkTarget(copy, sc.checkPorts([{ name: 'Ship of Harkinian', installed: true, dir: soh, exe: path.join(soh, 'soh.exe') }]));
  assert.equal(t.state, 'ready');
  assert.equal(sc.checkTarget(path.join(d, 'gone.o2r')).state, 'not-generated');
  assert.equal(sc.checkTarget(path.join(d, 'backup')).state, '', 'folders aren’t compared');
});

test('the port search reports each port’s archive state', async () => {
  const d = tmpDir(), soh = path.join(d, 'Games', 'SoH');
  touch(path.join(soh, 'soh.exe')); archive(path.join(soh, 'soh.o2r'), { portVersion: pv(10) });
  archive(path.join(soh, 'oot.o2r'), { version: version(OOT), portVersion: pv(9) });
  touch(path.join(d, 'Games', 'Ghostship', 'Ghostship.exe'));
  const r = await shipfind.find({ roots: [{ dir: path.join(d, 'Games'), depth: 3 }] });
  const by = Object.fromEntries(r.ports.map((p) => [p.name, p]));
  assert.equal(by['Ship of Harkinian'].state, 'outdated'); assert.equal(by['Ship of Harkinian'].build.text, '10.0.0');
  assert.equal(by.Ghostship.state, 'not-generated');
  assert.equal(by.Lighthouse.state, 'missing');
});
