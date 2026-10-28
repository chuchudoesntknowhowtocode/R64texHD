'use strict';
// Finds the Harbour Masters ports installed on this PC, for 4 · Ship Mods.
//
// Made to be fast and light: it never asks Windows Search, and only lists folders (one readdir per
// folder, no per-file stat). Where it looks, in order:
//   1. folders you already used (the archives / mods folders in Settings) and earlier finds;
//   2. the usual places: Desktop, Downloads, Documents, Games folders, each drive's root;
//   3. once a port turns up, its neighbours first: ports are usually kept side by side.
// It skips system folders, stops as soon as every port is found, and has a time and folder limit.
// A folder counts as a port when it has the port's program (soh.exe...), its own archive
// (soh.o2r...) or a game archive whose version file names the port's game.
const fs = require('fs');
const os = require('os');
const path = require('path');
const shipid = require('./shipid');
const shipcheck = require('./shipcheck');

const SKIP = new Set(['windows', '$recycle.bin', 'system volume information', 'programdata', 'appdata', 'node_modules', '.git', 'windowsapps',
  'winsxs', 'msocache', 'recovery', 'perflogs', 'config.msi', '$windows.~bt', '$windows.~ws', '$winreagent', 'intel', 'amd', 'nvidia', 'drivers',
  'onedrivetemp', 'temp', 'tmp', 'cache', '__pycache__', '.cache', '.npm', 'site-packages', 'dist-packages', 'proc', 'sys', 'dev', 'snap']);

function defaultRoots() {
  const home = os.homedir(), roots = [];
  const user = ['Desktop', 'Downloads', 'Documents', 'Games', 'OneDrive\\Desktop', 'OneDrive\\Documents', 'OneDrive'].map((d) => path.join(home, d));
  roots.push(...user.map((dir) => ({ dir, depth: 4 })), { dir: home, depth: 2 });
  if (process.platform === 'win32') {
    for (const L of 'CDEFGHIJKLMNOPQRSTUVWXYZ') {
      const d = `${L}:\\`;
      for (const sub of ['Games', 'Emulators', 'Emulation', 'N64', 'Ports', 'Program Files', 'Program Files (x86)']) roots.push({ dir: d + sub, depth: 4 });
      roots.push({ dir: d, depth: 4 });
    }
  }
  return roots;
}

// Lists a folder: { files: [names], dirs: [names] }, or null if it can't be read in time
// (a sleeping network drive must not hold the search up).
async function list(dir, ms) {
  let timer;
  const late = new Promise((r) => { timer = setTimeout(() => r(null), ms); });
  try {
    const entries = await Promise.race([fs.promises.readdir(dir, { withFileTypes: true }), late]);
    if (!entries) return null;
    const files = [], dirs = [];
    for (const e of entries) { if (e.isDirectory()) dirs.push(e.name); else files.push(e.name); }
    return { files, dirs };
  } catch { return null; } finally { clearTimeout(timer); }
}

async function find({ roots = defaultRoots(), seeds = [], timeLimit = 4000, maxFolders = 60000, onProgress = () => {} } = {}) {
  const t0 = Date.now(), ports = shipid.ports();
  const byExe = new Map(), byArchive = new Map();
  for (const p of ports) { for (const e of p.exe || []) byExe.set(e, p); for (const a of p.archives) byArchive.set(a + '.o2r', p).set(a + '.otr', p); }
  const found = {}, seen = new Set();
  const hot = [], queue = [];
  const key = (d) => (process.platform === 'win32' ? d.toLowerCase() : d);
  const push = (dir, depth, isHot) => { const k = key(dir); if (!seen.has(k)) { seen.add(k); (isHot ? hot : queue).push({ dir, depth, hot: isHot }); } };
  for (const s of seeds) if (s) { push(s, 2, true); push(path.dirname(s), 3, true); }
  for (const r of roots) push(r.dir, r.depth, false);
  let folders = 0;

  const note = (p, dir, how, file) => {
    const f = found[p.name] || (found[p.name] = { name: p.name, game: p.game, dir, exe: '', portArchive: '', archive: '', archives: [], how: [] });
    if (how === 'exe' && !f.exe) { f.exe = path.join(dir, file); f.dir = dir; }
    if (how === 'port archive' && !f.portArchive) f.portArchive = path.join(dir, file);
    if (how === 'game archive' && !f.archives.includes(path.join(dir, file))) f.archives.push(path.join(dir, file));
    if (!f.how.includes(how)) f.how.push(how);
  };
  const visit = async ({ dir, depth, hot: isHot }) => {
    const l = await list(dir, 400); folders++;
    if (!l) return;
    let hit = false;
    for (const name of l.files) {
      const n = name.toLowerCase();
      if (n.endsWith('.exe') && byExe.has(n)) { note(byExe.get(n), dir, 'exe', name); hit = true; }
      else if ((n.endsWith('.o2r') || n.endsWith('.otr')) && byArchive.has(n)) {
        const p = byArchive.get(n), id = shipid.identify(path.join(dir, name));
        if (id.kind === 'port') note(p, dir, 'port archive', name);
        else if (id.key && id.key === p.game) note(p, dir, 'game archive', name);
        else note(p, dir, 'port archive', name);
        hit = true;
      }
    }
    // A port folder may hold a renamed game archive: its version file still names the game.
    if (hit) for (const name of l.files) {
      if (!/\.o2r$/i.test(name)) continue;
      const id = shipid.identify(path.join(dir, name));
      const p = id.kind === 'game' && ports.find((x) => x.game === id.key);
      if (p) note(p, dir, 'game archive', name);
    }
    if (hit) { push(path.dirname(dir), 3, true); push(path.dirname(path.dirname(dir)), 3, true); }   // neighbours next
    if (depth > 0) for (const d of l.dirs) if (!SKIP.has(d.toLowerCase()) && !d.startsWith('.') && !d.startsWith('$')) push(path.join(dir, d), depth - 1, isHot || hit);
  };

  const allFound = () => Object.keys(found).length >= ports.length;
  const outOfTime = () => Date.now() - t0 > timeLimit || folders >= maxFolders;
  let active = 0;
  const workers = Array.from({ length: 12 }, async () => {
    while (!allFound() && !outOfTime()) {
      const item = hot.shift() || queue.shift();
      if (!item) { if (!active) break; await new Promise((r) => setTimeout(r, 2)); continue; }   // others may still add folders
      active++;
      try { await visit(item); } finally { active--; }
      if (folders % 500 === 0) onProgress(folders, Object.keys(found).length);
    }
  });
  await Promise.all(workers);
  for (const [name, f] of Object.entries(found)) {
    // Prefer the game archive next to the port's program (a copy elsewhere is only a fallback),
    // then see whether it's there and made by the installed build (shipcheck.js).
    const home = f.exe ? path.dirname(f.exe) : f.portArchive ? path.dirname(f.portArchive) : '';
    const archive = f.archives.find((a) => path.dirname(a) === home) || f.archives[0] || '';
    const dir = home || path.dirname(archive);
    const how = f.how;
    found[name] = { ...shipcheck.checkPort(ports.find((p) => p.name === name), dir, { ...f, archive }), how, installed: true };
  }
  return {
    ports: ports.map((p) => found[p.name] || { name: p.name, game: p.game, installed: false, state: 'missing', message: `${p.name} wasn’t found on this PC` }),
    folders, ms: Date.now() - t0, complete: allFound() || (!hot.length && !queue.length),   // false: stopped at the time / folder limit
  };
}

module.exports = { find, defaultRoots, SKIP };
