'use strict';
// Reads an ncnn model's upscale factor from its .param text (Real-ESRGAN models: RRDBNet ends in two
// Interp ×2 layers in a row, SRVGGNetCompact in one PixelShuffle ×4 beside an Interp of the input). Returns null when the file doesn't say
// (no upsample layer, or an Interp sized by output pixels), so the caller can fall back to the file name.
// Limit: a model that shrinks its input first (x2plus: pixel-unshuffle written as Reshape/Permute) reads too high.
function modelScale(paramText) {
  // Follows the scale along the graph (blob -> scale), so parallel branches don't multiply: realesr-animevideov3
  // upsamples the input beside its PixelShuffle and adds the two, and its x2/x3 files end in an Interp ×0.5 / ×0.75.
  const scaleOf = new Map();
  let found = false, last = null;
  for (const line of String(paramText).split(/\r?\n/).slice(2)) {
    const tok = line.trim().split(/\s+/);
    if (tok.length < 4) continue;
    const n = Number(tok[2]) || 0, m = Number(tok[3]) || 0;           // type name inputs outputs [blobs...] [k=v...]
    const ins = tok.slice(4, 4 + n), outs = tok.slice(4 + n, 4 + n + m);
    const kv = {};
    for (const t of tok.slice(4 + n + m)) { const i = t.indexOf('='); if (i > 0) kv[t.slice(0, i)] = t.slice(i + 1); }
    let f = 1;
    if (tok[0] === 'PixelShuffle') {
      f = Number(kv['0']);
      if (!(f >= 1) || Number(kv['1'] || 0) !== 0) return null;      // 1=mode other than 0: not a plain upscale
      found = true;
    } else if (tok[0] === 'Interp') {
      const sh = Number(kv['1'] || 1), sw = Number(kv['2'] || 1);
      if (kv['3'] || kv['4'] || sh !== sw) return null;               // fixed output size or uneven: can't tell
      if (sw !== 1) { f = sw; found = true; }
    }
    const inS = ins.length ? Math.max(...ins.map((b) => scaleOf.get(b) || 1)) : 1;
    for (const o of outs) scaleOf.set(o, inS * f);
    if (outs.length) last = outs[0];
  }
  return found && last ? Math.round(scaleOf.get(last) * 100) / 100 : null;
}

// The scale a file name claims ("2x-Foo", "foo_x2", "RealESRGAN_x2plus"), or null.
function nameScale(name) {
  const b = String(name).replace(/\.[^.]*$/, '');
  const m = b.match(/(?:^|[^a-z0-9])(\d{1,2})x(?=[^a-z0-9]|$)/i) || b.match(/(?:^|[^a-z0-9])x(\d{1,2})(?=[^0-9]|$)/i);
  return m ? Number(m[1]) : null;
}

module.exports = { modelScale, nameScale };
