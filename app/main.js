'use strict';
// HD Texture Toolkit: Electron main process (window, settings, native dialogs, tasks, tools).
const { app, BrowserWindow, ipcMain, dialog, shell, Menu, nativeTheme } = require('electron');
const fs = require('fs');
const os = require('os');
const path = require('path');
const https = require('https');
const tasks = require('./core/tasks');
const rtz = require('./core/rtz');

const APP_NAME = 'HD Texture Toolkit';
const WINDOW_TITLE = 'R64texHD - HD Texture Toolkit - RT64 Support';
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
  firstRunDone: false,
  dumpFolder: '', outputFolder: '', page: 'upscale',
  workers: 'auto', maxSize: 4096, texconv: '', realesrgan: '', realesrganModel: 'realesrgan-x4plus',
  upscale: { inputs: [], subfolders: true, method: 'standard', size: 4, fit: 2048, sharpness: 'normal', edges: 'clamp', hardAlpha: true,
    format: 'same', ddsFormat: 'auto', output: '', existing: 'overwrite', copyOther: true },
  convert: { input: '', format: 'png', ddsFormat: 'auto', output: '' },
  pack: { mode: 'pack', input: '', output: '', compression: 'zstd', level: 'balanced', lowMipCache: true },
  unpack: { input: '', output: '', keepCache: false },
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
    realesrganModel: settings.realesrganModel,
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
    width: 1280, height: 800, minWidth: 1100, minHeight: 700, show: false,
    title: WINDOW_TITLE, backgroundColor: '#0b1022', autoHideMenuBar: true,
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false },
  });
  win.loadFile(path.join(__dirname, 'ui', 'index.html'));
  win.once('ready-to-show', () => win.show());
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
  const fn = { upscale: tasks.upscaleTask, convert: tasks.convertTask, pack: tasks.packTask, unpack: tasks.unpackTask }[task];
  (async () => {
    try {
      const p = { ...params };
      if (task === 'upscale') p.maxSize = settings.maxSize;
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

const TOOL_URLS = {
  texconv: 'https://github.com/microsoft/DirectXTex/releases/latest/download/texconv.exe',
  realesrgan: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip',
};

async function installTool(name) {
  const progress = (got, total) => send('tool:progress', { name, got, total });
  if (name === 'texconv') {
    await download(TOOL_URLS.texconv, path.join(toolsDir(), 'texconv.exe'), progress);
  } else if (name === 'realesrgan') {
    const zip = path.join(TEMP_DIR, 'htk-realesrgan.zip');
    await download(TOOL_URLS.realesrgan, zip, progress);
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
function registerIpc() {
  ipcMain.handle('preview:list', (_e, { inputs, subfolders }) => tasks.previewList(inputs, subfolders));
  ipcMain.handle('preview', (_e, req) => requestPreview({ ...req, maxSize: settings.maxSize }));
  ipcMain.handle('state', () => ({ settings, dataDir: DATA_DIR, dataWritable, tools: tools(), version: app.getVersion(), platform: process.platform, cpus: os.cpus().length, workers: workerCount(), running: running && running.task }));
  ipcMain.handle('settings:save', (_e, s) => { settings = { ...settings, ...s }; saveSettings(); return true; });
  ipcMain.handle('dialog', async (_e, { kind, title, defaultPath }) => {
    const base = { title, defaultPath: defaultPath || settings.outputFolder || undefined };
    let r;
    if (kind === 'folder') r = await dialog.showOpenDialog(win, { ...base, properties: ['openDirectory', 'createDirectory'] });
    else if (kind === 'images') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile', 'multiSelections'], filters: [{ name: 'Textures', extensions: ['png', 'dds'] }] });
    else if (kind === 'open-rtz') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'RT64 texture pack', extensions: ['rtz'] }, { name: 'All files', extensions: ['*'] }] });
    else if (kind === 'exe') r = await dialog.showOpenDialog(win, { ...base, properties: ['openFile'], filters: [{ name: 'Programs', extensions: process.platform === 'win32' ? ['exe'] : ['*'] }] });
    else if (kind === 'save-rtz') {
      const s = await dialog.showSaveDialog(win, { ...base, filters: [{ name: 'RT64 texture pack', extensions: ['rtz'] }] });
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
  ipcMain.handle('open', (_e, p) => { if (fs.existsSync(p) && fs.statSync(p).isFile()) shell.showItemInFolder(p); else shell.openPath(p); return true; });
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
    if (!dataWritable) {
      dialog.showMessageBox(win, { type: 'warning', title: WINDOW_TITLE, message: 'This folder is read-only.',
        detail: `Settings and downloads cannot be saved in ${DATA_DIR}.\nMove the HD Texture Toolkit folder somewhere you can write to (for example C:\\Tools or your Documents).` });
    }
    selfTest();
  });
  app.on('window-all-closed', () => { cancelTask(); app.quit(); });
  app.on('will-quit', () => { try { fs.rmSync(TEMP_DIR, { recursive: true, force: true }); } catch { /* in use */ } });
}
