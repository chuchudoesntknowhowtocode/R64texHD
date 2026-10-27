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
  await wait(3200);                                   // splash: 2.5 s, then gone
  check(await js("document.querySelector('#splash').hidden"), 'splash fades out on its own');
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
  const soon = await js("window.htk.run('legacyImport', {})");
  check(soon.ok === false && /next build/.test(soon.error), 'Rice / GLideN64 page says "next build"');

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

  fs.writeFileSync(path.join(shots, 'selftest.txt'), report.join('\n') + '\n');
  app.exit(report.some((l) => l.startsWith('FAIL')) ? 1 : 0);
};
