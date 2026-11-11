# R64texHD handoff #7 — 2026-11-11
## Scope
Portable Windows Electron app (app/, plain JS, Electron 38). Roadmap 1–12 done; 13 partly (timings done). Latest release v0.9.2.0 (published 2026-11-08 16:25 UTC).

## Changes we made (since #5, all committed; pushed up to ada2e28)
- 6e18a43, e89cb96, b06de12 dither: tools/dither-tune.js; ditherScore = hits / busy (non-flat) pixels; DITHERED 0.10 (SF2T SNES noise ≤ 0.03, Perfect Dark dithered 16-colour 0.10–0.125); DITHER_NEAR 56
- 35e2fad, 7ed1c49 own models: app/core/ncnn.js modelScale follows the ncnn graph (Interp/PixelShuffle; parallel branches don't multiply), nameScale fallback; non-4× refused; verified on 8 real .param
- b65036d v0.9.2.0; ed504fd helper tools: first start offers all 4, GitHub API fallback on 5xx, local pack zips next to the app
- e91b099, 90d39b2 preview: zoomed → drag to pan, click centres; half-box padding so edges/corners reach the centre (padView, PV.scroll null = centred); Compare zoom keeps the middle spot
- 3d91c78 Compare Original cell; 16c9f9e split line outline
- 660b557, 67159b6, 39a7dca tools/bench.ps1 + docs/research/bench-2026-11-08.md (RTX 4060: ncnn x4plus 1.06 s, ONNX 4.9–5.7 s per 512×256; Intel UHD 6.35 / 25.6 s; ONNX CPU 32 s)
- ada2e28 release.sh defaults to handoff/next; v0.9.2.0 released (0a9165f notes)

## Changes we should make
- M: next release when there's enough: Unreleased = Original cell, edge pan, bench.ps1, release.sh fix (bump version, rebuild via ~/pk.sh trick, user runs build\release.cmd)
- L: aidither untested on real data (no dithered texture in SF2T/PD/GE/MK64 reaches the AI route)
- L: roadmap 13 leftovers: AMD timing, atlas batching on ORT, TensorRT/WinML; DirectML runs some nodes on CPU (ORT warning)
- L: ONNX runner doesn't log the card name (bench card column = "DirectML (GPU n)")

## Current state
- Works: tests 98 pass; v0.9.2.0 Windows test passed (user, 8 items); release downloads 200
- dist/ holds the v0.9.2.0 build; its folder has later UI files copied in, its zips are the released ones

## Decisions
- Dither: change the denominator, not the constants; cut-off 0.10 from Perfect Dark
- Model scale: layer scale wins; the name wins only when it says smaller
- First start = all tools; later startups check only texconv + Real-ESRGAN
- Both engines' "auto" picks the RTX on the user's laptop: no GPU-choice change
- No CPU lane: these ONNX models are too slow on the CPU

## Watch out for
- package.sh onto the mount gets killed (>180 s) and wipes dist first: build in ~ with `sed -e "s#^HERE=.*#HERE=\"$PWD\"#" -e 's#\$HERE/dist#$HOME/dist#g' -e 's#^OUT=.*#OUT="$HOME/dist/$NAME"#' build/package.sh > ~/pk.sh; bash ~/pk.sh` (~66 s), then `cp -f ~/dist/*.zip dist/` and `cp -rf ~/dist/<name>/. dist/<name>/` (exe/dll copy fails while the app runs; identical)
- `rm -rf dist` and folder access outside C:\GitHub are blocked by auto mode: overwrite; ask the user to copy data into C:\GitHub\test
- Background jobs in device_bash die when the call ends
- Node in the device shell needs NODE_USE_ENV_PROXY=1 for https
- Git: -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com; delete permission per chat on C:\GitHub; local branch is main (pushed to handoff/next)
- Computer use can't drive the Claude app or R64texHD.exe (not resolvable): Windows tests are MANUAL STEPs
- PowerShell scripts: Start-Process -Wait for R64texHD.exe (GUI exe); logs inside the repo (TEMP is unreadable)
- UI harness: stage app/ui/* + build/ui-preview/{mock-htk,preview-data,rom-preview-data}.js → container Playwright; set cfg.upscale.inputs=[…];render() first

## Files that matter most
app/ui/index.html (preview ~2160–2470, padView/setPreviewZoom ~2420, panDrag ~2580, compare ~2305–2410, askTools ~1280) · app/main.js (download ~171, fetchPack/installTool ~300, addModel) · app/core/{ncnn,smart,upscale,onnx-run}.js · tools/{dither-tune.js,bench.ps1} · build/{package.sh,release.sh}
