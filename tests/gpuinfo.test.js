'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { parse, vramText } = require('../app/core/gpuinfo');

test('gpuinfo: one card with a Vulkan driver', () => {
  const r = parse(JSON.stringify({ gpus: { name: 'NVIDIA GeForce RTX 3070', vram: 8589934592, vulkan: true }, loader: true }));
  assert.deepStrictEqual(r, { ok: true, loader: true, gpus: [{ name: 'NVIDIA GeForce RTX 3070', vram: 8589934592, vulkan: true }] });
});

test('gpuinfo: no loader means no Vulkan, even if the driver says so', () => {
  const r = parse(JSON.stringify({ gpus: [{ name: 'AMD Radeon RX 580', vram: 8589934592, vulkan: true }], loader: false }));
  assert.strictEqual(r.gpus[0].vulkan, false);
});

test('gpuinfo: basic display adapters and empty virtual displays are left out', () => {
  const r = parse(JSON.stringify({ gpus: [
    { name: 'Microsoft Basic Display Adapter', vram: 0, vulkan: false },
    { name: 'Parsec Virtual Display Adapter', vram: 0, vulkan: false },
    { name: 'Intel(R) UHD Graphics 630', vram: 134217728, vulkan: true },
    { name: 'NVIDIA GeForce GTX 1650', vram: 4294967296, vulkan: true }], loader: true }));
  assert.deepStrictEqual(r.gpus.map((g) => g.name), ['Intel(R) UHD Graphics 630', 'NVIDIA GeForce GTX 1650']);
});

test('gpuinfo: vulkaninfo --summary confirms a card the registry missed', () => {
  const vk = 'Devices:\n========\nGPU0:\n\tapiVersion         = 1.3.277\n\tdeviceName         = AMD Radeon RX 6600\n';
  const r = parse(JSON.stringify({ gpus: [{ name: 'AMD Radeon RX 6600', vram: 8589934592, vulkan: false }], loader: false }), vk);
  assert.strictEqual(r.gpus[0].vulkan, true);
});

test('gpuinfo: bad output', () => {
  assert.strictEqual(parse('').ok, false);
  assert.deepStrictEqual(parse('{"gpus":null,"loader":true}').gpus, []);
});

test('gpuinfo: memory text', () => {
  assert.strictEqual(vramText(8589934592), '8 GB');
  assert.strictEqual(vramText(12884901888), '12 GB');
  assert.strictEqual(vramText(1610612736), '1.5 GB');
  assert.strictEqual(vramText(134217728), '128 MB');
  assert.strictEqual(vramText(0), '');
});
