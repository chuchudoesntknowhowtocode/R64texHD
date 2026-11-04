# R64texHD handoff #2 — 2026-11-04

## Scope
v0.8.0.1 review, QoL fixes, Upscale UI work, upscaling research; next = research roadmap.

## Changes we made
- 2da2949 handoff: docs/handoff #1 committed after local fast-forward to 8c2d5e2 (via git bundle)
- d462c08 fix: AI batch → HD fallback, download 30 s timeout + .part cleanup, same-output-name skip, copy-error skip, texconv 5 min limit, estimate sample fix, preview tiling once, workers close on quit
- 9d60740 feat: clickable Upscale input card, folder-with-texture pixel icon (pixel-icons.js pixelSprite)
- 75e98dd perf: estimate caches classify results (path+size+mtime), stopEstimate() on task start
- 2179e66 feat: stepped Scale slider 1×/2×/4×/8×/16×/Fit/Anime/AI replaces Size buttons; full original under compare line; Smart caption shows real scale
- 08a848a docs: research report docs/research/Better N64 texture upscaling.md

## Changes we should make
- H roadmap 1: one ncnn spawn per folder, -j 4:4:4, -g explicit, multi-GPU by pixel count
- H roadmap 2–3: texconv -bc x -m 0, -wrap/-mirror from tiling, keep-coverage only binary alpha, parallel encodes; alpha classify/bleed/separate/threshold
- M roadmap 4–6: low-freq colour fix (RGB only); replicate pad + 3×3 tiling ≤32 px
- M roadmap 7–10: bundle permissive ESRGAN models (HDCube, GameAI, PixelPerfectV4, DitherDeleter, DEDXT) + credits; Smart v2; 4x→downscale; comparison grid
- L roadmap 11–13: onnxruntime-node DirectML utilityProcess (TextureDAT2, RGT-S_dither); model manager for NC models; experiments
- L untested on Windows: download timeout, AI fallback, Scale slider in Electron, Anime/AI previews

## Files changed
app/main.js, app/core/tasks.js, app/core/dds.js, app/ui/index.html, app/ui/pixel-icons.js, CHANGELOG.md, docs/task-logs/*, docs/task-features/2026-11-04-scale-slider.md, docs/research/*

## Current state
- Works: 77/77 tests; Chromium harness live test of Upscale page + real preview engine
- Not built (no builds unless asked)

## Decisions
- Anime = method ai + realesrgan-x4plus-anime; AI = method ai + realesrgan-x4plus (global model setting)
- Number steps switch ai → standard; disabled AI stops snap to nearest available
- Same-output-name textures: keep first, skip rest
- NC models only as opt-in downloads; upscayl-bin is AGPL (avoid bundling)

## Watch out for
- Device shell can't reach GitHub (403); user pushes manually. Commit with -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com
- Node 22 here: run tests with `node --test tests/*.test.js` (dir arg fails)
- CHANGELOG has two "### Upscaling" headings: insert under "## Unreleased" explicitly
- Live UI test: stage app/ui+core as a tar, run Playwright harness with a stubbed window.htk in the container, delete after
- C:\GitHub\_upstream\r64-update.bundle (178 MB) left over; user may delete

## Enhancements
- Reuse classify cache in Smart run (S, M)
- Smart preset stays highlighted at any scale (S, L)

## Open questions
- none

## Files that matter most
app/core/tasks.js (upscaleTask AI loop ~325-360, preview, estimate), app/core/dds.js (encodeTexconv), app/core/worker.js, app/ui/index.html (setCard, scaleSteps, drawPreview)
