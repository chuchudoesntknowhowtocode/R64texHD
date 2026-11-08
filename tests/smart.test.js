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

test('smart: a 2-colour font sheet goes to MMPX pixel art', () => {
  const s = stats(img(64, 32, (x, y) => ((x ^ y) & 4 ? [255, 255, 255, 255] : [0, 0, 0, 0])));
  assert.deepStrictEqual([s.colors, s.alpha], [1, 'binary']);
  assert.strictEqual(route(s), 'mmpx');
  assert.strictEqual(route({ w: 32, h: 32, colors: 6, alpha: 'opaque' }), 'mmpx');          // a flat HUD tile
});

test('smart: with the texture models, AI uses GameAI and colourful cut-out sprites get the Pixel model', () => {
  const { routeModel } = require('../app/core/smart');
  const sprite = { w: 48, h: 48, colors: 60, alpha: 'binary' };
  assert.strictEqual(route(sprite), 'hd');
  assert.strictEqual(route(sprite, { models: true }), 'aisprite');
  assert.strictEqual(routeModel('aisprite', { models: true }), 'pixelperfect4-x4');
  assert.strictEqual(routeModel('ai', { models: true }), 'gameai2-x4');
  assert.strictEqual(routeModel('ai', { models: false }), null);                            // the Settings model
  assert.strictEqual(route({ w: 12, h: 12, colors: 60, alpha: 'binary' }, { models: true }), 'pixel');   // never HDCube / AI under 16 px
});

test('smart: checker dithering is detected and softened, flat and noisy textures are not', () => {
  const { ditherScore, dedither } = require('../app/core/upscale');
  const checker = img(16, 16, (x, y) => ((x + y) & 1 ? [120, 80, 60, 255] : [140, 96, 70, 255]));
  const flat = img(16, 16, () => [120, 80, 60, 255]);
  assert.ok(ditherScore(checker) > 0.9, String(ditherScore(checker)));
  assert.strictEqual(ditherScore(flat), 0);
  assert.ok(ditherScore(img(16, 16, noisy)) < 0.12);
  const soft = dedither(checker);
  const at = (x, y) => soft.data[(y * 16 + x) * 4];
  assert.ok(Math.abs(at(5, 5) - at(6, 5)) < 4, `${at(5, 5)} vs ${at(6, 5)}`);               // dots pulled together
  assert.strictEqual(dedither(flat).data[0], 120);
  assert.ok(stats(checker).dither > 0.9);
});

test('mmpx: 2x per pass, keeps the palette, smooths a diagonal, flat stays flat', () => {
  const { mmpx2, mmpxScale } = require('../app/core/mmpx');
  const W = [255, 255, 255, 255], K = [0, 0, 0, 255];
  const diag = img(8, 8, (x, y) => (x === y ? K : W));
  const o = mmpx2(diag);
  assert.deepStrictEqual([o.width, o.height], [16, 16]);
  const cols = new Set(); for (let i = 0; i < o.data.length; i += 4) cols.add(o.data.slice(i, i + 4).join());
  assert.deepStrictEqual([...cols].sort(), [K.join(), W.join()].sort());                       // no new colours
  const px = (x, y) => o.data.slice((y * 16 + x) * 4, (y * 16 + x) * 4 + 4).join();
  assert.strictEqual(px(3, 2), K.join());                                                      // a 1 px line stays unbroken
  const edge = mmpx2(img(8, 8, (x, y) => (x < y ? K : W)));                                   // a solid diagonal edge
  const ep = (x, y) => edge.data[(y * 16 + x) * 4];
  for (let y = 2; y < 15; y++) for (let x = 0; x < 16; x++) assert.strictEqual(ep(x, y) === 0, x < y, `edge at ${x},${y}`);   // 1 px steps, not 2
  const flat = mmpx2(img(4, 4, () => K));
  assert.ok(flat.data.every((v, i) => v === K[i % 4]));
  const s = mmpxScale(img(8, 8, (x, y) => (x === y ? K : W)), 32, 32);
  assert.deepStrictEqual([s.width, s.height], [32, 32]);
  const s6 = mmpxScale(diag, 48, 48);                                                         // 6x: MMPX 4x, then nearest
  assert.deepStrictEqual([s6.width, s6.height], [48, 48]);
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
  assert.ok(log.some((l) => /Smart: 1 HD 4×, 0 AI 4×, 1 pixel art \(MMPX\), 1 pixel-perfect/.test(l)), log.join('\n'));
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
  assert.deepStrictEqual(e.groups, { pixel: 1, mmpx: 0, hd: 1, ai: 0, aisprite: 0, aidither: 0 });               // no Real-ESRGAN: the stone goes HD
  const px = 32 * 32 + 256 * 256;
  assert.strictEqual(e.disk, Math.round(px * 4 / 3));                           // BC7: 1 byte a pixel, plus mipmaps
  assert.strictEqual(e.vram, e.disk);
  assert.ok(e.seconds >= 0);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('scenes: the index lists only clips that are here; a downloaded pack fills in the rest', () => {
  const fs = require('fs'), os = require('os'), path = require('path');
  const scenes = require('../app/core/scenes');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'scn-')), appDir = path.join(root, 'app'), data = path.join(root, 'data');
  fs.mkdirSync(path.join(appDir, 'classic_01'), { recursive: true });
  fs.writeFileSync(path.join(appDir, 'classic_01', 'clip.json'), '{}');
  fs.writeFileSync(path.join(appDir, 'index.json'), JSON.stringify({ classic_01: { kind: 'classic' }, fight_goblin_robed: { kind: 'fight' } }));
  let r = scenes.index(appDir, data);
  assert.deepStrictEqual([Object.keys(r.index), r.here, r.total], [['classic_01'], 1, 2]);
  assert.ok(r.index.classic_01.base.startsWith('file://') && r.index.classic_01.base.endsWith('/classic_01/'));
  assert.deepStrictEqual(scenes.missing(appDir, data), ['fight_goblin_robed']);
  const got = scenes.install([
    { name: 'fight_goblin_robed/clip.json', data: () => Buffer.from('{}') },
    { name: 'fight_goblin_robed/atlas_0.webp', data: () => Buffer.from('x') },
    { name: '../evil/clip.json', data: () => Buffer.from('{}') },
    { name: 'Fight/x.exe', data: () => Buffer.from('x') }], data);
  assert.deepStrictEqual(got, { files: 2, clips: 1 });
  r = scenes.index(appDir, data);
  assert.strictEqual(r.here, 2);
  assert.ok(scenes.clipFile('fight_goblin_robed', appDir, data).startsWith(data));
  assert.strictEqual(scenes.clipFile('../x', appDir, data), null);
  fs.rmSync(root, { recursive: true, force: true });
});

test('smart: with the ONNX engine, dithered AI textures go to RGT-S dither (not softened first)', () => {
  const { routeModel, isAi } = require('../app/core/smart');
  const big = { w: 64, h: 64, colors: 200, alpha: 'opaque', dither: 0.3 };
  assert.strictEqual(route(big), 'ai');
  assert.strictEqual(route(big, { onnx: true }), 'aidither');
  assert.strictEqual(route({ ...big, dither: 0.01 }, { onnx: true }), 'ai');
  assert.strictEqual(routeModel('aidither'), 'rgts-dither-x4');
  assert.ok(isAi('aidither'));
});
