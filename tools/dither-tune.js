'use strict';
// Dither threshold tuning: scores every PNG/DDS in a folder (recursive, .map ignored) at several
// DITHER_NEAR limits and shows how many would count as dithered at several DITHERED shares.
// Usage: node tools/dither-tune.js <folder> [--csv out.csv] [--near 24,32,40,48,56,64,80] [--top 15]
const fs = require('fs');
const path = require('path');
const { loadImage } = require('../app/core/image');
const { ditherScore, DITHER_NEAR } = require('../app/core/upscale');
const smart = require('../app/core/smart');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const dir = args[0];
if (!dir) { console.error('usage: node tools/dither-tune.js <folder> [--csv out.csv] [--near a,b,c] [--top n]'); process.exit(2); }
const nears = opt('--near', '24,32,40,48,56,64,80').split(',').map(Number);
const shares = [0.04, 0.08, 0.12, 0.16, 0.2, 0.3];
const top = Number(opt('--top', 15));

const files = [];
(function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (/\.(png|dds)$/i.test(e.name)) files.push(p);
  }
})(dir);

const rows = [];
for (const f of files) {
  let img; try { img = loadImage(f); } catch { continue; }
  const st = smart.stats(img);
  const sc = nears.map((n) => Math.round(ditherScore(img, n) * 1000) / 1000);
  rows.push({ f: path.relative(dir, f), w: st.w, h: st.h, colors: st.colors, alpha: st.alpha, sc,
    route: smart.route(st, { models: true, onnx: true }) });
}
const csv = opt('--csv');
if (csv) fs.writeFileSync(csv, ['file,w,h,colors,alpha,route,' + nears.map((n) => 'near' + n).join(',')]
  .concat(rows.map((r) => [JSON.stringify(r.f), r.w, r.h, r.colors, r.alpha, r.route, ...r.sc].join(','))).join('\n'));

console.log(`${rows.length} images (current: DITHER_NEAR ${DITHER_NEAR}, DITHERED ${smart.DITHERED})`);
console.log('dithered count (all / AI-route candidates: min side>=32, colours>=96)');
console.log('near\\share ' + shares.map((s) => String(s).padStart(10)).join(''));
const aiCand = (r) => Math.min(r.w, r.h) >= 32 && r.colors >= 96;
nears.forEach((n, i) => {
  console.log(String(n).padEnd(11) + shares.map((s) => {
    const all = rows.filter((r) => r.sc[i] >= s).length, ai = rows.filter((r) => aiCand(r) && r.sc[i] >= s).length;
    return `${all}/${ai}`.padStart(10);
  }).join(''));
});
const cur = nears.indexOf(DITHER_NEAR);
if (cur >= 0) {
  const by = [...rows].sort((a, b) => b.sc[cur] - a.sc[cur]);
  console.log(`top ${top} at near ${DITHER_NEAR}:`);
  for (const r of by.slice(0, top)) console.log(`  ${r.sc[cur].toFixed(3)} ${r.w}x${r.h} c${r.colors} ${r.route} ${r.f}`);
}
