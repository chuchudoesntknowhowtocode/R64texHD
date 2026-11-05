'use strict';
// Texture upscaling.
//
// Standard: enlarge in 2x steps; after every step re-sharpen (a little more each step) so detail
// keeps up with the size. Each step is clamped to the range of the source pixels around it (no
// ringing/halos), edges follow the tiling mode, transparent pixels borrow neighbouring colours
// (no dark fringes) and on/off alpha stays crisp. Alpha is grown on its own, never by the AI.
// Smooth: one high-quality Lanczos resize, no sharpening.  Pixel art: nearest neighbour.
// AI: Real-ESRGAN does the first 4x (see tasks.js), then the Standard steps finish the job.

const ALPHA_TOL = 8, ALPHA_MID_SHARE = 0.005;   // see alphaKind
const SHARPNESS = { off: 0, soft: 0.35, normal: 0.6, strong: 0.9, extra: 1.25 };

// ---------------------------------------------------------------- helpers on one float plane
function edgeIndex(i, n, mode) {
  if (mode === 'wrap') return ((i % n) + n) % n;
  if (mode === 'mirror') { const k = ((i % (2 * n)) + 2 * n) % (2 * n); return k < n ? k : 2 * n - 1 - k; }
  return i < 0 ? 0 : (i >= n ? n - 1 : i);
}

function pad(plane, w, h, px, py, modeX, modeY) {
  const W = w + 2 * px, H = h + 2 * py, out = new Float32Array(W * H);
  const xs = new Int32Array(W);
  for (let x = 0; x < W; x++) xs[x] = edgeIndex(x - px, w, modeX);
  for (let y = 0; y < H; y++) {
    const sy = edgeIndex(y - py, h, modeY) * w, o = y * W;
    for (let x = 0; x < W; x++) out[o + x] = plane[sy + xs[x]];
  }
  return out;
}

const sinc = (x) => (x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x));
const lanczos3 = (x) => (x > -3 && x < 3 ? sinc(x) * sinc(x / 3) : 0);

function weights(inSize, outSize) {
  const scale = inSize / outSize, filterScale = Math.max(scale, 1), support = 3 * filterScale;
  const list = [];
  for (let o = 0; o < outSize; o++) {
    const center = (o + 0.5) * scale;
    const lo = Math.max(0, Math.floor(center - support)), hi = Math.min(inSize, Math.ceil(center + support));
    const w = [];
    let sum = 0;
    for (let i = lo; i < hi; i++) { const v = lanczos3((i + 0.5 - center) / filterScale); w.push(v); sum += v; }
    list.push({ lo, w: Float32Array.from(w.map((v) => v / (sum || 1))) });
  }
  return list;
}

function resize(plane, w, h, nw, nh) {
  const wx = weights(w, nw), wy = weights(h, nh);
  const tmp = new Float32Array(nw * h);
  for (let y = 0; y < h; y++) {
    const row = y * w;
    for (let x = 0; x < nw; x++) {
      const { lo, w: k } = wx[x];
      let s = 0;
      for (let i = 0; i < k.length; i++) s += plane[row + lo + i] * k[i];
      tmp[y * nw + x] = s;
    }
  }
  const out = new Float32Array(nw * nh);
  for (let y = 0; y < nh; y++) {
    const { lo, w: k } = wy[y];
    for (let x = 0; x < nw; x++) {
      let s = 0;
      for (let i = 0; i < k.length; i++) s += tmp[(lo + i) * nw + x] * k[i];
      out[y * nw + x] = s;
    }
  }
  return out;
}

// 3x3 neighbourhood min and max (separable).
function localRange(plane, w, h) {
  const mnH = new Float32Array(w * h), mxH = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = y * w;
    const a = plane[o + Math.max(x - 1, 0)], b = plane[o + x], c = plane[o + Math.min(x + 1, w - 1)];
    mnH[o + x] = Math.min(a, b, c); mxH[o + x] = Math.max(a, b, c);
  }
  const mn = new Float32Array(w * h), mx = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const u = Math.max(y - 1, 0) * w, m = y * w, d = Math.min(y + 1, h - 1) * w;
    for (let x = 0; x < w; x++) {
      mn[m + x] = Math.min(mnH[u + x], mnH[m + x], mnH[d + x]);
      mx[m + x] = Math.max(mxH[u + x], mxH[m + x], mxH[d + x]);
    }
  }
  return [mn, mx];
}

// Resize, then clamp every output pixel to the range of the source pixels it came from (anti-ringing).
function resizeClamped(plane, w, h, nw, nh) {
  const up = resize(plane, w, h, nw, nh);
  const [mn, mx] = localRange(plane, w, h);
  for (let y = 0; y < nh; y++) {
    const sy = Math.min(h - 1, Math.floor((y + 0.5) * h / nh)) * w, o = y * nw;
    for (let x = 0; x < nw; x++) {
      const s = sy + Math.min(w - 1, Math.floor((x + 0.5) * w / nw));
      const v = up[o + x];
      up[o + x] = v < mn[s] ? mn[s] : (v > mx[s] ? mx[s] : v);
    }
  }
  return up;
}

function gaussian(plane, w, h, sigma) {
  const r = Math.max(1, Math.round(sigma * 3)), k = [];
  let sum = 0;
  for (let i = -r; i <= r; i++) { const v = Math.exp(-(i * i) / (2 * sigma * sigma)); k.push(v); sum += v; }
  for (let i = 0; i < k.length; i++) k[i] /= sum;
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0;
    for (let i = -r; i <= r; i++) s += plane[y * w + Math.min(w - 1, Math.max(0, x + i))] * k[i + r];
    tmp[y * w + x] = s;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0;
    for (let i = -r; i <= r; i++) s += tmp[Math.min(h - 1, Math.max(0, y + i)) * w + x] * k[i + r];
    out[y * w + x] = s;
  }
  return out;
}

function sharpen(plane, w, h, amount, sigma) {
  if (amount <= 0) return plane;
  const blur = gaussian(plane, w, h, sigma);
  const [mn, mx] = localRange(plane, w, h);
  const out = new Float32Array(w * h);
  for (let i = 0; i < out.length; i++) {
    const v = plane[i] + amount * (plane[i] - blur[i]);
    out[i] = v < mn[i] ? mn[i] : (v > mx[i] ? mx[i] : v); // never past the neighbourhood: no halos
  }
  return out;
}

// Transparent pixels take the average colour of nearby visible pixels, growing outward ring by ring
// until every transparent pixel has one (or `iterations` rings). Big upscales then never pull dark
// or stray colours in from behind a cut-out edge. Each round only visits the newest ring: O(pixels).
function fillTransparent(img, iterations = Infinity) {
  const { width: w, height: h, data } = img, n = w * h;
  const out = Uint8Array.from(data), filled = new Uint8Array(n), queued = new Uint8Array(n);
  let any = false, all = true;   // near-invisible pixels (alpha <= ALPHA_TOL) count as hidden too
  for (let i = 0; i < n; i++) { filled[i] = data[i * 4 + 3] > ALPHA_TOL ? 1 : 0; if (filled[i]) any = true; else all = false; }
  if (all || !any) return { width: w, height: h, data: out };
  const around = (i, list) => {
    const x = i % w, y = (i - x) / w;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const xx = x + dx, yy = y + dy;
      if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
      const j = yy * w + xx;
      if (!filled[j] && !queued[j]) { queued[j] = 1; list.push(j); }
    }
  };
  let ring = [];
  for (let i = 0; i < n; i++) if (filled[i]) around(i, ring);
  for (let it = 0; it < iterations && ring.length; it++) {
    for (const i of ring) {           // colours come only from pixels filled before this ring
      const x = i % w, y = (i - x) / w;
      let r = 0, g = 0, b = 0, k = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const j = yy * w + xx;
        if (!filled[j]) continue;
        r += out[j * 4]; g += out[j * 4 + 1]; b += out[j * 4 + 2]; k++;
      }
      out[i * 4] = Math.round(r / k); out[i * 4 + 1] = Math.round(g / k); out[i * 4 + 2] = Math.round(b / k);
    }
    for (const i of ring) filled[i] = 1;
    const next = [];
    for (const i of ring) around(i, next);
    ring = next;
  }
  let r = 0, g = 0, b = 0, k = 0;
  for (let i = 0; i < n; i++) if (filled[i]) { r += out[i * 4]; g += out[i * 4 + 1]; b += out[i * 4 + 2]; k++; }
  for (let i = 0; i < n; i++) if (!filled[i]) { out[i * 4] = r / k; out[i * 4 + 1] = g / k; out[i * 4 + 2] = b / k; }
  return { width: w, height: h, data: out };
}

// ---------------------------------------------------------------- public
// Target size for an image under the options (scale 2/3/4/6/8 or fit: longest side), capped by maxSize.
function targetSize(w, h, opts) {
  let s = opts.size === 'fit' ? (Number(opts.fit) || 2048) / Math.max(w, h) : Number(opts.size) || 4;
  const cap = Number(opts.maxSize) || 4096;
  if (Math.max(w, h) * s > cap) s = cap / Math.max(w, h);
  if (opts.method === 'pixel') s = Math.max(1, Math.floor(s));
  return { scale: s, width: Math.max(1, Math.round(w * s)), height: Math.max(1, Math.round(h * s)) };
}

function isOpaque(img) { for (let i = 3; i < img.data.length; i += 4) if (img.data[i] !== 255) return false; return true; }

// What kind of transparency a texture has:
//   opaque  every pixel is fully visible
//   binary  cut-out (fences, leaves, text): alpha is on/off. Values within ALPHA_TOL of 0 or 255
//           count as on/off, and up to ALPHA_MID_SHARE of the pixels may sit in between (soft
//           edges left by DXT or old tools)
//   soft    smoke, glass, shadows: real in-between alpha, kept as is
function alphaKind(img) {
  const d = img.data, n = d.length / 4;
  let seeThrough = false, mid = 0;
  for (let i = 3; i < d.length; i += 4) {
    const a = d[i];
    if (a === 255) continue;
    seeThrough = true;
    if (a > ALPHA_TOL && a < 255 - ALPHA_TOL) mid++;
  }
  if (!seeThrough) return 'opaque';
  return mid <= n * ALPHA_MID_SHARE ? 'binary' : 'soft';
}

function nearest(img, nw, nh) {
  const { width: w, height: h, data } = img, out = new Uint8Array(nw * nh * 4);
  for (let y = 0; y < nh; y++) {
    const sy = Math.min(h - 1, Math.floor(y * h / nh));
    for (let x = 0; x < nw; x++) {
      const s = (sy * w + Math.min(w - 1, Math.floor(x * w / nw))) * 4, d = (y * nw + x) * 4;
      out[d] = data[s]; out[d + 1] = data[s + 1]; out[d + 2] = data[s + 2]; out[d + 3] = data[s + 3];
    }
  }
  return { width: nw, height: nh, data: out };
}

// One channel of `from` (already at scale `cur`) taken to the target size: padded by the tiling
// mode, grown in 2x steps (sharpened when `sharp`), then cropped.
function scalePlane(from, c, cur, t, edges, opts, base, sharp) {
  const sw = from.width, sh = from.height, P = 4 * cur;
  let plane = new Float32Array(sw * sh);
  for (let i = 0; i < sw * sh; i++) plane[i] = from.data[i * 4 + c] / 255;
  let pw = sw + 2 * P, ph = sh + 2 * P;
  plane = pad(plane, sw, sh, P, P, edges[0], edges[1]);
  let scale = cur, step = 0;
  if (opts.method === 'smooth') {
    const nw = Math.round(pw * t.scale / scale), nh = Math.round(ph * t.scale / scale);
    plane = resizeClamped(plane, pw, ph, nw, nh); pw = nw; ph = nh; scale = t.scale;
  } else {
    while (scale * 2 <= t.scale + 1e-6) {
      plane = resizeClamped(plane, pw, ph, pw * 2, ph * 2); pw *= 2; ph *= 2; scale *= 2; step++;
      if (sharp) plane = sharpen(plane, pw, ph, base * (1 + 0.35 * (step - 1)), 1 + 0.15 * step);
    }
    if (Math.abs(scale - t.scale) > 1e-6) { // 3x, 6x, fit sizes or AI overshoot: finish with one exact resize
      const nw = Math.round(pw * t.scale / scale), nh = Math.round(ph * t.scale / scale);
      plane = resizeClamped(plane, pw, ph, nw, nh); pw = nw; ph = nh; scale = t.scale;
      if (sharp && t.scale > cur && step === 0) plane = sharpen(plane, pw, ph, base, 1.15);
    }
  }
  const ox = Math.round(P * t.scale / cur), oy = Math.round(P * t.scale / cur);
  const crop = new Float32Array(t.width * t.height);
  for (let y = 0; y < t.height; y++) {
    const sy = Math.min(ph - 1, y + oy);
    for (let x = 0; x < t.width; x++) crop[y * t.width + x] = plane[sy * pw + Math.min(pw - 1, x + ox)];
  }
  return crop;
}

// img: RGBA source. opts: { size, fit, maxSize, method, sharpness, edges: 'clamp'|'wrap'|'mirror' or [x,y],
//   hardAlpha, alphaThreshold (0..1, where a cut-out edge is cut; default 0.5) }
// start: optional { img, scale } produced by AI (4x) to continue from. AI only does the colour:
// alpha is always grown from the source on its own, smooth (never sharpened), then cut for cut-outs.
function upscale(img, opts, start = null) {
  const { width: w, height: h } = img;
  const t = targetSize(w, h, opts);
  if (t.width === w && t.height === h) return img;
  if (opts.method === 'pixel') return nearest(img, t.width, t.height);
  const edges = Array.isArray(opts.edges) ? opts.edges : [opts.edges || 'clamp', opts.edges || 'clamp'];
  const kind = alphaKind(img), opaque = kind === 'opaque';
  const base = opts.method === 'smooth' ? 0 : (SHARPNESS[opts.sharpness] ?? SHARPNESS.normal);
  const src = start ? start.img : img, current = start ? start.scale : 1;
  const filled = opaque || start ? src : fillTransparent(src);   // AI input was filled before the AI ran
  const outPlanes = [];
  for (let c = 0; c < 3; c++) outPlanes.push(scalePlane(filled, c, current, t, edges, opts, base, true));
  if (!opaque) outPlanes.push(scalePlane(img, 3, 1, t, edges, opts, base, false));
  const cut = opts.hardAlpha !== false && kind === 'binary';
  const thr = Math.max(0.02, Math.min(0.98, Number(opts.alphaThreshold ?? 0.5)));
  const out = new Uint8Array(t.width * t.height * 4);
  for (let i = 0; i < t.width * t.height; i++) {
    for (let c = 0; c < 3; c++) out[i * 4 + c] = Math.max(0, Math.min(255, Math.round(outPlanes[c][i] * 255)));
    if (opaque) out[i * 4 + 3] = 255;
    else {
      let a = outPlanes[3][i];
      if (cut) a = a >= thr ? 1 : 0;
      out[i * 4 + 3] = Math.max(0, Math.min(255, Math.round(a * 255)));
    }
  }
  return { width: t.width, height: t.height, data: out };
}

// Resize an RGBA image to an exact size (Lanczos, clamped: no halos). Transparent pixels borrow
// nearby colours first so edges don't darken.
function resizeRGBA(img, nw, nh) {
  if (img.width === nw && img.height === nh) return img;
  const filled = fillTransparent(img), n = img.width * img.height, out = new Uint8Array(nw * nh * 4);
  for (let c = 0; c < 4; c++) {
    const src = c === 3 ? img : filled, plane = new Float32Array(n);
    for (let i = 0; i < n; i++) plane[i] = src.data[i * 4 + c] / 255;
    const r = resizeClamped(plane, img.width, img.height, nw, nh);
    for (let i = 0; i < nw * nh; i++) out[i * 4 + c] = Math.max(0, Math.min(255, Math.round(r[i] * 255)));
  }
  return { width: nw, height: nh, data: out };
}

module.exports = { upscale, targetSize, fillTransparent, alphaKind, ALPHA_TOL, pad, edgeIndex, resizeRGBA, SHARPNESS };
