'use strict';
// MMPX pixel-art magnification (2x per pass), after Morgan McGuire and Mara Gagiu, "MMPX Style-Preserving Pixel
// Art Magnification", Journal of Graphics Techniques, 2021 (reference code MIT). It only ever copies existing
// pixels, so the palette and hard alpha stay exact; it straightens 1:1 and 2:1 diagonals and keeps thin lines.
// Pixels are compared as whole RGBA values. Reads outside the texture follow its edge mode (clamp / wrap / mirror).
const { edgeIndex } = require('./upscale');

function luma(c) {   // brightness, with transparent pixels counting as bright (the reference's tie-break)
  return (((c >>> 0) & 0xff) + ((c >>> 8) & 0xff) + ((c >>> 16) & 0xff) + 1) * (256 - ((c >>> 24) & 0xff));
}
const eq2 = (b, a0, a1) => b === a0 && b === a1;
const eq3 = (b, a0, a1, a2) => b === a0 && b === a1 && b === a2;
const eq4 = (b, a0, a1, a2, a3) => b === a0 && b === a1 && b === a2 && b === a3;
const any3 = (b, a0, a1, a2) => b === a0 || b === a1 || b === a2;
const none2 = (b, a0, a1) => b !== a0 && b !== a1;
const none4 = (b, a0, a1, a2, a3) => b !== a0 && b !== a1 && b !== a2 && b !== a3;

// One 2x pass. img: { width, height, data: RGBA bytes }. edges: [x mode, y mode].
function mmpx2(img, edges = ['clamp', 'clamp']) {
  const { width: w, height: h } = img;
  const src = new Uint32Array(img.data.buffer.slice(img.data.byteOffset, img.data.byteOffset + w * h * 4));
  const out = new Uint32Array(w * h * 4), W = w * 2;
  const xs = (x) => edgeIndex(x, w, edges[0]), ys = (y) => edgeIndex(y, h, edges[1]);
  const at = (x, y) => src[ys(y) * w + xs(x)];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const A = at(x - 1, y - 1), B = at(x, y - 1), C = at(x + 1, y - 1);
      const D = at(x - 1, y), E = src[y * w + x], F = at(x + 1, y);
      const G = at(x - 1, y + 1), H = at(x, y + 1), I = at(x + 1, y + 1);
      let J = E, K = E, L = E, M = E;
      if (A !== E || B !== E || C !== E || D !== E || F !== E || G !== E || H !== E || I !== E) {
        const P = at(x, y - 2), S = at(x, y + 2), Q = at(x - 2, y), R = at(x + 2, y);
        const Bl = luma(B), Dl = luma(D), El = luma(E), Fl = luma(F), Hl = luma(H);
        // 1:1 slopes
        if ((D === B && D !== H && D !== F) && (El >= Dl || E === A) && any3(E, A, C, G) && (El < Dl || A !== D || E !== P || E !== Q)) J = D;
        if ((B === F && B !== D && B !== H) && (El >= Bl || E === C) && any3(E, A, C, I) && (El < Bl || C !== B || E !== P || E !== R)) K = B;
        if ((H === D && H !== F && H !== B) && (El >= Hl || E === G) && any3(E, A, G, I) && (El < Hl || G !== H || E !== S || E !== Q)) L = H;
        if ((F === H && F !== B && F !== D) && (El >= Fl || E === I) && any3(E, C, G, I) && (El < Fl || I !== H || E !== R || E !== S)) M = F;
        // intersections
        if ((E !== F && eq4(E, C, I, D, Q) && eq2(F, B, H)) && F !== at(x + 3, y)) { K = F; M = F; }
        if ((E !== D && eq4(E, A, G, F, R) && eq2(D, B, H)) && D !== at(x - 3, y)) { J = D; L = D; }
        if ((E !== H && eq4(E, G, I, B, P) && eq2(H, D, F)) && H !== at(x, y + 3)) { L = H; M = H; }
        if ((E !== B && eq4(E, A, C, H, S) && eq2(B, D, F)) && B !== at(x, y - 3)) { J = B; K = B; }
        // triangle tips
        if (Bl < El && eq4(E, G, H, I, S) && none4(E, A, D, C, F)) { J = B; K = B; }
        if (Hl < El && eq4(E, A, B, C, P) && none4(E, D, G, I, F)) { L = H; M = H; }
        if (Fl < El && eq4(E, A, D, G, Q) && none4(E, B, C, I, H)) { K = F; M = F; }
        if (Dl < El && eq4(E, C, F, I, R) && none4(E, B, A, G, H)) { J = D; L = D; }
        // 2:1 slopes
        if (H !== B) {
          if (H !== A && H !== E && H !== C) {
            if (eq3(H, G, F, R) && none2(H, D, at(x + 2, y - 1))) L = M;
            if (eq3(H, I, D, Q) && none2(H, F, at(x - 2, y - 1))) M = L;
          }
          if (B !== I && B !== G && B !== E) {
            if (eq3(B, A, F, R) && none2(B, D, at(x + 2, y + 1))) J = K;
            if (eq3(B, C, D, Q) && none2(B, F, at(x - 2, y + 1))) K = J;
          }
        }
        if (F !== D) {
          if (D !== I && D !== E && D !== C) {
            if (eq3(D, A, H, S) && none2(D, B, at(x + 1, y + 2))) J = L;
            if (eq3(D, G, B, P) && none2(D, H, at(x + 1, y - 2))) L = J;
          }
          if (F !== E && F !== A && F !== G) {
            if (eq3(F, C, H, S) && none2(F, B, at(x - 1, y + 2))) K = M;
            if (eq3(F, I, B, P) && none2(F, H, at(x - 1, y - 2))) M = K;
          }
        }
      }
      const o = (2 * y) * W + 2 * x;
      out[o] = J; out[o + 1] = K; out[o + W] = L; out[o + W + 1] = M;
    }
  }
  return { width: W, height: h * 2, data: new Uint8Array(out.buffer) };
}

// Whole-number scale with MMPX: 2x passes while they fit, then nearest neighbour for the rest (3x, 6x, Fit).
function mmpxScale(img, width, height, edges) {
  let cur = img;
  while (cur.width * 2 <= width && cur.height * 2 <= height) cur = mmpx2(cur, edges);
  if (cur.width === width && cur.height === height) return cur;
  const out = new Uint8Array(width * height * 4), src = cur.data;
  for (let y = 0; y < height; y++) {
    const sy = Math.min(cur.height - 1, Math.floor((y + 0.5) * cur.height / height));
    for (let x = 0; x < width; x++) {
      const sx = Math.min(cur.width - 1, Math.floor((x + 0.5) * cur.width / width)), s = (sy * cur.width + sx) * 4, d = (y * width + x) * 4;
      out[d] = src[s]; out[d + 1] = src[s + 1]; out[d + 2] = src[s + 2]; out[d + 3] = src[s + 3];
    }
  }
  return { width, height, data: out };
}

module.exports = { mmpx2, mmpxScale };
