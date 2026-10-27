'use strict';
// "Check a pack": looks over an .rtz or a pack folder before it is shared, following RT64's own
// texture pack advice (TEXTURE-PACKS.md): ship DDS not PNG, give DDS mipmaps, build the low-mip
// cache and keep it to about 100-200 MB, keep preloads few. Nothing is changed.
//
// fixPngToDds writes a fixed copy (<name>-fixed.rtz) with every PNG turned into DDS.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { parseHeader } = require('./dds');
const { Database, listFiles, databaseFromFiles, detectHashVersion, DATABASE, LOW_MIP_CACHE, KNOWN } = require('./rt64db');
const rtz = require('./rtz');
const recomp = require('./recomp');

const MB = 1048576;
const CACHE_WARN_MB = 200;
const BIG_SIDE = 4096;

// A uniform view of a pack: file list, sizes, and readers for whole files or just the start of one.
function openPack(input) {
  const st = fs.statSync(input);
  if (st.isDirectory()) {
    const files = listFiles(input);
    return {
      kind: 'folder', files,
      size: (f) => fs.statSync(path.join(input, f)).size,
      read: (f) => fs.readFileSync(path.join(input, f)),
      head: (f, n) => { const fd = fs.openSync(path.join(input, f), 'r'); try { const b = Buffer.alloc(n); const got = fs.readSync(fd, b, 0, n, 0); return b.subarray(0, got); } finally { fs.closeSync(fd); } },
      close: () => {},
    };
  }
  const entries = rtz.readEntries(input);
  const byName = new Map(entries.map((e) => [e.name, e]));
  const fd = fs.openSync(input, 'r');
  return {
    kind: 'rtz', files: entries.map((e) => e.name),
    size: (f) => byName.get(f).usize,
    read: (f) => rtz.readEntry(input, byName.get(f), fd),
    head: (f, n) => rtz.readEntry(input, byName.get(f), fd).subarray(0, n),
    close: () => fs.closeSync(fd),
  };
}

const plural = (n, one, many = one + 's') => `${n.toLocaleString()} ${n === 1 ? one : many}`;
const sizeText = (b) => (b >= 1024 * MB ? `${(b / 1024 / MB).toFixed(1)} GB` : b >= MB ? `${(b / MB).toFixed(b >= 10 * MB ? 0 : 1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

// Returns { checks: [{ level: ok|warn|bad, title, text, fix?, fixLabel? }], summary, textures }.
function checkPack(input, { progress = () => {}, cancelled = () => false } = {}) {
  const pack = openPack(input);
  const checks = [];
  const add = (level, title, text = '', extra = {}) => checks.push({ level, title, text, ...extra });
  let used = [], summary = '';
  const finish = () => {
    const order = { bad: 0, warn: 1, ok: 2 };
    checks.sort((a, b) => order[a.level] - order[b.level]);
    return { checks, summary: summary || path.basename(input), textures: used.length };
  };
  try {
    const files = pack.files.filter((f) => !/\.part$/i.test(f));
    const lower = new Set(files.map((f) => f.toLowerCase()));
    const imageFiles = files.filter((f) => KNOWN.some((e) => f.toLowerCase().endsWith(e)) && !/^thumb\.(png|dds)$/i.test(f));

    // rt64.json
    let db, generated = false;
    if (lower.has(DATABASE)) {
      try { db = Database.fromJSON(JSON.parse(pack.read(files.find((f) => f.toLowerCase() === DATABASE)).toString('utf8').replace(/^﻿/, ''))); }
      catch (e) { add('bad', 'rt64.json can’t be read', e.message); return finish(); }
    } else {
      const made = databaseFromFiles(imageFiles, detectHashVersion(imageFiles) || 5);
      db = made.db; generated = true;
      if (pack.kind === 'rtz') add('bad', 'No rt64.json in this pack', 'RT64 needs it to know which texture replaces which. Unpack, then pack again here to make one.');
      else add('warn', 'No rt64.json yet', `Packing makes one from the ${plural(db.textures.length, 'hash-named file')}.`);
    }

    const { resolved, missing } = db.resolvePaths(files);
    used = [...new Set([...resolved.values()].map((r) => r.rel))];
    if (!generated) {
      if (missing.length) add('bad', `${plural(missing.length, 'texture')} in rt64.json ${missing.length === 1 ? 'has' : 'have'} no file`, `For example ${missing[0]}. Those textures won’t be replaced in game.`);
      else add('ok', 'Every texture in rt64.json has a file');
    }

    // PNG still in the pack (RT64: "do not ship PNG packs").
    const pngs = used.filter((f) => /\.png$/i.test(f));
    if (pngs.length) {
      add('bad', `${plural(pngs.length, 'texture is', 'textures are')} still PNG`, 'RT64 says not to ship PNG: they load slowly and use more memory. Make them DDS.',
        { fix: 'png-to-dds', fixLabel: 'Make them DDS' });
    } else if (used.length) add('ok', 'All textures are DDS');

    // PNG + DDS for the same texture: only the DDS is used, the PNG just takes space.
    const usedSet = new Set(used.map((f) => f.toLowerCase()));
    const shadowed = imageFiles.filter((f) => /\.png$/i.test(f) && !usedSet.has(f.toLowerCase()) && usedSet.has(f.replace(/\.png$/i, '.dds').toLowerCase()));
    if (shadowed.length) add('warn', `${plural(shadowed.length, 'PNG has', 'PNGs have')} a DDS twin`, 'RT64 uses the DDS, so the PNG only adds size. The packer leaves them out.');

    // DDS details: mipmaps, very large textures.
    const dds = used.filter((f) => /\.dds$/i.test(f));
    let noMips = 0, big = 0, bigExample = '', unsupported = 0;
    dds.forEach((f, i) => {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      if (i % 100 === 0) progress(i, dds.length, `Looking at DDS textures (${i.toLocaleString()} / ${dds.length.toLocaleString()})`);
      const info = parseHeader(pack.head(f, 148));
      if (!info || info.unsupported) { unsupported++; return; }
      if (info.mips <= 1 && Math.max(info.width, info.height) > 4) noMips++;
      if (Math.max(info.width, info.height) > BIG_SIDE) { big++; if (!bigExample) bigExample = `${f} is ${info.width}×${info.height}`; }
    });
    if (dds.length) {
      if (noMips) add('warn', `${plural(noMips, 'DDS texture has', 'DDS textures have')} no mipmaps`, 'Without them textures shimmer in the distance. Upscale again with DDS output to add them.');
      else add('ok', 'All DDS textures have mipmaps');
    }
    if (unsupported) add('warn', `${plural(unsupported, 'DDS file')} R64texHD can’t read`, 'They may be a format RT64 doesn’t support either.');
    if (big) add('warn', `${plural(big, 'texture is', 'textures are')} over ${BIG_SIDE} px`, `${bigExample}. Very large textures use a lot of graphics memory and grow the low-mip cache.`);

    // Low-mip cache.
    const streamed = [...resolved.values()].filter((r) => /\.dds$/i.test(r.rel) && r.operation === 'stream').length;
    if (lower.has(LOW_MIP_CACHE)) {
      const mb = pack.size(files.find((f) => f.toLowerCase() === LOW_MIP_CACHE)) / MB;
      if (mb > CACHE_WARN_MB) add('warn', `Low-mip cache is ${Math.round(mb)} MB`, `RT64 suggests keeping it under about ${CACHE_WARN_MB} MB. Very large textures make it grow.`);
      else add('ok', `Low-mip cache is ${mb < 1 ? '<1' : Math.round(mb)} MB`);
    } else if (pack.kind === 'rtz' && streamed) {
      add('warn', 'No low-mip cache', 'Textures may pop in while they load. Pack again with Low-mip cache: Build.');
    }

    // Preload / stall.
    const ops = [...resolved.values()].map((r) => r.operation);
    const preload = ops.filter((o) => o === 'preload').length, stall = ops.filter((o) => o === 'stall').length;
    if (stall) add('warn', `${plural(stall, 'texture uses', 'textures use')} “stall”`, 'The game waits for these to load. RT64 doesn’t recommend it.');
    if (preload > 200) add('warn', `${plural(preload, 'texture is', 'textures are')} preloaded`, 'Preloads stay in memory the whole time. Keep them to the few that must never pop in.');

    // Files nothing uses.
    const extras = new Set([DATABASE, LOW_MIP_CACHE, recomp.MANIFEST, recomp.THUMB, 'thumb.dds', ...db.extraFiles.map((f) => f.toLowerCase())]);
    const unused = imageFiles.filter((f) => !usedSet.has(f.toLowerCase()) && !shadowed.includes(f) && !extras.has(f.toLowerCase()));
    if (unused.length) add('warn', `${plural(unused.length, 'image isn’t', 'images aren’t')} used by rt64.json`, `For example ${unused[0]}. ${pack.kind === 'rtz' ? 'It only adds size.' : 'The packer leaves it out.'}`);

    // Recomp mod info (optional).
    if (lower.has(recomp.MANIFEST)) {
      const v = recomp.validate(pack.read(files.find((f) => f.toLowerCase() === recomp.MANIFEST)).toString('utf8'));
      if (v.ok) {
        const i = v.info;
        add('ok', `Recomp mod info${lower.has(recomp.THUMB) || lower.has('thumb.dds') ? ' and picture' : ''} found`,
          `Shows as “${i.name}” by ${i.authors.join(', ')}, v${i.version}${i.toggle ? ', with an on / off switch' : ''}.`);
      } else add('bad', 'Recomp mod info has a problem', `${v.problems.join('; ')}. Recomp won’t load the pack like this.`);
    } else if (pack.kind === 'rtz') add('ok', 'No Recomp mod info (optional)', 'Recomp will name the pack after its file. Add a name, author and picture when you pack it.');

    summary = `${path.basename(input)} · ${plural(used.length, 'texture')} · ${sizeText(used.reduce((s, f) => s + pack.size(f), 0))}`;
    return finish();
  } finally { pack.close(); }
}

// Fixed copy of a pack with every PNG texture turned into DDS (and rt64.json pointed at them).
// encodeAll([{ src, dest }]) turns each PNG into a DDS file (tasks.js runs it on the worker pool).
async function fixPngToDds(input, encodeAll, { progress = () => {}, cancelled = () => false } = {}) {
  const isRtz = fs.statSync(input).isFile();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'r64-fix-'));
  try {
    const src = isRtz ? path.join(tmp, 'pack') : input;
    if (isRtz) rtz.unpack(input, src, { keepCache: false, progress: (d, t) => progress(d, t, 'Opening the pack') });
    const work = path.join(tmp, 'work');
    // Copy (or for an .rtz, move) everything into a work folder; PNG textures become DDS there.
    const files = listFiles(src);
    const dbFile = path.join(src, DATABASE);
    const db = fs.existsSync(dbFile) ? Database.load(dbFile) : databaseFromFiles(files, detectHashVersion(files) || 5).db;
    const { resolved } = db.resolvePaths(files);
    const pngs = new Set([...resolved.values()].map((r) => r.rel).filter((f) => /\.png$/i.test(f)));
    const jobs = [];
    for (const f of files) {
      if (cancelled()) throw Object.assign(new Error('Cancelled'), { cancelled: true });
      if (f.toLowerCase() === LOW_MIP_CACHE) continue;
      const to = path.join(work, f);
      fs.mkdirSync(path.dirname(to), { recursive: true });
      if (pngs.has(f)) jobs.push({ src: path.join(src, f), dest: to.replace(/\.png$/i, '.dds'), rel: f });
      else if (isRtz) fs.renameSync(path.join(src, f), to);
      else fs.copyFileSync(path.join(src, f), to);
    }
    const failed = await encodeAll(jobs);
    if (failed) throw new Error(`${plural(failed, 'PNG')} couldn’t be turned into DDS (see the log).`);
    for (const t of db.textures) if (t.path && /\.png$/i.test(t.path)) t.path = t.path.replace(/\.png$/i, '.dds');
    db.save(path.join(work, DATABASE));
    const base = isRtz ? input.replace(/\.rtz$/i, '') : input.replace(/[\\/]+$/, '');
    let out = `${base}-fixed.rtz`;
    for (let n = 2; fs.existsSync(out); n++) out = `${base}-fixed-${n}.rtz`;
    const r = rtz.packFolder(work, out, { compression: 'zstd', level: 'balanced', lowMipCache: true, cancelled,
      progress: (d, t, name) => progress(d, t, `Packing ${name}`) });
    return { output: out, converted: pngs.size, textures: r.textures, sizeMB: r.bytesOut / MB };
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

module.exports = { checkPack, fixPngToDds, openPack };
