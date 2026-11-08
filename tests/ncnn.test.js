'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { modelScale, nameScale } = require('../app/core/ncnn');

const head = '7767517\n10 12\nInput  data  0 1 data\nConvolution  conv_first  1 1 data c0 0=64 1=3 4=1 5=1 6=1728\n';
test('ncnn: model scale read from the .param layers', () => {
  const rrdb = head + 'Interp  up1  1 1 a b 0=1 1=2.000000e+00 2=2.000000e+00\nInterp  up2  1 1 b c 0=1 1=2.000000e+00 2=2.000000e+00\n';
  assert.equal(modelScale(rrdb), 4);
  assert.equal(modelScale(head + 'PixelShuffle  ps  1 1 a b 0=4\n'), 4);                 // SRVGGNetCompact
  assert.equal(modelScale(head + 'PixelShuffle  ps  1 1 a b 0=2\n'), 2);
  assert.equal(modelScale(head + 'Interp  up  1 1 a b 0=2 1=2.0 2=2.0\nPixelShuffle  ps  1 1 b c 0=4\n'), 8);
  assert.equal(modelScale(head), null);                                                  // no upsample layer: can't tell
  assert.equal(modelScale(head + 'Interp  up  1 1 a b 0=1 3=256 4=256\n'), null);        // fixed output size
  assert.equal(modelScale('7767517\n3 3\nInterp  up  2 1 a s b 0=1 1=4.0 2=4.0\n'), 4); // two inputs
});
test('ncnn: scale a file name claims', () => {
  assert.equal(nameScale('4x-UltraSharp.param'), 4);
  assert.equal(nameScale('2x_Foo.param'), 2);
  assert.equal(nameScale('RealESRGAN_x2plus.param'), 2);
  assert.equal(nameScale('realesr-animevideov3-x3.param'), 3);
  assert.equal(nameScale('GameAI.param'), null);
  assert.equal(nameScale('xbox-hd.param'), null);
});
