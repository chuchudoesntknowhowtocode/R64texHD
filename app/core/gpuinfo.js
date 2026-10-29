'use strict';
// Graphics cards for the Real-ESRGAN row in Settings: name, video memory and whether it has a Vulkan driver.
//
// Windows only. One PowerShell call reads the display adapters (Win32_VideoController, only the ones present
// now) and each adapter's driver key under the display class in the registry:
//   HardwareInformation.qwMemorySize   video memory in bytes (AdapterRAM from WMI stops at 4 GB)
//   VulkanDriverName(Wow)              set by NVIDIA, AMD and Intel drivers that ship a Vulkan driver
// plus whether the Vulkan loader (System32\vulkan-1.dll) is installed. If the registry says no Vulkan for a card
// and vulkaninfo.exe is on the PC (it comes with the Vulkan runtime), its --summary has the last word.
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

const PS = `
$ErrorActionPreference = 'SilentlyContinue'
$vc = @(Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM)
$cls = 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}'
$keys = @(Get-ChildItem $cls | Where-Object { $_.PSChildName -match '^\\d{4}$' } | ForEach-Object { Get-ItemProperty $_.PSPath })
$out = @()
foreach ($c in $vc) {
  $k = $keys | Where-Object { $_.DriverDesc -eq $c.Name } | Select-Object -First 1
  $mem = 0; $vk = $false
  if ($k) {
    $mem = $k.'HardwareInformation.qwMemorySize'
    if (-not $mem) { $m = $k.'HardwareInformation.MemorySize'; if ($m -is [byte[]]) { $mem = [BitConverter]::ToUInt32($m, 0) } elseif ($m) { $mem = $m } }
    $vk = [bool]($k.VulkanDriverName -or $k.VulkanDriverNameWow)
  }
  if (-not $mem) { $mem = $c.AdapterRAM }
  $out += [pscustomobject]@{ name = $c.Name; vram = [double]$mem; vulkan = $vk }
}
[pscustomobject]@{ gpus = $out; loader = (Test-Path "$env:SystemRoot\\System32\\vulkan-1.dll") } | ConvertTo-Json -Compress -Depth 4
`;

const SKIP = /^Microsoft (Basic|Remote)|Hyper-V/i;

// psJson: the PowerShell output. vkText: `vulkaninfo --summary` output, if it was run.
function parse(psJson, vkText = '') {
  let raw; try { raw = JSON.parse(psJson); } catch { return { ok: false, gpus: [], loader: false }; }
  let list = raw && raw.gpus; if (!list) list = []; if (!Array.isArray(list)) list = [list];
  const vkNames = [...String(vkText).matchAll(/deviceName\s*=\s*(.+)/g)].map((m) => m[1].trim().toLowerCase());
  const loader = !!(raw && raw.loader) || vkNames.length > 0;
  let gpus = list.filter((g) => g && g.name && !SKIP.test(g.name)).map((g) => {
    const name = String(g.name).trim(), vram = Number(g.vram) > 0 ? Number(g.vram) : 0;
    const inVk = vkNames.some((n) => n === name.toLowerCase() || n.includes(name.toLowerCase()) || name.toLowerCase().includes(n));
    return { name, vram, vulkan: loader && (!!g.vulkan || inVk) };
  });
  // virtual displays (streaming / VR apps) have no memory and no Vulkan: leave them out when there's a real card
  if (gpus.some((g) => g.vram > 0 || g.vulkan)) gpus = gpus.filter((g) => g.vram > 0 || g.vulkan);
  return { ok: true, loader, gpus };
}

// "8 GB", "1.5 GB", "512 MB"
function vramText(bytes) {
  if (!(bytes > 0)) return '';
  const gb = bytes / 1073741824;
  if (gb < 0.95) return Math.round(bytes / 1048576) + ' MB';
  return (gb >= 10 || Math.abs(gb - Math.round(gb)) < 0.05 ? String(Math.round(gb)) : gb.toFixed(1)) + ' GB';
}

function run(cmd, args, timeout) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout, windowsHide: true, maxBuffer: 4 << 20 }, (err, stdout) => resolve(err && !stdout ? '' : String(stdout || '')));
  });
}

let cached = null;
function detect() {
  if (cached) return cached;
  cached = (async () => {
    if (process.platform !== 'win32') return { ok: false, unsupported: true, gpus: [], loader: false };
    const ps = await run('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', Buffer.from(PS, 'utf16le').toString('base64')], 20000);
    let r = parse(ps.trim());
    if (r.ok && r.gpus.some((g) => !g.vulkan)) {
      const vi = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'vulkaninfo.exe');
      if (fs.existsSync(vi)) r = parse(ps.trim(), await run(vi, ['--summary'], 15000));
    }
    if (!r.ok) cached = null;                                    // try again next time
    return r;
  })();
  return cached;
}

module.exports = { detect, parse, vramText };
