'use strict';
// The only bridge between the launcher page and the app: a small, explicit API.
const { contextBridge, ipcRenderer } = require('electron');

const on = (channel) => (fn) => { const h = (_e, data) => fn(data); ipcRenderer.on(channel, h); return () => ipcRenderer.removeListener(channel, h); };

contextBridge.exposeInMainWorld('htk', {
  state: () => ipcRenderer.invoke('state'),
  saveSettings: (s) => ipcRenderer.invoke('settings:save', s),
  dialog: (opts) => ipcRenderer.invoke('dialog', opts),
  inspect: (kind, value) => ipcRenderer.invoke('inspect', { kind, value }),
  run: (task, params) => ipcRenderer.invoke('task:run', { task, params }),
  cancel: () => ipcRenderer.invoke('task:cancel'),
  open: (p) => ipcRenderer.invoke('open', p),
  createShortcuts: () => ipcRenderer.invoke('shortcuts'),
  openRepo: () => ipcRenderer.invoke('repo'),
  installTool: (name) => ipcRenderer.invoke('tool:install', name),
  quit: () => ipcRenderer.invoke('quit'),
  previewList: (inputs, subfolders) => ipcRenderer.invoke('preview:list', { inputs, subfolders }),
  preview: (req) => ipcRenderer.invoke('preview', req),
  thumbnail: (p) => ipcRenderer.invoke('thumbnail', p),
  romInfo: (file) => ipcRenderer.invoke('rom:info', file),
  shipIdentify: (file) => ipcRenderer.invoke('ship:identify', file),
  shipFind: (seeds) => ipcRenderer.invoke('ship:find', seeds),
  shipCheck: (ports, target) => ipcRenderer.invoke('ship:check', { ports, target }),
  sceneIndex: () => ipcRenderer.invoke('scenes:index'),
  sceneClip: (id) => ipcRenderer.invoke('scenes:clip', id),
  soundList: () => ipcRenderer.invoke('sounds:list'),
  audioInfo: () => ipcRenderer.invoke('audio:info'),
  musicAdd: () => ipcRenderer.invoke('music:add'),
  gpuInfo: () => ipcRenderer.invoke('gpu:info'),
  taskbar: (p, mode) => ipcRenderer.invoke('taskbar', p, mode),
  onStarted: on('task:started'),
  onProgress: on('task:progress'),
  onLog: on('task:log'),
  onDone: on('task:done'),
  onToolProgress: on('tool:progress'),
});
