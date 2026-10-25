'use strict';
// rt64.json (RT64's replacement database) and its path resolution rules.
const fs = require('fs');
const path = require('path');

const DATABASE = 'rt64.json';
const LOW_MIP_CACHE = 'rt64-low-mip-cache.bin';
const KNOWN = ['.dds', '.png'];
const HASH_RE = /^[0-9a-fA-F]{16}$/;

const fwd = (p) => p.replace(/\\/g, '/');
const removeKnownExt = (p) => { const l = p.toLowerCase(); for (const e of KNOWN) if (l.endsWith(e)) return p.slice(0, -e.length); return p; };

function checkWildcard(s, pat) {
  let si = 0, pi = 0, star = -1, match = -1;
  while (si < s.length) {
    if (pi < pat.length && (pat[pi] === '?' || s[si] === pat[pi])) { si++; pi++; }
    else if (pi < pat.length && pat[pi] === '*') { star = pi; match = si; pi++; }
    else if (star !== -1) { match++; pi = star + 1; si = match; }
    else return false;
  }
  while (pi < pat.length && pat[pi] === '*') pi++;
  return pi === pat.length;
}

class Database {
  constructor() {
    this.config = { configurationVersion: 3, autoPath: 'rt64', defaultOperation: 'stream', defaultShift: 'half', hashVersion: 5 };
    this.textures = [];
    this.operationFilters = [];
    this.shiftFilters = [];
    this.extraFiles = [];
  }

  static fromJSON(j) {
    const db = new Database();
    const c = j.configuration || {};
    const version = Number(c.configurationVersion ?? 1);
    db.config = {
      configurationVersion: 3, autoPath: c.autoPath ?? 'rt64', defaultOperation: c.defaultOperation ?? 'stream',
      defaultShift: c.defaultShift ?? (version < 3 ? 'none' : 'half'), hashVersion: Number(c.hashVersion ?? 1),
    };
    db.textures = (j.textures || []).map((t) => {
      const h = t.hashes || {};
      const e = { path: t.path || '', hashes: { rt64: h.rt64 ?? h.rt64v1 ?? '', rice: h.rice ?? '' } };
      if (t.operation && t.operation !== 'auto') e.operation = t.operation;
      if (t.shift && t.shift !== 'auto') e.shift = t.shift;
      return e;
    });
    db.operationFilters = (j.operationFilters || []).map((f) => ({ wildcard: fwd(f.wildcard || ''), operation: f.operation || 'stream' }));
    db.shiftFilters = (j.shiftFilters || []).map((f) => ({ wildcard: fwd(f.wildcard || ''), shift: f.shift || 'half' }));
    db.extraFiles = [...(j.extraFiles || [])];
    return db;
  }

  static load(file) {
    return Database.fromJSON(JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, '')));
  }

  toJSON() {
    return { configuration: { ...this.config }, textures: this.textures, operationFilters: this.operationFilters, shiftFilters: this.shiftFilters, extraFiles: this.extraFiles };
  }

  text() { return JSON.stringify(this.toJSON(), null, 4) + '\n'; }

  save(file) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file + '.part', this.text());
    fs.renameSync(file + '.part', file);
  }

  add(hash, p, rice = '') {
    hash = hash.toLowerCase();
    const found = this.textures.find((t) => t.hashes.rt64.toLowerCase() === hash);
    if (found) found.path = fwd(p);
    else this.textures.push({ path: fwd(p), hashes: { rt64: hash, rice } });
  }

  resolveOperation(rel, op) {
    if (op && op !== 'auto') return op;
    let r = this.config.defaultOperation || 'stream';
    for (const f of this.operationFilters) if (checkWildcard(rel, f.wildcard)) r = f.operation;
    return r;
  }

  // files: relative paths with forward slashes. Returns { resolved: Map(hash -> {rel, operation}), missing: [] }.
  resolvePaths(files, onlyDDS = false) {
    files = files.map(fwd);
    const byLower = new Map();
    for (const f of files) if (!byLower.has(f.toLowerCase())) byLower.set(f.toLowerCase(), f);
    const auto = new Map();
    const rice = this.config.autoPath === 'rice';
    for (const f of files) {
      const name = f.split('/').pop();
      if (!KNOWN.some((e) => name.toLowerCase().endsWith(e))) continue;
      if (rice) {
        const a = name.indexOf('#'), b = name.lastIndexOf('_');
        if (a !== -1 && b !== -1 && b > a) auto.set(name.slice(a + 1, b).toLowerCase(), f);
      } else {
        const dot = name.indexOf('.');
        if (dot !== -1) auto.set(name.slice(0, dot).toLowerCase(), f);
      }
    }
    const resolved = new Map(), missing = [];
    const add = (h, rel, op) => { h = h.toLowerCase(); if (!resolved.has(h)) resolved.set(h, { rel, operation: this.resolveOperation(rel, op) }); };
    for (const t of this.textures) {
      const h = t.hashes.rt64;
      if (!h) continue;
      if (t.path) {
        const base = removeKnownExt(fwd(t.path));
        let found = false;
        for (let i = 0; i < KNOWN.length; i++) {
          const real = byLower.get((base + KNOWN[i]).toLowerCase());
          if (real !== undefined) { if (!onlyDDS || i === 0) add(h, real, t.operation); found = true; break; }
        }
        if (!found) missing.push(h);
      } else {
        const real = auto.get((rice ? t.hashes.rice : h).toLowerCase());
        if (real !== undefined) add(h, real, t.operation);
      }
    }
    return { resolved, missing };
  }
}

function listFiles(folder) {
  const out = [];
  const walk = (dir, rel) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const r = rel ? rel + '/' + e.name : e.name;
      if (e.isDirectory()) walk(path.join(dir, e.name), r);
      else if (e.isFile()) out.push(r);
    }
  };
  walk(folder, '');
  return out.sort();
}

// rt64.json for hash-named textures (<16 hex>[.anything].png/.dds). Returns { db, skipped }.
function databaseFromFiles(files, hashVersion = 5) {
  const db = new Database();
  db.config.hashVersion = hashVersion;
  const chosen = new Map(), skipped = [];
  for (const f of [...files].sort()) {
    const name = f.split('/').pop();
    if (!KNOWN.some((e) => name.toLowerCase().endsWith(e))) continue;
    const h = name.split('.')[0];
    if (!HASH_RE.test(h)) { skipped.push(f); continue; }
    const k = h.toLowerCase();
    if (!chosen.has(k) || f.toLowerCase().endsWith('.dds')) chosen.set(k, f);
  }
  for (const k of [...chosen.keys()].sort()) db.add(k, chosen.get(k));
  return { db, skipped };
}

function detectHashVersion(files) {
  for (const f of files) { const m = /^[0-9a-fA-F]{16}\.v(\d+)\./.exec(f.split('/').pop()); if (m) return Number(m[1]); }
  return null;
}

module.exports = { Database, listFiles, databaseFromFiles, detectHashVersion, checkWildcard, removeKnownExt, fwd, DATABASE, LOW_MIP_CACHE, KNOWN };
