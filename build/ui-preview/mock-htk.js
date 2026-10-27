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
    firstRunDone: true, checkTools: true, page: q.get('page') || 'upscale', dumpFolder: 'D:\\N64\\RT64 dumps\\Majora', outputFolder: 'D:\\N64\\HD',
    workers: 'auto', maxSize: 4096, realesrganModel: 'realesrgan-x4plus', splash: q.has('splash'),
    upscale: { inputs: ['D:\\N64\\HD\\majora-textures'], subfolders: true, method: 'standard', size: 4, fit: 2048, sharpness: 'normal', edges: 'auto', hardAlpha: true,
      format: 'dds', ddsFormat: 'bc7', output: 'D:\\N64\\HD\\majora-textures-upscaled', existing: 'overwrite', copyOther: true, keepCoverage: true },
    convert: { input: 'D:\\N64\\RT64 dumps\\Majora', format: 'png', ddsFormat: 'auto', output: 'D:\\N64\\HD\\Majora-textures', wrapInfo: true, rice: true, onlyNew: true },
    pack: { mode: q.get('mode') || 'pack', input: 'D:\\N64\\HD\\majora-textures-upscaled', output: 'D:\\N64\\HD\\Majora HD.rtz', compression: 'zstd', level: 'balanced', lowMipCache: true,
      recomp: true, recompName: 'Majora HD Reimagined', recompAuthor: 'chuchu', recompVersion: '1.0.0', recompDescription: 'Every texture in Termina, redone in HD.', recompThumb: 'D:\\N64\\HD\\thumb.png', recompToggle: true },
    unpack: { input: '', output: '', keepCache: false },
    check: { input: 'D:\\N64\\HD\\Majora HD.rtz' },
    ports: { mode: q.get('mode') || 'extract', archive: 'C:\\Games\\2Ship\\mm.o2r', output: 'D:\\N64\\HD\\mm-textures', hdInput: 'D:\\N64\\HD\\mm-textures-upscaled',
      base: 'C:\\Games\\2Ship\\mm.o2r', modOutput: 'C:\\Games\\2Ship\\mods\\Majora HD.o2r', alt: true, compression: 'store' },
    legacy: { mode: q.get('mode') || 'import', input: 'D:\\Packs\\THE LEGEND OF ZELDA_HIRESTEXTURES.hts', output: 'D:\\N64\\HD\\OoT Reloaded-rt64',
      htsInput: 'D:\\N64\\HD\\majora-textures-upscaled', htsName: 'ZELDA MAJORA\'S MASK', htsOutput: 'D:\\N64\\HD\\ZELDA MAJORA\'S MASK_HIRESTEXTURES.hts',
      riceInput: 'D:\\Packs\\Djipi Cel-Shaded\\ZELDA MAJORA\'S MASK', base: 'C:\\Games\\2Ship\\mm.o2r', modOutput: 'C:\\Games\\2Ship\\mods\\Celda.o2r' },
  };
  const INSPECT = {
    upscale: ['ready', 'Ready', '4,812 images (4,812 PNG, 0 DDS), 1 other file\nD:\\N64\\HD\\majora-textures'],
    convert: ['ready', 'Ready', 'RT64 texture dump: 5,276 textures (hash v5). 1,204 are new since your last convert.\nD:\\N64\\RT64 dumps\\Majora'],
    pack: ['ready', 'Ready', '4,812 textures (0 PNG, 4,812 DDS) with rt64.json\nD:\\N64\\HD\\majora-textures-upscaled'],
    unpack: ['idle', 'Choose the .rtz pack to unpack', ''],
    check: ['ready', 'Ready', '.rtz pack: 4,812 textures (4,790 DDS, 22 PNG), 1.9 GB unpacked, zstd, rt64.json\nD:\\N64\\HD\\Majora HD.rtz'],
    o2rExtract: ['ready', 'Ready', '2 Ship 2 Harkinian game archive: 6,528 textures\nC:\\Games\\2Ship\\mm.o2r'],
    o2rBuild: ['ready', 'Ready', '6,412 HD textures match the game (116 not found in mm.o2r)\nD:\\N64\\HD\\mm-textures-upscaled'],
    legacyImport: ['ready', 'Ready', 'GLideN64 pack (.hts): 9,841 textures, Rice IDs\nD:\\Packs\\THE LEGEND OF ZELDA_HIRESTEXTURES.hts'],
    legacyHts: ['ready', 'Ready', '4,812 textures, 4,655 with Rice IDs\nD:\\N64\\HD\\majora-textures-upscaled'],
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
    state: async () => ({ settings, dataDir: 'C:\\Tools\\R64texHD-v0.7.1.1\\data', dataWritable: true,
      tools: noTools ? { texconv: '', realesrgan: '' } : window.__mixedTools ? { texconv: 'C:\\Tools\\R64texHD-v0.7.1.1\\data\\tools\\texconv.exe', realesrgan: '' } : { texconv: 'C:\\Tools\\R64texHD-v0.7.1.1\\data\\tools\\texconv.exe', realesrgan: 'C:\\Tools\\R64texHD-v0.7.1.1\\data\\tools\\realesrgan\\realesrgan-ncnn-vulkan.exe' },
      version: '0.7.1.1', platform: 'win32', cpus: 16, workers: 8, running: null }),
    saveSettings: async () => true,
    dialog: async () => null,
    inspect: async (kind) => { const r = INSPECT[kind] || ['idle', '', '']; return { state: r[0], title: r[1], text: r[2] }; },
    run: async (task) => {
      setTimeout(() => {
        if (task === 'check') emit('done', { task, result: { title: 'Checked', checks: CHECKS, output: settings.check.input, summary: 'Majora HD.rtz · 4,812 textures · 1.9 GB' } });
        else emit('done', { task, result: { title: 'Done', written: 4812, failed: 0, output: 'D:\\N64\\HD\\out', seconds: 42.1 } });
      }, 50);
      return { ok: true };
    },
    cancel: async () => true, open: async () => true, createShortcuts: async () => ({ ok: true }), openRepo: async () => '', quit: async () => true,
    installTool: async () => ({ ok: false, error: 'preview' }),
    fix: async () => ({ ok: true }),
    thumbnail: async () => 'splash.png',
    previewList: async () => ({ items: [{ src: 'a', rel: 'textures/0f3a9c21d8e4b7a1.png' }, { src: 'b', rel: 'textures/1b77e0a4c2d39f05.png' }], total: 4812 }),
    preview: async () => { const o = brick(32, 32); return { orig: o, up: smoothUp(o, 4), encoded: 'DDS BC7', ms: 180, edges: 'tile × tile (from dump)' }; },
    onStarted: on('started'), onProgress: on('progress'), onLog: on('log'), onDone: on('done'), onToolProgress: on('tool'),
  };
})();
