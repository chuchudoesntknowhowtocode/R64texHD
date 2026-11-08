'use strict';
// Edge-aware shrink: a tiling texture shrunk with wrap edges matches the middle of its 3×3 tiling shrunk as one
// image (no seam at the border); clamp does not.
const test = require('node:test');
const assert = require('node:assert/strict');
const { resizeRGBA, shrinkCut } = require('../app/core/upscale');

function tile(n) {
  const d = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) d.set([(x * 255 / (n - 1)) | 0, (128 + 120 * Math.sin(y * 0.7)) | 0, ((x * 31 + y * 17) * 7) & 255, 255], (y * n + x) * 4);
  return { width: n, height: n, data: d };
}
function tiled3(t) {
  const n = t.width, N = n * 3, d = new Uint8Array(N * N * 4);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) d.set(t.data.subarray(((y % n) * n + (x % n)) * 4, ((y % n) * n + (x % n)) * 4 + 4), (y * N + x) * 4);
  return { width: N, height: N, data: d };
}
function maxDiffCentre(big, small) {
  const n = small.width; let m = 0;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) for (let c = 0; c < 3; c++)
    m = Math.max(m, Math.abs(big.data[((y + n) * big.width + x + n) * 4 + c] - small.data[(y * n + x) * 4 + c]));
  return m;
}

test('shrink: wrap edges have no seam, clamp does', () => {
  const t = tile(32), ref = resizeRGBA(tiled3(t), 48, 48);
  assert.ok(maxDiffCentre(ref, resizeRGBA(t, 16, 16, ['wrap', 'wrap'])) <= 2);
  assert.ok(maxDiffCentre(ref, resizeRGBA(t, 16, 16)) > 8);
  const s = shrinkCut(t, 16, 16, { edges: 'wrap' }, 'opaque');
  assert.ok(maxDiffCentre(ref, s) <= 2);
  assert.deepEqual([s.width, s.height], [16, 16]);
});
