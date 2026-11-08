'use strict';
// ONNX engine (roadmap 11): onnx-run.js with a tiny 4× nearest-neighbour model (tests/fixtures/nearest4x.onnx).
// Needs onnxruntime-node: set ORT_NODE_DIR to its folder, or have it resolvable; skipped otherwise.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const png = require('../app/core/png');
const tasks = require('../app/core/tasks');

let ORT = process.env.ORT_NODE_DIR || '';
if (!ORT) try { ORT = path.dirname(require.resolve('onnxruntime-node/package.json')); } catch { ORT = ''; }
const MODEL = path.join(__dirname, 'fixtures', 'nearest4x.onnx');
const RUNNER = path.join(__dirname, '..', 'app', 'core', 'onnx-run.js');

function img(w, h) {
  const d = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) d.set([(x * 7) & 255, (y * 13) & 255, (x * y) & 255, 255], (y * w + x) * 4);
  return { width: w, height: h, data: d };
}
function nearestOk(src, up) {
  if (up.width !== src.width * 4 || up.height !== src.height * 4) return false;
  for (let y = 0; y < up.height; y++) for (let x = 0; x < up.width; x++) for (let c = 0; c < 3; c++)
    if (up.data[(y * up.width + x) * 4 + c] !== src.data[((y >> 2) * src.width + (x >> 2)) * 4 + c]) return false;
  return true;
}

test('onnx engine: folder in, 4× folder out (whole image and tiles)', { skip: !ORT && 'onnxruntime-node not installed' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'onnx-')), inDir = path.join(dir, 'in'), outDir = path.join(dir, 'out');
  fs.mkdirSync(inDir);
  const a = img(20, 12), b = img(300, 40);
  fs.writeFileSync(path.join(inDir, '0.png'), png.encodePNG(a));
  fs.writeFileSync(path.join(inDir, '1.png'), png.encodePNG(b));
  const log = execFileSync(process.execPath, [RUNNER, '-i', inDir, '-o', outDir, '-m', MODEL, '--ort', ORT, '-g', 'cpu', '-t', '128'], { encoding: 'utf8' });
  assert.match(log, /on CPU, 2 image/);
  assert.ok(nearestOk(a, png.decodePNG(fs.readFileSync(path.join(outDir, '0.png')))));
  assert.ok(nearestOk(b, png.decodePNG(fs.readFileSync(path.join(outDir, '1.png')))), 'tiled result matches');
  fs.rmSync(dir, { recursive: true, force: true });
});

test('onnx engine: the Upscale run uses it for an ONNX model, without Real-ESRGAN', { skip: !ORT && 'onnxruntime-node not installed' }, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'onnxrun-')), eng = path.join(dir, 'engine'), inDir = path.join(dir, 'in'), out = path.join(dir, 'out');
  fs.mkdirSync(path.join(eng, 'models'), { recursive: true }); fs.mkdirSync(path.join(eng, 'node_modules'), { recursive: true }); fs.mkdirSync(inDir);
  fs.symlinkSync(ORT, path.join(eng, 'node_modules', 'onnxruntime-node'), 'junction');
  fs.copyFileSync(MODEL, path.join(eng, 'models', 'texturedat2-x4.onnx'));
  fs.writeFileSync(path.join(inDir, 'aaaaaaaaaaaaaaaa.png'), png.encodePNG(img(16, 16)));
  const tools = { onnx: eng, realesrganModel: 'texturedat2-x4', aiGpu: 'cpu' };
  assert.equal(tasks.aiCan(tools, 'texturedat2-x4', false), true);
  assert.equal(tasks.aiCan({}, 'texturedat2-x4', true), false);
  const log = [];
  const r = await tasks.upscaleTask({ inputs: [inDir], output: out, size: 4, method: 'ai', sharpness: 'normal', edges: 'clamp', format: 'png' },
    { workers: 1, cancelled: () => false, onCancel: () => {}, log: (t) => log.push(t), progress: () => {} }, tools);
  assert.equal(r.written, 1, log.join('\n'));
  assert.ok(!log.some((l) => /Standard is used instead|failed/i.test(l)), log.join('\n'));
  assert.equal(png.decodePNG(fs.readFileSync(path.join(out, 'aaaaaaaaaaaaaaaa.png'))).width, 64);
  fs.rmSync(dir, { recursive: true, force: true });
});
