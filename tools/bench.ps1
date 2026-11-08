# R64texHD AI speed test (roadmap 13): Real-ESRGAN (ncnn/Vulkan) vs the ONNX engine (DirectML / CPU) on the
# same textures, every graphics card. Writes bench\bench-<date>.csv next to this repo and prints a table.
#
#   powershell -ExecutionPolicy Bypass -File tools\bench.ps1 [-Source <folder of PNGs>] [-Count 20] [-App <R64texHD folder>]
#
# Needs the helper tools installed in that R64texHD folder (Settings > Helper tools): Real-ESRGAN and the ONNX engine.
param(
  [string]$Source = "$PSScriptRoot\..\..\test\capture",
  [int]$Count = 20,
  [string]$App = ""
)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
if (-not $App) { $App = (Get-ChildItem "$repo\dist" -Directory | Where-Object Name -like 'R64texHD-v*' | Sort-Object Name | Select-Object -Last 1).FullName }
$exe = Join-Path $App 'R64texHD.exe'
$esr = Join-Path $App 'data\tools\realesrgan\realesrgan-ncnn-vulkan.exe'
$onnx = Join-Path $App 'data\tools\onnx'
$runner = Join-Path $App 'resources\app\core\onnx-run.js'
foreach ($f in @($exe, $esr, $runner)) { if (-not (Test-Path $f)) { throw "missing: $f (install the helper tools in Settings first)" } }

# The same small set of textures for every run.
$work = Join-Path $env:TEMP "r64bench"
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
$in = (New-Item -ItemType Directory "$work\in").FullName
$pngs = Get-ChildItem $Source -Filter *.png | Select-Object -First $Count
if (-not $pngs) { throw "no PNG files in $Source" }
$pngs | Copy-Item -Destination $in
$px = 0; foreach ($p in $pngs) { Add-Type -AssemblyName System.Drawing; $b = [System.Drawing.Image]::FromFile($p.FullName); $px += $b.Width * $b.Height; $b.Dispose() }
Write-Host "$($pngs.Count) textures, $([math]::Round($px / 1e6, 2)) Mpx, from $Source"

# Graphics cards as Real-ESRGAN numbers them (0, 1, ...); the ONNX engine (DirectML) uses the same order on most PCs.
$gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name })
$ErrorActionPreference = 'Continue'   # the tools print progress on stderr: not an error
$rows = @()
function Run($engine, $device, [scriptblock]$cmd, $n) {
  $out = "$work\out-$engine-$device"; New-Item -ItemType Directory $out -Force | Out-Null
  $t = Measure-Command { & $cmd $out 2>&1 | Out-File "$work\log-$engine-$device.txt" }
  $made = (Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue).Count
  $row = [pscustomobject]@{ engine = $engine; device = $device; textures = $made; of = $n; seconds = [math]::Round($t.TotalSeconds, 2); ms_per_texture = if ($made) { [math]::Round($t.TotalMilliseconds / $made) } else { 0 } }
  $script:rows += $row; $row | Format-Table -HideTableHeaders | Out-String | Write-Host -NoNewline
}

for ($g = 0; $g -lt $gpus.Count; $g++) {
  Run 'ncnn realesrgan-x4plus' "gpu$g" { param($o) & $esr -i $in -o $o -n realesrgan-x4plus -s 4 -f png -g $g -j 4:4:4 } $pngs.Count
}
if (Test-Path "$onnx\models") {
  $env:ELECTRON_RUN_AS_NODE = '1'
  $ort = "$onnx\node_modules\onnxruntime-node"
  foreach ($m in @('rgts-dither-x4', 'texturedat2-x4')) {
    for ($g = 0; $g -lt $gpus.Count; $g++) {
      Run "onnx $m" "dml$g" { param($o) & $exe $runner -i $in -o $o -m "$onnx\models\$m.onnx" --ort $ort -g $g } $pngs.Count
    }
  }
  # CPU: 3 textures only (TextureDAT2 on the CPU takes minutes per texture)
  Remove-Item "$in\*" ; $pngs | Select-Object -First 3 | Copy-Item -Destination $in
  Run 'onnx rgts-dither-x4' 'cpu' { param($o) & $exe $runner -i $in -o $o -m "$onnx\models\rgts-dither-x4.onnx" --ort $ort -g cpu } 3
  Remove-Item Env:\ELECTRON_RUN_AS_NODE
} else { Write-Host "ONNX engine not installed: skipped" }

$dir = New-Item -ItemType Directory "$repo\bench" -Force
$csv = Join-Path $dir ("bench-" + (Get-Date -Format 'yyyyMMdd-HHmm') + ".csv")
"# $($gpus -join ' | ') ; $($pngs.Count) textures, $([math]::Round($px / 1e6, 2)) Mpx" | Out-File $csv -Encoding utf8
$rows | ConvertTo-Csv -NoTypeInformation | Out-File $csv -Append -Encoding utf8
Write-Host ""; $rows | Format-Table -AutoSize
Write-Host "Saved: $csv  (logs: $work)"
