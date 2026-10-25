#!/usr/bin/env bash
# Builds the portable Windows release:  dist/HD Texture Toolkit/R64texHD.exe  and  dist/R64texHD-Windows.zip
#
# Needs: bash, curl, unzip, python3 with Pillow (pip install Pillow). pefile is fetched automatically.
# Works on Linux, macOS or Windows (Git Bash / WSL).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ELECTRON_VERSION="${ELECTRON_VERSION:-38.4.0}"
CACHE="$HERE/build/.cache"
OUT="$HERE/dist/HD Texture Toolkit"
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
python3 "$HERE/build/set_icon.py" "$OUT/electron.exe" "$HERE/app/assets/icon.png" "$OUT/icon.tmp.exe"
python3 "$HERE/build/set_version.py" "$OUT/icon.tmp.exe" "$OUT/R64texHD.exe"
rm "$OUT/electron.exe" "$OUT/icon.tmp.exe"
mkdir -p "$OUT/resources/app"
cp -r "$HERE/app/main.js" "$HERE/app/preload.js" "$HERE/app/package.json" "$HERE/app/core" "$HERE/app/ui" "$HERE/app/assets" "$OUT/resources/app/"
sed 's/$/\r/' "$HERE/docs/README.txt" > "$OUT/README.txt"
cp "$HERE/LICENSE" "$OUT/LICENSE.R64texHD.txt"
cp "$HERE/THIRD_PARTY_NOTICES.md" "$OUT/THIRD_PARTY_NOTICES.md"
( cd "$HERE/dist" && python3 -c "
import zipfile, os
with zipfile.ZipFile('R64texHD-Windows.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, _, files in os.walk('HD Texture Toolkit'):
        for f in sorted(files):
            z.write(os.path.join(root, f))
" )
echo "Done: $HERE/dist/R64texHD-Windows.zip"
