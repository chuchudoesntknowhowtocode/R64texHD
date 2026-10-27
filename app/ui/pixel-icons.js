'use strict';
// Pixel-art round status buttons (16x16 sprites drawn as crisp SVG squares), in the style of
// classic 8-bit UI buttons: dark outline, light top-left, shaded bottom-right, a white shine,
// and an optional symbol pressed into the face.
//   pixelIcon('green')            done
//   pixelIcon('green', 'play')    ready / working
//   pixelIcon('grey', 'menu')     choose / select
//   pixelIcon('red', 'x')         error / not downloaded
//   pixelIcon('yellow', 'bang')   something to look at
(function () {
  const PALETTES = {
    //        outline    dark       base       light      shine      symbol
    green:  ['#0b3d14', '#178a2c', '#22b63c', '#5be36f', '#d6ffd9', '#0e5a1c'],
    red:    ['#4a0a0a', '#a31616', '#d92626', '#ff6a5a', '#ffe0da', '#3a0404'],
    grey:   ['#1d2236', '#4b5272', '#6b7397', '#99a2c4', '#e6e9f5', '#262c45'],
    yellow: ['#5a3500', '#c27a00', '#f2a90f', '#ffd64d', '#fff6c8', '#6e4100'],
    purple: ['#2e0a4a', '#7a1fb3', '#a33ae0', '#cf7dff', '#f3dcff', '#3d0e5e'],
    orange: ['#4f2200', '#b84e00', '#e8720a', '#ffa349', '#ffe6cc', '#5c2700'],
  };
  // Symbols on the 16x16 grid: [x, y] cells.
  const SYMBOLS = {
    play: [[6,4],[6,5],[7,5],[6,6],[7,6],[8,6],[6,7],[7,7],[8,7],[9,7],[6,8],[7,8],[8,8],[9,8],[6,9],[7,9],[8,9],[6,10],[7,10],[6,11]],
    x: [[4,4],[5,4],[10,4],[11,4],[5,5],[6,5],[9,5],[10,5],[6,6],[7,6],[8,6],[9,6],[7,7],[8,7],[7,8],[8,8],[6,9],[7,9],[8,9],[9,9],[5,10],[6,10],[9,10],[10,10],[4,11],[5,11],[10,11],[11,11]],
    menu: [5,6,7,8,9,10].flatMap((x) => [[x,5],[x,8],[x,11]]),
    bang: [[7,4],[8,4],[7,5],[8,5],[7,6],[8,6],[7,7],[8,7],[7,8],[8,8],[7,10],[8,10],[7,11],[8,11]],
    check: [[10,5],[11,5],[9,6],[10,6],[8,7],[9,7],[4,8],[5,8],[7,8],[8,8],[5,9],[6,9],[7,9],[6,10]],
  };
  const N = 16, C = 7.5;
  const cache = new Map();

  function sprite(color, symbol) {
    const [outline, dark, base, light, shine, ink] = PALETTES[color] || PALETTES.grey;
    const cells = new Map();
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const d = Math.hypot(x - C, y - C);
      if (d > 7.7) continue;
      let c;
      if (d > 6.6) c = outline;                                   // dark ring
      else if (Math.hypot(x - (C - 1.4), y - (C - 1.4)) > 6.1) c = dark;   // shaded crescent, bottom right
      else if (Math.hypot(x - (C - 2.6), y - (C - 2.6)) < 3.2) c = light;  // lit area, top left
      else c = base;
      cells.set(x + ',' + y, c);
    }
    // shine: a short pixel arc in the top-left
    for (const [x, y] of [[4,3],[5,3],[3,4],[3,5],[4,4]]) cells.set(x + ',' + y, shine);
    // symbol, with a one-pixel highlight under it so it looks pressed in
    if (symbol && SYMBOLS[symbol]) {
      const pressed = true;
      const sym = SYMBOLS[symbol];
      for (const [x, y] of sym) {
        const k = x + ',' + (y + 1);
        if (pressed && !sym.some(([a, b]) => a === x && b === y + 1) && cells.has(k)) cells.set(k, light);
      }
      for (const [x, y] of sym) cells.set(x + ',' + y, ink);
    }
    let rects = '';
    for (const [k, c] of cells) { const [x, y] = k.split(','); rects += `<rect x="${x}" y="${y}" width="1" height="1" fill="${c}"/>`; }
    return `<svg class="px-icon" viewBox="0 0 16 16" shape-rendering="crispEdges" aria-hidden="true">${rects}</svg>`;
  }

  window.pixelIcon = (color, symbol = '') => {
    const key = color + '|' + symbol;
    if (!cache.has(key)) cache.set(key, sprite(color, symbol));
    return cache.get(key);
  };
})();
