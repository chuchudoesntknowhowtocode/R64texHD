'use strict';
// Roadmap 10: Compare picks — a texture's saved pick overrides the method in the Upscale run and in the preview.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const tasks = require('../app/core/tasks');
const png = require('../app/core/png');

const quietCtx = (log = []) => ({ workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} });
function gradient(w, h) {
  const d = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set([x * 16, y * 16, (x * y) & 255, 255], (y * w + x) * 4);
  return { width: w, height: h, data: d };
}
// Every 4×4 block one colour: what Pixel-perfect (nearest neighbour) makes from a 4× upscale.
function blocky(img) {
  for (let y = 0; y < img.height; y++) for (let x = 0; x < img.width; x++) {
    const o = (y * img.width + x) * 4, b = ((y & ~3) * img.width + (x & ~3)) * 4;
    for (let c = 0; c < 4; c++) if (img.data[o + c] !== img.data[b + c]) return false;
  }
  return true;
}

test('picks: keys, parsing and what this PC can make', () => {
  assert.equal(tasks.pickKey('C:/dump/textures/0123456789ABCDEF.png', 'textures/0123456789ABCDEF.png'), '0123456789abcdef');
  assert.equal(tasks.pickKey('/x/Sub/Wall.png', 'Sub\\Wall.png'), 'sub/wall.png');
  assert.deepEqual(tasks.parsePick('mmpx'), { route: 'mmpx', model: null });
  assert.deepEqual(tasks.parsePick('ai:gameai2-x4'), { route: 'ai', model: 'gameai2-x4' });
  assert.equal(tasks.parsePick('smart'), null);
  assert.equal(tasks.parsePick('ai:../x'), null);
  assert.equal(tasks.pickUsable(tasks.parsePick('ai:realesrgan-x4plus'), {}, true), false);
  assert.equal(tasks.pickUsable(tasks.parsePick('ai:realesrgan-x4plus'), { realesrgan: 'x' }, true), true);
  assert.equal(tasks.pickUsable(tasks.parsePick('ai:gameai2-x4'), { realesrgan: 'x' }, true), false);
  assert.equal(tasks.pickUsable(tasks.parsePick('ai:gameai2-x4'), { realesrgan: 'x', models: 'y' }, false), false);
});

test('picks: the run uses the picked version; textures without a pick keep the method', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'picks-')), inDir = path.join(dir, 'in'), out = path.join(dir, 'out');
  fs.mkdirSync(inDir);
  fs.writeFileSync(path.join(inDir, '1111111111111111.png'), png.encodePNG(gradient(16, 16)));
  fs.writeFileSync(path.join(inDir, '2222222222222222.png'), png.encodePNG(gradient(16, 16)));
  const log = [];
  await tasks.upscaleTask({ inputs: [inDir], output: out, size: 4, method: 'standard', sharpness: 'normal', edges: 'clamp', format: 'png', hardAlpha: true,
    picks: { '1111111111111111': 'pixel', '2222222222222222x': 'mmpx', '3333333333333333': 'ai:gameai2-x4' } }, quietCtx(log), {});
  const a = png.decodePNG(fs.readFileSync(path.join(out, '1111111111111111.png')));
  const b = png.decodePNG(fs.readFileSync(path.join(out, '2222222222222222.png')));
  assert.deepEqual([a.width, b.width], [64, 64]);
  assert.ok(blocky(a), 'picked texture is pixel-perfect');
  assert.ok(!blocky(b), 'the other one is Standard');
  assert.ok(log.some((l) => /Your picks: 1 texture/.test(l) && /Pixel-perfect/.test(l)), log.join('\n'));
  // An AI pick on a PC without Real-ESRGAN falls back to the method and says so.
  const log2 = [];
  await tasks.upscaleTask({ inputs: [inDir], output: out, existing: 'overwrite', size: 4, method: 'standard', sharpness: 'normal', edges: 'clamp', format: 'png',
    picks: { '1111111111111111': 'ai:realesrgan-x4plus' } }, quietCtx(log2), {});
  assert.ok(log2.some((l) => /1 pick\(s\) need AI/.test(l)), log2.join('\n'));
  // Preview of one Compare cell.
  const r = await tasks.preview({ src: path.join(inDir, '1111111111111111.png'), method: 'standard', size: 4, sharpness: 'normal', edges: 'clamp', format: 'png', pick: 'mmpx' }, {});
  assert.equal(r.route, 'Pixel art (MMPX)');
  assert.equal(r.up.width, 64);
  const e = await tasks.preview({ src: path.join(inDir, '1111111111111111.png'), method: 'standard', size: 4, edges: 'clamp', format: 'png', pick: 'ai:realesrgan-x4plus' }, {});
  assert.match(e.error, /Real-ESRGAN/);
  await tasks.closePreview();
  fs.rmSync(dir, { recursive: true, force: true });
});
