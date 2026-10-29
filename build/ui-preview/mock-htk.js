// Stand-in for the app bridge (preload.js) so the launcher page can be opened in a normal browser
// with made-up data. Used only to make UI previews and screenshots; it is not shipped.
(() => {
  const listeners = { started: [], progress: [], log: [], done: [], tool: [] };
  const on = (k) => (fn) => { listeners[k].push(fn); return () => {}; };
  const emit = (k, v) => listeners[k].forEach((f) => f(v));
  const q = new URLSearchParams(location.search);
  const noTools = q.has('notools');

  // A small N64-style brick texture, and a smooth 8x version of it for the "upscaled" side.
  function brick(w, h) {
    const d = new Uint8Array(w * h * 4);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const row = Math.floor(y / 8), off = row % 2 ? 8 : 0, bx = (x + off) % 16, by = y % 8;
      const mortar = bx === 0 || by === 0;
      const n = ((x * 73856093) ^ (y * 19349663)) & 31;
      const i = (y * w + x) * 4;
      if (mortar) { d[i] = 120 + n; d[i + 1] = 112 + n; d[i + 2] = 98 + n; }
      else { d[i] = 150 + n * 2; d[i + 1] = 64 + n; d[i + 2] = 40 + (n >> 1); }
      d[i + 3] = 255;
    }
    return { width: w, height: h, data: d };
  }
  function smoothUp(img, k) {
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(img.data), img.width, img.height), 0, 0);
    const o = document.createElement('canvas'); o.width = img.width * k; o.height = img.height * k;
    const g = o.getContext('2d'); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    g.filter = 'contrast(1.08) saturate(1.1)'; g.drawImage(c, 0, 0, o.width, o.height);
    const id = g.getImageData(0, 0, o.width, o.height);
    return { width: o.width, height: o.height, data: new Uint8Array(id.data.buffer) };
  }

  const settings = {
    firstRunDone: !q.has('setup'), checkTools: true, page: q.get('page') || 'upscale', dumpFolder: 'D:\\N64\\RT64 dumps\\Majora', outputFolder: 'D:\\N64\\HD',
    workers: 'auto', maxSize: 4096, realesrganModel: 'realesrgan-x4plus', splash: q.has('splash'),
    upscale: { inputs: ['D:\\N64\\HD\\majora-textures'], subfolders: true, method: 'standard', size: 4, fit: 2048, sharpness: 'normal', edges: 'auto', hardAlpha: true,
      format: 'dds', ddsFormat: 'auto', output: 'D:\\N64\\HD\\majora-textures-upscaled', existing: 'overwrite', copyOther: true, keepCoverage: true },
    convert: { input: 'D:\\N64\\RT64 dumps\\Majora', format: 'png', ddsFormat: 'auto', output: 'D:\\N64\\HD\\Majora-textures', wrapInfo: true, rice: true, onlyNew: true },
    pack: { mode: q.get('mode') || 'pack', input: 'D:\\N64\\HD\\majora-textures-upscaled', output: 'D:\\N64\\HD\\Majora HD.rtz', compression: 'zstd', level: 'balanced', lowMipCache: true,
      recomp: true, recompName: 'Majora HD Reimagined', recompAuthor: 'chuchu', recompVersion: '1.0.0', recompDescription: 'Every texture in Termina, redone in HD.', recompThumb: 'D:\\N64\\HD\\thumb.png', recompToggle: true },
    unpack: { input: '', output: '', keepCache: false },
    check: { input: 'D:\\N64\\HD\\Majora HD.rtz' },
    ports: { mode: q.get('mode') || 'extract', archive: q.get('ship') === 'ghost' ? 'C:\\Games\\Ghostship\\sm64.o2r' : 'C:\\Games\\2Ship\\mm.o2r', output: 'D:\\N64\\HD\\mm-textures', hdInput: 'D:\\N64\\HD\\mm-textures-upscaled',
      base: 'C:\\Games\\2Ship\\mm.o2r', modOutput: 'C:\\Games\\2Ship\\mods\\Majora HD.o2r', alt: true, compression: 'store' },
    legacy: { mode: q.get('mode') || 'import', input: 'D:\\Packs\\THE LEGEND OF ZELDA_HIRESTEXTURES.hts', output: 'D:\\N64\\HD\\OoT Reloaded-rt64',
      htsInput: 'D:\\N64\\HD\\majora-textures-upscaled', htsName: 'ZELDA MAJORA\'S MASK', htsOutput: 'D:\\N64\\HD\\ZELDA MAJORA\'S MASK_HIRESTEXTURES.hts',
      riceInput: 'D:\\Packs\\Djipi Cel-Shaded\\ZELDA MAJORA\'S MASK', base: 'C:\\Games\\2Ship\\mm.o2r', modOutput: 'C:\\Games\\2Ship\\mods\\Celda.o2r' },
    roms: { folder: q.has('noroms') ? '' : 'D:\\N64\\ROMs' },
  };
  const INSPECT = {
    upscale: ['ready', 'Ready', '4,812 images (4,812 PNG, 0 DDS), 1 other file\nD:\\N64\\HD\\majora-textures'],
    convert: ['ready', 'Ready', 'RT64 texture dump: 5,276 textures (hash v5). 1,204 are new since your last convert.\nD:\\N64\\RT64 dumps\\Majora'],
    pack: ['ready', 'Ready', '4,812 textures (0 PNG, 4,812 DDS) with rt64.json\nD:\\N64\\HD\\majora-textures-upscaled'],
    unpack: ['idle', 'Choose the .rtz pack to unpack', ''],
    check: ['ready', 'Ready', '.rtz pack: 4,812 textures (4,790 DDS, 22 PNG), 1.9 GB unpacked, zstd, rt64.json\nD:\\N64\\HD\\Majora HD.rtz'],
    o2rExtract: q.get('ship') === 'ghost' ? ['ready', 'Ready', 'Ghostship game archive: 2,874 textures\nC:\\Games\\Ghostship\\sm64.o2r'] : ['ready', 'Ready', '2 Ship 2 Harkinian game archive: 6,528 textures\nC:\\Games\\2Ship\\mm.o2r'],
    o2rBuild: ['ready', 'Ready', '6,412 HD textures match the game (116 not found in mm.o2r)\nD:\\N64\\HD\\mm-textures-upscaled'],
    legacyImport: ['ready', 'Ready', 'GLideN64 pack (.hts): 9,841 textures, Rice IDs\nD:\\Packs\\THE LEGEND OF ZELDA_HIRESTEXTURES.hts'],
    legacyHts: ['ready', 'Ready', '4,812 textures, 4,655 with Rice IDs\nD:\\N64\\HD\\majora-textures-upscaled'],
    roms: ['ready', 'Ready', 'About 14 ROM files\nD:\\N64\\ROMs'],
    riceToO2r: ['ready', 'Ready', 'Rice pack: 6,528 PNG textures\nD:\\Packs\\Djipi Cel-Shaded\\ZELDA MAJORA\'S MASK'],
  };
  const CHECKS = [
    { level: 'bad', title: '22 textures are still PNG', text: 'RT64 says not to ship PNG: they load slowly and use more memory. Turn them into BC7 DDS.', fix: 'png-to-dds', fixLabel: 'Make them DDS' },
    { level: 'warn', title: 'Low-mip cache is 236 MB', text: 'RT64 suggests keeping it under about 200 MB. Very large textures make it grow.' },
    { level: 'warn', title: '3 textures changed shape', text: 'Their width and height don’t match the original’s proportions, so they may look stretched in game.' },
    { level: 'ok', title: 'Every texture in rt64.json has a file', text: '' },
    { level: 'ok', title: 'All DDS textures have mipmaps', text: '' },
    { level: 'ok', title: 'Recomp mod info and picture found', text: 'Shows as “Majora HD Reimagined” by chuchu, v1.0.0, with an on / off switch.' },
  ];

  window.htk = {
    state: async () => ({ settings, dataDir: 'C:\\Tools\\R64texHD-v0.8.0.1\\data', dataWritable: true,
      tools: noTools ? { texconv: '', realesrgan: '' } : window.__mixedTools ? { texconv: 'C:\\Tools\\R64texHD-v0.8.0.1\\data\\tools\\texconv.exe', realesrgan: '' } : { texconv: 'C:\\Tools\\R64texHD-v0.8.0.1\\data\\tools\\texconv.exe', realesrgan: 'C:\\Tools\\R64texHD-v0.8.0.1\\data\\tools\\realesrgan\\realesrgan-ncnn-vulkan.exe' },
      version: '0.8.0.1', platform: 'win32', cpus: 16, workers: 8, running: null, shipPorts: (window.__SHIP || {}).ports || [] }),
    saveSettings: async () => true,
    dialog: async () => null,
    inspect: async (kind) => { const r = INSPECT[kind === 'pipeline' ? 'convert' : kind] || ['idle', '', '']; return { state: r[0], title: r[1], text: r[2] }; },
    run: async (task) => {
      setTimeout(() => {
        const R = window.__ROMS || { list: [], folder: 'D:\\N64\\ROMs' };
        if (task === 'roms') emit('done', { task, result: { title: 'Found', roms: R.list, count: R.list.length, matched: R.matched || 0, libraryCount: R.libraryCount || 0, folders: new Set(R.list.map((r) => r.folder)).size, output: R.folder, seconds: 0.4 } });
        else if (task === 'check') emit('done', { task, result: { title: 'Checked', checks: CHECKS, output: settings.check.input, summary: 'Majora HD.rtz · 4,812 textures · 1.9 GB' } });
        else emit('done', { task, result: { title: 'Done', written: 4812, failed: 0, output: 'D:\\N64\\HD\\out', seconds: 42.1 } });
      }, 50);
      return { ok: true };
    },
    cancel: async () => true, open: async () => true, createShortcuts: async () => ({ ok: true }), openRepo: async () => '', quit: async () => true,
    installTool: async () => ({ ok: false, error: 'preview' }),
    fix: async () => ({ ok: true }),
    // Ship Mods: installed ports (the real app lists folders; see core/shipfind.js).
    shipFind: async () => {
      await new Promise((r) => setTimeout(r, q.has('slowfind') ? 4000 : 150));
      const have = { 'Ship of Harkinian': ['C:\\Games\\SoH', 'oot.o2r'], '2 Ship 2 Harkinian': ['C:\\Games\\2Ship', 'mm.o2r'], Ghostship: ['C:\\Games\\Ghostship', 'sm64.o2r'] };
      const ports = ((window.__SHIP || {}).ports || []).map((p) => have[p.name]
        ? { name: p.name, game: p.game, installed: true, dir: have[p.name][0], exe: '', archive: have[p.name][0] + '\\' + have[p.name][1], mods: have[p.name][0] + '\\mods' }
        : { name: p.name, game: p.game, installed: false });
      return { ports, folders: 18342, ms: 640, complete: true };
    },
    // Footer scenes: read straight from app/assets/scenes (serve the app folder over http for previews).
    sceneIndex: async () => { try { const j = async (f) => (await fetch('../assets/scenes/' + f)).json(); const index = await j('index.json'); return { stage: await j('stage.json'), index, here: Object.keys(index).length, total: Object.keys(index).length, download: { state: 'done' } }; } catch (e) { return { error: String(e) }; } },
    sceneClip: async (id) => { try { return await (await fetch('../assets/scenes/' + id + '/clip.json')).json(); } catch (e) { return { error: String(e) }; } },
    soundList: async () => ({}),
    audioInfo: async () => ({ music: ['normal-8bit-ree-you-ss-f.ogg', 'dmt-8bit-lat.ogg', 'dmt-8bit-pati.ogg'].map((n) => ({ name: n, url: '../assets/music/' + n, mode: /^dmt/.test(n) ? 'dmt' : 'standard', custom: false })),
      sfx: {}, customSfx: [], dirs: { music: 'C:\\R64texHD\\data\\music', sounds: 'C:\\R64texHD\\data\\sounds' } }),
    musicAdd: async () => ({ added: 0 }),
    estimate: async (req) => { await new Promise((r) => setTimeout(r, 200)); const k = { smart: 1, standard: 1, ai: 1.3, pixel: 0.4, smooth: 0.8 }[req.method] || 1; const sz = Number(req.size) || 4;
      return { count: 4812, disk: Math.round(2.36e9 * k * (sz / 4) ** 2 * (req.format === 'png' ? 1.7 : 1)), vram: Math.round(6.7e8 * (sz / 4) ** 2 * (req.format === 'png' ? 4 : 1)), seconds: Math.round(370 * k * (sz / 4) ** 2), groups: { hd: 3904, ai: req.aiOk === false ? 0 : 702, pixel: 206 }, smart: req.method === 'smart', aiReady: req.aiOk !== false }; },
    gpuInfo: async () => ({ ok: true, loader: true, gpus: [{ name: 'NVIDIA GeForce RTX 3070', vram: 8589934592, vulkan: true }, { name: 'Intel(R) UHD Graphics 630', vram: 134217728, vulkan: false }] }),
    taskbar: async () => true,
    notify: async () => true,
    // Ship Mods: looks at each port and the chosen archive again (the real app reads portVersion; core/shipcheck.js).
    shipCheck: async (ports, target) => {
      const id = target ? await window.htk.shipIdentify(target) : null;
      const out = (ports || null) && ports.map((p) => p.installed ? { ...p, state: p.name === 'Ghostship' ? 'not-generated' : 'ready', build: { major: 9, minor: 0, patch: 2, text: '9.0.2' },
        message: p.name === 'Ghostship' ? 'Ghostship hasn’t made its game archive yet: run it once and give it your ROM.' : '' } : p);
      return { ports: out, target: target ? { file: target, id, state: id && id.kind === 'game' ? 'ready' : '', message: '', build: null, version: null } : null };
    },
    // Ship Mods: which game an archive is (the real app reads the archive's version file).
    shipIdentify: async (file) => {
      const SH = window.__SHIP || { ports: [], games: {} };
      const port = SH.ports.find((p) => p.archives.some((a) => new RegExp(`\\\\${a}\\.o2r$`, 'i').test(file))) || SH.ports.find((p) => file.toLowerCase().includes(p.archives[0]));
      const g = port && SH.games[port.game];
      if (!g) return { file, crc: '', rom: '', source: '', key: '', game: null, port: null, kind: '' };
      const folder = !/\.o2r$/i.test(file);
      return { file, crc: g.crc, rom: g.rom, source: folder ? 'the texture list R64texHD saved here' : 'the archive’s version file', key: port.game, game: g.game, port, kind: folder ? 'folder' : 'game' };
    },
    romInfo: async (file) => (window.__ROMS && window.__ROMS.info[file]) || { error: 'Not in the preview data' },
    thumbnail: async () => 'splash.png',
    previewList: async () => ({ items: [{ src: 'a', rel: 'textures/0f3a9c21d8e4b7a1.png' }, { src: 'b', rel: 'textures/1b77e0a4c2d39f05.png' }], total: 4812 }),
    preview: async () => {
      // Real upscale result from make-preview-data.js when present; a quick stand-in otherwise.
      const P = window.__PREVIEW;
      if (P) {
        const dec = (x) => ({ width: x.width, height: x.height, data: Uint8Array.from(atob(x.data), (c) => c.charCodeAt(0)) });
        return { orig: dec(P.orig), up: dec(P.up), encoded: P.encoded, ms: 140, edges: 'tile × tile (from dump)', route: 'HD 4×' };
      }
      const o = brick(32, 32); return { orig: o, up: smoothUp(o, 4), encoded: 'DDS BC7', ms: 180, edges: 'tile × tile (from dump)', route: 'HD 4×' };
    },
    onStarted: on('started'), onProgress: on('progress'), onLog: on('log'), onDone: on('done'), onToolProgress: on('tool'),
  };
})();
