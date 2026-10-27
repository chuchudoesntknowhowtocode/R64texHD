'use strict';
// Worker thread: does the per-texture work so the window stays responsive and all CPU cores are used.
const { parentPort } = require('worker_threads');
const fs = require('fs');
const path = require('path');
const { loadImage, saveImage } = require('./image');
const { upscale, fillTransparent, pad, edgeIndex } = require('./upscale');
const { loadDump } = require('./tmem');
const png = require('./png');
const rtz = require('./rtz');
const dds = require('./dds');

function padImage(img, p, edges) {
  const { width: w, height: h, data } = img, W = w + 2 * p, H = h + 2 * p, out = new Uint8Array(W * H * 4);
  for (let y = 0; y < H; y++) {
    const sy = edgeIndex(y - p, h, edges[1]);
    for (let x = 0; x < W; x++) {
      const s = (sy * w + edgeIndex(x - p, w, edges[0])) * 4, d = (y * W + x) * 4;
      out[d] = data[s]; out[d + 1] = data[s + 1]; out[d + 2] = data[s + 2]; out[d + 3] = data[s + 3];
    }
  }
  return { width: W, height: H, data: out };
}

function crop(img, x0, y0, w, h) {
  const out = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) out.set(img.data.subarray(((y0 + y) * img.width + x0) * 4, ((y0 + y) * img.width + x0 + w) * 4), y * w * 4);
  return { width: w, height: h, data: out };
}

// Preview: the real upscale, then (for DDS output) an encode + decode so compression shows too.
function previewResult(img, out, job, t0) {
  const fmt = job.save.format === 'same' ? (/\.dds$/i.test(job.src) ? 'dds' : 'png') : job.save.format;
  let shown = out, encoded = 'PNG';
  if (fmt === 'dds') {
    const bytes = dds.encodeDDS(out, job.save.ddsFormat, { mipmaps: false, texconv: job.save.texconv });
    const info = dds.parseHeader(bytes);
    encoded = 'DDS ' + ({ 71: 'BC1', 77: 'BC3', 98: 'BC7', 28: 'uncompressed' }[info && info.dxgi] || '');
    shown = dds.decodeDDS(bytes);
  }
  return { orig: img, up: shown, encoded: encoded.trim(), ms: Date.now() - t0 };
}

const edgesOf = (job) => (Array.isArray(job.edges) ? job.edges : [job.edges || 'clamp', job.edges || 'clamp']);

const handlers = {
  upscale(job) {
    const img = loadImage(job.src);
    const out = upscale(img, { ...job.opts, edges: edgesOf(job) });
    const file = saveImage(out, job.outNoExt, job.save);
    return { out: file, from: [img.width, img.height], to: [out.width, out.height] };
  },
  aiPrep(job) {
    // Pad (by tiling mode) and fill transparent colours, then hand the PNG to Real-ESRGAN.
    const img = loadImage(job.src);
    const ready = padImage(fillTransparent(img, 16), job.pad, edgesOf(job));
    fs.writeFileSync(job.tmpPng, png.encodePNG(ready, 1));
    return { size: [img.width, img.height] };
  },
  aiFinish(job) {
    const img = loadImage(job.src);
    let ai = loadImage(job.aiPng);
    ai = crop(ai, job.pad * 4, job.pad * 4, img.width * 4, img.height * 4);
    const out = upscale(img, { ...job.opts, edges: edgesOf(job) }, { img: ai, scale: 4 });
    const file = saveImage(out, job.outNoExt, job.save);
    return { out: file, from: [img.width, img.height], to: [out.width, out.height] };
  },
  dump(job) {
    const d = loadDump(job.src);
    const img = d.decode();
    const file = saveImage(img, job.outNoExt, job.save);
    return { out: file, from: [img.width, img.height], to: [img.width, img.height], edges: d.edges };
  },
  preview(job) {
    const t0 = Date.now();
    const img = loadImage(job.src);
    const out = upscale(img, { ...job.opts, edges: edgesOf(job) });
    return previewResult(img, out, job, t0);
  },
  previewAi(job) {
    const t0 = Date.now();
    const img = loadImage(job.src);
    let ai = loadImage(job.aiPng);
    ai = crop(ai, job.pad * 4, job.pad * 4, img.width * 4, img.height * 4);
    const out = upscale(img, { ...job.opts, edges: edgesOf(job) }, { img: ai, scale: 4 });
    return previewResult(img, out, job, t0);
  },
  o2rExtract(job, progress) {
    return require('./o2r').extract(job.archive, job.output, { progress, skipPalette: job.skipPalette });
  },
  o2rBuild(job, progress) {
    return require('./o2r').build(job.input, job.base, job.output, { alt: job.alt, compression: job.compression, progress });
  },
  legacyImport(job, progress) { return require('./legacy').importToRt64(job.input, job.dumpDb, job.output, { progress }); },
  legacyHts(job, progress) { return require('./legacy').makeHts(job.input, job.output, { progress }); },
  riceToO2r(job, progress) { return require('./legacy').riceToO2r(job.input, job.base, job.output, { alt: job.alt, compression: job.compression, progress }); },
  romScan(job, progress) { return require('./rom').scan(job.folder, { progress }); },
  romInfo(job) { return require('./rom').info(job.file); },
  check(job, progress) {
    return require('./check').checkPack(job.input, { progress });
  },
  toDds(job) {
    // One PNG -> DDS with mipmaps (fences far away kept), written atomically.
    const img = loadImage(job.src);
    const bytes = dds.encodeDDS(img, job.ddsFormat, { mipmaps: true, texconv: job.texconv, keepCoverage: true });
    fs.writeFileSync(job.dest + '.part', bytes);
    fs.renameSync(job.dest + '.part', job.dest);
    return { out: job.dest };
  },
  unpack(job, progress) {
    return rtz.unpack(job.file, job.output, { keepCache: job.keepCache, progress });
  },
  pack(job, progress) {
    return rtz.packFolder(job.folder, job.outFile, { ...job.options, progress });
  },
};

parentPort.on('message', (msg) => {
  const progress = (done, total, name) => parentPort.postMessage({ id: msg.id, progress: [done, total, name] });
  try {
    const result = handlers[msg.kind](msg.job, progress);
    parentPort.postMessage({ id: msg.id, ok: true, result });
  } catch (e) {
    parentPort.postMessage({ id: msg.id, ok: false, error: e && e.message ? e.message : String(e) });
  }
});
