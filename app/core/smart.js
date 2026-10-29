'use strict';
// Smart upscaling: picks a method per texture.
//   pixel  tiny textures, fonts, HUD icons and flat cut-outs: blocky pixels and hard edges stay crisp
//   ai     big, detailed textures (stone, wood, skies): Real-ESRGAN, when it's installed and the GPU has Vulkan
//   hd     everything else: Standard 4x with normal sharpening
// The rules look at the size, the number of distinct colours and the kind of transparency.

const COLOR_CAP = 256;

function stats(img) {
  const { width: w, height: h, data: d } = img;
  const seen = new Set();
  let alpha = 'opaque', colors = 0;
  for (let i = 0; i < d.length; i += 4) {
    const a = d[i + 3];
    if (a !== 255) alpha = a === 0 ? (alpha === 'soft' ? 'soft' : 'binary') : 'soft';
    if (colors < COLOR_CAP && a !== 0) {
      const key = (d[i] << 16) | (d[i + 1] << 8) | d[i + 2];
      if (!seen.has(key)) { seen.add(key); colors++; }
    }
  }
  return { w, h, colors, alpha };
}

function route(s) {
  const side = Math.max(s.w, s.h), small = Math.min(s.w, s.h);
  if (side <= 16) return 'pixel';
  if (s.colors <= 8 && side <= 64) return 'pixel';
  if (s.alpha === 'binary' && s.colors <= 16 && side <= 64) return 'pixel';
  if (small >= 32 && s.colors >= 96) return 'ai';
  return 'hd';
}

// What each route does. size / fit / maxSize come from the run's own settings.
const ROUTE_OPTS = {
  pixel: { method: 'pixel', hardAlpha: true },
  hd: { method: 'standard', sharpness: 'normal' },
  ai: { method: 'ai', sharpness: 'normal' },
};
const ROUTE_NAMES = { pixel: 'Pixel-perfect', hd: 'HD 4×', ai: 'AI 4×' };

module.exports = { stats, route, ROUTE_OPTS, ROUTE_NAMES, COLOR_CAP };
