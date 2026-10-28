'use strict';
// R64texHD - classic texture packs (Rice / GLideN64) with RT64, GLideN64 and Ship ports.
// Copyright (C) 2026 R64texHD contributors. GPL-2.0-or-later (see LICENSE).
const fs = require('fs');
const path = require('path');
const png = require('./png');
const rice = require('./rice');
const o2r = require('./o2r');
const { loadImage } = require('./image');
const { Database, listFiles, DATABASE } = require('./rt64db');

const keyFull = (e) => rice.riceId(e).toLowerCase();
const keyBase = (e) => `${rice.hex8(e.crc)}#${e.fmt}#${e.siz}`;
const cancelCheck = (cancelled) => { if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true }); };

// Use in RT64: match a classic pack to an RT64 dump's Rice IDs (rt64.json from Convert with Add Rice IDs)
// and write a normal RT64 pack folder: textures/<rt64 hash>.png + rt64.json.
function importToRt64(input, dumpDir, outDir, { progress = () => {}, cancelled = () => false } = {}) {
  const dbFile = path.join(dumpDir, DATABASE);
  if (!fs.existsSync(dbFile)) throw new Error('That folder has no rt64.json. Pick the folder you made with 2 · Convert RT64 Dump (Add Rice IDs on).');
  const src = Database.load(dbFile);
  const byFull = new Map(), byBase = new Map();
  for (const t of src.textures) {
    const r = rice.parseRiceId(t.hashes.rice);
    if (!r || !t.hashes.rt64) continue;
    byFull.set(keyFull(r), t.hashes.rt64);
    if (!byBase.has(keyBase(r))) byBase.set(keyBase(r), t.hashes.rt64);
  }
  if (!byFull.size) throw new Error('That rt64.json has no Rice IDs. Convert your RT64 dump again with “Add Rice IDs” on.');
  const pack = readPack(input);
  const out = new Database();
  out.config.hashVersion = src.config.hashVersion;
  fs.mkdirSync(path.join(outDir, 'textures'), { recursive: true });
  let matched = 0;
  const seen = new Set();
  pack.forEach((e, i) => {
    cancelCheck(cancelled);
    const hash = byFull.get(keyFull(e)) || (!e.pal ? byBase.get(keyBase(e)) : null);
    if (!hash || seen.has(hash)) return;
    seen.add(hash);
    const rel = `textures/${hash}.png`, target = path.join(outDir, rel);
    if (e.file && e.kind !== 'rgb') fs.copyFileSync(e.file, target + '.part');   // a Rice PNG: copied as it is
    else fs.writeFileSync(target + '.part', png.encodePNG(e.load(), 6));
    fs.renameSync(target + '.part', target);
    out.add(hash, rel, rice.riceId(e));
    matched++;
    if (i % 25 === 0) progress(i + 1, pack.length, e.rel);
  });
  out.save(path.join(outDir, DATABASE));
  return { textures: pack.length, matched, dumpTextures: byFull.size };
}

// Make a GLideN64 pack (.hts) from a folder: textures listed in rt64.json with Rice IDs, and/or Rice-named PNGs.
function makeHts(input, outFile, { progress = () => {}, cancelled = () => false } = {}) {
  const entries = [], seen = new Set();
  const add = (e, load, label) => { const k = keyFull(e); if (seen.has(k)) return; seen.add(k); entries.push({ ...e, img: load, label }); };
  const dbFile = path.join(input, DATABASE);
  let fromDb = 0;
  if (fs.existsSync(dbFile)) {
    const db = Database.load(dbFile);
    const { resolved } = db.resolvePaths(listFiles(input));
    for (const t of db.textures) {
      const r = rice.parseRiceId(t.hashes.rice);
      const hit = resolved.get((t.hashes.rt64 || '').toLowerCase());
      if (!r || !hit) continue;
      add(r, () => loadImage(path.join(input, hit.rel)), hit.rel);
      fromDb++;
    }
  }
  let fromNames = 0;
  for (const e of rice.readClassicPack(input)) { const before = seen.size; add(e, e.load, e.rel); if (seen.size > before) fromNames++; }
  if (!entries.length) throw new Error('No textures with Rice IDs here. Use a folder made with Add Rice IDs on, or Rice-named PNGs.');
  cancelCheck(cancelled);
  const r = rice.writeHts(entries, outFile, { onEntry: (d, t) => { cancelCheck(cancelled); progress(d, t, `Adding ${entries[d - 1].label}`); } });
  return { ...r, fromDb, fromNames };
}

// Use in a Ship port: match a classic pack to the textures in a Ship .o2r by Rice ID and build an HD mod.
function riceToO2r(input, baseFile, outFile, { alt = true, compression = 'store', progress = () => {}, cancelled = () => false } = {}) {
  const pack = readPack(input);
  const base = o2r.readTextures(baseFile, { progress: (d, t) => progress(d, t * 2, 'Reading the game archive'), cancelled });
  const byKey = new Map();
  for (const t of base) {
    const r = rice.riceForTexture(t);
    if (!r) continue;
    const k = keyBase(r);
    if (!byKey.has(k)) byKey.set(k, []);
    byKey.get(k).push(t);
  }
  const pairs = [], used = new Set();
  let matched = 0;
  const unmatched = [];
  for (const e of pack) {
    cancelCheck(cancelled);
    const list = byKey.get(keyBase(e));
    if (!list) { unmatched.push(e.rel); continue; }
    let any = false;
    for (const t of list) {
      if (used.has(t.name)) continue;
      used.add(t.name); any = true;
      pairs.push({ t: { ...t, data: null }, img: e.load, label: e.rel });
    }
    if (any) matched++;
  }
  if (!pairs.length) throw new Error('No textures in this pack match the game archive. Is it a pack for this game?');
  const r = o2r.writeMod(pairs, outFile, { alt, compression, progress, cancelled, offset: base.length, total: base.length + pairs.length, note: o2r.modNote(baseFile) });
  return { written: r.written, matched, packTextures: pack.length, unmatched, resized: r.resized, bytesOut: r.bytesOut, game: o2r.gameOf(baseFile) };
}

function readPack(input) {
  const pack = rice.readClassicPack(input);
  if (!pack.length) throw new Error(fs.statSync(input).isFile() ? 'No textures in this pack file.' : 'No Rice-named PNGs here (like GAME#1A2B3C4D#0#2_all.png).');
  return pack;
}

// Quick look for the status cards.
function inspectPack(input) {
  const st = fs.statSync(input);
  if (st.isFile()) {
    if (/\.htc$/i.test(input)) return { kind: 'GLideN64 pack (.htc)', textures: -1 };   // reading the count means unpacking all of it
    return { kind: 'GLideN64 pack (.hts)', textures: rice.readGlidenPack(input).length };
  }
  return { kind: 'Rice pack', textures: rice.readClassicPack(input).length };
}

module.exports = { importToRt64, makeHts, riceToO2r, inspectPack };
