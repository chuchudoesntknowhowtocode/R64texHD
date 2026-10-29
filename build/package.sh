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
echo "Done: $HERE/dist/$NAME-Windows.zip and $HERE/dist/$NAME-scenes.zip (attach both to the release)"
