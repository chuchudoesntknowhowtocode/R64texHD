'use strict';
// AI colour fix (roadmap 5): broad hue/brightness drift is taken off, detail and alpha stay.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { upscale, colourFix } = require(path.join(__dirname, '..', 'app', 'core', 'upscale'));

function make(w, h, f) {
  const data = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) data.set(f(x, y), (y * w + x) * 4);
  return { width: w, height: h, data };
}
const nearest4 = (img, f) => make(img.width * 4, img.height * 4, (x, y) => f(img.data.slice(((y >> 2) * img.width + (x >> 2)) * 4, ((y >> 2) * img.width + (x >> 2)) * 4 + 4), x, y));
const mean = (img, c) => { let s = 0, n = 0; for (let i = 0; i < img.data.length; i += 4) if (img.data[i + 3] > 8) { s += img.data[i + c]; n++; } return s / n; };

test('colourFix pulls a tinted AI result back to the source colours, keeping detail', () => {
  const src = make(32, 32, (x, y) => [120 + (x % 4) * 10, 90, 60 + y, 255]);
  // Fake AI: same picture, warmer and darker, plus fine detail (a 1px checker).
  const ai = nearest4(src, (p, x, y) => [p[0] + 30, p[1] - 20, p[2] - 15, 255].map((v, c) => (c < 3 ? v + ((x + y) & 1 ? 6 : -6) : v)));
  const fixed = colourFix(ai, src);
  for (let c = 0; c < 3; c++) assert.ok(Math.abs(mean(fixed, c) - mean(src, c)) < 2, `channel ${c}: ${mean(fixed, c)} vs ${mean(src, c)}`);
  const k = (40 * 128 + 40) * 4, k2 = (40 * 128 + 41) * 4;
  assert.ok(Math.abs(fixed.data[k] - fixed.data[k2]) >= 10, 'checker detail survives');
});

test('grey sources come back grey; hidden pixels do not skew the fix', () => {
  const src = make(16, 16, (x, y) => (x < 4 ? [255, 0, 255, 0] : [100 + x * 5, 100 + x * 5, 100 + x * 5, 255]));
  const ai = nearest4(src, (p) => [p[0] + 25, p[1], p[2] - 10, 255]);
  const fixed = colourFix(ai, src);
  for (let i = 0; i < fixed.data.length; i += 4) assert.ok(fixed.data[i] === fixed.data[i + 1] && fixed.data[i + 1] === fixed.data[i + 2]);
  const vis = (img) => { let s = 0, n = 0; for (let y = 0; y < 64; y++) for (let x = 16; x < 64; x++) { s += img.data[(y * 64 + x) * 4]; n++; } return s / n; };
  const want = (() => { let s = 0, n = 0; for (let y = 0; y < 16; y++) for (let x = 4; x < 16; x++) { s += src.data[(y * 16 + x) * 4]; n++; } return s / n; })();
  assert.ok(Math.abs(vis(fixed) - want) < 2, `${vis(fixed)} vs ${want}`);
});

test('upscale with AI start: colour fixed by default, off when asked; alpha untouched', () => {
  const src = make(16, 16, (x, y) => [200, 60, 40, (x - 8) ** 2 + (y - 8) ** 2 < 30 ? 255 : 0]);
  const ai = make(64, 64, () => [230, 40, 20, 255]);
  const o = { size: 4, method: 'ai', sharpness: 'off' };
  const on = upscale(src, o, { img: ai, scale: 4 }), off = upscale(src, { ...o, colourFix: false }, { img: ai, scale: 4 });
  const c = (32 * 64 + 32) * 4;
  assert.ok(Math.abs(on.data[c] - 200) <= 2 && Math.abs(on.data[c + 1] - 60) <= 2, `${on.data.slice(c, c + 3)}`);
  assert.equal(off.data[c], 230);
  for (let i = 3; i < on.data.length; i += 4) assert.equal(on.data[i], off.data[i]);
});
