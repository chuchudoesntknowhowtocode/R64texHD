'use strict';
// The toolkit's processes: 1) upscale textures, 2) convert an RT64 dump, 3) pack to .rtz.
// Each runs on a pool of worker threads and reports progress / log lines through `ctx`.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Worker } = require('worker_threads');
const { spawn } = require('child_process');
const { findDumps, loadDump } = require('./tmem');
const { Database, listFiles, DATABASE } = require('./rt64db');
const rtz = require('./rtz');
const tiling = require('./tiling');

const IMAGE_RE = /\.(png|dds)$/i;
const WORKER = path.join(__dirname, 'worker.js');

class Cancelled extends Error { constructor() { super('Cancelled'); this.cancelled = true; } }

class Pool {
  constructor(size) {
    this.size = Math.max(1, size);
    this.workers = [];
    this.queue = [];
    this.pending = new Map();
    this.nextId = 1;
    this.closed = false;
  }
  spawnWorker() {
    const w = new Worker(WORKER);
    w.busy = null;
    w.on('message', (m) => {
      const p = this.pending.get(m.id);
      if (!p) return;
      if (m.progress) { p.onProgress && p.onProgress(...m.progress); return; }
      this.pending.delete(m.id);
      w.busy = null;
      if (m.ok) p.resolve(m.result); else p.reject(new Error(m.error));
      this.pump();
    });
    w.on('error', (e) => { if (w.busy) { const p = this.pending.get(w.busy); this.pending.delete(w.busy); p && p.reject(e); } this.drop(w); });
    w.on('exit', (code) => { if (w.busy && !this.closed) { const p = this.pending.get(w.busy); this.pending.delete(w.busy); p && p.reject(new Error('worker stopped (out of memory?)')); } this.drop(w); });
    this.workers.push(w);
    return w;
  }
  drop(w) { this.workers = this.workers.filter((x) => x !== w); if (!this.closed) this.pump(); }
  run(kind, job, onProgress) {
    if (this.closed) return Promise.reject(new Cancelled());
    return new Promise((resolve, reject) => {
      const id = this.nextId++;
      this.pending.set(id, { resolve, reject, onProgress });
      this.queue.push({ id, kind, job });
      this.pump();
    });
  }
  pump() {
    while (this.queue.length) {
      let w = this.workers.find((x) => !x.busy);
      if (!w && this.workers.length < this.size) w = this.spawnWorker();
      if (!w) return;
      const item = this.queue.shift();
      w.busy = item.id;
      w.postMessage(item);
    }
  }
  async close() {
    this.closed = true;
    for (const { id } of this.queue) { const p = this.pending.get(id); this.pending.delete(id); p && p.reject(new Cancelled()); }
    this.queue = [];
    for (const [id, p] of this.pending) { this.pending.delete(id); p.reject(new Cancelled()); }
    await Promise.all(this.workers.map((w) => w.terminate()));
    this.workers = [];
  }
}

// Runs fn over items with the pool, counting progress; failures are logged and counted, not fatal.
async function runAll(pool, items, kind, makeJob, ctx, label) {
  let done = 0, failed = 0;
  const results = [];
  await Promise.all(items.map((it, i) => pool.run(kind, makeJob(it)).then((r) => { results[i] = r; }, (e) => {
    if (e instanceof Cancelled || ctx.cancelled()) return;
    failed++;
    if (failed <= 25) ctx.log(`Failed ${it.rel || path.basename(it.src)}: ${e.message}`);
  }).finally(() => {
    done++;
    if (!ctx.cancelled()) ctx.progress(done, items.length, label(it));
  })));
  if (ctx.cancelled()) throw new Cancelled();
  if (failed > 25) ctx.log(`... ${failed} failed in total`);
  return { results, failed };
}

// Removes .part files left by writes that a cancel interrupted.
function cleanupParts(dir) {
  const walk = (d) => {
    let entries; try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const f = path.join(d, e.name);
      if (e.isDirectory()) walk(f); else if (e.name.endsWith('.part')) fs.rmSync(f, { force: true });
    }
  };
  walk(dir);
}

function sameFolder(a, b) { return path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase(); }
function inside(child, parent) { const r = path.relative(path.resolve(parent), path.resolve(child)); return r && !r.startsWith('..') && !path.isAbsolute(r); }

// ---------------------------------------------------------------- inspect (status card)
function walkCount(folder, limit = 500000) {
  let png = 0, dds = 0, other = 0, dumps = 0, n = 0, db = false;
  const walk = (dir) => {
    let entries; try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (++n > limit) return;
      if (e.isDirectory()) walk(path.join(dir, e.name));
      else if (/\.png$/i.test(e.name)) png++;
      else if (/\.dds$/i.test(e.name)) dds++;
      else if (/^[0-9a-f]{16}\.v\d+\.tmem$/i.test(e.name)) dumps++;
      else { other++; if (e.name === DATABASE && dir === folder) db = true; }
    }
  };
  walk(folder);
  return { png, dds, other, dumps, db, truncated: n > limit };
}

function inspect(kind, value) {
  const list = Array.isArray(value) ? value : (value ? [value] : []);
  if (!list.length) return { state: 'idle', title: 'Choose an input', text: '' };
  const missing = list.filter((p) => !fs.existsSync(p));
  if (missing.length) return { state: 'error', title: 'Not found', text: missing[0] };
  if (kind === 'pack-output') return { state: 'ready', title: 'Ready', text: list[0] };
  if (kind === 'unpack') {
    if (!fs.statSync(list[0]).isFile()) return { state: 'error', title: 'Not a file', text: 'Choose an .rtz pack file.\n' + list[0] };
    let info;
    try { info = rtz.inspect(list[0]); } catch (e) { return { state: 'error', title: 'Not an .rtz pack', text: `${e.message}\n${list[0]}` }; }
    const methods = Object.keys(info.methods).join(', ');
    return { state: 'ready', title: 'Ready', text: `.rtz pack: ${info.textures.toLocaleString()} textures (${info.dds.toLocaleString()} DDS, ${info.png.toLocaleString()} PNG), ${(info.size / 1048576).toFixed(1)} MB unpacked, ${methods}${info.hasDatabase ? ', rt64.json' : ''}\n${list[0]}` };
  }
  const p = list[0];
  const st = fs.statSync(p);
  if (kind === 'upscale') {
    if (list.length > 1 || st.isFile()) {
      const images = list.filter((f) => IMAGE_RE.test(f));
      return images.length ? { state: 'ready', title: 'Ready', text: `${images.length} image${images.length === 1 ? '' : 's'} selected\n${list.length > 1 ? path.dirname(p) : p}` }
        : { state: 'error', title: 'Not usable here', text: 'Choose PNG or DDS images, or a folder of them' };
    }
    const c = walkCount(p);
    const n = c.png + c.dds;
    return n ? { state: 'ready', title: 'Ready', text: `${n.toLocaleString()} images (${c.png.toLocaleString()} PNG, ${c.dds.toLocaleString()} DDS)${c.other ? `, ${c.other.toLocaleString()} other files` : ''}\n${p}` }
      : { state: 'error', title: 'No images here', text: (c.dumps ? 'This is an RT64 texture dump: use 2 · Convert RT64 Dump first.\n' : 'No PNG or DDS files in this folder.\n') + p };
  }
  if (kind === 'convert') {
    if (!st.isDirectory()) return { state: 'error', title: 'Not a folder', text: p };
    const { files, problems } = findDumps(p);
    if (!files.length) return { state: 'error', title: 'No RT64 dumps here', text: `No <hash>.v<N>.tmem files with .tile.json in this folder.\n${p}` };
    const v = loadDump(files[0]).version;
    return { state: 'ready', title: 'Ready', text: `RT64 texture dump: ${files.length.toLocaleString()} textures (hash v${v})${problems.length ? `, ${problems.length} incomplete` : ''}\n${p}` };
  }
  if (kind === 'pack') {
    if (!st.isDirectory()) return { state: 'error', title: 'Not a folder', text: p };
    const c = walkCount(p);
    const n = c.png + c.dds;
    if (!n) return { state: 'error', title: 'No textures here', text: `No PNG or DDS files in this folder.\n${p}` };
    return { state: 'ready', title: 'Ready', text: `${n.toLocaleString()} textures (${c.png.toLocaleString()} PNG, ${c.dds.toLocaleString()} DDS)${c.db ? ' with rt64.json' : ', no rt64.json (made from hash-named files)'}\n${p}` };
  }
  if (kind === 'roms') {
    if (!st.isDirectory()) return { state: 'error', title: 'Not a folder', text: p };
    let n = 0;
    const walk = (d, depth) => { let es; try { es = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
      for (const e of es) { if (n > 50000) return; if (e.isDirectory()) { if (depth < 12) walk(path.join(d, e.name), depth + 1); } else if (/\.(z64|v64|n64|rom|bin|u64|ndd|zip)$/i.test(e.name)) n++; } };
    walk(p, 0);
    return n ? { state: 'ready', title: 'Ready', text: `${n.toLocaleString()} possible ROM file(s) to look at\n${p}` }
      : { state: 'error', title: 'No N64 ROMs here', text: `No .z64, .v64, .n64 or .zip files in this folder or below.\n${p}` };
  }
  if (kind === 'check') {
    if (st.isFile()) {
      let info;
      try { info = rtz.inspect(p); } catch (e) { return { state: 'error', title: 'Not an .rtz pack', text: `${e.message}\n${p}` }; }
      return { state: 'ready', title: 'Ready', text: `.rtz pack: ${info.textures.toLocaleString()} textures (${info.dds.toLocaleString()} DDS, ${info.png.toLocaleString()} PNG), ${(info.size / 1048576).toFixed(0)} MB unpacked${info.hasRecomp ? ', Recomp mod info' : ''}\n${p}` };
    }
    const c = walkCount(p);
    if (!c.png && !c.dds) return { state: 'error', title: 'No textures here', text: `No PNG or DDS files in this folder.\n${p}` };
    return { state: 'ready', title: 'Ready', text: `Pack folder: ${(c.png + c.dds).toLocaleString()} textures (${c.png.toLocaleString()} PNG, ${c.dds.toLocaleString()} DDS)${c.db ? ' with rt64.json' : ''}\n${p}` };
  }
  if (kind === 'o2rExtract') {
    if (!st.isFile()) return { state: 'error', title: 'Not a file', text: 'Choose the game’s .o2r or .otr archive.\n' + p };
    try {
      const o = require('./o2r').inspect(p);
      return { state: 'ready', title: 'Ready', text: `${o.game} game archive: ${o.files.toLocaleString()} files, ${(o.size / 1048576).toFixed(0)} MB\n${p}` };
    } catch (e) { return { state: 'error', title: 'Can’t open this archive', text: `${e.message}\n${p}` }; }
  }
  if (kind === 'o2rBuild') {
    if (!st.isDirectory()) return { state: 'error', title: 'Not a folder', text: p };
    const n = require('./o2r').listPngs(p).length;
    const fromShip = fs.existsSync(path.join(p, require('./o2r').INFO_FILE));
    return n ? { state: 'ready', title: 'Ready', text: `${n.toLocaleString()} PNG textures${fromShip ? ' (from Extract Textures)' : ''}\n${p}` }
      : { state: 'error', title: 'No PNG textures here', text: `Ship mods are built from PNG: upscale with Output format PNG.\n${p}` };
  }
  if (kind === 'legacyImport' || kind === 'riceToO2r') {
    try {
      const r = require('./legacy').inspectPack(p);
      return r.textures ? { state: 'ready', title: 'Ready', text: `${r.kind}${r.textures > 0 ? `: ${r.textures.toLocaleString()} textures` : ''}\n${p}` }
        : { state: 'error', title: 'No classic textures here', text: `No Rice-named PNGs (like GAME#1A2B3C4D#0#2_all.png).\n${p}` };
    } catch (e) { return { state: 'error', title: 'Can’t read this pack', text: `${e.message}\n${p}` }; }
  }
  if (kind === 'legacyHts') {
    if (!st.isDirectory()) return { state: 'error', title: 'Not a folder', text: p };
    let withRice = 0;
    try { withRice = Database.load(path.join(p, DATABASE)).textures.filter((t) => t.hashes.rice).length; } catch { /* no rt64.json */ }
    const named = require('./rice').readClassicPack(p).length;
    return withRice || named ? { state: 'ready', title: 'Ready', text: `${(withRice + named).toLocaleString()} textures with Rice IDs\n${p}` }
      : { state: 'error', title: 'No Rice IDs here', text: `Convert your RT64 dump with Add Rice IDs on, or use Rice-named PNGs.\n${p}` };
  }
  return { state: 'idle', title: '', text: '' };
}

// ---------------------------------------------------------------- 1) upscale
function gatherImages(inputs, subfolders) {
  const items = [], others = [];
  const roots = [];
  for (const input of inputs) {
    const st = fs.statSync(input);
    if (st.isDirectory()) {
      roots.push(input);
      const files = subfolders ? listFiles(input) : fs.readdirSync(input, { withFileTypes: true }).filter((e) => e.isFile()).map((e) => e.name);
      for (const rel of files) {
        if (/\.part$/i.test(rel)) continue;
        if (IMAGE_RE.test(rel)) items.push({ src: path.join(input, rel), rel });
        else others.push({ src: path.join(input, rel), rel });
      }
    } else if (IMAGE_RE.test(input)) items.push({ src: input, rel: path.basename(input) });
  }
  return { items, others, roots };
}

async function upscaleTask(p, ctx, tools) {
  const t0 = Date.now();
  const inputs = (Array.isArray(p.inputs) ? p.inputs : [p.inputs]).filter(Boolean);
  if (!inputs.length) throw new Error('Choose a folder or images to upscale.');
  if (!p.output) throw new Error('Choose the output folder.');
  for (const i of inputs) {
    if (!fs.existsSync(i)) throw new Error('Not found: ' + i);
    if (fs.statSync(i).isDirectory() && sameFolder(i, p.output)) throw new Error('The output folder must be different from the input folder.');
  }
  const { items, others, roots } = gatherImages(inputs, p.subfolders !== false);
  if (!items.length) throw new Error('No PNG or DDS images found.');
  const opts = { size: p.size, fit: p.fit, maxSize: p.maxSize, method: p.method, sharpness: p.sharpness, hardAlpha: p.hardAlpha };
  const outInside = roots.some((r) => inside(p.output, r));
  const work = items.filter((it) => !(outInside && inside(it.src, p.output))).map((it) => {
    const fmt = p.format === 'same' ? path.extname(it.src).slice(1).toLowerCase() : p.format;
    const outNoExt = path.join(p.output, it.rel.replace(/\.(png|dds)$/i, ''));
    return { ...it, fmt, outNoExt };
  });
  let todo = work;
  if (p.existing === 'skip') {
    todo = work.filter((it) => !fs.existsSync(`${it.outNoExt}.${it.fmt}`));
    if (todo.length < work.length) ctx.log(`Skipping ${work.length - todo.length} image(s) that already exist in the output folder.`);
  }
  let ai = null;
  if (p.method === 'ai') {
    ai = tools.realesrgan;
    if (!ai) { ctx.log('Real-ESRGAN is not installed (Settings), so Standard is used instead.'); opts.method = 'standard'; }
  }
  const sizeText = p.size === 'fit' ? `to ${p.fit} px` : `${p.size}x`;
  ctx.log(`Upscaling ${todo.length.toLocaleString()} image(s) ${sizeText} with ${ai ? 'AI (Real-ESRGAN) + Standard' : { standard: 'Standard', smooth: 'Smooth', pixel: 'Pixel art' }[opts.method] || 'Standard'}${opts.method === 'standard' || ai ? `, sharpness ${p.sharpness || 'normal'}` : ''}.`);
  fs.mkdirSync(p.output, { recursive: true });
  if (p.copyOther !== false && others.length) {
    let copied = 0;
    for (const o of others) {
      if (outInside && inside(o.src, p.output)) continue;
      const dest = path.join(p.output, o.rel);
      if (p.existing === 'skip' && fs.existsSync(dest)) continue;
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(o.src, dest);
      copied++;
    }
    if (copied) ctx.log(`Copied ${copied} other file(s) (such as rt64.json) alongside.`);
  }
  const save = (it) => ({ format: it.fmt, ddsFormat: p.ddsFormat, texconv: tools.texconv, keepCoverage: p.keepCoverage !== false });
  // Edges: Auto uses each texture's own tiling from the RT64 dump (saved by Convert).
  const tileMap = p.edges === 'auto' ? tiling.loadFor(roots.length ? roots : inputs) : null;
  const edgesOf = (it) => tiling.edgesFor(it.src, p.edges || 'clamp', tileMap);
  if (tileMap) {
    const known = todo.filter((it) => { const h = tiling.hashOf(it.src); return h && tileMap.has(h); }).length;
    ctx.log(tileMap.size ? `Edges: Auto, tiling known for ${known.toLocaleString()} of ${todo.length.toLocaleString()} texture(s); the rest use Normal.`
      : 'Edges: Auto found no tiling info (convert the RT64 dump with “Remember tiling” on), so Normal is used.');
  }
  const pool = new Pool(ctx.workers);
  ctx.onCancel(() => pool.close());
  let failed = 0, written = 0;
  try {
    if (!ai) {
      const r = await runAll(pool, todo, 'upscale', (it) => ({ src: it.src, outNoExt: it.outNoExt, opts, edges: edgesOf(it), save: save(it) }), ctx, (it) => it.rel);
      failed = r.failed; written = r.results.filter(Boolean).length;
    } else {
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'htk-ai-'));
      try {
        const batch = 32;
        for (let s = 0; s < todo.length; s += batch) {
          const chunk = todo.slice(s, s + batch);
          const inDir = path.join(tmp, 'in'), outDir = path.join(tmp, 'out');
          fs.rmSync(inDir, { recursive: true, force: true }); fs.rmSync(outDir, { recursive: true, force: true });
          fs.mkdirSync(inDir, { recursive: true }); fs.mkdirSync(outDir, { recursive: true });
          const prepared = await Promise.all(chunk.map((it, i) => pool.run('aiPrep', { src: it.src, tmpPng: path.join(inDir, `${i}.png`), pad: 8, edges: edgesOf(it) }).then(() => true, (e) => { failed++; ctx.log(`Failed ${it.rel}: ${e.message}`); return false; })));
          if (ctx.cancelled()) throw new Cancelled();
          await runProcess(ai, aiArgs(inDir, outDir, tools), ctx);
          const ready = chunk.filter((_, i) => prepared[i] && fs.existsSync(path.join(outDir, `${i}.png`)));
          const idx = new Map(chunk.map((it, i) => [it, i]));
          const missingAi = chunk.filter((_, i) => prepared[i]).length - ready.length;
          if (missingAi) { failed += missingAi; ctx.log(`Real-ESRGAN produced no output for ${missingAi} image(s).`); }
          const r = await runAll(pool, ready, 'aiFinish', (it) => ({ src: it.src, aiPng: path.join(outDir, `${idx.get(it)}.png`), pad: 8, outNoExt: it.outNoExt, opts, edges: edgesOf(it), save: save(it) }),
            { ...ctx, progress: (d) => ctx.progress(s + d, todo.length, '') }, (it) => it.rel);
          failed += r.failed; written += r.results.filter(Boolean).length;
        }
      } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
    }
  } finally { await pool.close(); if (ctx.cancelled()) cleanupParts(p.output); }
  const fromO2r = roots.some((r) => fs.existsSync(path.join(r, require('./o2r').INFO_FILE)));
  return { title: 'Upscaled', written, failed, output: p.output, packable: written > 0, fromO2r, seconds: (Date.now() - t0) / 1000 };
}

// Real-ESRGAN command line: model, 4x, PNG, plus the graphics card and memory (tile size) choices.
function aiArgs(inDir, outDir, tools) {
  const args = ['-i', inDir, '-o', outDir, '-n', tools.realesrganModel || 'realesrgan-x4plus', '-s', '4', '-f', 'png'];
  if (tools.aiGpu && tools.aiGpu !== 'auto') args.push('-g', String(tools.aiGpu));
  if (tools.aiTile && tools.aiTile !== 'auto') args.push('-t', String(tools.aiTile));
  return args;
}

function runProcess(exe, args, ctx) {
  return new Promise((resolve, reject) => {
    const child = spawn(exe, args, { cwd: path.dirname(exe), windowsHide: true });
    let err = '';
    child.stderr.on('data', (d) => { err = (err + d).slice(-2000); });
    ctx.onCancel(() => child.kill());
    child.on('error', reject);
    child.on('close', (code) => {
      if (ctx.cancelled()) reject(new Cancelled());
      else if (code !== 0) reject(new Error(`Real-ESRGAN failed (${code}): ${err.trim().split('\n').slice(-2).join(' ')}`));
      else resolve();
    });
  });
}

// ---------------------------------------------------------------- 2) convert RT64 dump
async function convertTask(p, ctx, tools) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose the RT64 texture dump folder.');
  if (!p.output) throw new Error('Choose the output folder.');
  if (sameFolder(p.input, p.output)) throw new Error('The output folder must be different from the dump folder.');
  const { files, problems } = findDumps(p.input);
  problems.slice(0, 5).forEach((x) => ctx.log('Skipped ' + x));
  if (problems.length > 5) ctx.log(`... and ${problems.length - 5} more incomplete dumps`);
  const seen = new Set(), versions = new Map(), items = [];
  for (const f of files) {
    let d;
    try { d = loadDump(f); } catch (e) { ctx.log(`Skipped ${path.basename(f)}: ${e.message}`); continue; }
    if (seen.has(d.hash) || d.width <= 0 || d.height <= 0) continue;
    seen.add(d.hash);
    versions.set(d.version, (versions.get(d.version) || 0) + 1);
    items.push({ src: f, rel: `textures/${d.hash}`, hash: d.hash, version: d.version });
  }
  if (!items.length) throw new Error('No RT64 texture dumps (<hash>.v<N>.tmem with .tile.json) in that folder.');
  const version = [...versions.entries()].sort((a, b) => b[1] - a[1])[0][0];
  let todo = items;
  if (versions.size > 1) { todo = items.filter((i) => i.version === version); ctx.log(`Dumps use several hash versions; keeping the ${todo.length} made with v${version}.`); }
  const dbFile = path.join(p.output, DATABASE);
  const already = new Set();
  if (p.onlyNew) {
    for (const it of todo) if (['png', 'dds'].some((e) => fs.existsSync(path.join(p.output, `${it.rel}.${e}`)))) already.add(it.hash);
    if (already.size) ctx.log(`Only new textures: ${already.size.toLocaleString()} already converted, skipped.`);
  }
  const fresh = todo.filter((it) => !already.has(it.hash));
  if (!fresh.length) {
    ctx.log('Nothing new to convert.');
    return { title: 'Nothing new:', written: 0, failed: 0, output: p.output, packable: fs.existsSync(dbFile), seconds: (Date.now() - t0) / 1000 };
  }
  ctx.log(`Converting ${fresh.length.toLocaleString()} textures to ${p.format.toUpperCase()} (hash version ${version}).`);
  const pool = new Pool(ctx.workers);
  ctx.onCancel(() => pool.close());
  let res;
  try {
    res = await runAll(pool, fresh, 'dump', (it) => ({ src: it.src, outNoExt: path.join(p.output, it.rel), save: { format: p.format, ddsFormat: p.ddsFormat, texconv: tools.texconv } }), ctx, (it) => it.hash);
  } finally { await pool.close(); if (ctx.cancelled()) cleanupParts(p.output); }
  // rt64.json: add to the existing one when only converting new textures.
  let db = new Database();
  if (p.onlyNew && fs.existsSync(dbFile)) { try { db = Database.load(dbFile); } catch { db = new Database(); } }
  db.config.hashVersion = version;
  // Rice IDs (from the .rice.* files RT64 dumps next to each texture) let classic packs be matched up.
  let riceCount = 0;
  const riceOf = (it) => { if (p.rice === false) return ''; try { const r = require('./rice').riceFromDump(it.src); if (r) riceCount++; return r || ''; } catch { return ''; } };
  fresh.forEach((it, i) => { if (res.results[i]) db.add(it.hash, `${it.rel}.${p.format}`, riceOf(it)); });
  if (p.rice !== false) ctx.log(riceCount ? `Added Rice IDs for ${riceCount.toLocaleString()} texture(s).` : 'No Rice IDs: this dump has no .rice files (dump again with a newer RT64).');
  db.save(dbFile);
  // Remember how each texture repeats, for Upscale's Edges: Auto.
  if (p.wrapInfo !== false) {
    const map = p.onlyNew ? tiling.load(path.join(p.output, tiling.TILING)) : new Map();
    fresh.forEach((it, i) => { if (res.results[i] && res.results[i].edges) map.set(it.hash, res.results[i].edges); });
    tiling.save(p.output, map);
    const tiled = [...map.values()].filter((e) => e[0] !== 'clamp' || e[1] !== 'clamp').length;
    ctx.log(`Remembered tiling: ${tiled.toLocaleString()} repeating texture(s).`);
  }
  const written = res.results.filter(Boolean).length;
  return { title: 'Converted', written, failed: res.failed, output: p.output, packable: written > 0, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- 3) pack
async function packTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input) || !fs.statSync(p.input).isDirectory()) throw new Error('Choose the texture folder to pack.');
  if (!p.output) throw new Error('Choose where to save the .rtz.');
  if (!/\.rtz$/i.test(p.output)) throw new Error('The pack name must end in .rtz.');
  ctx.log(`Packing ${p.input} (${p.compression}${p.compression === 'store' ? '' : ', ' + p.level}).`);
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let r;
  try {
    const recompOpts = p.recomp ? { name: p.recompName || path.basename(p.output).replace(/\.rtz$/i, ''), author: p.recompAuthor, version: p.recompVersion,
      description: p.recompDescription, game: p.recompGame, thumb: p.recompThumb, toggle: p.recompToggle !== false } : null;
    if (recompOpts) require('./recomp').manifest(recompOpts);          // check the version etc. before packing
    r = await pool.run('pack', { folder: p.input, outFile: p.output, options: { compression: p.compression, level: p.level, lowMipCache: p.lowMipCache !== false, recomp: recompOpts } },
      (done, total, name) => ctx.progress(done, total, name));
  } finally { await pool.close(); if (ctx.cancelled()) fs.rmSync(p.output + '.part', { force: true }); }
  if (ctx.cancelled()) throw new Cancelled();
  (r.notes || []).forEach((n) => ctx.log(n));
  if (r.cacheEntries) ctx.log(`Low-mip cache: ${r.cacheEntries} DDS texture(s).`);
  return { title: 'Packed', written: r.textures, failed: 0, output: r.file, sizeMB: r.bytesOut / 1048576, checkable: true, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- 4) unpack
async function unpackTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input) || !fs.statSync(p.input).isFile()) throw new Error('Choose the .rtz pack to unpack.');
  if (!p.output) throw new Error('Choose the output folder.');
  ctx.log(`Unpacking ${p.input}${p.keepCache ? '' : ' (low-mip cache left out)'}.`);
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let n;
  try {
    n = await pool.run('unpack', { file: p.input, output: p.output, keepCache: !!p.keepCache }, (done, total, name) => ctx.progress(done, total, name));
  } finally { await pool.close(); if (ctx.cancelled()) cleanupParts(p.output); }
  if (ctx.cancelled()) throw new Cancelled();
  const textures = (() => { try { return rtz.inspect(p.input).textures; } catch { return n; } })();
  return { title: 'Unpacked', written: textures, files: n, failed: 0, output: p.output, upscalable: textures > 0, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- 4) Ship port archives (.o2r)
async function o2rExtractTask(p, ctx) {
  const t0 = Date.now();
  if (!p.archive || !fs.existsSync(p.archive)) throw new Error('Choose the game’s .o2r or .otr archive.');
  if (!p.output) throw new Error('Choose the output folder.');
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let r;
  try { r = await pool.run('o2rExtract', { archive: p.archive, output: p.output, skipPalette: !!p.skipPalette }, (d, t, m) => ctx.progress(d, t, m)); }
  finally { await pool.close(); if (ctx.cancelled()) cleanupParts(p.output); }
  if (ctx.cancelled()) throw new Cancelled();
  ctx.log(`${r.game}: ${r.textures.toLocaleString()} textures, ${r.written.toLocaleString()} saved as PNG.`);
  if (r.palette) ctx.log(`${r.palette.toLocaleString()} are palette textures: they look grey because their colours live in a separate palette. Paint them in colour for HD.`);
  ctx.log('Next: upscale this folder on 1 · Upscale Textures, then come back and Build an HD mod.');
  return { title: 'Got', written: r.written, failed: 0, output: p.output, upscalable: r.written > 0, seconds: (Date.now() - t0) / 1000 };
}

async function o2rBuildTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose your HD texture folder.');
  if (!p.base || !fs.existsSync(p.base)) throw new Error('Choose the game’s own .o2r or .otr archive.');
  if (!p.output) throw new Error('Choose where to save the mod.');
  if (!/\.o2r$/i.test(p.output)) throw new Error('The mod name must end in .o2r.');
  if (path.resolve(p.output).toLowerCase() === path.resolve(p.base).toLowerCase()) throw new Error('Save the mod as a new file, not over the game archive.');
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let r;
  try { r = await pool.run('o2rBuild', { input: p.input, base: p.base, output: p.output, alt: p.alt !== false, compression: p.compression || 'store' }, (d, t, m) => ctx.progress(d, t, m)); }
  finally { await pool.close(); if (ctx.cancelled()) fs.rmSync(p.output + '.part', { force: true }); }
  if (ctx.cancelled()) throw new Cancelled();
  ctx.log(`${r.game} mod: ${r.written.toLocaleString()} HD texture(s)${p.alt !== false ? ', switched with “Use Alternate Assets” (Tab)' : ''}.`);
  if (r.same.length) ctx.log(`${r.same.length.toLocaleString()} are the original size (kept in their own format).`);
  if (require('./archive').isMpq(p.base)) ctx.log('The game archive is the older .otr kind. The pack is made as .o2r: if your port doesn’t load it, update the port to a version that uses .o2r.');
  if (r.resized.length) { ctx.log(`${r.resized.length.toLocaleString()} weren’t a whole multiple of the original size and were fitted:`); r.resized.slice(0, 10).forEach((x) => ctx.log('  ' + x)); }
  if (r.unmatched.length) { ctx.log(`${r.unmatched.length.toLocaleString()} PNG(s) don’t match a texture in the game and were left out, e.g. ${r.unmatched.slice(0, 3).join(', ')}`); }
  ctx.log('Put the .o2r in the port’s mods folder. File names set the load order.');
  return { title: 'Built', written: r.written, failed: 0, output: r.file, sizeMB: r.bytesOut / 1048576, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- 5) classic packs (Rice / GLideN64)
async function runOne(kind, job, ctx, cleanup) {
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  try { return await pool.run(kind, job, (d, t, m) => ctx.progress(d, t, m)); }
  finally { await pool.close(); if (ctx.cancelled()) { cleanup(); throw new Cancelled(); } }
}

async function legacyImportTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose the classic pack (a Rice folder, or a .hts / .htc file).');
  if (!p.dumpDb || !fs.existsSync(p.dumpDb)) throw new Error('Choose your converted RT64 dump (made with Add Rice IDs on).');
  if (!p.output) throw new Error('Choose the output folder.');
  const r = await runOne('legacyImport', { input: p.input, dumpDb: p.dumpDb, output: p.output }, ctx, () => cleanupParts(p.output));
  ctx.log(`${r.matched.toLocaleString()} of the pack’s ${r.textures.toLocaleString()} textures match textures in your dump (${r.dumpTextures.toLocaleString()} with Rice IDs).`);
  if (r.matched < r.textures) ctx.log('The rest weren’t in your dump: play more of the game with RT64 dumping on, convert again, then import again.');
  return { title: 'Imported', written: r.matched, failed: 0, output: p.output, packable: r.matched > 0, seconds: (Date.now() - t0) / 1000 };
}

async function legacyHtsTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose your texture folder.');
  const name = String(p.name || '').trim();
  if (!name) throw new Error('Type the game name (the name in the ROM header, like THE LEGEND OF ZELDA).');
  const out = p.output || path.join(path.dirname(p.input), `${name}_HIRESTEXTURES.hts`);
  const r = await runOne('legacyHts', { input: p.input, output: out }, ctx, () => fs.rmSync(out + '.part', { force: true }));
  ctx.log(`GLideN64 pack: ${r.textures.toLocaleString()} texture(s)${r.fromDb ? `, ${r.fromDb.toLocaleString()} from rt64.json` : ''}${r.fromNames ? `, ${r.fromNames.toLocaleString()} from Rice file names` : ''}.`);
  ctx.log('In GLideN64, turn on hi-res textures and “Texture Hires File Storage”, and put the file in its cache folder.');
  return { title: 'Made', written: r.textures, failed: 0, output: out, sizeMB: fs.statSync(out).size / 1048576, seconds: (Date.now() - t0) / 1000 };
}

async function riceToO2rTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose the classic pack (a Rice folder, or a .hts / .htc file).');
  if (!p.base || !fs.existsSync(p.base)) throw new Error('Choose the game’s own .o2r or .otr archive.');
  if (!p.output || !/\.o2r$/i.test(p.output)) throw new Error('Choose where to save the mod (a name ending in .o2r).');
  if (path.resolve(p.output).toLowerCase() === path.resolve(p.base).toLowerCase()) throw new Error('Save the mod as a new file, not over the game archive.');
  const r = await runOne('riceToO2r', { input: p.input, base: p.base, output: p.output, alt: p.alt !== false, compression: p.compression || 'store' }, ctx,
    () => fs.rmSync(p.output + '.part', { force: true }));
  ctx.log(`${r.game} mod: ${r.matched.toLocaleString()} of the pack’s ${r.packTextures.toLocaleString()} textures matched, ${r.written.toLocaleString()} game texture(s) replaced.`);
  if (r.unmatched.length) ctx.log(`${r.unmatched.length.toLocaleString()} didn’t match (often textures the port draws differently), e.g. ${r.unmatched.slice(0, 3).join(', ')}`);
  if (r.resized.length) ctx.log(`${r.resized.length.toLocaleString()} weren’t a whole multiple of the original size and were fitted.`);
  ctx.log('Put the .o2r in the port’s mods folder.');
  return { title: 'Built', written: r.written, failed: 0, output: p.output, sizeMB: r.bytesOut / 1048576, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- 6) ROM Tools
async function romsTask(p, ctx) {
  const t0 = Date.now();
  if (!p.folder || !fs.existsSync(p.folder) || !fs.statSync(p.folder).isDirectory()) throw new Error('Choose the folder with your N64 ROMs.');
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let r;
  try { r = await pool.run('romScan', { folder: p.folder }, (d, t, m) => ctx.progress(d, t, `Reading ${m}`)); }
  finally { await pool.close(); }
  if (ctx.cancelled()) throw new Cancelled();
  const folders = new Set(r.roms.map((x) => x.folder)).size;
  ctx.log(`Found ${r.roms.length.toLocaleString()} N64 ROM(s) in ${folders.toLocaleString()} folder(s).`);
  if (r.skipped) ctx.log(`${r.skipped.toLocaleString()} file(s) with ROM-like names aren’t N64 ROMs and were left out.`);
  if (r.truncated) ctx.log('Stopped at 20,000 files: pick a smaller folder to see the rest.');
  return { title: 'Found', roms: r.roms, count: r.roms.length, folders, matched: r.matched, libraryCount: r.libraryCount, output: p.folder, seconds: (Date.now() - t0) / 1000 };
}

// Everything about one ROM (hashes, checksum...), on its own worker so the window stays responsive.
let romPool = null;
async function romInfo(file) {
  if (!romPool) romPool = new Pool(1);
  return romPool.run('romInfo', { file });
}

// ---------------------------------------------------------------- 3b) check a pack, and its fixes
async function checkTask(p, ctx) {
  const t0 = Date.now();
  if (!p.input || !fs.existsSync(p.input)) throw new Error('Choose an .rtz pack or a pack folder to check.');
  const pool = new Pool(1);
  ctx.onCancel(() => pool.close());
  let r;
  try { r = await pool.run('check', { input: p.input }, (done, total, name) => ctx.progress(done, total, name)); }
  finally { await pool.close(); }
  if (ctx.cancelled()) throw new Cancelled();
  for (const c of r.checks) ctx.log(`${{ ok: 'OK  ', warn: 'Look', bad: 'Fix ' }[c.level]}  ${c.title}${c.text ? ' – ' + c.text : ''}`);
  return { title: 'Checked', checks: r.checks, summary: r.summary, output: p.input, seconds: (Date.now() - t0) / 1000 };
}

// Fixes offered by Check a pack. png-to-dds: a fixed copy of the pack with PNG textures as DDS.
async function fixTask(p, ctx, tools) {
  const t0 = Date.now();
  if (p.kind !== 'png-to-dds') throw new Error('Unknown fix.');
  if (!p.input || !fs.existsSync(p.input)) throw new Error('The pack to fix was not found.');
  const ddsFormat = tools.texconv ? 'bc7' : 'auto';
  ctx.log(`Making the PNG textures DDS (${ddsFormat === 'bc7' ? 'BC7' : 'BC1 / BC3'}, with mipmaps) in a fixed copy of the pack.`);
  const pool = new Pool(ctx.workers);
  ctx.onCancel(() => pool.close());
  let r;
  try {
    r = await require('./check').fixPngToDds(p.input, async (jobs) => {
      const res = await runAll(pool, jobs, 'toDds', (j) => ({ src: j.src, dest: j.dest, ddsFormat, texconv: tools.texconv }), ctx, (j) => `Making DDS: ${j.rel}`);
      return res.failed;
    }, { progress: ctx.progress, cancelled: ctx.cancelled });
  } finally { await pool.close(); }
  if (ctx.cancelled()) throw new Cancelled();
  ctx.log(`Saved as ${r.output}`);
  return { title: 'Fixed:', written: r.converted, failed: 0, output: r.output, sizeMB: r.sizeMB, fixed: true, seconds: (Date.now() - t0) / 1000 };
}

// ---------------------------------------------------------------- live preview (1 · Upscale)
// Textures available to preview for the current inputs.
function previewList(inputs, subfolders) {
  try {
    const list = (Array.isArray(inputs) ? inputs : [inputs]).filter((i) => i && fs.existsSync(i));
    if (!list.length) return { items: [], total: 0 };
    const { items } = gatherImages(list, subfolders !== false);
    items.sort((a, b) => a.rel.localeCompare(b.rel, undefined, { numeric: true, sensitivity: 'base' }));
    return { items: items.slice(0, 5000).map((i) => ({ src: i.src, rel: i.rel })), total: items.length };
  } catch (e) { return { items: [], total: 0, error: e.message }; }
}

let previewPool = null;
// One texture upscaled with the current settings; runs on its own worker, separate from jobs.
async function preview(req, tools) {
  if (!previewPool) previewPool = new Pool(1);
  const auto = req.edges === 'auto';
  const edges = tiling.edgesFor(req.src, req.edges || 'clamp', auto ? tiling.loadFor([path.dirname(req.src)]) : null);
  const known = auto && tiling.hashOf(req.src) && tiling.loadFor([path.dirname(req.src)]).has(tiling.hashOf(req.src));
  const NAMES = { clamp: 'normal', wrap: 'tile', mirror: 'mirror' };
  const edgesLabel = `${NAMES[edges[0]]} × ${NAMES[edges[1]]}${auto ? (known ? ' (from dump)' : ' (no dump info)') : ''}`;
  req = { ...req, edges };
  const opts = { size: req.size, fit: req.fit, maxSize: req.maxSize, method: req.method, sharpness: req.sharpness, hardAlpha: req.hardAlpha };
  const save = { format: req.format, ddsFormat: req.ddsFormat, texconv: tools.texconv, keepCoverage: req.keepCoverage !== false };
  let r;
  if (req.method === 'ai' && tools.realesrgan) {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'htk-preview-'));
    try {
      const inDir = path.join(tmp, 'in'), outDir = path.join(tmp, 'out');
      fs.mkdirSync(inDir); fs.mkdirSync(outDir);
      await previewPool.run('aiPrep', { src: req.src, tmpPng: path.join(inDir, '0.png'), pad: 8, edges: req.edges });
      const noCancel = { cancelled: () => false, onCancel: () => {} };
      await runProcess(tools.realesrgan, aiArgs(inDir, outDir, tools), noCancel);
      r = await previewPool.run('previewAi', { src: req.src, aiPng: path.join(outDir, '0.png'), pad: 8, opts, edges: req.edges, save });
    } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
  } else {
    if (opts.method === 'ai') opts.method = 'standard';
    r = await previewPool.run('preview', { src: req.src, opts, edges: req.edges, save });
  }
  return { ...r, edges: edgesLabel };
}

// Stops the preview worker (on quit, and in tests).
async function closePreview() { if (previewPool) { const p = previewPool; previewPool = null; await p.close(); } if (romPool) { const p = romPool; romPool = null; await p.close(); } }

module.exports = { upscaleTask, convertTask, packTask, unpackTask, checkTask, fixTask, o2rExtractTask, o2rBuildTask, romsTask, romInfo, legacyImportTask, legacyHtsTask, riceToO2rTask, inspect, previewList, preview, closePreview, aiArgs, Cancelled, Pool };
