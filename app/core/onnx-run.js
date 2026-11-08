'use strict';
// The ONNX AI engine (roadmap 11): a small command-line runner with Real-ESRGAN's folder interface, so the AI step
// can use it in place of realesrgan-ncnn-vulkan. Runs as its own Node process (Electron with ELECTRON_RUN_AS_NODE),
// so the app never blocks. onnxruntime-node comes from the optional "ONNX engine" download, not from the app.
//
//   onnx-run.js -i <in dir> -o <out dir> -m <model.onnx> --ort <onnxruntime-node dir> [-g auto|cpu|0|1] [-t tile]
//
// Every PNG in <in dir> is upscaled into <out dir> under the same name. Graphics card: DirectML on Windows
// (falls back to the CPU if DirectML can't start), the CPU elsewhere. Big images run in overlapping tiles.
const fs = require('fs');
const path = require('path');
const { decodePNG, encodePNG } = require('./png');

function parseArgs(argv) {
  const a = { g: 'auto', t: 0 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = argv[i + 1];
    if (k === '-i') a.i = v; else if (k === '-o') a.o = v; else if (k === '-m') a.m = v; else if (k === '--ort') a.ort = v;
    else if (k === '-g') a.g = v; else if (k === '-t') a.t = Number(v) || 0; else continue;
    i++;
  }
  if (!a.i || !a.o || !a.m || !a.ort) throw new Error('usage: onnx-run.js -i <in> -o <out> -m <model.onnx> --ort <onnxruntime-node dir>');
  return a;
}

async function openSession(ort, model, gpu) {
  const base = { graphOptimizationLevel: 'all' };
  if (process.platform === 'win32' && gpu !== 'cpu') {
    const deviceId = /^\d+$/.test(String(gpu)) ? Number(gpu) : 0;
    try { return { session: await ort.InferenceSession.create(model, { ...base, executionProviders: [{ name: 'dml', deviceId }] }), ep: `DirectML (GPU ${deviceId + 1})` }; }
    catch (e) { process.stderr.write(`DirectML could not start (${String(e.message || e).split('\n')[0]}), using the CPU.\n`); }
  }
  return { session: await ort.InferenceSession.create(model, { ...base, executionProviders: ['cpu'] }), ep: 'CPU' };
}

// One RGB float tensor [1,3,h,w] from a region of an RGBA image.
function toTensor(img, x0, y0, w, h) {
  const n = w * h, t = new Float32Array(3 * n);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const s = ((y0 + y) * img.width + x0 + x) * 4, d = y * w + x;
    t[d] = img.data[s] / 255; t[n + d] = img.data[s + 1] / 255; t[2 * n + d] = img.data[s + 2] / 255;
  }
  return t;
}

async function runTile(ort, session, img, x0, y0, w, h) {
  const r = await session.run({ [session.inputNames[0]]: new ort.Tensor('float32', toTensor(img, x0, y0, w, h), [1, 3, h, w]) });
  const o = r[session.outputNames[0]];
  return { data: o.data, w: o.dims[3], h: o.dims[2] };
}

// Whole image when it fits in one tile, otherwise tiles with an overlap that is cut away again.
async function upscaleImage(ort, session, img, tile) {
  const T = tile || 256, OV = 16;
  if (img.width <= T && img.height <= T) {
    const r = await runTile(ort, session, img, 0, 0, img.width, img.height);
    return pack(r.data, r.w, r.h);
  }
  let scale = 0, out = null;
  for (let ty = 0; ty < img.height; ty += T) for (let tx = 0; tx < img.width; tx += T) {
    const x0 = Math.max(0, tx - OV), y0 = Math.max(0, ty - OV);
    const x1 = Math.min(img.width, tx + T + OV), y1 = Math.min(img.height, ty + T + OV);
    const r = await runTile(ort, session, img, x0, y0, x1 - x0, y1 - y0);
    if (!scale) { scale = r.w / (x1 - x0); out = new Uint8Array(img.width * scale * img.height * scale * 4); }
    const W = img.width * scale, n = r.w * r.h;
    const cw = Math.min(T, img.width - tx) * scale, ch = Math.min(T, img.height - ty) * scale;
    const ox = (tx - x0) * scale, oy = (ty - y0) * scale;
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      const s = (oy + y) * r.w + ox + x, d = ((ty * scale + y) * W + tx * scale + x) * 4;
      for (let c = 0; c < 3; c++) out[d + c] = clamp8(r.data[c * n + s]);
      out[d + 3] = 255;
    }
  }
  return { width: img.width * scale, height: img.height * scale, data: out };
}
const clamp8 = (v) => (v <= 0 ? 0 : v >= 1 ? 255 : Math.round(v * 255));
function pack(data, w, h) {
  const n = w * h, out = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) { out[i * 4] = clamp8(data[i]); out[i * 4 + 1] = clamp8(data[n + i]); out[i * 4 + 2] = clamp8(data[2 * n + i]); out[i * 4 + 3] = 255; }
  return { width: w, height: h, data: out };
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  const ort = require(path.resolve(a.ort));
  const { session, ep } = await openSession(ort, a.m, a.g);
  const files = fs.readdirSync(a.i).filter((f) => /\.png$/i.test(f)).sort();
  process.stdout.write(`ONNX engine: ${path.basename(a.m)} on ${ep}, ${files.length} image(s)\n`);
  fs.mkdirSync(a.o, { recursive: true });
  let done = 0;
  for (const f of files) {
    const img = decodePNG(fs.readFileSync(path.join(a.i, f)));
    const up = await upscaleImage(ort, session, img, a.t);
    const tmp = path.join(a.o, f + '.part');
    fs.writeFileSync(tmp, encodePNG(up, 1));
    fs.renameSync(tmp, path.join(a.o, f));                       // whole files only, so progress counts are right
    process.stdout.write(`${++done}/${files.length}\n`);
  }
}

if (require.main === module) main().catch((e) => { process.stderr.write(String(e && e.stack || e) + '\n'); process.exit(1); });
module.exports = { upscaleImage, parseArgs };
