'use strict';
// 4 · Ship Mods: finding the Harbour Masters ports installed on this PC.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const shipfind = core('shipfind'), rtz = core('rtz');

const version = (crc) => { const b = Buffer.alloc(5); b[0] = 1; b.writeUInt32BE(crc, 1); return b; };
function archive(file, entries) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const zip = new rtz.ZipWriter(file);
  for (const [name, buf] of Object.entries(entries)) zip.add(name, buf, 0, zlib.crc32(buf), buf.length, Date.now());
  zip.close();
}
const touch = (f) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, 'x'); };

// A pretend PC: ports in a Games folder and in Downloads, lots of other folders, a decoy in node_modules.
function pc() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'r64find-'));
  const games = path.join(root, 'Games'), dl = path.join(root, 'Downloads');
  touch(path.join(games, 'SoH', 'soh.exe'));
  archive(path.join(games, 'SoH', 'oot.o2r'), { version: version(0xec7011b7) });
  touch(path.join(games, 'Ports', '2Ship', '2ship.exe'));
  archive(path.join(games, 'Ports', '2Ship', 'majora backup.o2r'), { version: version(0x5354631c) });   // renamed game archive
  touch(path.join(games, 'Ports', 'Ghostship', 'Ghostship.exe'));
  archive(path.join(dl, 'Starship-win64', 'starship.o2r'), { portVersion: Buffer.from([1, 0, 0, 0, 0, 0]) });    // only the port's own archive
  touch(path.join(dl, 'project', 'node_modules', 'spaghetti', 'Spaghettify.exe'));                             // skipped folder
  for (let i = 0; i < 40; i++) for (let j = 0; j < 40; j++) fs.mkdirSync(path.join(root, 'Documents', `d${i}`, `e${j}`), { recursive: true });
  return { root, roots: [{ dir: games, depth: 4 }, { dir: dl, depth: 4 }, { dir: path.join(root, 'Documents'), depth: 4 }] };
}

test('finds installed ports, their game archives and mods folders', async () => {
  const { root, roots } = pc();
  const r = await shipfind.find({ roots });
  const by = Object.fromEntries(r.ports.map((p) => [p.name, p]));
  assert.equal(by['Ship of Harkinian'].installed, true);
  assert.equal(by['Ship of Harkinian'].archive, path.join(root, 'Games', 'SoH', 'oot.o2r'));
  assert.equal(by['Ship of Harkinian'].mods, path.join(root, 'Games', 'SoH', 'mods'));
  assert.equal(by['2 Ship 2 Harkinian'].archive, path.join(root, 'Games', 'Ports', '2Ship', 'majora backup.o2r'), 'renamed archive found by its version file');
  assert.equal(by.Ghostship.installed, true); assert.equal(by.Ghostship.archive, '', 'no game archive until the port has made one');
  assert.equal(by.Starship.installed, true); assert.ok(by.Starship.portArchive.endsWith('starship.o2r'));
  assert.equal(by.SpaghettiKart.installed, false, 'node_modules is never searched');
  assert.equal(by.Lighthouse.installed, false);
  assert.equal(r.complete, true);
  assert.ok(r.ms < 3000, `took ${r.ms} ms`);
});

test('folders already used are searched first, and their neighbours', async () => {
  const { root } = pc();
  // Only a seed (an archive used before) and no roots: its neighbours are found too.
  const r = await shipfind.find({ roots: [], seeds: [path.join(root, 'Games', 'SoH', 'oot.o2r')] });
  const names = r.ports.filter((p) => p.installed).map((p) => p.name);
  assert.ok(names.includes('Ship of Harkinian') && names.includes('2 Ship 2 Harkinian') && names.includes('Ghostship'), names.join());
  assert.ok(r.ms < 3000, `took ${r.ms} ms`);
});

test('a copy of a game archive elsewhere doesn’t beat the one next to the port', async () => {
  const { root, roots } = pc();
  archive(path.join(root, 'Downloads', 'backup', 'oot.o2r'), { version: version(0xec7011b7) });
  const r = await shipfind.find({ roots: [{ dir: path.join(root, 'Downloads'), depth: 4 }, ...roots] });
  const soh = r.ports.find((p) => p.name === 'Ship of Harkinian');
  assert.equal(soh.archive, path.join(root, 'Games', 'SoH', 'oot.o2r'));
  assert.equal(soh.mods, path.join(root, 'Games', 'SoH', 'mods'));
});

test('time and folder limits are kept', async () => {
  const { roots } = pc();
  const r = await shipfind.find({ roots, maxFolders: 20 });
  assert.ok(r.folders <= 40, `${r.folders}`);
  assert.equal(r.complete, false);
});
