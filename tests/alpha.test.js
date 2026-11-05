'use strict';
// Alpha handling (roadmap 4): classifier, colour bleed, separate alpha upscale, cut-out threshold.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const core = (m) => require(path.join(__dirname, '..', 'app', 'core', m));
const { upscale, fillTransparent, alphaKind } = core('upscale');
const smart = core('smart');

// w×h RGBA image; f(x, y) -> [r, g, b, a]
function make(w, h, f) {
  const data = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) data.set(f(x, y), (y * w + x) * 4);
  return { width: w, height: h, data };
}
// A round cut-out: red disc on black hidden pixels (the dark colour must not bleed in).
const disc = (w = 16, a = (inside) => (inside ? 255 : 0)) => make(w, w, (x, y) => {
  const inside = (x - w / 2 + 0.5) ** 2 + (y - w / 2 + 0.5) ** 2 < (w * 0.35) ** 2;
  return inside ? [220, 40, 30, a(true)] : [0, 0, 0, a(false)];
});
const alphas = (img) => { const s = new Set(); for (let i = 3; i < img.data.length; i += 4) s.add(img.data[i]); return s; };
const visible = (img) => { let n = 0; for (let i = 3; i < img.data.length; i += 4) if (img.data[i]) n++; return n; };

test('alphaKind: opaque, on/off, near on/off and soft', () => {
  assert.equal(alphaKind(make(8, 8, () => [1, 2, 3, 255])), 'opaque');
  assert.equal(alphaKind(disc()), 'binary');
  assert.equal(alphaKind(disc(16, (i) => (i ? 250 : 4))), 'binary');            // DXT-style noise near 0 / 255
  const edge = disc(64); edge.data[3] = 128;                                     // one soft pixel in 4096
  assert.equal(alphaKind(edge), 'binary');
  assert.equal(alphaKind(make(16, 16, (x) => [200, 200, 200, x * 16])), 'soft'); // smoke / glass ramp
  assert.equal(smart.stats(disc(16, (i) => (i ? 250 : 4))).alpha, 'binary');    // Smart uses the same rules
});

test('fillTransparent reaches every hidden pixel and keeps alpha', () => {
  const img = make(64, 64, (x, y) => (x === 0 && y === 0 ? [10, 200, 30, 255] : [0, 0, 0, 0]));
  const out = fillTransparent(img);
  for (let i = 0; i < 64 * 64; i++) {
    assert.deepEqual([...out.data.slice(i * 4, i * 4 + 3)], [10, 200, 30]);
    assert.equal(out.data[i * 4 + 3], img.data[i * 4 + 3]);
  }
});

test('cut-out upscale: hard alpha, no dark fringe, threshold moves the edge', () => {
  for (const method of ['standard', 'smooth']) {
    const src = disc(16, (i) => (i ? 251 : 3));
    const out = upscale(src, { size: 4, method, sharpness: 'strong' });
    assert.deepEqual([...alphas(out)].sort((a, b) => a - b), [0, 255], method);
    for (let i = 0; i < out.data.length; i += 4) if (out.data[i + 3]) assert.ok(out.data[i] > 150, `${method}: dark fringe at ${i / 4}`);
    const thin = visible(upscale(src, { size: 4, method, alphaThreshold: 0.8 }));
    const thick = visible(upscale(src, { size: 4, method, alphaThreshold: 0.2 }));
    assert.ok(thick > thin, `${method}: lower threshold keeps more (${thick} vs ${thin})`);
  }
  const soft = upscale(disc(), { size: 4, method: 'standard', hardAlpha: false });
  assert.ok(alphas(soft).size > 2, 'Smooth cut-out edges keep in-between alpha');
});

test('soft alpha stays soft with Hard cut-out edges on', () => {
  const out = upscale(make(16, 16, (x) => [200, 200, 200, x * 16]), { size: 2, method: 'standard', hardAlpha: true });
  assert.ok(alphas(out).size > 8);
});

test('AI start: colour from the AI image, alpha from the source', () => {
  const src = disc();
  const ai = make(64, 64, () => [90, 90, 90, 255]);            // what Real-ESRGAN returns: colour only
  const out = upscale(src, { size: 4, method: 'ai', sharpness: 'off' }, { img: ai, scale: 4 });
  assert.deepEqual([...alphas(out)].sort((a, b) => a - b), [0, 255]);
  assert.equal(visible(out), visible(upscale(src, { size: 4, method: 'standard' })));
  assert.equal(out.data[(32 * 64 + 32) * 4], 90);
});
