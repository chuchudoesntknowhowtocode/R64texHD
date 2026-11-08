#!/usr/bin/env bash
# Builds the portable Windows release:  dist/R64texHD-v<version>/R64texHD.exe  and  dist/R64texHD-v<version>-Windows.zip
#
# Needs: bash, curl, unzip, python3 with Pillow (pip install Pillow). pefile is fetched automatically.
# Works on Linux, macOS or Windows (Git Bash / WSL).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ELECTRON_VERSION="${ELECTRON_VERSION:-38.4.0}"
CACHE="$HERE/build/.cache"
VERSION="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$HERE/app/package.json")"
NAME="R64texHD-v$VERSION"
OUT="$HERE/dist/$NAME"
mkdir -p "$CACHE"

ZIP="$CACHE/electron-v$ELECTRON_VERSION-win32-x64.zip"
if [ ! -f "$ZIP" ]; then
  echo "Downloading Electron $ELECTRON_VERSION (win32-x64)..."
  curl -fL --retry 3 -o "$ZIP.part" "https://github.com/electron/electron/releases/download/v$ELECTRON_VERSION/electron-v$ELECTRON_VERSION-win32-x64.zip"
  mv "$ZIP.part" "$ZIP"
fi
if ! python3 -c "import pefile" 2>/dev/null; then
  if [ ! -d "$CACHE/pefile" ]; then git clone -q --depth 1 https://github.com/erocarrera/pefile.git "$CACHE/pefile"; fi
  export PYTHONPATH="$CACHE/pefile${PYTHONPATH:+:$PYTHONPATH}"
fi

rm -rf "$HERE/dist" && mkdir -p "$OUT"
unzip -q "$ZIP" -d "$OUT"
rm -f "$OUT/resources/default_app.asar"
# R64texHD.exe: Electron's exe with the app icon and R64texHD version info (the name Task Manager shows).
python3 "$HERE/build/set_icon.py" "$OUT/electron.exe" "$HERE/app/assets/icon.ico" "$OUT/icon.tmp.exe"
python3 "$HERE/build/set_version.py" "$OUT/icon.tmp.exe" "$OUT/R64texHD.exe"
rm "$OUT/electron.exe" "$OUT/icon.tmp.exe"
mkdir -p "$OUT/resources/app"
cp -r "$HERE/app/main.js" "$HERE/app/preload.js" "$HERE/app/package.json" "$HERE/app/core" "$HERE/app/ui" "$HERE/app/assets" "$OUT/resources/app/"
# Smaller download: English is the only UI language, so the other Chromium locales go (~40 MB unpacked).
find "$OUT/locales" -name '*.pak' ! -name 'en-US.pak' -delete
# Footer scenes: the starter set (classics, peeks, busy, re-robe) stays in the app; fights and trips go in a
# separate pack attached to the GitHub release. The app downloads it once (assets/scenes/remote.json).
REPO_URL="https://github.com/chuchudoesntknowhowtocode/R64texHD"
# The pack's URL: the release tagged v<version>. Set SCENES_URL to use another tag.
SCENES_URL="${SCENES_URL:-$REPO_URL/releases/download/v$VERSION/$NAME-scenes.zip}"
python3 - "$OUT/resources/app/assets/scenes" "$HERE/dist/$NAME-scenes.zip" "$SCENES_URL" <<'PY'
import hashlib, json, os, shutil, sys, zipfile
src, out, url = sys.argv[1:4]
for f in os.listdir(src):
    if f.startswith('index_') and f.endswith('.json'): os.remove(os.path.join(src, f))
moved = [d for d in sorted(os.listdir(src)) if os.path.isdir(os.path.join(src, d)) and d.split('_')[0] in ('fight', 'trip')]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for d in moved:
        for f in sorted(os.listdir(os.path.join(src, d))): z.write(os.path.join(src, d, f), f'{d}/{f}')
for d in moved: shutil.rmtree(os.path.join(src, d))
data = open(out, 'rb').read()
json.dump({'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'clips': len(moved)}, open(os.path.join(src, 'remote.json'), 'w'), indent=1)
print(f'scenes pack: {len(moved)} clips, {len(data) / 1e6:.1f} MB')
PY
# Texture models pack (build/models/out, made by build/models/convert.py): a separate download next to the release,
# installed from Settings into Real-ESRGAN's models folder. Skipped when the models haven't been converted.
MODELS_URL="${MODELS_URL:-$REPO_URL/releases/download/v$VERSION/$NAME-models.zip}"
if ls "$HERE/build/models/out/"*.param >/dev/null 2>&1; then
  python3 - "$HERE/build/models" "$HERE/dist/$NAME-models.zip" "$MODELS_URL" "$OUT/resources/app/assets/models" <<'PY'
import hashlib, json, os, sys, zipfile
src, out, url, dest = sys.argv[1:5]
names = ['hdcube-x4', 'gameai2-x4', 'pixelperfect4-x4']
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for n in names:
        for ext in ('.param', '.bin'): z.write(os.path.join(src, 'out', n + ext), n + ext)
    z.write(os.path.join(src, 'CREDITS.txt'), 'texture-models-CREDITS.txt')
data = open(out, 'rb').read(); os.makedirs(dest, exist_ok=True)
json.dump({'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'models': names}, open(os.path.join(dest, 'remote.json'), 'w'), indent=1)
print(f'texture models pack: {len(names)} models, {len(data) / 1e6:.1f} MB')
PY
fi
# ONNX engine pack (roadmap 11): onnxruntime-node (Windows x64 binaries only) + the two CC BY 4.0 ONNX texture models,
# a separate download installed from Settings into data/tools/onnx. Cached in build/.cache/onnx.
ONNX_URL="${ONNX_URL:-$REPO_URL/releases/download/v$VERSION/$NAME-onnx.zip}"
ORT_VERSION=1.22.0
OC="$CACHE/onnx"; mkdir -p "$OC"
for p in onnxruntime-node onnxruntime-common; do
  [ -f "$OC/$p-$ORT_VERSION.tgz" ] || ( cd "$OC" && npm pack -s "$p@$ORT_VERSION" >/dev/null )
done
[ -f "$OC/texturedat2-x4.onnx" ] || curl -fsSL -o "$OC/texturedat2-x4.onnx" https://github.com/Phhofm/models/releases/download/4xTextureDAT2_otf/4xTextureDAT2_otf_fp32_opset17.onnx
[ -f "$OC/rgts-dither-x4.onnx" ] || curl -fsSL -o "$OC/rgts-dither-x4.onnx" https://github.com/Phhofm/models/releases/download/4xTextures_GTAV_rgt-s_dither/4xTextures_GTAV_rgt-s_dither_fp32_opset17.onnx
python3 - "$OC" "$ORT_VERSION" "$HERE/build/onnx/CREDITS.txt" "$HERE/dist/$NAME-onnx.zip" "$ONNX_URL" "$OUT/resources/app/assets/onnx" <<'PY'
import hashlib, json, os, sys, tarfile, zipfile
oc, ver, credits, out, url, dest = sys.argv[1:7]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in ('onnxruntime-node', 'onnxruntime-common'):
        with tarfile.open(os.path.join(oc, f'{p}-{ver}.tgz')) as t:
            for m in t.getmembers():
                if not m.isfile(): continue
                rel = m.name.split('/', 1)[1]                          # package/<rel>
                if p == 'onnxruntime-node' and not (rel in ('package.json', 'LICENSE', 'README.md') or rel.startswith('dist/') or rel.startswith('bin/napi-v6/win32/x64/')): continue
                if p == 'onnxruntime-common' and not (rel in ('package.json', 'LICENSE', 'README.md') or rel.startswith('dist/cjs/')): continue
                z.writestr(f'node_modules/{p}/{rel}', t.extractfile(m).read())
    for m in ('texturedat2-x4', 'rgts-dither-x4'): z.write(os.path.join(oc, m + '.onnx'), f'models/{m}.onnx')
    z.write(credits, 'ONNX-CREDITS.txt')
data = open(out, 'rb').read(); os.makedirs(dest, exist_ok=True)
json.dump({'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'models': ['texturedat2-x4', 'rgts-dither-x4']}, open(os.path.join(dest, 'remote.json'), 'w'), indent=1)
print(f'ONNX engine pack: {len(data) / 1e6:.1f} MB')
PY
sed 's/$/\r/' "$HERE/docs/README.txt" > "$OUT/README.txt"
cp "$HERE/LICENSE" "$OUT/LICENSE.R64texHD.txt"
cp "$HERE/THIRD_PARTY_NOTICES.md" "$OUT/THIRD_PARTY_NOTICES.md"
( cd "$HERE/dist" && python3 -c "
import zipfile, os
with zipfile.ZipFile('$NAME-Windows.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, _, files in os.walk('$NAME'):
        for f in sorted(files):
            z.write(os.path.join(root, f))
" )
echo "Done: $HERE/dist/$NAME-Windows.zip, $NAME-scenes.zip, $NAME-onnx.zip and (if built) $NAME-models.zip: attach them all to the release"
