'use strict';
// Background music (BGM). Two playlists: the normal one, and the "dmt" one while Psychedelic mode is on.
// Shipped tracks live in app/assets/music, yours in the data folder's "music" folder (Settings > Sound >
// Custom sounds). A file whose name starts with "dmt" goes in the Psychedelic playlist, anything else in the
// normal one. Each playlist cycles through its tracks in a shuffled order with no repeats until all have played.
(function () {
  let host = { settings: () => ({}), onTrack: () => {} };
  let S = {}, info = { music: [] };
  const a = new Audio(); a.preload = 'auto';
  let mode = null, track = null, fadeT = null, fails = 0, started = false, pausing = false;
  const queue = { standard: [], dmt: [] };

  const level = () => (S.musicOn ? Math.pow(Math.max(0, Math.min(100, S.musicVolume ?? 35)) / 100, 2) : 0);
  const shuffle = (l) => { for (let i = l.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [l[i], l[j]] = [l[j], l[i]]; } return l; };

  function listFor(m) {
    let l = info.music.filter((t) => t.mode === m);
    if (S.musicSource === 'custom') { const c = l.filter((t) => t.custom); if (c.length) l = c; }
    return l;
  }
  function wantedMode() { return S.psychedelic && listFor('dmt').length ? 'dmt' : 'standard'; }
  function nextOf(m) {
    const l = listFor(m); if (!l.length) return null;
    let q = queue[m].filter((u) => l.some((t) => t.url === u));
    if (!q.length) { q = shuffle(l.map((t) => t.url)); if (q.length > 1 && track && q[0] === track.url) q.push(q.shift()); }
    const u = q.shift(); queue[m] = q;
    return l.find((t) => t.url === u);
  }
  // target: a number, or a function (fading in follows the volume slider as it moves)
  function fadeTo(target, ms, then) {
    clearInterval(fadeT);
    const from = a.volume, t0 = performance.now(), v = () => (typeof target === 'function' ? target() : target);
    if (ms <= 0) { a.volume = v(); then && then(); return; }
    fadeT = setInterval(() => {
      const k = Math.min(1, (performance.now() - t0) / ms);
      a.volume = Math.max(0, Math.min(1, from + (v() - from) * k));
      if (k >= 1) { clearInterval(fadeT); fadeT = null; then && then(); }
    }, 40);
  }
  function start(t) {
    track = t; host.onTrack(M.now());
    if (!t) { a.pause(); return; }
    a.src = t.url; a.volume = 0;
    a.play().then(() => { fails = 0; fadeTo(level, 1500); }).catch(() => {});
  }
  function switchTo(m) {
    mode = m;
    const go = () => start(nextOf(m));
    if (!a.paused && a.volume > 0.01) fadeTo(0, 700, go); else go();
  }
  a.addEventListener('ended', () => { if (S.musicOn) start(nextOf(mode)); });
  a.addEventListener('error', () => {                              // a broken file: skip it (but don't spin on a folder of them)
    if (!S.musicOn || ++fails > 5) return;
    setTimeout(() => start(nextOf(mode)), 500);
  });

  function apply() {
    if (!started) return;
    if (!S.musicOn) { if (!a.paused && !pausing) { pausing = true; fadeTo(0, 600, () => { pausing = false; a.pause(); }); } return; }
    if (pausing) { pausing = false; clearInterval(fadeT); fadeT = null; }   // back on before the fade-out finished
    const m = wantedMode();
    const stillThere = track && listFor(m).some((t) => t.url === track.url);
    if (m !== mode || !track || !stillThere) { switchTo(m); return; }
    if (a.paused) { a.volume = 0; a.play().then(() => fadeTo(level, 800)).catch(() => {}); return; }
    if (!fadeT) a.volume = level();                                  // volume slider: right away
  }

  const pretty = (name) => name.replace(/\.[^.]+$/, '').replace(/^(dmt|normal|standard)[-_ ]*/i, '').replace(/^8-?bit[-_ ]*/i, '')
    .replace(/[-_]+/g, ' ').trim().replace(/\b\w/g, (c) => c.toUpperCase()) || name;

  const M = {
    async init(opts) {
      host = Object.assign(host, opts); S = host.settings();
      await M.reload();
      started = true; apply();
    },
    async reload() {
      try { info = (await window.htk.audioInfo()) || { music: [] }; } catch { info = { music: [] }; }
      if (started) apply();
      return info;
    },
    settingsChanged() { S = host.settings(); apply(); },
    next() { if (S.musicOn) { fails = 0; switchTo(wantedMode()); } },
    now() { return track ? { name: pretty(track.name), file: track.name, mode, custom: track.custom, playing: !a.paused } : null; },
    counts() {
      const c = (f) => info.music.filter(f).length;
      return { standard: c((t) => t.mode === 'standard'), dmt: c((t) => t.mode === 'dmt'), yours: c((t) => t.custom), yoursDmt: c((t) => t.custom && t.mode === 'dmt') };
    },
    info: () => info,
    _debug: () => ({ mode, track: track && track.name, paused: a.paused, volume: a.volume, time: a.currentTime, error: a.error && a.error.code }),
  };
  window.Music = M;
})();
