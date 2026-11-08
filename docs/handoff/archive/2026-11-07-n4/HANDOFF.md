# R64texHD handoff #4 — 2026-11-07

## Scope
Research roadmap (docs/research/Better N64 texture upscaling.md): items 1–9 done; 10–13 left. v0.8.0.1 + local work.

## Changes we made
- 98aec3e, 1bcfc8f (other chat): roadmap 4 cut-out alpha (classifier, bleed, separate alpha, threshold), 5 AI colour fix
- 9d969bd feat: preview fills its box (clamp 300–720 px), − / Fit / + / % zoom, mouse-wheel zoom 100–800% at the cursor
- 25dc487 feat: roadmap 6 — full-tile AI padding for textures ≤ 32 px (aiPad); clamp already = replicate
- da3b7f0 + 2e1037e feat: roadmap 7 — texture models HDCube / GameAI 2.0 / PixelPerfectV4: build/models/convert.py (.pth → ncnn, no PyTorch), check.py (ncnn vs NumPy), Settings › Texture models download, AI model row (6 choices), package.sh makes <name>-models.zip + assets/models/remote.json
- 20f5c94 feat: roadmap 8 — Smart v2: MMPX (app/core/mmpx.js), routes mmpx / aisprite (Pixel model) / ai → GameAI with models, dither detector + softening, MMPX method
- 66368e4 feat: roadmap 9 — Supersample (2× then Lanczos, cut-outs re-cut) and Half-size copy ("<output> (half size)")

## Changes we should make
- H: user pushes (2 commits ahead: 20f5c94, 66368e4 — check `git status`)
- H: roadmap 10 — comparison grid (plan first)
- M: Windows test with real Real-ESRGAN: texture models, Smart v2 routes, supersample, half copy, preview zoom
- M: GitHub release v0.8.x: attach Windows zip + scenes zip + models zip (models download needs it + public repo)
- L: roadmap 11 (onnxruntime-node DirectML: TextureDAT2, RGT-S_dither, 1x dedither / DEDXT), 12 (model manager for NC models), 13 (experiments)
- L: tune dither thresholds (DITHERED 0.12, DITHER_NEAR 56) on real dumps; edge-aware shrink; pack the half copy too

## Current state
- Works: 92/92 tests (`node --test tests/*.test.js`); models verified (ncnn vs NumPy ~1e-5; demo pictures sane)
- Build: C:\GitHub\R64texHD\dist\R64texHD-v0.8.0.1 (+ -Windows.zip 163 MB, -models.zip 93 MB); test models pre-placed in dist\…\data\tools\realesrgan\models (data/ is excluded from the zip)
- Not tested on Windows: items 6–9, preview zoom, model download (needs release)

## Decisions
- Models: optional download, not in the app zip; ids hdcube-x4, gameai2-x4, pixelperfect4-x4; 1x models wait for roadmap 11
- Smart never picks HDCube; ai → GameAI with models; aisprite = binary alpha 16–64 px → Pixel model
- Roadmap 2 (multi-GPU) skipped: user has one RTX 4060 8 GB
- Supersample/half default off; half folder next to output, not inside

## Watch out for
- Pushing: device shell gets 403; cloud GitHub link has no push access. User runs `git push origin main` (cmd: `cd /d C:\GitHub\R64texHD`)
- Git from $HOME/mnt/R64texHD (delete allowed after asking once per chat); commit with -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com
- Full build/package.sh takes > 3 min (tool limit): refresh dist by copying app files into dist/R64texHD-v0.8.0.1/resources/app + `zip -q -r -6 … -x '…/data/*'`
- ncnn Python: ncnn.Mat(numpy) borrows memory — keep the array alive and copy outputs (np.array(o, copy=True))
- Downloads: built-in browser pane doesn't save files; Claude in Chrome does (→ C:\Users\Chuchu\Downloads, folder access granted)
- CHANGELOG: insert under "## Unreleased" → first "### Upscaling"
- UI screenshots: tar app/ui app/core build/ui-preview → stage → container Playwright with mock-htk.js; delete after

## Enhancements
- Comparison grid could reuse PV cache (S, H)
- Reuse classify cache in Smart run (S, M)

## Open questions
- none

## Files that matter most
app/core/tasks.js (upscaleTask, preview, estimate), app/core/upscale.js, app/core/smart.js, app/core/mmpx.js, app/core/worker.js, app/main.js (tools, installTool), app/ui/index.html (preview ~2050–2200, settings ~1130), build/models/*
