'use strict';
// Smart upscaling: picks a method per texture.
//   mmpx      true pixel art (sprites, fonts, HUD: hard cut-outs and few colours, or flat tiles): MMPX, which
//             straightens diagonals but only ever uses the texture's own colours
//   pixel     tiny opaque textures (16 px and under): plain blocky pixels
//   ai        big, detailed textures (stone, wood, skies): Real-ESRGAN, when it's installed and the GPU has Vulkan;
//             with the texture models installed it uses GameAI (made for game textures)
//   aisprite  mid-size cut-out sprites with many colours: the Pixel texture model (only with the texture models)
//   hd        everything else: Standard 4x with normal sharpening
// The rules look at the size, the number of distinct colours and the kind of transparency. Dithered textures
// (checker / ordered dither dots) are softened first on the HD and AI routes, so the dots aren't magnified.
// HDCube is never picked: its card says it isn't for icons or text, and GameAI covers the same textures.

const { alphaKind, ditherScore } = require('./upscale');

const COLOR_CAP = 256;
const DITHERED = 0.12;            // share of dithered pixels above which a texture counts as dithered

function stats(img) {
  const { width: w, height: h, data: d } = img;
  const seen = new Set();
  let colors = 0;
  for (let i = 0; i < d.length; i += 4) {
    const a = d[i + 3];
    if (colors < COLOR_CAP && a !== 0) {
      const key = (d[i] << 16) | (d[i + 1] << 8) | d[i + 2];
      if (!seen.has(key)) { seen.add(key); colors++; }
    }
  }
  return { w, h, colors, alpha: alphaKind(img), dither: Math.round(ditherScore(img) * 1000) / 1000 };
}

// models: the texture models are installed (they add the aisprite route and pick GameAI for ai).
// onnx: the ONNX engine is installed: dithered AI textures go to RGT-S dither (trained with dithering), not softened first.
function route(s, { models = false, onnx = false } = {}) {
  const side = Math.max(s.w, s.h), small = Math.min(s.w, s.h);
  if (s.alpha === 'binary' && s.colors <= 16 && side <= 64) return 'mmpx';
  if (side <= 16) return 'pixel';
  if (s.colors <= 8 && side <= 64) return 'mmpx';
  if (small >= 32 && s.colors >= 96) return onnx && dithered(s) ? 'aidither' : 'ai';
  if (models && s.alpha === 'binary' && side <= 64 && small >= 16) return 'aisprite';
  return 'hd';
}
const isAi = (r) => r === 'ai' || r === 'aisprite' || r === 'aidither';
const dithered = (s) => (s.dither || 0) >= DITHERED;

// What each route does. size / fit / maxSize come from the run's own settings.
const ROUTE_OPTS = {
  pixel: { method: 'pixel', hardAlpha: true },
  mmpx: { method: 'mmpx', hardAlpha: true },
  hd: { method: 'standard', sharpness: 'normal' },
  ai: { method: 'ai', sharpness: 'normal' },
  aisprite: { method: 'ai', sharpness: 'normal' },
  aidither: { method: 'ai', sharpness: 'normal' },
};
const ROUTE_NAMES = { pixel: 'Pixel-perfect', mmpx: 'Pixel art (MMPX)', hd: 'HD 4×', ai: 'AI 4×', aisprite: 'AI sprite 4×', aidither: 'AI dither 4×' };
// Real-ESRGAN model for an AI route (null: the model chosen in Settings).
function routeModel(r, { models = false } = {}) {
  if (r === 'aisprite') return 'pixelperfect4-x4';
  if (r === 'aidither') return 'rgts-dither-x4';
  if (r === 'ai' && models) return 'gameai2-x4';
  return null;
}

module.exports = { stats, route, routeModel, isAi, dithered, ROUTE_OPTS, ROUTE_NAMES, COLOR_CAP, DITHERED };
