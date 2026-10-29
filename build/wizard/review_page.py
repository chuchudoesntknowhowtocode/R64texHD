"""Writes the Wizard Scene Review page (v2) from the render manifests.   python3 review_page.py <review dir>"""
import os, sys, json, glob, html
D = sys.argv[1]
man = {}
for m in sorted(glob.glob(os.path.join(D, 'manifest*.json'))): man.update(json.load(open(m)))
ORDER = ['Chained runs', 'Fights', 'Clips', 'Psychedelic: LSD', 'Psychedelic: DMT', 'Found in the toolkit (12-21)', 'Older fighter tests']
KEY_ORDER = ['run_robe', 'run_twin', 'run_bonus', 'end_success', 'end_cancel', 'end_error']
GROUP_NOTE = {
    'Chained runs': 'How the director strings clips together on a real job. The bar fills from the right as the job runs; between scenes: wait (3 s, or 2 segments if sooner), the peek, wait.',
    'Fights': 'Each opponent once, with the new look. The robe and hat burn on a robed start; later in the job he starts in the gi.',
    'Clips': 'The pieces between scenes, and what plays when no job is running.',
    'Psychedelic: LSD': 'Behind the Psychedelic switch (off by default). Re-rendered with the new wizard.',
    'Psychedelic: DMT': 'Behind the Psychedelic switch. The 9 earlier-run duplicates and elf draft 42 are out.',
    'Found in the toolkit (12-21)': 'Your toolkit has scenes 12-21 (scenes2.py). You said there are none, so they are not in the pool. Mark Looks right to add one, Needs a fix or leave it to keep it out.',
    'Older fighter tests': 'Kept as they are (old style). In the pool as one-offs.',
}
items = []
for g in ORDER:
    keys = [k for k, v in man.items() if v['group'] == g]
    keys.sort(key=lambda k: (KEY_ORDER.index(k) if k in KEY_ORDER else 99, k))
    if keys: items.append({'group': g, 'note': GROUP_NOTE.get(g, ''), 'items': [dict(key=k, **man[k]) for k in keys]})
data = json.dumps(items, ensure_ascii=False)

page = r'''<title>Wizard Scene Review</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* One column of clip cards in the app's own night-purple world (single dark theme by choice), grouped like the director's pool. */
:root {
  color-scheme: dark;
  --bg: #120a1e; --panel: #1c1230; --panel-2: #24183c; --line: #3b2657; --fg: #f3ebf7; --muted: #ab98ba;
  --accent: #ff4fd8; --cyan: #3fe8ff; --ok: #6be36b; --fix: #ff8d5c; --warn: #ffd21f;
  --display: "Archivo", "Segoe UI", system-ui, sans-serif; --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
}
body { background: var(--bg); color: var(--fg); font: 15px/1.5 var(--display); }
.wrap { max-width: 1440px; margin: 0 auto; padding-block: 28px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }
header { display: grid; gap: 12px; }
h1 { margin: 0; font-size: clamp(26px, 4vw, 40px); font-weight: 800; letter-spacing: -.01em; text-wrap: balance; }
h1 span { color: var(--accent); }
.lead { margin: 0; max-width: 76ch; color: var(--muted); }
.how { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.how div { background: var(--panel); border: 1px solid var(--line); padding: 12px 14px; font-size: 13.5px; color: var(--muted); }
.how b { display: block; color: var(--fg); font-size: 14px; margin-bottom: 2px; }
.tally { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-family: var(--mono); font-size: 13px; }
.pill { padding: 3px 10px; border: 1px solid var(--line); background: var(--panel); }
.pill.ok { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); }
.pill.fix { color: var(--fix); border-color: color-mix(in srgb, var(--fix) 45%, var(--line)); }
.save-note { font-size: 12.5px; color: var(--muted); }
nav.toc { display: flex; flex-wrap: wrap; gap: 8px; }
nav.toc a { font: 600 12.5px var(--mono); color: var(--cyan); text-decoration: none; padding: 4px 10px; background: var(--panel-2); }
nav.toc a:hover, nav.toc a:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
.group { display: grid; gap: 16px; }
.group > h2 { margin: 12px 0 0; font-size: 24px; font-weight: 800; }
.group > p { margin: 0; color: var(--muted); max-width: 80ch; }
.scene { background: var(--panel); border: 1px solid var(--line); display: grid; gap: 12px; padding: 18px; min-width: 0; }
.scene.ok { box-shadow: inset 4px 0 0 var(--ok); } .scene.fix { box-shadow: inset 4px 0 0 var(--fix); }
.top { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: baseline; justify-content: space-between; }
.top h3 { margin: 0; font-size: 19px; font-weight: 800; }
.top small { font: 400 12.5px var(--mono); color: var(--muted); }
.note { margin: 0; color: var(--muted); font-size: 14px; max-width: 90ch; }
.anim { overflow-x: auto; background: #0d0716; border: 1px solid var(--line); }
.anim video { display: block; width: 100%; min-width: 720px; height: auto; image-rendering: pixelated; }
.marks { display: flex; flex-wrap: wrap; gap: 6px; }
.marks button { font: 600 11.5px var(--mono); padding: 3px 9px; background: var(--panel-2); color: var(--cyan); border: 1px solid var(--line); cursor: pointer; }
.marks button:hover { border-color: var(--cyan); }
.verdict { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start; border-top: 1px dashed var(--line); padding-top: 14px; }
.verdict button { font: 600 14px var(--display); padding: 8px 16px; border: 1px solid var(--line); background: var(--panel-2); color: var(--fg); cursor: pointer; }
.verdict button:hover { border-color: var(--muted); }
.verdict button[aria-pressed="true"].ok { background: color-mix(in srgb, var(--ok) 22%, var(--panel-2)); border-color: var(--ok); }
.verdict button[aria-pressed="true"].fix { background: color-mix(in srgb, var(--fix) 22%, var(--panel-2)); border-color: var(--fix); }
button:focus-visible, textarea:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
.verdict button:disabled { opacity: .5; cursor: not-allowed; }
textarea { flex: 1 1 320px; min-height: 42px; resize: vertical; font: 14px var(--display); color: var(--fg); background: var(--bg); border: 1px solid var(--line); padding: 8px 10px; }
.status { font-size: 12.5px; color: var(--muted); align-self: center; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div class="wrap">
<header>
  <h1>Wizard scenes v2: <span>fights, trips and the new look</span></h1>
  <p class="lead">Everything new since the 11 approved scenes, in the new style from your sheet. The app's narrowest window is now 1280 px, so each clip is shown once, exactly as it will play. Watch, then mark each one.</p>
  <div class="how">
    <div><b>The bar</b>Dim when idle; filled segments light up from the right toward the pipe. Scene tints go under the segments and behind Quit.</div>
    <div><b>Chained runs first</b>The four runs you asked for, then every clip on its own. Chapter buttons under a run jump to each part.</div>
    <div><b>Not shown yet</b>Pokes (they react live in the app), sounds (slots wait for your OGG clips) and the Settings switches.</div>
    <div><b>What to look for</b>Anything that reads wrong: timing, a pose, text, a call-out, the hat or robe at the wrong moment.</div>
  </div>
  <div class="tally" id="tally"><span class="pill">Loading verdicts…</span></div>
  <nav class="toc" id="toc" aria-label="Sections"></nav>
</header>
<main id="groups" class="wrap" style="padding:0"></main>
</div>

<script>
const GROUPS = __DATA__;
const ALL = GROUPS.flatMap((g) => g.items);
const V = {};
let db = null;
const el = (t, cls, txt) => { const e = document.createElement(t); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

function build() {
  const toc = document.getElementById('toc'); toc.textContent = '';
  const root = document.getElementById('groups'); root.textContent = '';
  for (const g of GROUPS) {
    const a = el('a', null, `${g.group} (${g.items.length})`); a.href = '#' + slug(g.group); toc.append(a);
    const sec = el('section', 'group'); sec.id = slug(g.group);
    sec.append(el('h2', null, g.group)); if (g.note) sec.append(el('p', null, g.note));
    for (const s of g.items) sec.append(card(s));
    root.append(sec);
  }
}
function card(s) {
  const c = el('section', 'scene'); c.id = 'c-' + s.key; c.dataset.key = s.key;
  const top = el('div', 'top'); top.append(el('h3', null, s.title), el('small', null, `${s.key} · ${s.seconds} s`)); c.append(top);
  if (s.note) c.append(el('p', 'note', s.note));
  const box = el('div', 'anim'); const v = el('video'); v.src = s.video; v.poster = s.poster; v.muted = true; v.loop = true; v.playsInline = true; v.controls = true; v.preload = 'metadata';
  v.setAttribute('aria-label', s.title);
  box.append(v); c.append(box);
  if (s.marks && s.marks.length > 1) {
    const m = el('div', 'marks');
    for (const [f, label] of s.marks) { const b = el('button', null, `${(f / 30).toFixed(1)} s · ${label}`); b.type = 'button'; b.onclick = () => { v.currentTime = f / 30; v.play().catch(() => {}); }; m.append(b); }
    c.append(m);
  }
  const vd = el('div', 'verdict');
  const ok = el('button', 'ok', 'Looks right'), fix = el('button', 'fix', 'Needs a fix'); ok.type = fix.type = 'button';
  const note = el('textarea'); note.id = 'note-' + s.key; note.placeholder = 'What looks wrong? e.g. "hat flies off too late", "banner covers the goblin"';
  const st = el('span', 'status');
  ok.onclick = () => save(s.key, 'ok', note.value, st); fix.onclick = () => save(s.key, 'fix', note.value, st);
  note.onchange = () => { if ((V[s.key] || {}).status) save(s.key, V[s.key].status, note.value, st); };
  vd.append(ok, fix, note, st); c.append(vd);
  return c;
}
function paint() {
  for (const s of ALL) {
    const c = document.getElementById('c-' + s.key); if (!c) continue; const v = V[s.key] || {};
    c.classList.toggle('ok', v.status === 'ok'); c.classList.toggle('fix', v.status === 'fix');
    const [ok, fix] = c.querySelectorAll('.verdict button'); ok.setAttribute('aria-pressed', v.status === 'ok'); fix.setAttribute('aria-pressed', v.status === 'fix');
    ok.disabled = fix.disabled = !db;
    const note = c.querySelector('textarea'); note.disabled = !db; if (document.activeElement !== note && v.note != null) note.value = v.note;
    c.querySelector('.status').textContent = db ? (v.status ? 'Saved' : '') : 'Saving isn’t available in this view. Tell me in chat instead.';
  }
  const t = document.getElementById('tally'); t.textContent = '';
  const n = (k) => ALL.filter((s) => (V[s.key] || {}).status === k).length;
  t.append(el('span', 'pill ok', `${n('ok')} look right`), el('span', 'pill fix', `${n('fix')} need a fix`), el('span', 'pill', `${ALL.length - n('ok') - n('fix')} to review`));
  t.append(el('span', 'save-note', db ? 'Your marks save as you go; Claude reads them back.' : 'Marks can’t be saved here; reply in chat with fixes.'));
}
async function save(key, status, note, st) {
  if (!db) return;
  st.textContent = 'Saving…';
  try { await db.doc('verdicts2/' + key).set({ status, note: note.slice(0, 2000), at: new Date().toISOString() }); st.textContent = 'Saved'; }
  catch (e) { st.textContent = e && e.code === 'permission_denied' ? 'You can view this page but not mark clips.' : 'Couldn’t save. Try again.'; }
}
// play only what's on screen
const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => { for (const e of es) { const v = e.target; if (e.isIntersecting) v.play().catch(() => {}); else v.pause(); } }, { threshold: 0.4 }) : null;
build(); paint();
if (io) document.querySelectorAll('video').forEach((v) => io.observe(v));
(async () => {
  try { db = window.claude ? await window.claude.use('db') : null; } catch { db = null; }
  paint();
  if (!db) return;
  db.collection('verdicts2').onSnapshot((snap) => { for (const d of snap.docs) if (d.exists) V[d.id] = d.data(); paint(); }, () => paint());
})();
</script>
'''
open(os.path.join(D, 'index.html'), 'w').write(page.replace('__DATA__', data))
print(len(man), 'clips')
