'use strict';
// Run inside the real app (HTK_SELFTEST=this file, see main.js): clicks through every page,
// runs a small Convert and Upscale on a generated RT64 dump, and saves screenshots.
//   HTK_SHOTS=<folder> HTK_DUMP=<dump folder> HTK_OUT=<output folder>
const fs = require('fs');
const path = require('path');

module.exports = async ({ app, win }) => {
  const shots = process.env.HTK_SHOTS;
  fs.mkdirSync(shots, { recursive: true });
  const wc = win.webContents;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const js = (code) => wc.executeJavaScript(code, true);
  const shot = async (name) => { const img = await wc.capturePage(); fs.writeFileSync(path.join(shots, name + '.png'), img.toPNG()); };
  const report = [];
  const check = (ok, what) => { report.push(`${ok ? 'PASS' : 'FAIL'} ${what}`); };

  await new Promise((r) => (wc.isLoading() ? wc.once('did-finish-load', r) : r()));
  await wait(1200);                                   // splash: 3.5 s; the app appears at 3 s
  check(!(await js("document.querySelector('#splash').hidden")) && (await js("document.querySelector('.app').classList.contains('waiting')")), 'splash shows first, app still hidden at ~1.5 s');
  await shot('splash-early');
  await wait(2000);
  check(!(await js("document.querySelector('.app').classList.contains('waiting')")), 'app shown by ~3.2 s, under the fading splash');
  await shot('splash-handover');
  await wait(800);
  check(await js("document.querySelector('#splash').hidden"), 'splash gone after 3.5 s');
  check((await js("document.querySelector('#ver').textContent")) === 'v' + app.getVersion(), 'version in the header');

  // Every page renders, and the subtitle phrase changes on each switch.
  const pages = ['upscale', 'convert', 'pack', 'ports', 'legacy', 'settings', 'about'];
  const seen = new Set();
  for (const p of pages) {
    await js(`document.querySelector('nav button[data-page="${p}"]').click()`); await wait(350);
    seen.add(await js("document.querySelector('#sub').textContent"));
    check((await js("document.querySelector('#page h2').textContent")).length > 0, `page ${p} renders`);
    await shot('app-' + p);
  }
  check(seen.size >= pages.length - 1, `subtitle phrase changes per page (${seen.size} different)`);

  // A page whose engine comes later answers kindly instead of failing.
  await js(`document.querySelector('nav button[data-page="ports"]').click()`); await wait(300);


  // Picking a folder again (even the same one) looks at it again: an empty dump folder, then files arrive.
  const late = path.join(process.env.HTK_OUT, 'late-dump');
  fs.mkdirSync(late, { recursive: true });
  await js(`document.querySelector('nav button[data-page="convert"]').click()`); await wait(300);
  await js(`cfg.convert.input = ${JSON.stringify(late)}; onPath('convert.input'); render();`); await wait(600);
  check(/No RT64 dumps here/.test(await js("document.querySelector('#status .t').textContent")), 'empty dump folder shows the problem');
  check(!!(await js("document.querySelector('#check-again')")), 'problem card has a Check again button');
  for (const f of fs.readdirSync(process.env.HTK_DUMP)) fs.copyFileSync(path.join(process.env.HTK_DUMP, f), path.join(late, f));
  await js(`cfg.convert.input = ${JSON.stringify(late)}; onPath('convert.input'); render();`); await wait(600);   // same folder picked again
  check(/Ready/.test(await js("document.querySelector('#status .t').textContent")), 'same folder picked again: dump now found');
  fs.rmSync(late, { recursive: true, force: true }); fs.mkdirSync(late);
  await js(`document.querySelector('#check-again') ? 0 : 0; recheck();`); await wait(600);
  check(/No RT64 dumps here/.test(await js("document.querySelector('#status .t').textContent")), 'Check again sees the folder change');
  await js(`document.querySelector('#check-again').click()`); await wait(300);
  await shot('run-check-again');
  fs.rmSync(late, { recursive: true, force: true });

  // Convert the generated dump, then upscale it with Edges: Auto.
  const runAndWait = async (setup, task) => {
    await js(setup); await wait(200);
    await js(`(async () => { window.__done = null; if (!window.__hooked) { window.__hooked = true; window.htk.onDone((d) => { window.__done = d; }); } await start('${task}'); })()`);
    for (let i = 0; i < 200; i++) { const d = await js('window.__done'); if (d) return d; await wait(100); }
    return null;
  };
  const dump = JSON.stringify(process.env.HTK_DUMP), out = process.env.HTK_OUT;
  const conv = JSON.stringify(path.join(out, 'converted')), up = JSON.stringify(path.join(out, 'upscaled'));
  await js(`document.querySelector('nav button[data-page="convert"]').click()`); await wait(300);
  const c = await runAndWait(`cfg.convert.input = ${dump}; cfg.convert.output = ${conv}; cfg.convert.format = 'png'; cfg.convert.wrapInfo = true; render();`, 'convert');
  check(c && c.result && c.result.written === 2, 'Convert RT64 Dump: 2 textures');
  check(fs.existsSync(path.join(out, 'converted', 'r64texhd-tiling.json')), 'tiling file written');
  await wait(300);
  check((global.opened || []).some((p) => path.resolve(p.replace(/\\/g, '/')) === path.resolve(out, 'converted', 'textures')), 'after Convert the converted textures folder opens');
  await wait(400); await js("closeModal()"); await shot('run-convert-done');

  await js(`document.querySelector('nav button[data-page="upscale"]').click()`); await wait(300);
  const u = await runAndWait(`cfg.upscale.inputs = [${conv}]; cfg.upscale.output = ${up}; cfg.upscale.edges = 'auto'; cfg.upscale.size = 4; cfg.upscale.format = 'dds'; cfg.upscale.ddsFormat = 'auto'; render();`, 'upscale');
  check(u && u.result && u.result.written === 2, 'Upscale: 2 textures to DDS');
  await wait(1500); await js("closeModal()"); await wait(300);
  const log = await js("job.log.join('\\n')");
  check(/tiling known for 2 of 2/.test(log), 'Edges: Auto found the dump tiling');
  await shot('run-upscale-done');
  const cap = await js("(document.querySelector('#pv-cap-o') || {}).textContent || ''");
  check(/from dump/.test(cap), `preview shows edges from the dump (${cap.trim()})`);

  // Step 2: pack the upscaled DDS with Recomp info, check it; then check + fix the PNG folder.
  const rtzOut = JSON.stringify(path.join(out, 'Majora HD.rtz'));
  const thumb = JSON.stringify(path.join(__dirname, '..', '..', 'app', 'ui', 'splash.png'));
  await js(`document.querySelector('nav button[data-page="pack"]').click()`); await wait(300);
  const pk = await runAndWait(`cfg.pack.mode = 'pack'; cfg.pack.input = ${up}; cfg.pack.output = ${rtzOut}; cfg.pack.recomp = true; cfg.pack.recompName = 'Majora HD Reimagined';
    cfg.pack.recompAuthor = 'chuchu'; cfg.pack.recompVersion = '1.0.0'; cfg.pack.recompDescription = 'Every texture in Termina, redone in HD.'; cfg.pack.recompThumb = ${thumb}; render();`, 'pack');
  check(pk && pk.result && pk.result.written === 2, 'Pack .rtz with Recomp info');
  await wait(400); await js('document.querySelector("#page").scrollTop = 99999'); await wait(200); await shot('run-pack-recomp');
  await js('document.querySelector("#page").scrollTop = 0');
  const ck = await (async () => { await js(`window.__done = null; document.querySelector('#go-check').click()`); for (let i = 0; i < 100; i++) { const d = await js('window.__done'); if (d) return d; await wait(100); } return null; })();
  check(ck && ck.result && ck.result.checks.every((c) => c.level === 'ok'), 'Check it: the new pack is all good');
  check(ck && ck.result.checks.some((c) => /Recomp mod info and picture found/.test(c.title)), 'Check sees the Recomp info and picture');
  await wait(300); await shot('run-check-good');

  const cp = await runAndWait(`cfg.pack.mode = 'check'; cfg.check.input = ${conv}; render();`, 'check');
  check(cp && cp.result.checks.some((c) => c.fix === 'png-to-dds'), 'Check finds PNG textures and offers a fix');
  await wait(300); await shot('run-check-png');
  await js(`window.__done = null; document.querySelector('[data-fix="png-to-dds"]').click()`);
  let fixedCheck = null;
  for (let i = 0; i < 200; i++) { const d = await js('window.__done'); if (d && d.task === 'check') { fixedCheck = d; break; } await wait(100); }
  check(fixedCheck && fixedCheck.result.checks.every((c) => c.level === 'ok'), 'Make them DDS, then the fixed pack checks all good');
  check(fs.existsSync(path.join(out, 'converted-fixed.rtz')), 'fixed copy saved next to the folder');
  await wait(300); await shot('run-check-fixed');

  // Step 3: Ship mods. Get textures from a game archive, upscale them (PNG), build the HD mod.
  const arc = path.join(out, 'game', 'mm.o2r');
  require('child_process').execFileSync(process.execPath, [path.join(__dirname, 'make-test-o2r.js'), arc], { env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' } });
  const got = JSON.stringify(path.join(out, 'mm-textures')), shipUp = JSON.stringify(path.join(out, 'mm-textures-upscaled')), mod = JSON.stringify(path.join(out, 'mods', 'Majora HD.o2r'));
  await js(`document.querySelector('nav button[data-page="ports"]').click()`); await wait(300);
  const gx = await runAndWait(`cfg.ports.mode = 'extract'; cfg.ports.archive = ${JSON.stringify(arc)}; cfg.ports.output = ${got}; render();`, 'o2rExtract');
  check(gx && gx.result && gx.result.written === 3, 'Ship Mods: Get textures (3 from mm.o2r)');
  await wait(300); await shot('run-o2r-extract');
  await js(`window.__done = null; document.querySelector('#go-upscale').click()`); await wait(400);
  check((await js("cfg.upscale.format")) === 'png', 'Upscale these: switches output to PNG for Ship mods');
  const su = await runAndWait(`cfg.upscale.output = ${shipUp}; cfg.upscale.size = 4; render();`, 'upscale');
  check(su && su.result && su.result.fromO2r, 'Upscale knows the textures came from a Ship archive');
  await wait(1500); await js("closeModal()"); await wait(300);
  await js(`document.querySelector('#go-ship').click()`); await wait(400);
  check((await js("cfg.ports.mode")) === 'build' && (await js("cfg.ports.base")) === arc, 'Build HD mod button fills in the folder and game archive');
  const sb = await runAndWait(`cfg.ports.modOutput = ${mod}; render();`, 'o2rBuild');
  check(sb && sb.result && sb.result.written === 3, 'Ship Mods: Build HD mod (3 textures)');
  const o2r = require(path.join(__dirname, '..', '..', 'app', 'core', 'o2r'));
  const rtzm = require(path.join(__dirname, '..', '..', 'app', 'core', 'rtz'));
  const modFile = path.join(out, 'mods', 'Majora HD.o2r');
  const e = rtzm.readEntries(modFile).find((x) => x.name === 'alt/objects/gameplay_keep/gBrickWallTex');
  const t = e && o2r.parseTexture(rtzm.readEntry(modFile, e));
  check(t && t.width === 128 && t.flags === 1 && t.hScale === 8 && t.vScale === 4, 'mod texture: 128×128 RGBA32, alt/ path, scales 8 × 4');
  await wait(300); await shot('run-o2r-build');

  // Step 4: classic packs. A Rice pack made to match mm.o2r goes into a Ship mod; a dump with Rice files
  // is converted with Rice IDs, a Rice pack is imported through it, and a GLideN64 .hts is made.
  const core = (m) => require(path.join(__dirname, '..', '..', 'app', 'core', m));
  const riceM = core('rice'), pngM = core('png');
  const ricePack = path.join(out, 'rice-pack');
  fs.mkdirSync(ricePack, { recursive: true });
  const solid = (w, h, c) => { const d = new Uint8Array(w * h * 4); for (let i = 0; i < w * h; i++) d.set(c, i * 4); return { width: w, height: h, data: d }; };
  for (const t of o2r.readTextures(arc)) {
    const r = riceM.riceForTexture(t);
    fs.writeFileSync(path.join(ricePack, `ZELDA MAJORA'S MASK#${riceM.hex8(r.crc).toUpperCase()}#${r.fmt}#${r.siz}_all.png`), pngM.encodePNG(solid(t.width * 4, t.height * 4, [30, 200, 90, 255])));
  }
  await js(`document.querySelector('nav button[data-page="legacy"]').click()`); await wait(300);
  const rs = await runAndWait(`cfg.legacy.mode = 'ship'; cfg.legacy.riceInput = ${JSON.stringify(ricePack)}; cfg.legacy.base = ${JSON.stringify(arc)};
    cfg.legacy.modOutput = ${JSON.stringify(path.join(out, 'mods', 'Rice pack.o2r'))}; render();`, 'riceToO2r');
  check(rs && rs.result && rs.result.written === 3, 'Rice / GLideN64: Rice pack into a Ship mod (3 textures)');
  await wait(300); await shot('run-rice-ship');

  const rdump = path.join(out, 'dump-rice');
  fs.mkdirSync(rdump, { recursive: true });
  const rdram = Buffer.alloc(16 * 8 * 2); for (let i = 0; i < rdram.length; i++) rdram[i] = (i * 37) & 255;
  const tmem = Buffer.alloc(4096); rdram.copy(tmem);
  fs.writeFileSync(path.join(rdump, 'cccccccccccccccc.v5.tmem'), tmem);
  fs.writeFileSync(path.join(rdump, 'cccccccccccccccc.v5.tile.json'), JSON.stringify({ width: 16, height: 8, tlut: 'None',
    tile: { fmt: 0, siz: 2, line: 4, tmem: 0, cms: 0, cmt: 0, masks: 4, maskt: 3, uls: 0, ult: 0, lrs: 60, lrt: 28 } }));
  fs.writeFileSync(path.join(rdump, 'cccccccccccccccc.v5.rice.json'), JSON.stringify({ type: 'Tile', tile: { fmt: 0, siz: 2, uls: 0, ult: 0, lrs: 60, lrt: 28 }, texture: { address: 0, fmt: 0, siz: 2, width: 16 } }));
  fs.writeFileSync(path.join(rdump, 'cccccccccccccccc.v5.rice.rdram'), rdram);
  const riceId = riceM.riceFromDump(path.join(rdump, 'cccccccccccccccc.v5.tmem'));
  const convRice = path.join(out, 'dump-rice-converted');
  await js(`document.querySelector('nav button[data-page="convert"]').click()`); await wait(300);
  const cr = await runAndWait(`cfg.convert.input = ${JSON.stringify(rdump)}; cfg.convert.output = ${JSON.stringify(convRice)}; cfg.convert.rice = true; cfg.convert.onlyNew = false; render();`, 'convert');
  await wait(400); await js('closeModal()');
  check(cr && cr.result && fs.readFileSync(path.join(convRice, 'rt64.json'), 'utf8').includes(riceId), 'Convert with Add Rice IDs writes the Rice ID');
  const pack2 = path.join(out, 'rice-pack-rt64');
  fs.mkdirSync(pack2, { recursive: true });
  fs.writeFileSync(path.join(pack2, `GAME#${riceId.split('#')[0].toUpperCase()}#0#2_all.png`), pngM.encodePNG(solid(64, 32, [220, 40, 40, 255])));
  await js(`document.querySelector('nav button[data-page="legacy"]').click()`); await wait(300);
  const im = await runAndWait(`cfg.legacy.mode = 'import'; cfg.legacy.input = ${JSON.stringify(pack2)}; cfg.legacy.dumpDb = ${JSON.stringify(convRice)};
    cfg.legacy.output = ${JSON.stringify(path.join(out, 'imported'))}; render();`, 'legacyImport');
  check(im && im.result && im.result.written === 1 && fs.existsSync(path.join(out, 'imported', 'textures', 'cccccccccccccccc.png')), 'Rice / GLideN64: classic pack into RT64 (matched through the dump)');
  await wait(300); await shot('run-rice-import');
  const ht = await runAndWait(`cfg.legacy.mode = 'hts'; cfg.legacy.htsInput = ${JSON.stringify(path.join(out, 'imported'))}; cfg.legacy.htsName = 'GAME';
    cfg.legacy.htsOutput = ${JSON.stringify(path.join(out, 'GAME_HIRESTEXTURES.hts'))}; render();`, 'legacyHts');
  const hl = ht && ht.result ? riceM.readGlidenPack(path.join(out, 'GAME_HIRESTEXTURES.hts')) : [];
  check(hl.length === 1 && riceM.riceId(hl[0]) === riceId, 'Rice / GLideN64: GLideN64 .hts made with the right Rice ID');
  await wait(300); await shot('run-rice-hts');

  fs.writeFileSync(path.join(shots, 'selftest.txt'), report.join('\n') + '\n');
  app.exit(report.some((l) => l.startsWith('FAIL')) ? 1 : 0);
};
