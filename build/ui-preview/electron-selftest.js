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
  // Written as it goes, so a crash part-way still shows how far it got.
  const check = (ok, what) => { report.push(`${ok ? 'PASS' : 'FAIL'} ${what}`); fs.writeFileSync(path.join(shots, 'selftest.txt'), report.join('\n') + '\n'); };

  await new Promise((r) => (wc.isLoading() ? wc.once('did-finish-load', r) : r()));
  await wait(1200);                                   // splash: 5 s; the app appears at 4.5 s
  // Read the state and the page's own clock together, so a slow machine can't make this flaky.
  const early = await js("({ t: performance.now(), splash: !document.querySelector('#splash').hidden, waiting: document.querySelector('.app').classList.contains('waiting') })");
  check(early.t >= 4400 || (early.splash && early.waiting), `splash shows first, app still hidden (at ${(early.t / 1000).toFixed(1)} s)`);
  await shot('splash-early');
  // Other keys don't skip it; Space / Enter / Esc and a click on the logo do (tried in the preview tests).
  await js("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true }))"); await wait(100);
  const stillUp = await js("({ t: performance.now(), up: !document.querySelector('#splash').hidden })");
  check(stillUp.up || stillUp.t >= 5000, 'a random key does not skip the splash');
  const t0 = await js('performance.now()'); await wait(Math.max(0, 4800 - t0));
  check(!(await js("document.querySelector('.app').classList.contains('waiting')")), 'app shown by ~4.7 s, under the fading splash');
  await shot('splash-handover');
  // The animation clock starts when the page first paints, a little after the page's own clock.
  let gone = false; for (let i = 0; i < 30 && !gone; i++) { await wait(100); gone = await js("document.querySelector('#splash').hidden"); }
  const goneAt = await js('performance.now()');
  check(gone && goneAt < 7000, `splash gone after 5 s (closed by ${(goneAt / 1000).toFixed(1)} s)`);
  await wait(400);                                     // the start-up prompts open once the splash is gone
  check((await js("document.querySelector('#ver').textContent")) === 'v' + app.getVersion(), 'version in the header');

  // First launch: no setup step. It opens on Welcome and asks about the missing helper tools.
  check((await js('page')) === 'welcome', 'first launch opens on the Welcome page (nothing to fill in)');
  const toolsAsk = await js("(() => { const m = document.querySelector('#modal'); return m && !m.hidden ? m.innerText : ''; })()");
  check(/New install, who dis\?/.test(toolsAsk) && /Download Helper Tools\?/.test(toolsAsk) && /texconv/.test(toolsAsk) && /Real-ESRGAN/.test(toolsAsk), 'helper tools question lists the tools');
  await js("document.querySelector('#tools-no').click()"); await wait(300);
  check((await js("document.querySelector('#modal').hidden")) && (await js('page')) === 'welcome', 'No closes it and stays on Welcome');
  await shot('first-launch-welcome');
  await js(`document.querySelector('nav button[data-page="convert"]').click()`); await wait(200);
  await js("document.querySelector('#home').click()"); await wait(300);
  check((await js('page')) === 'welcome' && (await js("document.querySelector('#home').classList.contains('on')")), 'Welcome button brings the Welcome page back');

  // Every page renders, and the subtitle phrase changes on each switch.
  const pages = ['upscale', 'convert', 'pack', 'ports', 'legacy', 'roms', 'settings', 'about'];
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

  // Step 3: Ship mods. Extract Textures from a game archive, upscale them (PNG), Create HD Texture Pack.
  const arc = path.join(out, 'game', 'mm.o2r');
  require('child_process').execFileSync(process.execPath, [path.join(__dirname, 'make-test-o2r.js'), arc], { env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' } });
  const got = JSON.stringify(path.join(out, 'mm-textures')), shipUp = JSON.stringify(path.join(out, 'mm-textures-upscaled')), mod = JSON.stringify(path.join(out, 'mods', 'Majora HD.o2r'));
  await js(`document.querySelector('nav button[data-page="ports"]').click()`); await wait(300);
  const gx = await runAndWait(`cfg.ports.mode = 'extract'; cfg.ports.archive = ${JSON.stringify(arc)}; cfg.ports.output = ${got}; render();`, 'o2rExtract');
  check(gx && gx.result && gx.result.written === 3, 'Ship Mods: Extract Textures (3 from mm.o2r)');
  await wait(500);
  const shipCard = await js("document.querySelector('#sx-id').innerText");
  check(/Majora's Mask/.test(shipCard) && /2 Ship 2 Harkinian/.test(shipCard) && /version file/.test(shipCard) && /5354631C/.test(shipCard), 'Ship Mods: the archive’s version file names the game (Majora’s Mask, 2Ship)');
  const shipArt = await js("(() => { const i = document.querySelector('#rx-art img'); return i ? [i.getAttribute('src'), i.naturalWidth] : null; })()");
  check(shipArt && /Majora/.test(shipArt[0]) && shipArt[1] > 0, 'Ship Mods: box art shows');
  check(/Termina/.test(await js("document.querySelector('#rx-desc').innerText")), 'Ship Mods: game description shows');
  await wait(300); await shot('run-o2r-extract');
  await js(`window.__done = null; document.querySelector('#go-upscale').click()`); await wait(400);
  check((await js("cfg.upscale.format")) === 'png', 'Upscale these: switches output to PNG for Ship mods');
  const su = await runAndWait(`cfg.upscale.output = ${shipUp}; cfg.upscale.size = 4; render();`, 'upscale');
  check(su && su.result && su.result.fromO2r, 'Upscale knows the textures came from a Ship archive');
  await wait(1500); await js("closeModal()"); await wait(300);
  await js(`document.querySelector('#go-ship').click()`); await wait(400);
  check((await js("cfg.ports.mode")) === 'build' && (await js("cfg.ports.base")) === arc, 'Create HD Texture Pack button fills in the folder and game archive');
  const sb = await runAndWait(`cfg.ports.modOutput = ${mod}; render();`, 'o2rBuild');
  check(sb && sb.result && sb.result.written === 3, 'Ship Mods: Create HD Texture Pack (3 textures)');
  const modId = await js(`window.htk.shipIdentify(${JSON.stringify(path.join(out, 'mods', 'Majora HD.o2r'))})`);
  check(modId && modId.key === 'NZS' && modId.kind === 'mod', 'Ship Mods: the built mod remembers its game');
  // An older .otr (MPQ) game archive: picked, checked again, recognised and extracted.
  const otr = path.join(out, 'old-port', 'oot-mq.otr');
  fs.mkdirSync(path.dirname(otr), { recursive: true }); fs.copyFileSync(path.join(__dirname, '..', '..', 'tests', 'fixtures', 'oot-test.otr'), otr);
  await js(`cfg.ports.mode = 'extract'; cfg.ports.archive = ${JSON.stringify(otr)}; onPath('ports.archive'); document.querySelector('nav button[data-page="ports"]').click()`); await wait(800);
  check(/Ready/.test(await js("document.querySelector('#status .t').textContent")), 'Ship Mods: an older .otr archive is ready (not "Can’t open")');
  await js('recheck()'); await wait(600);
  check(/Ready/.test(await js("document.querySelector('#status .t').textContent")), 'Ship Mods: Check again on a .otr stays ready');
  check(/Ocarina of Time/.test(await js("document.querySelector('#sx-id').innerText")) && /version file/.test(await js("document.querySelector('#sx-id').innerText")), 'Ship Mods: the .otr’s version file names the game');
  const ox = await runAndWait(`cfg.ports.output = ${JSON.stringify(path.join(out, 'otr-textures'))}; render();`, 'o2rExtract');
  check(ox && ox.result && ox.result.written === 3, 'Ship Mods: Extract Textures from a .otr (3 textures)');
  await js(`cfg.ports.mode = 'extract'; cfg.ports.archive = ${JSON.stringify(arc)}; document.querySelector('nav button[data-page="ports"]').click()`); await wait(600);
  // Finding installed ports (HTK_SHIPFIND_ROOTS keeps the search to the test folder): a 2Ship folder
  // with its program and game archive. Then the chips are toggles: green found, red not, purple selected.
  const portDir = path.join(out, 'Games', '2Ship');
  fs.mkdirSync(portDir, { recursive: true }); fs.writeFileSync(path.join(portDir, '2ship.exe'), 'x'); fs.copyFileSync(arc, path.join(portDir, 'mm.o2r'));
  await js('findPorts()');
  for (let i = 0; i < 50 && (await js('SHIP.finding')); i++) await wait(100);
  const chipState = await js("Object.fromEntries([...document.querySelectorAll('#ship-chips .chip')].map((c) => [c.textContent, c.className.replace('chip ship-port ', '')]))");
  check(chipState['2 Ship 2 Harkinian'] === 'sel' && chipState.Starship === 'missing' && chipState.Ghostship === 'missing', `Ship Mods: found ports become toggles (${JSON.stringify(chipState)})`);
  check(/Found 2 of 7 ports/.test(await js("document.querySelector('#sx-find').innerText")), 'Ship Mods: says how many ports it found (2Ship, and SoH from the .otr)');
  check(await js("getComputedStyle(document.querySelector('.chip-w.sel')).filter.includes('drop-shadow')"), 'Ship Mods: the selected port glows');
  await js(`cfg.ports.archive = ''; render();`); await wait(400);
  check((await js("document.querySelector('[data-port=\"2 Ship 2 Harkinian\"]').className")).includes('have'), 'Ship Mods: an installed port that isn’t selected is green');
  await js(`document.querySelector('[data-port="2 Ship 2 Harkinian"]').click()`); await wait(500);
  check((await js('cfg.ports.archive')) === path.join(portDir, 'mm.o2r') && (await js('cfg.ports.modOutput')).startsWith(path.join(portDir, 'mods')), 'Ship Mods: clicking an installed port uses its game archive and mods folder');
  // Every toggle / Check again / Search again looks again: is the game archive made, and from this build?
  {
    const rz = require(path.join(__dirname, '..', '..', 'app', 'core', 'rtz')), zl = require('zlib');
    const pv = (m) => Buffer.from([1, 0, m, 0, 0, 0, 0]);
    const zip = (file, entries) => { const w = new rz.ZipWriter(file); for (const [n, b] of entries) w.add(n, b, 0, zl.crc32(b), b.length, Date.now()); w.close(); };
    const status = () => js("document.querySelector('#status .t').textContent");
    const chip = () => js(`document.querySelector('[data-port="2 Ship 2 Harkinian"]').textContent`);
    const settle = async () => { for (let i = 0; i < 30 && (await status()) === 'Checking…'; i++) await wait(100); await wait(150); };
    zip(path.join(portDir, '2ship.o2r'), [['portVersion', pv(2)]]);          // the port updates to 2.0.0; mm.o2r has no portVersion
    await js(`document.querySelector('[data-port="2 Ship 2 Harkinian"]').click()`); await wait(300); await settle();
    await shot('ship-outdated');
    check(/outdated/i.test(await status()) && /outdated/.test(await chip()), `Ship Mods: toggling a port finds its game archive is older than the port (${await status()} / ${await chip()})`);
    const mmEntries = rz.readEntries(arc).map((e) => [e.name, rz.readEntry(arc, e)]);
    zip(path.join(portDir, 'mm.o2r'), [...mmEntries, ['portVersion', pv(2)]]);   // the port makes it again
    await js(`document.querySelector('#check-again').click()`); await wait(300); await settle();
    check(/Ready/.test(await status()) && !/outdated/.test(await chip()), `Ship Mods: Check again sees the archive made again (${await status()})`);
    check(/Made by 2 Ship 2 Harkinian 2\.0\.0, matches the installed build/.test(await js("document.querySelector('#sx-id').innerText")), 'Ship Mods: the card says which build made the archive');
    fs.renameSync(path.join(portDir, 'mm.o2r'), path.join(portDir, 'mm.bak'));
    await js('findPorts()'); for (let i = 0; i < 50 && (await js('SHIP.finding')); i++) await wait(100); await settle();
    check(/not made yet/i.test(await status()) && /run once/.test(await chip()), `Ship Mods: Search again sees the game archive is gone (${await status()} / ${await chip()})`);
    fs.renameSync(path.join(portDir, 'mm.bak'), path.join(portDir, 'mm.o2r'));
    await js(`window.dispatchEvent(new Event('focus'))`); await wait(300); await settle();
    check(/Ready/.test(await status()), 'Ship Mods: coming back to the app checks again');
  }
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

  // Step 6: ROM Tools. Picking a folder scans it on its own; clicking a ROM shows its header.
  // HTK_ROMS=<folder of real ROMs> also checks that their checksums come out OK.
  const romDir = process.env.HTK_ROMS || path.join(out, 'roms');
  if (!process.env.HTK_ROMS) {
    fs.mkdirSync(path.join(romDir, 'USA'), { recursive: true });
    const head = (title, code) => { const b = Buffer.alloc(0x2000, 0x11); b.writeUInt32BE(0x80371240, 0); b.fill(0x20, 0x20, 0x34); b.write(title, 0x20, 'latin1'); b.write(code, 0x3b, 'latin1'); return b; };
    fs.writeFileSync(path.join(romDir, 'USA', 'Alpha.z64'), head('ALPHA TEST', 'NATE'));
    const v = head('PAPERMARIO', 'NMQJ');            // a Japanese copy of a library game: same box art for (let i = 0; i < v.length; i += 2) { const t = v[i]; v[i] = v[i + 1]; v[i + 1] = t; }
    fs.writeFileSync(path.join(romDir, 'Bravo.v64'), v);
  }
  global.dialogs = [];
  await js(`cfg.roms.folder = ''; ROMS.asked = false; document.querySelector('nav button[data-page="upscale"]').click()`); await wait(200);
  await js(`document.querySelector('nav button[data-page="roms"]').click()`); await wait(500);
  check(global.dialogs.includes('folder'), 'ROM Tools: opening it with no folder asks where the ROMs are');
  await js(`window.__done = null; if (!window.__hooked) { window.__hooked = true; window.htk.onDone((d) => { window.__done = d; }); }
    cfg.roms.folder = ${JSON.stringify(romDir)}; onPath('roms.folder'); render();`);
  let rd = null; for (let i = 0; i < 300 && !rd; i++) { await wait(100); rd = await js('window.__done'); }
  const want = process.env.HTK_ROMS ? null : 2;
  check(rd && rd.task === 'roms' && rd.result.count > 0 && (want == null || rd.result.count === want), `ROM Tools: picking the folder scans it (${rd ? rd.result.count : 0} ROMs)`);
  await wait(300);
  check((await js("document.querySelectorAll('.rom-item').length")) === (rd ? rd.result.count : -1), 'ROM Tools: every ROM is listed');
  await js("([...document.querySelectorAll('.rom-item')].find((b) => /ALPHA/.test(b.textContent)) || document.querySelector('.rom-item')).click()"); await wait(1500);
  const det = await js("document.querySelector('#rom-detail').innerText");
  check(/GAME/.test(det) && /MD5/.test(det) && /CIC chip/.test(det), 'ROM Tools: clicking a ROM shows its details');
  if (process.env.HTK_ROMS) {
    let allOk = true;
    for (const r of rd.result.roms) { const i = await js(`window.htk.romInfo(${JSON.stringify(r.path)})`); if (!i || i.checksumOk !== true) { allOk = false; report.push(`  checksum: ${r.rel}: ${i && (i.checksum || i.error)}`); } }
    check(allOk, `ROM Tools: checksum OK for all ${rd.result.count} real ROMs`);
  } else {
    check(/ALPHA TEST/.test(det) && /NATE/.test(det) && /North America/.test(det), 'ROM Tools: title, game code and region read');
    check((await js("document.querySelector('#rx-desc').innerText")).trim() === 'No ROM match found, what is this game?', 'ROM Tools: a game not in the library says so');
    check(/ROM: 1 out of 303 \(NTSC\) titles found/.test(await js("document.querySelector('#rx-count').innerText")), 'ROM Tools: counter shows 1 out of 303 titles');
    await js("[...document.querySelectorAll('.rom-item')].find((b) => /PAPERMARIO/.test(b.textContent)).click()"); await wait(1200);
    const art = await js("(() => { const i = document.querySelector('#rx-art img'); return i ? [i.getAttribute('src'), i.naturalWidth] : null; })()");
    check(art && /Paper%20Mario/.test(art[0]) && art[1] > 0, 'ROM Tools: box art shows (Japanese ROM, US box)');
    check(/paper-styled visuals/.test(await js("document.querySelector('#rx-desc').innerText")), 'ROM Tools: game description shows');
    check(/Paper%20Mario/.test(await js("document.querySelector('#rx-ghost').style.backgroundImage")), 'ROM Tools: faded box art behind the details');
    check(/Paper%20Mario/.test(await js("(document.querySelector('.rom-item.on .rom-art') || {}).outerHTML || ''")) && (await js("document.querySelectorAll('.rom-art').length")) === 1, 'ROM Tools: the selected row shows its box art (and only that row)');
    check(await js("document.querySelector('#rx-prog').hidden"), 'ROM Tools: no progress bar once the scan is done');
    check(await js("getComputedStyle(document.querySelector('.rom-folderpick .glow')).filter.includes('drop-shadow')"), 'ROM Tools: Browse… glows');
    await js("document.querySelector('#rom-search').value = 'paper'; document.querySelector('#rom-search').dispatchEvent(new Event('input', { bubbles: true }))"); await wait(200);
    check((await js("[...document.querySelectorAll('.rom-item b')].map((b) => b.textContent).join()")) === 'PAPERMARIO', 'ROM Tools: search filters the list');
    await js("document.querySelector('#rom-search').value = ''; document.querySelector('#rom-search').dispatchEvent(new Event('input', { bubbles: true }))");
  }
  await wait(200); await shot('run-rom-tools');

  fs.writeFileSync(path.join(shots, 'selftest.txt'), report.join('\n') + '\n');
  app.exit(report.some((l) => l.startsWith('FAIL')) ? 1 : 0);
};
