'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { stats, route } = require('../app/core/smart');

function img(w, h, fn) {
  const data = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const [r, g, b, a] = fn(x, y); data.set([r, g, b, a], (y * w + x) * 4); }
  return { width: w, height: h, data };
}
const noisy = (x, y) => [(x * 37 + y * 11) & 255, (x * 7 + y * 53) & 255, (x * 91 + y * 29) & 255, 255];

test('smart: tiny textures go pixel-perfect', () => {
  assert.strictEqual(route(stats(img(16, 16, noisy))), 'pixel');
});

test('smart: a 2-colour font sheet goes pixel-perfect', () => {
  const s = stats(img(64, 32, (x, y) => ((x ^ y) & 4 ? [255, 255, 255, 255] : [0, 0, 0, 0])));
  assert.deepStrictEqual([s.colors, s.alpha], [1, 'binary']);
  assert.strictEqual(route(s), 'pixel');
});

test('smart: big detailed textures go to AI', () => {
  assert.strictEqual(route(stats(img(64, 64, noisy))), 'ai');
});

test('smart: mid-detail textures go HD', () => {
  const s = stats(img(32, 32, (x, y) => [x * 2, y * 2, 40, 255]));
  assert.ok(s.colors > 8 && s.colors < 96 || s.colors >= 96);
  assert.strictEqual(route({ w: 32, h: 32, colors: 40, alpha: 'opaque' }), 'hd');
  assert.strictEqual(route({ w: 128, h: 16, colors: 200, alpha: 'opaque' }), 'hd');   // a thin strip: not enough height for AI
});

test('smart: soft alpha is noticed', () => {
  assert.strictEqual(stats(img(4, 4, () => [10, 10, 10, 128])).alpha, 'soft');
  assert.strictEqual(stats(img(4, 4, (x) => [10, 10, 10, x ? 255 : 0])).alpha, 'binary');
});

test('smart: one upscale run picks a method per texture, AI parts fall back to HD without Real-ESRGAN', async () => {
  const fs = require('fs'), os = require('os'), path = require('path');
  const tasks = require('../app/core/tasks');
  const { encodePNG } = require('../app/core/png');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'smart-')), inDir = path.join(dir, 'in'), out = path.join(dir, 'out');
  fs.mkdirSync(inDir);
  fs.writeFileSync(path.join(inDir, 'tiny.png'), encodePNG(img(8, 8, noisy)));
  fs.writeFileSync(path.join(inDir, 'font.png'), encodePNG(img(64, 32, (x, y) => ((x ^ y) & 4 ? [255, 255, 255, 255] : [0, 0, 0, 0]))));
  fs.writeFileSync(path.join(inDir, 'stone.png'), encodePNG(img(64, 64, noisy)));
  const log = [], steps = [];
  const ctx = { workers: 2, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: (d, t) => steps.push([d, t]) };
  const r = await tasks.upscaleTask({ inputs: [inDir], output: out, size: 4, method: 'smart', sharpness: 'normal', edges: 'clamp', format: 'png', hardAlpha: true }, ctx, {});
  assert.strictEqual(r.written, 3);
  assert.ok(log.some((l) => /Real-ESRGAN isn't downloaded, so the 1 AI texture\(s\) use HD 4×/.test(l)), log.join('\n'));
  assert.ok(log.some((l) => /Smart: 1 HD 4×, 0 AI 4×, 2 pixel-perfect/.test(l)), log.join('\n'));
  const last = steps[steps.length - 1]; assert.deepStrictEqual(last, [30, 30]);         // 3 looked at + 3 x 9 upscaled
  // the pixel-perfect ones are blocky: every 4x4 block in the tiny one is one colour
  const { loadImage } = require('../app/core/image');
  const t = loadImage(path.join(out, 'tiny.png'));
  assert.deepStrictEqual([t.width, t.height], [32, 32]);
  assert.deepStrictEqual([...t.data.subarray(0, 4)], [...t.data.subarray(12, 16)]);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('estimate: counts, disk, video memory and the Smart split', async () => {
  const fs = require('fs'), os = require('os'), path = require('path');
  const tasks = require('../app/core/tasks');
  const { encodePNG } = require('../app/core/png');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'est-'));
  fs.writeFileSync(path.join(dir, 'tiny.png'), encodePNG(img(8, 8, noisy)));
  fs.writeFileSync(path.join(dir, 'stone.png'), encodePNG(img(64, 64, noisy)));
  const e = await tasks.estimate({ inputs: [dir], method: 'smart', size: 4, sharpness: 'normal', format: 'dds', ddsFormat: 'bc7', maxSize: 4096 }, {}, 2);
  assert.strictEqual(e.count, 2);
  assert.deepStrictEqual(e.groups, { pixel: 1, hd: 1, ai: 0 });               // no Real-ESRGAN: the stone goes HD
  const px = 32 * 32 + 256 * 256;
  assert.strictEqual(e.disk, Math.round(px * 4 / 3));                           // BC7: 1 byte a pixel, plus mipmaps
  assert.strictEqual(e.vram, e.disk);
  assert.ok(e.seconds >= 0);
  fs.rmSync(dir, { recursive: true, force: true });
});
