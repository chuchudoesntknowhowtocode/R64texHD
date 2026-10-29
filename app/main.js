'use strict';
// HD Texture Toolkit: Electron main process (window, settings, native dialogs, tasks, tools).
// R64texHD - Copyright (C) 2026 R64texHD contributors. GPL-2.0-or-later (see LICENSE).
const { app, BrowserWindow, ipcMain, dialog, shell, Menu, nativeTheme, Notification } = require('electron');
const fs = require('fs');
const os = require('os');
const path = require('path');
const https = require('https');
const tasks = require('./core/tasks');
const rtz = require('./core/rtz');

const APP_NAME = 'R64texHD';
const REPO_URL = 'https://github.com/chuchudoesntknowhowtocode/R64texHD';
const WINDOW_TITLE = `R64texHD v${app.getVersion()} - HD textures for N64 games`;
app.setName(APP_NAME);
app.setAppUserModelId('HDTextureToolkit');
nativeTheme.themeSource = 'dark';

// ---------------------------------------------------------------- portable data folder
// Everything the toolkit writes (settings, downloaded tools, Chromium's own cache and
// state, temporary files) lives in a "data" folder next to the program, never in AppData.
// Moving or deleting the toolkit folder takes all of it along.
const DATA_DIR = process.env.HTK_DATA
  || (app.isPackaged ? path.join(path.dirname(process.execPath), 'data') : path.join(__dirname, '..', 'data'));
let dataWritable = true;
try {
  fs.mkdirSync(path.join(DATA_DIR, 'temp'), { recursive: true });
  fs.accessSync(DATA_DIR, fs.constants.W_OK);
} catch { dataWritable = false; }
// Read-only location (e.g. inside Program Files): the window engine still needs somewhere to
// write, so it uses a throwaway temp folder for this session; the user is told to move the toolkit.
const CHROMIUM_DIR = dataWritable ? path.join(DATA_DIR, 'chromium') : path.join(os.tmpdir(), 'HD Texture Toolkit (read-only copy)');
for (const key of ['userData', 'sessionData', 'crashDumps', 'logs']) {
  try { app.setPath(key, key === 'userData' || key === 'sessionData' ? CHROMIUM_DIR : path.join(CHROMIUM_DIR, key)); } catch { /* path type not available */ }
}
// Temporary files (texconv / Real-ESRGAN scratch, Chromium temp) go to data\temp too.
const TEMP_DIR = path.join(DATA_DIR, 'temp');
// (Windows only: on Linux, Chromium's single-instance socket lives in the temp folder and a long
// path there exceeds the socket path limit.)
if (dataWritable && process.platform === 'win32') { process.env.TEMP = TEMP_DIR; process.env.TMP = TEMP_DIR; }

const settingsFile = () => path.join(DATA_DIR, 'settings.json');
const toolsDir = () => path.join(DATA_DIR, 'tools');
const programDir = () => (app.isPackaged ? path.dirname(process.execPath) : path.join(__dirname, '..'));

const DEFAULTS = {
  firstRunDone: false, checkTools: true, iconStamp: '',
  dumpFolder: '', outputFolder: '', page: 'upscale',
  workers: 'auto', maxSize: 4096, texconv: '', realesrgan: '', realesrganModel: 'realesrgan-x4plus', aiGpu: 'auto', aiTile: 'auto',
  splash: true, cleanPhrases: false,
  upscale: { inputs: [], subfolders: true, method: 'standard', size: 4, fit: 2048, sharpness: 'normal', edges: 'auto', hardAlpha: true,
    format: 'same', ddsFormat: 'auto', output: '', existing: 'overwrite', copyOther: true, keepCoverage: true },
  convert: { input: '', format: 'png', ddsFormat: 'auto', output: '', wrapInfo: true, rice: true, onlyNew: false },
  pack: { mode: 'pack', input: '', output: '', compression: 'zstd', level: 'balanced', lowMipCache: true,
    recomp: false, recompName: '', recompAuthor: '', recompVersion: '1.0.0', recompDescription: '', recompThumb: '', recompToggle: true },
  unpack: { input: '', output: '', keepCache: false },
  check: { input: '' },
  ports: { mode: 'extract', archive: '', output: '', hdInput: '', base: '', modOutput: '', alt: true, compression: 'store' },
  legacy: { mode: 'import', input: '', dumpDb: '', output: '', htsInput: '', htsName: '', htsOutput: '', riceInput: '', base: '', modOutput: '' },
  roms: { folder: '' },
};

function loadSettings() {
  const s = JSON.parse(JSON.stringify(DEFAULTS));
  try {
    const saved = JSON.parse(fs.readFileSync(settingsFile(), 'utf8'));
    for (const [k, v] of Object.entries(saved)) {
      if (v && typeof v === 'object' && !Array.isArray(v) && typeof s[k] === 'object' && !Array.isArray(s[k])) Object.assign(s[k], v);
      else s[k] = v;
    }
  } catch { /* first run */ }
  return s;
}
let settings;
function saveSettings() {
  if (!dataWritable) return;
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(settingsFile() + '.part', JSON.stringify(settings, null, 2));
  fs.renameSync(settingsFile() + '.part', settingsFile());
}

function findTool(configured, candidates) {
  for (const c of [configured, ...candidates]) if (c && fs.existsSync(c)) return c;
  return '';
}
function tools() {
  const exe = process.platform === 'win32' ? '.exe' : '';
  return {
    texconv: findTool(settings.texconv, [path.join(toolsDir(), 'texconv.exe'), path.join(programDir(), 'tools', 'texconv.exe')]),
    realesrgan: findTool(settings.realesrgan, [path.join(toolsDir(), 'realesrgan', 'realesrgan-ncnn-vulkan' + exe),
      path.join(programDir(), 'tools', 'realesrgan', 'realesrgan-ncnn-vulkan' + exe)]),
    realesrganModel: settings.realesrganModel, aiGpu: settings.aiGpu, aiTile: settings.aiTile,
  };
}
function workerCount() {
  const cpus = os.cpus().length || 2;
  if (settings.workers === 'one') return 1;
  if (settings.workers === 'half') return Math.max(1, cpus >> 1);
  return Math.max(1, Math.min(cpus - 1, 8));
}

let win = null;
function send(channel, payload) { if (win && !win.isDestroyed()) win.webContents.send(channel, payload); }

function createWindow() {
  win = new BrowserWindow({
    width: 1280, height: 800, minWidth: 1280, minHeight: 700, show: false,
    title: WINDOW_TITLE, backgroundColor: '#130a22', autoHideMenuBar: true,
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false, autoplayPolicy: 'no-user-gesture-required' },
  });
  win.loadFile(path.join(__dirname, 'ui', 'index.html'));
  win.once('ready-to-show', () => win.show());
  win.on('page-title-updated', (e) => e.preventDefault());   // keep the title with the version
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (e) => e.preventDefault());
  win.on('close', (e) => {
    if (running && !quitting) {
      e.preventDefault();
      const choice = dialog.showMessageBoxSync(win, { type: 'warning', buttons: ['Keep working', 'Cancel and close'], defaultId: 0, cancelId: 0,
        title: WINDOW_TITLE, message: 'A task is still running.', detail: 'Closing now cancels it.' });
      if (choice === 1) { quitting = true; cancelTask(); setTimeout(() => win.close(), 300); }
    }
  });
}

// ---------------------------------------------------------------- tasks
let running = null, quitting = false;
function cancelTask() { if (running) running.cancel(); }

async function runTask(task, params) {
  if (running) return { ok: false, error: 'A task is already running.' };
  const hooks = [];
  let cancelledFlag = false, lastProgress = 0;
  const ctx = {
    workers: workerCount(),
    cancelled: () => cancelledFlag,
    onCancel: (fn) => hooks.push(fn),
    log: (text) => send('task:log', text),
    progress: (done, total, message) => {
      const now = Date.now();
      if (now - lastProgress > 80 || done === total) { lastProgress = now; send('task:progress', { done, total, message }); }
    },
  };
  running = { task, cancel: () => { cancelledFlag = true; hooks.splice(0).forEach((f) => { try { f(); } catch { /* ignore */ } }); } };
  send('task:started', { task });
  const t = tools();
  const fn = { upscale: tasks.upscaleTask, convert: tasks.convertTask, pack: tasks.packTask, pipeline: tasks.pipelineTask, watch: tasks.watchTask, unpack: tasks.unpackTask, check: tasks.checkTask, fix: tasks.fixTask,
    o2rExtract: tasks.o2rExtractTask, o2rBuild: tasks.o2rBuildTask,
    legacyImport: tasks.legacyImportTask, legacyHts: tasks.legacyHtsTask, riceToO2r: tasks.riceToO2rTask, roms: tasks.romsTask }[task];
  if (!fn) { running = null; return { ok: false, error: 'This part arrives in the next build. Hang tight!' }; }
  (async () => {
    try {
      const p = { ...params };
      if (task === 'upscale' || task === 'pipeline' || task === 'watch') p.maxSize = settings.maxSize;
      const result = await fn(p, ctx, t);
      send('task:done', { task, result });
    } catch (e) {
      send('task:done', { task, error: e.cancelled || cancelledFlag ? 'Cancelled' : (e.message || String(e)) });
    } finally {
      running = null;
    }
  })();
  return { ok: true };
}

// ---------------------------------------------------------------- tool downloads
function download(url, dest, onProgress, redirects = 0) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': APP_NAME } }, (res) => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location && redirects < 8) {
        res.resume();
        resolve(download(new URL(res.headers.location, url).toString(), dest, onProgress, redirects + 1));
        return;
      }
      if (res.statusCode !== 200) { res.resume(); reject(new Error(`download failed (HTTP ${res.statusCode})`)); return; }
      const total = Number(res.headers['content-length'] || 0);
      let got = 0;
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      const out = fs.createWriteStream(dest + '.part');
      res.on('data', (d) => { got += d.length; onProgress(got, total); });
      res.pipe(out);
      out.on('finish', () => out.close(() => { fs.renameSync(dest + '.part', dest); resolve(dest); }));
      out.on('error', reject);
      res.on('error', reject);
    }).on('error', reject);
  });
}

// Helper tools: pinned versions, checked against their SHA-256 after download. To add a tool, add it here
// and to TOOL_INFO in ui/index.html (the Settings page and the startup check pick it up from there).
const TOOL_URLS = {
  texconv: { url: 'https://github.com/microsoft/DirectXTex/releases/download/may2026/texconv.exe',
    sha256: 'dcfdec10244e02cf5037fba089c55fb7e1326b1c8181742d77d15fa5cb5eef06' },
  realesrgan: { url: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip',
    sha256: 'abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d' },
};
function checkSha(file, want) {
  const got = require('crypto').createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if (got !== want) { fs.rmSync(file, { force: true }); throw new Error('the download did not match the expected file (checksum). Try again later.'); }
}

async function installTool(name) {
  const progress = (got, total) => send('tool:progress', { name, got, total });
  if (name === 'texconv') {
    const tmp = path.join(TEMP_DIR, 'htk-texconv.exe');
    await download(TOOL_URLS.texconv.url, tmp, progress);
    checkSha(tmp, TOOL_URLS.texconv.sha256);
    fs.mkdirSync(toolsDir(), { recursive: true });
    fs.copyFileSync(tmp, path.join(toolsDir(), 'texconv.exe'));
    fs.rmSync(tmp, { force: true });
  } else if (name === 'realesrgan') {
    const zip = path.join(TEMP_DIR, 'htk-realesrgan.zip');
    await download(TOOL_URLS.realesrgan.url, zip, progress);
    checkSha(zip, TOOL_URLS.realesrgan.sha256);
    const dir = path.join(toolsDir(), 'realesrgan');
    for (const e of rtz.readEntries(zip)) {
      const target = path.resolve(dir, e.name);
      if (!target.startsWith(path.resolve(dir) + path.sep)) continue;
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, rtz.readEntry(zip, e));
    }
    fs.rmSync(zip, { force: true });
  }
  return tools();
}

// ---------------------------------------------------------------- footer scenes: the rest download once
// The release build ships the starter set (classic scenes, peeks) plus assets/scenes/remote.json naming the
// pack with the fights and trips (made by build/package.sh, attached to the GitHub release next to the exe).
// It downloads in the background a little after start-up, into data\scenes; a failed try is repeated later.
const scenes = require('./core/scenes');
const SCENES_APP = path.join(__dirname, 'assets', 'scenes');
const SCENES_DATA = path.join(DATA_DIR, 'scenes');
let sceneDl = { state: 'idle' };
async function downloadScenes(now = false) {
  if (sceneDl.state === 'busy') return;
  let remote; try { remote = JSON.parse(fs.readFileSync(path.join(SCENES_APP, 'remote.json'), 'utf8')); } catch { sceneDl = { state: 'none' }; return; }
  const need = scenes.missing(SCENES_APP, SCENES_DATA);
  if (!need.length) { sceneDl = { state: 'done' }; return; }
  sceneDl = { state: 'busy', got: 0, total: remote.size || 0 };
  const zip = path.join(TEMP_DIR, 'htk-scenes.zip');
  try {
    await download(remote.url, zip, (got, total) => { sceneDl = { state: 'busy', got, total: total || remote.size || 0 }; });
    checkSha(zip, remote.sha256);
    const r = scenes.install(rtz.readEntries(zip).map((e) => ({ name: e.name, data: () => rtz.readEntry(zip, e) })), SCENES_DATA);
    sceneDl = { state: 'done', clips: r.clips };
    send('scenes:updated', sceneDl);
  } catch (e) {
    sceneDl = { state: 'failed', error: e.message, at: Date.now() };
    send('scenes:updated', sceneDl);
    if (!now) setTimeout(() => downloadScenes(), 10 * 60000);           // try again in 10 minutes
  } finally { fs.rmSync(zip, { force: true }); }
}

// ---------------------------------------------------------------- desktop shortcut (Windows)
// Only a Desktop shortcut: the Start menu folder is inside AppData, which a portable tool leaves alone.
function createShortcuts() {
  if (process.platform !== 'win32') return { ok: false, error: 'Shortcuts are created on Windows.' };
  const lnk = path.join(app.getPath('desktop'), `${APP_NAME}.lnk`);
  const ok = shell.writeShortcutLink(lnk, fs.existsSync(lnk) ? 'replace' : 'create', {
    target: process.execPath, cwd: path.dirname(process.execPath), icon: process.execPath, iconIndex: 0,
    description: 'Upscale, convert, pack and unpack textures', appUserModelId: 'HDTextureToolkit',
  });
  return { ok, made: ok ? [lnk] : [] };
}

// ---------------------------------------------------------------- Windows icon refresh
// Explorer caches exe icons by path, so an updated R64texHD.exe unzipped over an older copy keeps
// showing the old icon. Once per new build (exe size + date), ask Windows to refresh its icon cache
// and re-save our Desktop shortcut so it picks up the current icon too.
function refreshWindowsIcon() {
  if (process.platform !== 'win32' || !app.isPackaged) return;
  let stamp = '';
  try { const st = fs.statSync(process.execPath); stamp = `${st.size}-${Math.round(st.mtimeMs)}`; } catch { return; }
  if (settings.iconStamp === stamp) return;
  settings.iconStamp = stamp;
  saveSettings();
  try {
    const lnk = path.join(app.getPath('desktop'), `${APP_NAME}.lnk`);
    if (fs.existsSync(lnk) && path.resolve(shell.readShortcutLink(lnk).target) === path.resolve(process.execPath)) createShortcuts();
  } catch { /* not our shortcut */ }
  try {
    const ie4uinit = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'ie4uinit.exe');
    const arg = /^6\.[0-2]\./.test(os.release()) ? '-ClearIconCache' : '-show';   // Windows 7/8 vs 10/11
    if (fs.existsSync(ie4uinit)) require('child_process').spawn(ie4uinit, [arg], { detached: true, stdio: 'ignore', windowsHide: true }).unref();
  } catch { /* cosmetic only */ }
}

// ---------------------------------------------------------------- live preview
// Only the newest request matters: if one is waiting when another arrives, the older one is
// answered { superseded: true } and dropped; the one being rendered finishes normally.
let previewBusy = false, previewNext = null;
function requestPreview(req) {
  return new Promise((resolve) => {
    if (previewNext) previewNext.resolve({ superseded: true });
    previewNext = { req, resolve };
    pumpPreview();
  });
}
async function pumpPreview() {
  if (previewBusy || !previewNext) return;
  const { req, resolve } = previewNext;
  previewNext = null;
  previewBusy = true;
  try { resolve(await tasks.preview(req, tools())); }
  catch (e) { resolve({ error: e.message || String(e) }); }
  finally { previewBusy = false; pumpPreview(); }
}

// ---------------------------------------------------------------- IPC
const SAVE_KINDS = {
  'save-rtz': { name: 'RT64 texture pack', extensions: ['rtz'] },
  'save-o2r': { name: 'Ship port mod', extensions: ['o2r'] },
  'save-hts': { name: 'GLideN64 texture pack', extensions: ['hts'] },
};
// A small picture (PNG, up to 4 MB) as a data URL, for the Recomp mod picture preview.
function thumbnail(p) {
  try {
    if (!p || !/\.png$/i.test(p)) return null;
    const st = fs.statSync(p);
    if (!st.isFile() || st.size > 4 * 1048576) return null;
    return 'data:image/png;base64,' + fs.readFileSync(p).toString('base64');
  } catch { return null; }
}
function registerIpc() {
  ipcMain.handle('thumbnail', (_e, p) => thumbnail(p));
  ipcMain.handle('rom:info', async (_e, file) => { try { return await tasks.romInfo(file); } catch (e) { return { error: e.message || String(e) }; } });
  // 4 · Ship Mods: the N64 game behind a port archive, mod or texture folder (reads the archive's version file).
  // 4 · Ship Mods: find the installed Harbour Masters ports (folder listings only; see core/shipfind.js).
  ipcMain.handle('ship:find', async (_e, seeds) => {
    try {
      const shipfind = require('./core/shipfind');
      const roots = process.env.HTK_SHIPFIND_ROOTS ? process.env.HTK_SHIPFIND_ROOTS.split(';').filter(Boolean).map((dir) => ({ dir, depth: 4 })) : shipfind.defaultRoots();
      return await shipfind.find({ roots, seeds: (seeds || []).filter((x) => typeof x === 'string' && x) });
    } catch (e) { return { error: e.message || String(e) }; }
  });
  // Every toggle, Check again and search: is each port's game archive there, and made by the installed build?
  ipcMain.handle('ship:check', (_e, { ports, target } = {}) => {
    try {
      const sc = require('./core/shipcheck');
      const checked = Array.isArray(ports) ? sc.checkPorts(ports) : null;
      return { ports: checked, target: target ? sc.checkTarget(target, checked || []) : null };
    } catch (e) { return { error: e.message || String(e) }; }
  });
  ipcMain.handle('ship:identify', (_e, file) => { try { return require('./core/shipid').identify(file); } catch (e) { return { error: e.message || String(e) }; } });
  ipcMain.handle('preview:list', (_e, { inputs, subfolders }) => tasks.previewList(inputs, subfolders));
  ipcMain.handle('preview', (_e, req) => requestPreview({ ...req, maxSize: settings.maxSize }));
  ipcMain.handle('upscale:estimate', (_e, req) => tasks.estimate({ ...req, maxSize: settings.maxSize }, tools(), Math.max(1, workerCount() - 1)).catch((e) => ({ error: e.message })));
  // Footer scenes (app/assets/scenes, made by build/wizard/export_app.py) and the owner's sound clips.
  const SCENES = SCENES_APP;
  ipcMain.handle('scenes:index', () => {
    try { const r = scenes.index(SCENES, SCENES_DATA); return { stage: JSON.parse(fs.readFileSync(path.join(SCENES, 'stage.json'), 'utf8')), ...r, download: sceneDl }; }
    catch (e) { return { error: e.message }; }
  });
  ipcMain.handle('scenes:download', () => { downloadScenes(true); return sceneDl; });
  ipcMain.handle('scenes:clip', (_e, id) => {
    if (typeof id !== 'string' || !/^[a-z0-9_]+$/.test(id)) return { error: 'bad clip id' };
    try { return JSON.parse(fs.readFileSync(scenes.clipFile(id, SCENES, SCENES_DATA), 'utf8')); } catch (e) { return { error: e.message }; }
  });
  // Sound slots: <slot>.ogg in the data folder's "sounds" (yours) or app/assets/sounds (shipped). Missing = silent.
  ipcMain.handle('sounds:list', () => {
    const out = {};
    for (const dir of [path.join(__dirname, 'assets', 'sounds'), path.join(DATA_DIR, 'sounds')]) {
      let names = []; try { names = fs.readdirSync(dir); } catch { continue; }
      for (const n of names) if (/\.ogg$/i.test(n)) out[n.replace(/\.ogg$/i, '').toLowerCase()] = require('url').pathToFileURL(path.join(dir, n)).href;
    }
    return out;
  });
  // Background music: app/assets/music (shipped) and the data folder's "music" (yours). Names starting with
  // "dmt" play in Psychedelic mode, everything else in the normal playlist.
  const AUDIO_EXT = /\.(ogg|opus|mp3|wav|flac|m4a)$/i;
  const userDir = (name) => { const d = path.join(DATA_DIR, name); try { fs.mkdirSync(d, { recursive: true }); } catch { /* read-only */ } return d; };
  ipcMain.handle('audio:info', () => {
    const url = (f) => require('url').pathToFileURL(f).href;
    const music = [];
    for (const [dir, custom] of [[path.join(__dirname, 'assets', 'music'), false], [userDir('music'), true]]) {
      let names = []; try { names = fs.readdirSync(dir).sort(); } catch { continue; }
      for (const n of names) if (AUDIO_EXT.test(n)) music.push({ name: n, url: url(path.join(dir, n)), mode: /^dmt/i.test(n) ? 'dmt' : 'standard', custom });
    }
    const sfx = {}, yours = [];
    for (const [dir, custom] of [[path.join(__dirname, 'assets', 'sounds'), false], [userDir('sounds'), true]]) {
      let names = []; try { names = fs.readdirSync(dir); } catch { continue; }
      for (const n of names) if (AUDIO_EXT.test(n)) { const slot = n.replace(AUDIO_EXT, '').toLowerCase(); sfx[slot] = url(path.join(dir, n)); if (custom) yours.push(slot); }
    }
    return { music, sfx, customSfx: yours, dirs: { music: userDir('music'), sounds: userDir('sounds') } };
  });
  ipcMain.handle('music:add', async () => {
    if (process.env.HTK_SELFTEST) { (global.dialogs = global.dialogs || []).push('music'); return { added: 0 }; }
    const r = await dialog.showOpenDialog(win, { title: 'Add music', properties: ['openFile', 'multiSelections'],
      filters: [{ name: 'Music', extensions: ['ogg', 'opus', 'mp3', 'wav', 'flac', 'm4a'] }] });
    if (r.canceled) return { added: 0 };
    const dir = userDir('music'); let added = 0;
    for (const f of r.filePaths) { try { fs.copyFileSync(f, path.join(dir, path.basename(f))); added++; } catch { /* skip */ } }
    return { added };
  });
  // Graphics cards for the Real-ESRGAN row: name, video memory, Vulkan driver (Windows).
  ipcMain.handle('gpu:info', async () => { try { return await require('./core/gpuinfo').detect(); } catch (e) { return { ok: false, gpus: [], error: e.message }; } });
  // Queue finished: a Windows notification (clicking it brings the window back) and a taskbar flash.
  ipcMain.handle('notify', (_e, title, body) => {
    if (process.env.HTK_SELFTEST) { (global.notified = global.notified || []).push(title); return true; }
    try {
      if (Notification.isSupported()) { const n = new Notification({ title, body, icon: path.join(__dirname, 'assets', 'icon.ico') }); n.on('click', () => { if (win) { win.show(); win.focus(); } }); n.show(); }
      if (win && !win.isFocused()) win.flashFrame(true);
    } catch { /* ignore */ }
    return true;
  });
  // The Windows taskbar button shows the footer bar too (red when a job fails).
  ipcMain.handle('taskbar', (_e, p, mode) => { try { if (win && !win.isDestroyed()) win.setProgressBar(typeof p === 'number' ? p : -1, { mode: mode === 'error' ? 'error' : 'normal' }); } catch { /* ignore */ } return true; });
  ipcMain.handle('state', () => ({ settings, dataDir: DATA_DIR, dataWritable, tools: tools(), version: app.getVersion(), platform: process.platform, cpus: os.cpus().length, workers: workerCount(), running: running && running.task, shipPorts: require('./core/shipid').ports() }));
  ipcMain.handle('settings:save', (_e, s) => { settings = { ...settings, ...s }; saveSettings(); return true; });
  ipcMain.handle('dialog', async (_e, { kind, title, defaultPath }) => {
    if (process.env.HTK_SELFTEST) { (global.dialogs = global.dialogs || []).push(kind); return null; }   // self-test: note it, don't block on a window
    const base = { title, defaultPath: defaultPath || settings.outputFolder || undefined };
    let r;
    if (kind === 'folder') r = await dialog.showOpenDialog(win, { ...base, properties: ['openDirectory', 'createDirectory'] });
    else if (kind === 'images') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile', 'multiSelections'], filters: [{ name: 'Textures', extensions: ['png', 'dds'] }] });
    else if (kind === 'open-rtz') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'RT64 texture pack', extensions: ['rtz'] }, { name: 'All files', extensions: ['*'] }] });
    else if (kind === 'exe') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'Programs', extensions: process.platform === 'win32' ? ['exe'] : ['*'] }] });
    else if (kind === 'image') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'Picture', extensions: ['png'] }] });
    else if (kind === 'open-o2r') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'Game archive', extensions: ['o2r', 'otr'] }, { name: 'All files', extensions: ['*'] }] });
    else if (kind === 'open-hts') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'GLideN64 texture pack', extensions: ['hts', 'htc'] }, { name: 'All files', extensions: ['*'] }] });
    else if (SAVE_KINDS[kind]) {
      const s = await dialog.showSaveDialog(win, { ...base, filters: [SAVE_KINDS[kind]] });
      return s.canceled ? null : s.filePath;
    }
    if (!r || r.canceled || !r.filePaths.length) return null;
    return kind === 'images' ? r.filePaths : r.filePaths[0];
  });
  ipcMain.handle('inspect', (_e, { kind, value }) => {
    try { return tasks.inspect(kind, value); } catch (e) { return { state: 'error', title: 'Could not read this', text: e.message }; }
  });
  ipcMain.handle('task:run', (_e, { task, params }) => runTask(task, params));
  ipcMain.handle('task:cancel', () => { cancelTask(); return true; });
  ipcMain.handle('open', (_e, p) => {
    if (process.env.HTK_SELFTEST) { (global.opened = global.opened || []).push(p); return true; }   // self-test: note it, don't open windows
    if (!p || !fs.existsSync(p)) return false;
    if (fs.statSync(p).isFile()) shell.showItemInFolder(p); else shell.openPath(p);
    return true;
  });
  ipcMain.handle('repo', () => { shell.openExternal(REPO_URL); return REPO_URL; });
  ipcMain.handle('shortcuts', () => createShortcuts());
  ipcMain.handle('tool:install', async (_e, name) => { try { return { ok: true, tools: await installTool(name) }; } catch (e) { return { ok: false, error: e.message }; } });
  ipcMain.handle('quit', () => { if (running) cancelTask(); quitting = true; setTimeout(() => app.quit(), 200); return true; });
}

// Test hook: HTK_SELFTEST=<script> runs a Node script with access to the window (used by the build's UI tests).
async function selfTest() {
  if (!process.env.HTK_SELFTEST) return;
  try { await require(path.resolve(process.env.HTK_SELFTEST))({ app, win, settings }); }
  catch (e) { console.error('SELFTEST FAILED', e); app.exit(1); }
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(() => {
    settings = loadSettings();
    registerIpc();
    createWindow();
    refreshWindowsIcon();
    if (!dataWritable) {
      dialog.showMessageBox(win, { type: 'warning', title: WINDOW_TITLE, message: 'This folder is read-only.',
        detail: `Settings and downloads cannot be saved in ${DATA_DIR}.\nMove the R64texHD folder somewhere you can write to (for example C:\\Tools or your Documents).` });
    }
    selfTest();
    if (!process.env.HTK_SELFTEST) setTimeout(() => downloadScenes(), 15000);   // after the splash, quietly
  });
  app.on('window-all-closed', () => { cancelTask(); app.quit(); });
  app.on('will-quit', () => { try { fs.rmSync(TEMP_DIR, { recursive: true, force: true }); } catch { /* in use */ } });
}
