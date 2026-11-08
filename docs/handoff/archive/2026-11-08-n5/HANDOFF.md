# R64texHD handoff #5 — 2026-11-08
## Scope
Portable Windows Electron app (app/, plain JS, Electron 38). Research roadmap: docs/research/Better N64 texture upscaling.md — items 1–12 done (12 = "your own models" lite), 13 (experiments) left.

## Changes we made (this chat, all committed)
- 359a557 roadmap 10: Compare grid (2–4 versions side by side, per-texture picks used by the run); b658a3d v0.9.0.0
- 14293ef edge-aware (wrap/mirror) shrink for half copy + supersample; 9fc738e "Pack the half-size copy" button
- a40a499 your own 4× Real-ESRGAN ncnn models (Settings, AI model, Compare)
- fd9fba5 + dfa8182 roadmap 11: ONNX engine (app/core/onnx-run.js, onnxruntime-node 1.22 DirectML/CPU, TextureDAT2 + RGT-S dither, optional download), v0.9.1.0
- a757616, 46a0c4d, f4bd4f9, 8cebfc0 build: package.sh without unzip + tool checks; build/release.sh + release.cmd (owner: merge handoff branch, use/build zips, verify, notes, tag + release)
- 7062ada handoff settings: owner pushes/releases
- bcd1a0b, da980cb, c04b6a3 Upscale page: preview 70% / 50vh with grip, Output panel (file type .PNG/.DDS, DDS compression, Compare, Open folder, Reset), input not remembered ("Normal Textures"), output placeholder; splash gap +3 chars between blue/pink
- 26a5f1b README v0.9, title image with catchphrase (docs/r64texhd-title-phrase.png), new screenshots + upscale-grid
- 06ebb06 Smart route `aidither`: dithered AI textures → RGT-S dither when ONNX engine installed (no softening)
- Releases v0.9.0.0 and v0.9.1.0 published on GitHub (4 zips each for 0.9.1.0, verified 200)

## Changes we should make
- H: Windows test (needs user or bot): ONNX engine download + DirectML start + speed/VRAM; new Upscale page (grip, panel, reset, small windows); Compare with real AI; your own model; Smart aidither; items 6–9
- H: user pushes handoff/next (06ebb06 local only; GitHub handoff/next = 26a5f1b, main = 7062ada); owner merges + next release (bump version, build\release.cmd)
- M: tune dither thresholds (DITHERED 0.12, DITHER_NEAR 56) on real dumps (dump folder is outside C:\GitHub: ask access)
- M: own models: read scale from .param instead of file name
- L: roadmap 13 (ncnn vs DML timing on AMD/Intel, CPU lane, TensorRT/WinML); ORT session per GPU, fp16 models; Compare "Original" cell

## Current state
- Works (tests 96 pass): everything above in Node/Chromium harness; ONNX verified on Linux CPU (both models, full pipeline)
- Untested on Windows: DirectML, new UI layout at small window sizes, release.cmd on the owner's PC (worked once on user's PC)

## Decisions
- Output is PNG or DDS only ("same" migrates to DDS); format + DDS compression live in the Output panel, not Advanced
- Preview not sticky any more (50vh would cover settings)
- ONNX runs as child process (process.execPath + ELECTRON_RUN_AS_NODE), Real-ESRGAN-style folder CLI; Smart keeps Real-ESRGAN except aidither
- No NC model downloads from the app (licence); users bring their own models

## Watch out for
- Pushing: user runs `git push origin HEAD:refs/heads/handoff/next`; owner merges; never push from the device shell (no creds)
- release.sh stops on uncommitted changes (build/set_icon.py CRLF noise was reverted once)
- Full package.sh > 3 min: run its parts stepwise in the device shell (unzip/icon, scenes+models+onnx sections via sed extracts, zip -6)
- Git from $HOME/mnt/GitHub/R64texHD; delete permission is on C:\GitHub (connected root)
- UI screenshots: tar app/ui (+ build/ui-preview) → stage → container Playwright with mock-htk.js; docs shots: build/ui-preview/docs-shots.py (needs preview-data.js from make-preview-data.js)
- onnxruntime-node npm install needs --ignore-scripts (postinstall hits nuget, blocked)

## Files that matter most
app/ui/index.html (upscale page, previewPanel/upSide/compare ~2080–2300) · app/core/tasks.js (upscaleTask, preview, runAi/aiCan) · app/core/onnx-run.js · app/core/smart.js · app/main.js (tools(), installTool) · build/package.sh · build/release.sh
