'use strict';
// Footer scene clips: the starter set ships inside the app (app/assets/scenes: classic scenes, peeks, the busy
// peek, re-robe); fights and trips download once into the data folder's "scenes" folder.
//   index(appDir, dataDir)   the clip index with only the clips that are here, each with its folder URL
//   clipFile(id, ...)        where a clip's clip.json is
//   install(zip, dataDir)    unpacks a downloaded scenes pack (only clip folders with safe names)
//   missing(appDir, dataDir) ids in the index that aren't here yet
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const ID = /^[a-z0-9_]+$/;
const FILE = /^[a-z0-9_]+\.(json|webp|png)$/;

function readIndex(appDir) { return JSON.parse(fs.readFileSync(path.join(appDir, 'index.json'), 'utf8')); }
const here = (dir, id) => fs.existsSync(path.join(dir, id, 'clip.json'));
function where(id, appDir, dataDir) {
  if (!ID.test(id)) return null;
  if (here(appDir, id)) return path.join(appDir, id);
  if (dataDir && here(dataDir, id)) return path.join(dataDir, id);
  return null;
}

function index(appDir, dataDir) {
  const all = readIndex(appDir), out = {};
  for (const [id, meta] of Object.entries(all)) {
    const dir = where(id, appDir, dataDir);
    if (dir) out[id] = { ...meta, base: pathToFileURL(dir).href + '/' };
  }
  return { index: out, total: Object.keys(all).length, here: Object.keys(out).length };
}

function missing(appDir, dataDir) { return Object.keys(readIndex(appDir)).filter((id) => !where(id, appDir, dataDir)); }

function clipFile(id, appDir, dataDir) { const dir = where(id, appDir, dataDir); return dir ? path.join(dir, 'clip.json') : null; }

// entries: [{ name, data: () => Buffer }] (from the zip reader). Writes <dataDir>/<id>/<file> for safe names only.
function install(entries, dataDir) {
  let files = 0; const ids = new Set();
  for (const e of entries) {
    const parts = e.name.replace(/\\/g, '/').split('/').filter(Boolean);
    if (parts.length !== 2 || !ID.test(parts[0]) || !FILE.test(parts[1])) continue;
    const dir = path.join(dataDir, parts[0]);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, parts[1] + '.part'), e.data());
    fs.renameSync(path.join(dir, parts[1] + '.part'), path.join(dir, parts[1]));
    files++; ids.add(parts[0]);
  }
  return { files, clips: ids.size };
}

module.exports = { index, missing, clipFile, install, where };
