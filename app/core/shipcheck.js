'use strict';
// 4 · Ship Mods: is a port's game archive there, and was it made by the port build that's installed?
//
// The ports keep their build number in "portVersion", a small file Torch / the port's extractor
// writes into every archive: an endianness byte (0 little, 1 big) then u16 major, minor, patch
// (Torch's ParseVersionString; without the endianness byte it's 6 bytes, big-endian).
//   - The port's own archive (soh.o2r, 2ship.o2r...) ships with each release: that's the build.
//   - The game archive (oot.o2r, mm.o2r...) gets the build that made it from your ROM.
// Ship of Harkinian asks to make the game archive again when the majors differ
// (OTRGlobals.cpp VerifyArchiveVersion), and an archive with no portVersion reads as 0.0.0, so it
// counts as outdated too. When the port has no archive of its own, the program's file version
// (Windows version resource) stands in for the build.
//
// Everything is read fresh on each call: the port may have been run (or updated) since the last look.
const fs = require('fs');
const path = require('path');
const archive = require('./archive');
const shipid = require('./shipid');

// "portVersion" bytes -> { major, minor, patch, text } or null.
function readPortVersion(buf) {
  if (!buf || buf.length < 6) return null;
  let o = 0, big = true;
  if (buf.length >= 7) { big = buf[0] !== 0; o = 1; }
  const u16 = (i) => (big ? buf.readUInt16BE(o + i * 2) : buf.readUInt16LE(o + i * 2));
  const v = { major: u16(0), minor: u16(1), patch: u16(2) };
  if (v.major === 0x7fff) return null;                       // INT16_MAX: "no version" in the ports
  v.text = `${v.major}.${v.minor}.${v.patch}`;
  return v;
}

// The portVersion inside an archive: a version, null when it has none, undefined when it can't be read.
function archiveVersion(file) {
  let entries;
  try { entries = archive.entries(file); } catch { return undefined; }
  const e = entries.find((x) => x.name === 'portVersion');
  if (!e) return null;
  try { return readPortVersion(archive.read(file, e)); } catch { return undefined; }
}

// A Windows program's file version from its version resource (VS_FIXEDFILEINFO), or null.
function exeVersion(file) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
    const at = (len, pos) => { const b = Buffer.alloc(len); const n = fs.readSync(fd, b, 0, len, pos); return b.subarray(0, n); };
    const dos = at(64, 0);
    if (dos.length < 64 || dos.toString('latin1', 0, 2) !== 'MZ') return null;
    const pe = dos.readUInt32LE(0x3c), head = at(24, pe);
    if (head.length < 24 || head.readUInt32LE(0) !== 0x4550) return null;
    const nSec = head.readUInt16LE(6), optSize = head.readUInt16LE(20), opt = pe + 24;
    const o = at(optSize, opt);
    const dirs = o.readUInt16LE(0) === 0x20b ? 112 : 96;
    if (o.length < dirs + 24) return null;
    const rva = o.readUInt32LE(dirs + 16), size = o.readUInt32LE(dirs + 20);     // data directory 2: resources
    if (!rva || !size) return null;
    const secs = at(nSec * 40, opt + optSize);
    for (let i = 0; i < nSec; i++) {
      const va = secs.readUInt32LE(i * 40 + 12), raw = secs.readUInt32LE(i * 40 + 16), ptr = secs.readUInt32LE(i * 40 + 20);
      if (rva < va || rva >= va + raw) continue;
      const rsrc = at(Math.min(size, raw - (rva - va), 16 << 20), ptr + (rva - va));
      const sig = Buffer.from([0xbd, 0x04, 0xef, 0xfe]);
      for (let p = rsrc.indexOf(sig); p >= 0; p = rsrc.indexOf(sig, p + 4)) {
        if (p + 24 > rsrc.length || p % 4) continue;
        const ms = rsrc.readUInt32LE(p + 8), ls = rsrc.readUInt32LE(p + 12);
        const v = { major: ms >>> 16, minor: ms & 0xffff, patch: ls >>> 16 };
        if (!v.major && !v.minor && !v.patch) return null;
        v.text = `${v.major}.${v.minor}.${v.patch}`;
        return v;
      }
      return null;
    }
    return null;
  } catch { return null; } finally { if (fd !== undefined) try { fs.closeSync(fd); } catch { /* ignore */ } }
}

const exists = (f) => { try { return !!f && fs.statSync(f).isFile(); } catch { return false; } };
const isDir = (d) => { try { return !!d && fs.statSync(d).isDirectory(); } catch { return false; } };

// One port in one folder, looked at now. `p` is the port from ports.json; `prev` what an earlier
// search found (kept for archives that live elsewhere and the archive picked before).
function checkPort(p, dir, prev = {}) {
  const out = { name: p.name, game: p.game, installed: false, dir, exe: '', portArchive: '', archive: '', archives: [], mods: dir ? path.join(dir, 'mods') : '',
    build: null, buildFrom: '', version: null, generated: false, state: 'missing', message: '' };
  if (!isDir(dir)) { out.message = `${p.name} wasn’t found on this PC`; return out; }
  let files = [];
  try { files = fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isFile()).map((e) => e.name); } catch { /* unreadable */ }
  const exes = (p.exe || []).map((e) => e.toLowerCase());
  for (const name of files) {
    const n = name.toLowerCase(), full = path.join(dir, name);
    if (n.endsWith('.exe') && exes.includes(n)) { if (!out.exe) out.exe = full; continue; }
    if (!/\.(o2r|otr)$/.test(n)) continue;
    const base = n.replace(/\.(o2r|otr)$/, '');
    const id = shipid.identify(full);
    if (id.kind === 'port' && p.archives.includes(base)) { if (!out.portArchive) out.portArchive = full; }
    else if (id.kind === 'game' && id.key === p.game) out.archives.push(full);
  }
  // Same order as the port's own list (oot before oot-mq), then the rest.
  const rank = (f) => { const i = p.archives.indexOf(path.basename(f).toLowerCase().replace(/\.(o2r|otr)$/, '')); return i < 0 ? 99 : i; };
  out.archives.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  for (const a of prev.archives || []) if (!out.archives.includes(a) && exists(a)) out.archives.push(a);   // copies elsewhere: fallback only
  out.installed = !!(out.exe || out.portArchive || out.archives.some((a) => path.dirname(a) === dir));
  if (!out.installed) { out.message = `${p.name} is no longer in ${dir}`; return out; }
  // Only an archive in the port's own folder counts as made by it (copies elsewhere are listed, not used).
  out.archive = out.archives.includes(prev.archive) && path.dirname(prev.archive) === dir ? prev.archive
    : out.archives.find((a) => path.dirname(a) === dir) || '';
  // The build that's installed.
  if (out.portArchive) { const v = archiveVersion(out.portArchive); if (v) { out.build = v; out.buildFrom = path.basename(out.portArchive); } }
  if (!out.build && out.exe) { const v = exeVersion(out.exe); if (v) { out.build = v; out.buildFrom = path.basename(out.exe); } }
  Object.assign(out, judge(p.name, out.archive, out.build));
  return out;
}

// Is this game archive there and made by this build? -> { generated, version, state, message }
function judge(portName, file, build) {
  if (!exists(file)) {
    return { generated: false, version: null, state: 'not-generated',
      message: `${portName} hasn’t made its game archive yet: run it once and give it your ROM.` };
  }
  const v = archiveVersion(file);
  const name = path.basename(file);
  if (v === undefined) return { generated: true, version: null, state: 'unreadable', message: `${name} can’t be read: it may be damaged. Let ${portName} make it again.` };
  if (!build) {
    return { generated: true, version: v, state: 'ready',
      message: `${name} is there${v ? ` (made by ${portName} ${v.text})` : ''}. The installed build’s version couldn’t be read, so it can’t be compared.` };
  }
  if (!v || v.major !== build.major) {
    return { generated: true, version: v, state: 'outdated',
      message: `${name} was made by ${v ? `${portName} ${v.text}` : 'an older build'}, but version ${build.text} is installed. Open ${portName} and let it make the archive again from your ROM, then check again.` };
  }
  return { generated: true, version: v, state: 'ready', message: `${name} matches ${portName} ${build.text}.` };
}

// Checks again every port an earlier search found (or didn't). Ports not found stay not found:
// only Search again looks for new places.
function checkPorts(found = []) {
  return shipid.ports().map((p) => {
    const f = found.find((x) => x && x.name === p.name);
    if (!f || !f.installed) return { name: p.name, game: p.game, installed: false, state: 'missing', message: `${p.name} wasn’t found on this PC` };
    const home = f.exe ? path.dirname(f.exe) : f.portArchive ? path.dirname(f.portArchive) : f.dir;
    return checkPort(p, home, f);
  });
}

// A game archive picked by hand or from a port: which game and port, and is it current for the
// port build in the same folder?
// `ports` (from checkPorts) supplies the build when the archive is kept somewhere else.
function checkTarget(file, ports = []) {
  const id = shipid.identify(file);
  const r = { file, id, state: '', message: '', build: null, version: null };
  if (!file) return r;
  let isFolder = false; try { isFolder = fs.statSync(file).isDirectory(); } catch { /* gone */ }
  if (isFolder) return r;                                      // a texture folder: nothing to compare
  if (!exists(file)) { r.state = 'not-generated'; r.message = `${path.basename(file)} isn’t there any more. Run the port to make it, or pick it again.`; return r; }
  if (id.kind !== 'game' || !id.port) return r;                // mods and port archives: nothing to compare
  const p = shipid.ports().find((x) => x.name === id.port.name);
  const here = checkPort(p, path.dirname(file), { archive: file });
  const elsewhere = ports.find((x) => x && x.name === p.name && x.installed && x.build);
  const build = here.build || (elsewhere && elsewhere.build) || null;
  r.build = build;
  Object.assign(r, judge(p.name, file, build));
  if (!build) r.message = `${path.basename(file)} is there, but no installed ${p.name} build was found to compare it with.`;
  return r;
}

module.exports = { readPortVersion, archiveVersion, exeVersion, checkPort, checkPorts, checkTarget, judge };
