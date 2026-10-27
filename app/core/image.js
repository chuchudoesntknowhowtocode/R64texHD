'use strict';
// Load any PNG / DDS into RGBA, save as PNG or DDS.
const fs = require('fs');
const path = require('path');
const png = require('./png');
const dds = require('./dds');

const IMAGE_EXTENSIONS = ['.png', '.dds'];

function loadImage(file) {
  const buf = fs.readFileSync(file);
  if (buf.length >= 8 && buf[0] === 0x89 && buf.toString('latin1', 1, 4) === 'PNG') return png.decodePNG(buf);
  if (buf.length >= 4 && buf.toString('latin1', 0, 4) === 'DDS ') return dds.decodeDDS(buf);
  throw new Error('not a PNG or DDS image');
}

// Writes `img` to `fileNoExt` + .png/.dds atomically; returns the written path.
function saveImage(img, fileNoExt, { format = 'png', ddsFormat = 'auto', texconv = null, mipmaps = true, pngLevel = 6, keepCoverage = false } = {}) {
  const out = fileNoExt + (format === 'dds' ? '.dds' : '.png');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const data = format === 'dds' ? dds.encodeDDS(img, ddsFormat, { mipmaps, texconv, keepCoverage }) : png.encodePNG(img, pngLevel);
  const tmp = out + '.part';
  fs.writeFileSync(tmp, data);
  fs.renameSync(tmp, out);
  return out;
}

module.exports = { loadImage, saveImage, IMAGE_EXTENSIONS };
