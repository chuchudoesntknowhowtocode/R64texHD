'use strict';
// The footer: progress bar + the wizard (spec: project doc claude/footer-progress-spec.md, v2 2026-10-28).
//
// The footer stage is the 890 x 100 strip the scenes were drawn on (assets/scenes/stage.png). Layers, back to front:
//   stage image (idle bar dimmed) -> world canvas (scene tints, under the segments) -> bar canvas (filled
//   segments) -> sprite canvas (wizard, opponents, call-outs) -> fx canvas (live endings, bursts, pokes)
//   -> the real buttons (pipe = Home, Quit).
// Clips are pre-rendered by build/wizard/export_app.py: per frame a piece of the world and the sprite
// layer from lossless atlases, plus the wizard / opponent boxes and events (hits, K.O., ...).
//
// The director picks what plays: during a job, a scene that fits the time left (fights, classic scenes,
// trips when Psychedelic is on), with "wait, peek, wait" between scenes; the busy peek when there's no
// percentage yet; idle peeks with a phrase when nothing runs. Endings: success mid-fight = instant exit,
// otherwise the scene finishes at 3x; cancel / error = a yellow / red burst.
(function () {
  const FPS = 30;
  const $ = (s) => document.querySelector(s);
  let ST = null, IDX = null, S = {};                            // stage meta, clip index, live settings
  const els = {};
  const cx = {};

  // ------------------------------------------------------------------ settings + host hooks
  let host = { settings: () => ({}), saveWins: () => {}, goToJob: () => {}, assets: '../assets/scenes/' };
  const on = (k, dflt = true) => (S[k] === undefined ? dflt : S[k] !== false);
  const anim = () => on('sceneAnimations');

  // ------------------------------------------------------------------ assets
  const imgCache = new Map();
  function loadImg(src) {
    if (!imgCache.has(src)) imgCache.set(src, new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; }));
    return imgCache.get(src);
  }
  const clipCache = new Map();                                    // id -> Promise<{meta, imgs}>, a few kept
  function loadClip(id) {
    if (clipCache.has(id)) { const p = clipCache.get(id); clipCache.delete(id); clipCache.set(id, p); return p; }
    const p = window.htk.sceneClip(id).then((meta) => {
      if (!meta || meta.error) throw new Error((meta && meta.error) || 'no clip ' + id);
      const base = (IDX && IDX[id] && IDX[id].base) || host.assets + id + '/';   // starter clips in the app, the rest in data\scenes
      return Promise.all(meta.atlases.map((a) => loadImg(base + a)))
        .then((imgs) => ({ meta, imgs, opp: meta.kind === 'fight' ? loadImg(base + 'opponent.png').catch(() => null) : null }));
    });
    clipCache.set(id, p);
    while (clipCache.size > 6) { const k = clipCache.keys().next().value; clipCache.delete(k); }
    p.catch(() => clipCache.delete(id));
    return p;
  }

  // ------------------------------------------------------------------ sound slots (OGG clips the owner supplies)
  const SOUND_SLOTS = ['job_start', 'into_pipe', 'cancel_burst', 'error_burst', 'hit', 'ko', 'impact', 'burn', 'vs', 'honk',
    'rerobe', 'peek', 'bubble', 'poke', 'zap', 'trip_start', 'bonus'];
  let sounds = {};
  function sfx(slot) {
    if (!S.soundEffects || !sounds[slot]) return;
    try { const a = new Audio(sounds[slot]); a.volume = Math.pow(Math.max(0, Math.min(100, S.soundVolume ?? 60)) / 100, 2); a.play().catch(() => {}); } catch { /* ignore */ }
  }

  // ------------------------------------------------------------------ the bar
  const bar = { p: 0, mode: 'idle', k: 0, drainFrom: 0 };
  function drawBar(worldHere) {
    const g = cx.bar; g.clearRect(0, 0, 890, 100);
    if (bar.mode === 'idle' || !ST || !els.full) return;
    const { x0, x1, seg } = ST.bar;
    let p = bar.p;
    if (bar.mode === 'fail') { const k = bar.k; p = bar.drainFrom * Math.max(0, 1 - Math.max(0, k - 16) / 24); }
    const fx = x1 - Math.round((p * (x1 - x0)) / seg) * seg;
    if (fx >= x1) return;
    g.globalAlpha = worldHere ? 0.75 : 1;
    g.drawImage(els.full, fx, 0, x1 - fx, 100, fx, 0, x1 - fx, 100);
    g.globalAlpha = 1;
    if (bar.mode === 'run') {                                      // the front segment a little brighter
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = 0.28;
      g.drawImage(els.full, fx, 0, seg, 100, fx, 0, seg, 100);
      g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
    }
    if (bar.mode === 'fail' && bar.k < 16 && Math.floor(bar.k / 4) % 2 === 0) {   // red flash, twice
      g.globalCompositeOperation = 'source-atop'; g.fillStyle = 'rgba(255,40,50,.6)'; g.fillRect(fx, 0, x1 - fx, 100); g.globalCompositeOperation = 'source-over';
    }
  }

  // ------------------------------------------------------------------ player
  let cur = null;                       // { id, meta, imgs, opp, i, speed, loop, done, kind, onEnd }
  function play(id, opts = {}) {
    return loadClip(id).then(({ meta, imgs, opp }) => new Promise((resolve) => {
      cur = { id, meta, imgs, opp, i: 0, speed: opts.speed || 1, loop: !!opts.loop, kind: meta.kind, onEnd: resolve, last: -1 };
      if (meta.kind === 'trip') sfx('trip_start');
      if (meta.kind === 'rerobe') sfx('rerobe');
      if (meta.kind === 'peek') sfx('peek');
    })).catch(() => { cur = null; return 'failed'; });
  }
  function stopClip() { if (cur) { const f = cur.onEnd; cur = null; clearScene(); f && f('stopped'); } }
  function clearScene() { cx.world.clearRect(0, 0, 890, 100); cx.sprite.clearRect(0, 0, 890, 100); hideButtons(false, false); }
  const inRuns = (r, i) => !!r && r.some(([a, b]) => i >= a && i < b);
  let hidden = [false, false];
  function hideButtons(pipe, quit) {
    if (hidden[0] === pipe && hidden[1] === quit) return; hidden = [pipe, quit];
    const img = document.querySelector('#home img'); if (img) img.style.visibility = pipe ? 'hidden' : '';
    const q = document.querySelector('#quit'); if (q) q.style.opacity = quit ? '0' : '';
  }
  function piece(g, imgs, p, dx = 0, dy = 0) { if (p) g.drawImage(imgs[p[0]], p[1], p[2], p[3], p[4], p[5] + dx, p[6] + dy, p[3], p[4]); }
  function drawClipFrame() {
    const c = cur; if (!c) { clearScene(); return false; }
    const i = Math.min(c.meta.frames - 1, Math.floor(c.i));
    clearScene();
    const hop = poke.hop > 0 ? -2 : 0, shake = poke.shake > 0 ? (poke.shake % 2 ? 2 : -2) : 0;
    // a scene that moves or recolours the pipe / Quit draws its own copy: the real one steps aside (still clickable)
    hideButtons(inRuns(c.meta.hidePipe, i), inRuns(c.meta.hideQuit, i));
    piece(cx.world, c.imgs, c.meta.world[i]);
    piece(cx.sprite, c.imgs, c.meta.sprite[i], shake, hop);
    // events between the last drawn frame and this one
    const ev = c.meta.events || {};
    for (const [name, list] of Object.entries(ev)) for (const f of list) if (f > c.last && f <= i) sfx(name === 'impact' ? 'impact' : name);
    c.last = i;
    return !!c.meta.world[i];
  }
  function advance() {
    const c = cur; if (!c) return;
    c.i += c.speed;
    if (c.i >= c.meta.frames) {
      if (c.loop) { c.i = 0; c.last = -1; return; }
      const f = c.onEnd; cur = null; clearScene(); f && f('ended');
    }
  }

  // ------------------------------------------------------------------ live effects (fx canvas)
  const fx = [];                         // {draw(g, k) -> bool keep, k}
  function addFx(draw) { fx.push({ draw, k: 0 }); }
  function drawFx() {
    const g = cx.fx; g.clearRect(0, 0, 890, 100);
    for (let j = fx.length - 1; j >= 0; j--) { if (!fx[j].draw(g, fx[j].k++)) fx.splice(j, 1); }
  }
  const snap = (v) => Math.round(v);
  function burstRings(x, y, kind, scale = 1) {
    const col = kind === 'error' ? ['#ff4040', '#ffaaa0'] : ['#ffd628', '#fff5aa'];
    addFx((g, k) => {
      if (k >= 30) return false;
      g.globalAlpha = k < 18 ? 1 : 1 - (k - 18) / 12;
      [[3.5, 6, false], [5.5, 4, true]].forEach(([sp, r, blink], ri) => {
        if (blink && Math.floor(k / 2) % 2) return;
        const R = (4 + k * sp) * scale;
        for (let j = 0; j < 8; j++) {
          const a = (j * Math.PI) / 4 + (ri * Math.PI) / 8, px = snap(x + R * Math.cos(a)), py = snap(y + R * 0.6 * Math.sin(a));
          g.fillStyle = col[0]; g.beginPath(); g.arc(px, py, r, 0, Math.PI * 2); g.fill();
          g.fillStyle = col[1]; g.fillRect(px - r / 3, py - r / 3, 2, 2);
        }
      });
      g.globalAlpha = 1; return true;
    });
  }
  // the call-out font's ! ? + 1 (5 x 7), drawn as pixel blocks
  const GLYPH = { '!': ['00100', '00100', '00100', '00100', '00100', '00000', '00100'], '?': ['01110', '10001', '00001', '00110', '00100', '00000', '00100'],
    '+': ['00000', '00100', '00100', '11111', '00100', '00100', '00000'], '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'] };
  function text(g, s, x, y, col, px = 2) {
    [...s].forEach((ch, n) => (GLYPH[ch] || []).forEach((row, r) => [...row].forEach((v, c) => {
      if (v !== '1') return;
      g.fillStyle = '#0a0e2a'; g.fillRect(x + (n * 6 + c) * px - 1, y + r * px - 1, px + 2, px + 2);
    })));
    [...s].forEach((ch, n) => (GLYPH[ch] || []).forEach((row, r) => [...row].forEach((v, c) => { if (v === '1') { g.fillStyle = col; g.fillRect(x + (n * 6 + c) * px, y + r * px, px, px); } })));
  }
  function spark(x, y, col = '#ffffff') {
    addFx((g, k) => {
      if (k > 6) return false;
      const r = 3 + k * 3, a = 1 - k / 7; g.globalAlpha = a;
      for (let ang = 0; ang < 360; ang += 45) {
        const L = r * (ang % 90 === 0 ? 1 : 0.6);
        for (let s = 0; s < L; s += 2) { g.fillStyle = s < L * 0.4 ? col : '#ffdc3c'; g.fillRect(snap(x + s * Math.cos(ang * Math.PI / 180)) - 1, snap(y + s * Math.sin(ang * Math.PI / 180)) - 1, 2, 2); }
      }
      g.fillStyle = col; g.fillRect(snap(x) - 3, snap(y) - 3, 6, 6); g.globalAlpha = 1; return true;
    });
  }

  // instant exit (success mid-fight): the opponent goes into the pipe, he follows
  function instantExit(c) {
    const i = Math.min(c.meta.frames - 1, Math.floor(c.i)), a = (c.meta.actors && c.meta.actors[i]) || [ST.sx, ST.sx - 230];
    const robed = i < (c.meta.robedUntil || 0);
    const P = ST.poses, poses = els.poses, M = ST.mouth;
    const opp = c.opp;
    stopClipSilently();
    return new Promise((resolve) => {
      Promise.resolve(opp).then((oppImg) => addFx((g, k) => {
        if (k >= 26) { sfx('into_pipe'); resolve(); return false; }
        g.save(); g.beginPath(); g.rect(M, 0, 890 - M, 100); g.clip();
        if (oppImg && k < 16) {                                       // opponent spins into the pipe
          const t = Math.min(1, k / 14), x = a[1] + (M - 55 - a[1]) * (t * t * 0.5 + t * 0.5), y = ST.floor - 15 - 20 * Math.sin(Math.PI * t);
          g.translate(snap(x), snap(y)); g.rotate((Math.floor((k * 60) / 45) * 45 * Math.PI) / 180);
          g.drawImage(oppImg, -oppImg.width / 2, -oppImg.height / 2); g.setTransform(1, 0, 0, 1, 0, 0);
        }
        const draw = (name, hx, footY) => { const p = P[name]; g.drawImage(poses, p.x, p.y, p.w, p.h, snap(hx - p.hipx), snap(footY - p.foot), p.w, p.h); };
        if (robed) {                                                  // still in the robe: he just runs in
          const t = k / 26, x = a[0] + (M - 40 - a[0]) * t; draw('robe' + (Math.floor(k / 2) % 4), x, ST.floor);
        } else if (k < 4) { draw('up', a[0], ST.floor - 6); }
        else {
          const t = (k - 4) / 22;
          if (t < 0.6) { const x = a[0] + (M + 120 - a[0]) * (t / 0.6); draw(Math.floor(k / 3) % 2 ? 'run1' : 'run2', x, ST.floor); }
          else { const x = M + 120 + (M - 60 - (M + 120)) * ((t - 0.6) / 0.4); draw('fly', x, ST.air + 20); }
        }
        g.restore(); return true;
      }));
    });
  }
  function stopClipSilently() { cur = null; clearScene(); }

  // ------------------------------------------------------------------ pokes
  const poke = { hop: 0, shake: 0, times: [] };
  function boxAt(list, i) { return list && list[Math.min(list.length - 1, i)]; }
  function inBox(b, x, y, pad = 4) { return b && x >= b[0] - pad && x <= b[0] + b[2] + pad && y >= b[1] - pad && y <= b[1] + b[3] + pad; }
  function onStageClick(e) {
    const r = els.click.getBoundingClientRect(), x = ((e.clientX - r.left) * 890) / r.width, y = ((e.clientY - r.top) * 100) / r.height;
    const c = cur, i = c ? Math.floor(c.i) : 0;
    if (c && on('poking')) {
      const wz = boxAt(c.meta.wizard, i), op = boxAt(c.meta.opponent, i);
      if (inBox(wz, x, y)) { pokeWizard(c, i, x, y, wz); return; }
      if (inBox(op, x, y)) { spark(x, y); poke.shake = 6; sfx('poke'); return; }
    }
    if (D.job && !D.job.ended) host.goToJob();
  }
  function pokeWizard(c, i, x, y, wz) {
    const now = performance.now(); poke.times = poke.times.filter((t) => now - t < 3000); poke.times.push(now);
    sfx('poke');
    if (poke.times.length >= 5) {                                    // annoyed: glare, then zap the cursor spot
      poke.times = [];
      const hx = wz[0] + wz[2] / 2, hy = wz[1] + 6;
      addFx((g, k) => {
        if (k > 20) return false;
        text(g, '!', hx + 12, Math.max(1, wz[1] - 16), '#ff4a3c');
        if (k >= 6 && k < 14) {
          g.strokeStyle = '#c48cff'; g.lineWidth = 2; g.beginPath(); g.moveTo(hx, hy);
          const n = 5; for (let s = 1; s <= n; s++) g.lineTo(hx + ((x - hx) * s) / n + (s < n ? (k % 2 ? 3 : -3) : 0), hy + ((y - hy) * s) / n);
          g.stroke(); if (k === 6) { spark(x, y, '#e2c2ff'); sfx('zap'); }
        }
        return true;
      });
      return;
    }
    if (c.kind === 'fight' && c.meta.combo && i >= c.meta.combo[0] && i < c.meta.combo[1]) {   // an extra hit in the combo
      spark(x, y); sfx('hit');
      addFx((g, k) => { if (k > 14) return false; g.globalAlpha = 1 - k / 15; text(g, '+1', snap(x) - 6, snap(y) - 14 - k, '#ffdc3c'); g.globalAlpha = 1; return true; });
      return;
    }
    if (c.kind === 'peek') {                                         // startled, and says something else
      addFx((g, k) => { if (k > 10) return false; text(g, '!', wz[0] + wz[2] + 2, Math.max(1, wz[1] - 4), '#ffdc3c'); return true; });
      setTimeout(() => { if (cur === c) { stopClip(); } }, 300);
      return;
    }
    poke.hop = 4;
    const ch = Math.random() < 0.5 ? '!' : '?';
    addFx((g, k) => { if (k > 16) return false; text(g, ch, wz[0] + wz[2] / 2 + 8, Math.max(1, wz[1] - 16), ch === '!' ? '#ffdc3c' : '#ffffff'); return true; });
  }

  // ------------------------------------------------------------------ the director
  const D = { job: null, inGi: false, busyN: 0, lastOpp: '', idleSince: performance.now(), nextPeekAt: 0, deck: [], seq: 0 };
  const byKind = (k) => Object.values(IDX || {}).filter((c) => c.kind === k);
  const dur = (c) => c.frames / FPS;
  const wait = (ms) => new Promise((r) => { const t = setTimeout(r, ms); D.waitCancel = () => { clearTimeout(t); r('cancel'); }; });
  function eta() {
    const j = D.job; if (!j || !j.rate || j.rate <= 0) return null;
    return Math.max(0, (1 - j.p) / j.rate);
  }
  function fightId(opp, robed) {
    let id = `fight_${opp}_${robed ? 'robed' : 'gi'}`;
    if ((opp === 'golem' || opp === 'robot') && Math.random() < 0.35) id += '_odd_hit';
    if (opp === 'twin' && Math.random() < 1 / 3) id += '_twin_wins_r1';
    return IDX[id] ? id : `fight_${opp}_${robed ? 'robed' : 'gi'}`;
  }
  function pickScene(R) {
    const cats = [];
    const fits = (c, most) => dur(c) * most <= R;
    if (on('fights')) {
      const wins = host.wins();
      const opps = ['goblin', 'golem', 'robot', 'twin'].concat(on('psychedelic', false) ? ['elf'] : []).filter((o) => o !== D.lastOpp);
      const bonusDue = wins > 0 && wins % 3 === 0 && host.bonusAt() !== wins;
      const opp = bonusDue ? 'car' : opps[Math.floor(Math.random() * opps.length)];
      const id = fightId(opp, !D.inGi);
      if (IDX[id] && fits(IDX[id], 0.7)) cats.push({ kind: 'fight', id, opp });
    }
    const cl = byKind('classic').filter((c) => fits(c, 0.6));
    if (cl.length) cats.push({ kind: 'classic', id: cl[Math.floor(Math.random() * cl.length)].id });
    if (on('psychedelic', false)) {
      const tr = byKind('trip').filter((c) => fits(c, 0.6));
      if (tr.length) cats.push({ kind: 'trip', id: tr[Math.floor(Math.random() * tr.length)].id });
    }
    return cats.length ? cats[Math.floor(Math.random() * cats.length)] : null;
  }
  async function jobLoop(seq) {
    const alive = () => D.job && !D.job.ended && D.seq === seq;
    if (D.inGi && anim()) { await play('rerobe'); D.inGi = false; if (!alive()) return; }
    while (alive()) {
      if (!anim()) { await wait(500); continue; }
      const R = eta(), elapsed = (performance.now() - D.job.t0) / 1000;
      let pick = R != null && elapsed > 1.5 ? pickScene(R) : null;
      if (D.eggNext) { D.eggNext = false; pick = { kind: 'fight', id: fightId('elf', !D.inGi), opp: 'elf', egg: true }; }
      if (!pick) { if ((await play('busy_11_peek_buffering')) === 'failed') await wait(1000); continue; }
      if (pick.kind !== 'fight' && D.inGi) { await play('rerobe'); D.inGi = false; if (!alive()) return; }
      if (pick.kind === 'fight') D.lastOpp = pick.opp;
      const r = await play(pick.id);
      if (r === 'failed') { await wait(1000); continue; }
      if (pick.kind === 'fight' && r === 'ended') {
        D.inGi = true;
        if (pick.opp === 'car') { host.setBonusAt(host.wins()); sfx('bonus'); }
        else if (!pick.egg) host.addWin();
      }
      if (!alive()) return;
      // wait, peek, wait (3 s, or until 2 more segments fill if that's sooner; at least 1 s)
      for (const step of ['wait', 'peek', 'wait']) {
        if (!alive()) return;
        if (step === 'peek') { await play('busy_11_peek_buffering'); continue; }
        const j = D.job, segP = ST.bar.seg / (ST.bar.x1 - ST.bar.x0), t2 = j.rate > 0 ? (2 * segP) / j.rate : 3;
        await wait(1000 * Math.max(1, Math.min(3, t2)));
      }
    }
  }
  async function idleLoop() {
    // nothing running: every 20 s (60 s after 5 minutes) he peeks out of the pipe and says something
    if (D.job || D.busyN || cur || D.peeking || D.egg || !on('idlePeeks')) return;
    const now = performance.now();
    if (now < D.nextPeekAt) return;
    const idleFor = now - D.idleSince;
    D.nextPeekAt = now + (idleFor > 5 * 60000 ? 60000 : 20000);
    if (!D.deck.length) { D.deck = byKind('peek').map((c) => c.id).sort(() => Math.random() - 0.5); }
    const id = D.deck.shift(); if (!id) return;
    D.peeking = true;
    try {
      const r = await play(id);
      if (r === 'stopped' && !D.job && D.deck.length) { await play(D.deck.shift()); }   // poked: a startled "!" and a new phrase
    } finally { D.peeking = false; }
  }

  // ------------------------------------------------------------------ hidden: 5 clicks on the pipe within 5 s = the machine elf
  const egg = { times: [] };
  function onPipeClick() {
    const now = performance.now(); egg.times = egg.times.filter((t) => now - t < 5000); egg.times.push(now);
    if (egg.times.length < 5) return;
    egg.times = [];
    W.secretElf();
  }
  async function secretElf() {
    if (!IDX || !IDX.fight_elf_robed) return false;
    addFx((g, k) => { if (k > 18) return false; text(g, '!', ST.mouth + 6, 8 - (k < 4 ? 4 - k : 0), '#c48cff'); return true; });
    if (D.job && !D.job.ended) {                                     // during a job: it's the next scene
      D.eggNext = true;
      if (cur && cur.kind === 'busy') stopClip();
      return true;
    }
    if (D.egg) return false;
    D.egg = true; D.seq++;
    try {
      stopClip();
      if (D.waitCancel) D.waitCancel();
      const r = await play(fightId('elf', !D.inGi));
      if (r === 'ended') D.inGi = true;                              // robe burned: it rebuilds before the next job's first scene
    } finally { D.egg = false; D.idleSince = performance.now(); D.nextPeekAt = performance.now() + 20000; }
    return true;
  }

  // ------------------------------------------------------------------ ticking
  let paused = false;
  function tick() {
    if (paused) return;
    const worldHere = drawClipFrame();
    drawBar(worldHere);
    drawFx();
    advance();
    if (poke.hop > 0) poke.hop--; if (poke.shake > 0) poke.shake--;
    if (bar.mode === 'fail') { bar.k++; if (bar.k > 46) { bar.mode = 'idle'; bar.p = 0; } }
    if (bar.mode === 'done') { bar.k++; if (bar.k > 12) { bar.mode = 'idle'; bar.p = 0; } }
    taskbar();
    if (!D.job) idleLoop();
  }
  let lastTask = '';
  function taskbar() {
    const v = bar.mode === 'run' ? bar.p : bar.mode === 'fail' && bar.k < 30 ? 1 : -1, mode = bar.mode === 'fail' ? 'error' : 'normal';
    const key = v.toFixed(3) + mode; if (key === lastTask) return; lastTask = key;
    window.htk.taskbar && window.htk.taskbar(v, mode);
  }
  document.addEventListener('visibilitychange', () => {
    paused = document.hidden;
    if (!paused && D.job && !D.job.ended && cur && cur.kind !== 'busy') { stopClip(); }   // back from minimised: a new scene
    if (!paused) D.nextPeekAt = Math.max(D.nextPeekAt, performance.now() + 5000);
  });

  // ------------------------------------------------------------------ public API
  const W = {
    async init(opts) {
      host = Object.assign(host, opts);
      ['stage', 'world', 'bar', 'sprite', 'fx', 'click'].forEach((k) => (els[k] = $('#fx-' + k)));
      ['world', 'bar', 'sprite', 'fx'].forEach((k) => { cx[k] = els[k].getContext('2d'); cx[k].imageSmoothingEnabled = false; });
      els.click.addEventListener('click', onStageClick);
      const pipe = document.querySelector('#home'); if (pipe) pipe.addEventListener('click', onPipeClick);
      S = host.settings();
      try {
        const r = await window.htk.sceneIndex(); ST = r.stage; IDX = r.index || {}; W.library = { here: r.here, total: r.total, download: r.download };
        if (window.htk.onScenesUpdated) window.htk.onScenesUpdated(async (d) => {
          try { const n = await window.htk.sceneIndex(); IDX = n.index || IDX; W.library = { here: n.here, total: n.total, download: d }; } catch { /* keep what we have */ }
          if (host.onLibrary) host.onLibrary(W.library);
        });
        els.full = await loadImg(host.assets + 'bar_full.png'); els.poses = await loadImg(host.assets + 'poses.png');
      } catch (e) { console.warn('footer scenes unavailable', e); IDX = {}; }
      await W.reloadSounds();
      setInterval(tick, 1000 / FPS);
    },
    settingsChanged() { S = host.settings(); if (!anim() && cur && cur.kind !== 'peek') stopClip(); },
    jobStart() {
      D.seq++; D.job = { t0: performance.now(), p: 0, rate: 0, lastT: performance.now(), lastP: 0, ended: false };
      bar.mode = 'run'; bar.p = 0; bar.k = 0;
      sfx('job_start');
      if (cur && (cur.kind === 'peek' || cur.kind === 'busy' || D.egg)) { if (D.egg) D.eggNext = true; stopClip(); }
      jobLoop(D.seq);
    },
    progress(done, total) {
      const j = D.job; if (!j || !(total > 0)) return;
      const p = Math.max(0, Math.min(1, done / total)), now = performance.now(), dt = (now - j.lastT) / 1000;
      if (dt > 0.25 && p > j.lastP) {
        const r = (p - j.lastP) / dt; j.rate = j.rate ? j.rate * 0.7 + r * 0.3 : r; j.lastT = now; j.lastP = p;
      }
      j.p = p; bar.p = p;
    },
    async jobEnd(kind) {                                            // 'done' | 'cancel' | 'error'
      const j = D.job; if (!j) return;
      j.ended = true; D.seq++; if (D.waitCancel) D.waitCancel();
      const c = cur;
      if (kind === 'done') {
        bar.p = 1; bar.mode = 'done'; bar.k = 0;
        if (c && c.kind === 'fight' && c.meta.combo && Math.floor(c.i) < c.meta.combo[1]) { await instantExit(c); D.inGi = true; }
        else if (c) { c.speed = 3; if (c.kind === 'fight') D.inGi = true; }
        else sfx('into_pipe');
      } else {
        const drainFrom = bar.p; bar.mode = 'fail'; bar.k = 0; bar.drainFrom = drainFrom;
        sfx(kind === 'error' ? 'error_burst' : 'cancel_burst');
        if (c && anim()) {
          const i = Math.min(c.meta.frames - 1, Math.floor(c.i)), wz = boxAt(c.meta.wizard, i), op = c.meta.opponent && boxAt(c.meta.opponent, i);
          if (wz) burstRings(wz[0] + wz[2] / 2, wz[1] + wz[3] / 2, kind === 'error' ? 'error' : 'cancel');
          if (op) burstRings(op[0] + op[2] / 2, op[1] + op[3] / 2, kind === 'error' ? 'error' : 'cancel', 0.6);
          if (c.kind === 'fight') D.inGi = D.inGi || Math.floor(c.i) >= (c.meta.robedUntil || 0);
        }
        stopClipSilently();
      }
      D.job = null; D.idleSince = performance.now(); D.nextPeekAt = performance.now() + 20000;
    },
    busy(onOff) {                                                    // work with no percentage (reading, checking...)
      D.busyN = Math.max(0, D.busyN + (onOff ? 1 : -1));
      if (D.job || !anim()) return;
      if (D.busyN && !cur && !D.busyStarting && !D.egg) { D.busyStarting = true; play('busy_11_peek_buffering', { loop: true }).finally(() => { D.busyStarting = false; }); }
      if (!D.busyN && cur && cur.kind === 'busy' && cur.loop) { cur.loop = false; cur.speed = 2; }
    },
    secretElf,
    async reloadSounds() { try { sounds = ((await window.htk.audioInfo()) || {}).sfx || {}; } catch { sounds = {}; } return sounds; },
    sfx,
    _debug: () => ({ D, bar, cur: cur && { id: cur.id, i: cur.i } }),
  };
  window.Wizard = W;
})();
