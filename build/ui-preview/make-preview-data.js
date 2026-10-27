'use strict';
// Makes build/ui-preview/preview-data.js: a sample 32x32 N64-style texture and its real 4x Standard
// upscale (DDS, Auto compression, decoded back), so UI screenshots show a genuine result.
const fs = require('fs');
const path = require('path');
const core = (m) => require(path.join(__dirname, '..', '..', 'app', 'core', m));
const { upscale } = core('upscale');
const dds = core('dds');

// Stone bricks with mortar, a little noise and shading: the kind of texture N64 games tile on walls.
const W = 32, H = 32, d = new Uint8Array(W * H * 4);
const noise = (x, y) => (((x * 73856093) ^ (y * 19349663) ^ 0x5bd1e995) >>> 0) % 23;
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
  const row = Math.floor(y / 8), bx = (x + (row % 2 ? 8 : 0)) % 16, by = y % 8;
  const mortar = bx === 0 || by === 0;
  const edge = bx === 1 || by === 1 ? 18 : bx === 15 || by === 7 ? -16 : 0;
  const n = noise(x, y), i = (y * W + x) * 4;
  if (mortar) d.set([92 + n, 86 + n, 78 + n, 255], i);
  else d.set([150 + n + edge + row * 3, 70 + (n >> 1) + edge / 2, 44 + (n >> 1), 255], i);
}
const orig = { width: W, height: H, data: d };
const up = upscale(orig, { size: 4, method: 'standard', sharpness: 'normal', edges: ['wrap', 'wrap'], hardAlpha: true, maxSize: 4096 });
const shown = dds.decodeDDS(dds.encodeDDS(up, 'auto', { mipmaps: false }));
const b64 = (img) => Buffer.from(img.data).toString('base64');
fs.writeFileSync(path.join(__dirname, 'preview-data.js'),
  `window.__PREVIEW = ${JSON.stringify({ orig: { width: W, height: H, data: b64(orig) }, up: { width: shown.width, height: shown.height, data: b64(shown) }, encoded: 'DDS BC1' })};\n`);
console.log('preview-data.js written', up.width + 'x' + up.height);
