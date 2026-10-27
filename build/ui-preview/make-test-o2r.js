'use strict';
// Writes a small made-up Ship game archive (mm.o2r) for the app self-test:  node make-test-o2r.js <file>
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const core = (m) => require(path.join(__dirname, '..', '..', 'app', 'core', m));
const o2r = core('o2r'), rtz = core('rtz');
const img = (w, h, fn) => { const d = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set(fn(x, y), (y * w + x) * 4); return { width: w, height: h, data: d }; };
const file = process.argv[2];
fs.mkdirSync(path.dirname(file), { recursive: true });
const zip = new rtz.ZipWriter(file);
const add = (name, buf) => zip.add(name, zlib.deflateRawSync(buf), 8, zlib.crc32(buf), buf.length, Date.now());
const brick = img(32, 32, (x, y) => { const m = (x + (Math.floor(y / 8) % 2 ? 8 : 0)) % 16 === 0 || y % 8 === 0; return m ? [120, 112, 98, 255] : [168, 72, 40, 255]; });
add('objects/gameplay_keep/gBrickWallTex', o2r.resource({ type: 2, width: 32, height: 32, data: o2r.encodePixels(brick, 2) }));
add('objects/gameplay_field_keep/gGrassTex', o2r.resource({ type: 2, width: 16, height: 16, data: o2r.encodePixels(img(16, 16, (x, y) => [40, 120 + ((x * y) % 60), 30, 255]), 2) }));
add('textures/skybox/gCloudsTex', o2r.resource({ type: 6, width: 16, height: 8, data: Buffer.from([...Array(128).keys()].map((i) => (i * 2) & 255)) }));
add('version', Buffer.from('1.0'));
zip.close();
