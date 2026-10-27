'use strict';
// Remembers how each RT64 texture repeats (its edges), so Upscale can keep repeating textures
// seamless without the user sorting them by hand ("Edges: Auto").
//
// Convert RT64 Dump writes r64texhd-tiling.json next to rt64.json:
//   { "version": 1, "textures": { "<16 hex hash>": ["wrap" | "mirror" | "clamp", <y axis>] } }
// RT64 ignores the file and the .rtz packer leaves it out.
const fs = require('fs');
const path = require('path');

const TILING = 'r64texhd-tiling.json';
const MODES = new Set(['wrap', 'mirror', 'clamp']);
const HASH_RE = /(?:^|[^0-9a-f])([0-9a-f]{16})(?![0-9a-f])/i;

function save(folder, map) {
  const textures = {};
  for (const k of [...map.keys()].sort()) textures[k] = map.get(k);
  const file = path.join(folder, TILING);
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(file + '.part', JSON.stringify({ version: 1, textures }, null, 1) + '\n');
  fs.renameSync(file + '.part', file);
  return file;
}

function load(file) {
  const out = new Map();
  try {
    const j = JSON.parse(fs.readFileSync(file, 'utf8'));
    for (const [h, e] of Object.entries(j.textures || {})) {
      if (Array.isArray(e) && e.length === 2 && MODES.has(e[0]) && MODES.has(e[1])) out.set(h.toLowerCase(), e);
    }
  } catch { /* missing or unreadable: no tiling info */ }
  return out;
}

// The tiling info for a set of input folders: looks in each folder and the two folders above it
// (so picking the "textures" subfolder of a converted dump still finds it).
function loadFor(roots) {
  const map = new Map();
  const seen = new Set();
  for (const r of roots) {
    let dir = path.resolve(r);
    try { if (!fs.statSync(dir).isDirectory()) dir = path.dirname(dir); } catch { continue; }
    for (let i = 0; i < 3; i++) {
      const f = path.join(dir, TILING);
      if (!seen.has(f) && fs.existsSync(f)) { seen.add(f); for (const [k, v] of load(f)) if (!map.has(k)) map.set(k, v); }
      const up = path.dirname(dir);
      if (up === dir) break;
      dir = up;
    }
  }
  return map;
}

const hashOf = (file) => { const m = HASH_RE.exec(path.basename(file)); return m ? m[1].toLowerCase() : null; };

// Edges for one texture: the chosen mode, or (auto) what the dump said, falling back to clamp.
function edgesFor(file, mode, map) {
  if (mode !== 'auto') return [mode, mode];
  const h = hashOf(file);
  return (h && map && map.get(h)) || ['clamp', 'clamp'];
}

module.exports = { TILING, save, load, loadFor, hashOf, edgesFor };
