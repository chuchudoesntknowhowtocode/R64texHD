'use strict';
// Pixel icons for the folded left menu (12 x 12, drawn at 2x). Original drawings, not project logos.
//   upscale  small pixel block growing into a big one     rt64      texture memory chip (the dump)
//   rtz      archive box with a zipper                    ship      a little sailing ship
//   classic  a stack of texture packs                     roms      cartridge under a magnifying glass
//   settings gear                                          about     "i" in a speech bubble
(function () {
  const C = { o: '#ff9a6a', O: '#c8574a', y: '#ffd166', Y: '#b8862e', w: '#f1e4ff', W: '#b9a6d6', v: '#c48cff', V: '#7b55b3', d: '#2b1b47', k: '#0c0618',
    g: '#3fcf7a', G: '#1f8a4c', b: '#6cc6ff', B: '#2f7fb8', p: '#ff6ad5', P: '#a83f8c', r: '#ff6464', s: '#9aa3b5', S: '#5b6274', n: '#8a5a3b', N: '#5a3a26' };
  const ICONS = {
    upscale: [
      '......oOoOoO',
      '......OoOoOo',
      '......oOoOoO',
      '...wwwOoOoOo',
      '....wwoOoOoO',
      '...w.wOoOoOo',
      '..w.........',
      '.w..........',
      'yYy.........',
      'Yyy.........',
      'yyY.........',
      '............'],
    rt64: [
      '.w.w.w.w.w..',
      'VVVVVVVVVVV.',
      'VddddddddddV',
      'VdbBdgGdoOdV',
      'VdBbdGgdOodV',
      'VddddddddddV',
      'VdyYdpPdvVdV',
      'VdYydPpdVvdV',
      'VddddddddddV',
      '.VVVVVVVVVV.',
      '.w.w.w.w.w..',
      '............'],
    rtz: [
      '..yyyyyyyy..',
      '.yYYYwkYYYy.',
      '.yyyywkyyyy.',
      '.yyyykwyyyy.',
      '.yyyywkyyyy.',
      '.yyyykwyyyy.',
      '.yyyywwyyyy.',
      '.yyyyWWyyyy.',
      '.yyyyWWyyyy.',
      '.yyyyyyyyyy.',
      '.YYYYYYYYYY.',
      '............'],
    ship: [
      '.....r......',
      '.....rr.....',
      '.....w......',
      '....ww.ww...',
      '...www.www..',
      '..wwww.wwww.',
      '.wwwww.wwwww',
      '.....n......',
      'nnnnnnnnnnnn',
      '.NnnnnnnnnN.',
      '..NNNNNNNN..',
      'b.bb.bb.bb.b'],
    classic: [
      '....gggggggg',
      '....gGGGGGGg',
      '..vvvvvvvvGg',
      '..vVVVVVVvGg',
      'ppppppppvvGg',
      'pPPPPPPpvVgg',
      'pPwPPwPpvV..',
      'pPPPPPPpvv..',
      'pPPwPPPpv...',
      'pPPPPPPp....',
      'pppppppp....',
      '............'],
    roms: [
      '.ssssssss...',
      '.sSSSSSSs...',
      '.sbbbbbbs...',
      '.sbBBBBbs...',
      '.sbbbbbbs...',
      '.sSSSwwwS...',
      '.sssw...ws..',
      '.s.w.....w..',
      '.S.w.....w..',
      '....w...w...',
      '.....www.w..',
      '..........ww'],
    settings: [
      '.....ww.....',
      '..w.wwww.w..',
      '..wwwwwwww..',
      '.wwwW..Www..',
      'wwwW....Wwww',
      '.wwW....Ww..',
      '.wwW....Ww..',
      'wwwW....Wwww',
      '.wwwW..Www..',
      '..wwwwwwww..',
      '..w.wwww.w..',
      '.....ww.....'],
    about: [
      '.vvvvvvvvvv.',
      'vvvvvwwvvvvv',
      'vvvvvwwvvvvv',
      'vvvvvvvvvvvv',
      'vvvvwwwvvvvv',
      'vvvvvwwvvvvv',
      'vvvvvwwvvvvv',
      'vvvvvwwvvvvv',
      'vvvvwwwwvvvv',
      '.vvvvvvvvvv.',
      '..vv........',
      '..v.........'],
  };
  window.navIcon = (name) => {
    const rows = ICONS[name]; if (!rows) return '';
    let r = '';
    rows.forEach((row, y) => [...row].forEach((ch, x) => { if (C[ch]) r += `<rect x="${x}" y="${y}" width="1" height="1" fill="${C[ch]}"/>`; }));
    return `<svg viewBox="0 0 12 12" width="24" height="24" shape-rendering="crispEdges" aria-hidden="true">${r}</svg>`;
  };
  window.NAV_ICONS = Object.keys(ICONS);
})();
