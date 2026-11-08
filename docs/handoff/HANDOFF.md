# R64texHD handoff #6 — 2026-11-08
## Scope
Portable Windows Electron app (app/, plain JS, Electron 38). Roadmap 1–12 done, 13 (experiments) left. Current version v0.9.2.0 (built in dist/, not released).

## Changes we made (this chat, all committed)
- 6e18a43 tools/dither-tune.js (scores a folder at several DITHER_NEAR limits); ditherScore(img, lim)
- e89cb96 dither share = hits / busy (non-flat) pixels; tuned on 160 SF2T captures (C:\GitHub\test\capture): 7/7 dithered gradients found (was 4), noise ≤ 0.027; DITHER_NEAR 56, DITHERED 0.12 kept
- 35e2fad + 7ed1c49 own models: app/core/ncnn.js modelScale (follows the ncnn graph: Interp/PixelShuffle, parallel branches don't multiply) + nameScale; addModel rejects non-4×; verified on 8 real .param (animevideov3 x2/x3/x4, x4plus, anime, 3 texture models)
- b65036d v0.9.2.0 (package.json, CHANGELOG, README)
- ed504fd helper tools: first start offers all 4 tools (continues past failures); download() falls back to GitHub API asset link on 5xx/429 (github.com/releases/download gave 504 for every file on 11-08); fetchPack() installs …-onnx.zip / …-models.zip found next to the program folder (unpublished builds, offline)
- e91b099 preview: zoomed → drag to pan, click centres the spot (also Compare grid, middle button); split line drags from the line (24 px grip); Fit unchanged
- b06de12 (after #6) DITHERED 0.12 → 0.10: N64 Glide dumps (x64tractor/samples PD/GE/MK64, 4055 textures) — PD dithered 16-colour scenes 0.10–0.125, none on the AI route
- Pushed by user: handoff/next = ac76f5d. Not pushed: b06de12

## Changes we should make
- H: user pushes; Windows test of dist\R64texHD-v0.9.2.0: ONNX engine (DirectML start, speed/VRAM), Upscale page (grip, Output panel, reset, small windows), pan/click-centre, Compare with real AI, own model add (4× ok, 2× refused), Smart aidither; first-start prompt (fresh unzip)
- H: owner merges handoff/next + releases v0.9.2.0 (build\release.cmd); until then in-app pack downloads 404 (local zips next to the folder work)
- M: aidither still untested on real data: no dithered texture in SF2T/PD/GE/MK64 reaches the AI route (colours < 96)
- L: pan: points near the edge can't reach the centre (no padding); split line lost its black outline when zoomed
- L: roadmap 13 (ncnn vs DML timing AMD/Intel, CPU lane, TensorRT/WinML); ORT session per GPU, fp16; Compare "Original" cell

## Current state
- Works: tests 98 pass; pan verified in Chromium harness; download fallback verified (texconv via API, sha ok); dist build + 4 zips consistent (remote.json sha = zips)
- User confirmed helper tools "looking good" after restart (11-08)
- Untested on Windows: DirectML, pan on real app, own-model add with real files

## Decisions
- Dither: change the denominator, not the constants (small N64 textures have few flat pixels → scores ~unchanged)
- Model scale: layer scale wins; name wins only when it says smaller (unshuffle models read high)
- First start = all tools; later startups still check only required tools (texconv, Real-ESRGAN)
- Bot mode skipped: computer use can't drive the Claude app or the portable R64texHD exe (not resolvable)

## Watch out for
- package.sh straight onto the mount gets killed (>180 s, background jobs die with the call) and `rm -rf dist` first → half-wiped dist. Use: `sed -e "s#^HERE=.*#HERE=\"$PWD\"#" -e 's#\$HERE/dist#$HOME/dist#g' -e 's#^OUT=.*#OUT="$HOME/dist/$NAME"#' build/package.sh > ~/pk.sh; bash ~/pk.sh` (~66 s), then `cp -f ~/dist/*.zip dist/` and `cp -rf ~/dist/<name>/. dist/<name>/` (exe/dll copy fails while the app runs: identical anyway; check with diff -rq)
- `rm -rf dist` is blocked by auto mode; overwrite instead
- Folder access outside C:\GitHub is blocked (auto mode): ask the user to copy data into C:\GitHub\test
- Node in the device shell needs NODE_USE_ENV_PROXY=1 for https
- Git: commit with -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com (no identity in the shell); delete permission per chat on C:\GitHub
- UI harness: stage app/ui/* + build/ui-preview/{mock-htk,preview-data,rom-preview-data}.js → container Playwright; set cfg.upscale.inputs=[…];render() first (input isn't remembered)

## Files that matter most
app/ui/index.html (preview ~2160–2460, panDrag ~2545, askTools/installAll ~1280/1400) · app/main.js (download/githubApiAsset ~171, fetchPack/installTool ~300, addModel) · app/core/ncnn.js · app/core/upscale.js (ditherScore ~246) · app/core/smart.js · tools/dither-tune.js · build/package.sh
