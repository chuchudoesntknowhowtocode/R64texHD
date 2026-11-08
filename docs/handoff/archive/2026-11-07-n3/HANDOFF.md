# R64texHD handoff #3 — 2026-11-04

## Scope
Research roadmap (docs/research/Better N64 texture upscaling.md) items 1–6, approved by the user. v0.8.0.1 + local work.

## Changes we made
- f256a85 perf: roadmap 1 — one Real-ESRGAN run per AI group, -j 4:4:4, -t covers largest padded texture (≤400, Auto only), progress from output folder; on failure retry unfinished at -t 128, then HD 4× fallback
- 0b45703 feat: roadmap 3 — BC7 quality setting (Settings › Upscaling › Performance: Fast -bc q / Normal / Best -bc x, default Best); texconv -wrap/-mirror when both axes tile the same way
- Earlier (handoff #2 chat): d462c08 review fixes, 9d60740 input card, 75e98dd estimate cache, 2179e66 Scale slider, 08a848a research report

## Changes we should make
- H: get the 9 local commits (8c2d5e2..0b45703) onto GitHub — user's push failed, error unknown
- H: roadmap 4 — alpha classify (opaque/binary/graded), dilation bleed, separate alpha upscale, user threshold
- M: roadmap 5 — low-frequency colour fix vs original (RGB only)
- M: roadmap 6 — replicate pad for clamp; 3×3 tile pad for ≤32 px
- L: Windows test of AI one-spawn + Low retry, BC7 Best speed on a real dump, Scale slider in Electron, download timeout
- L: roadmap 2 multi-GPU (skipped: single GPU) — needs ncnn device list probe + Settings picker

## Current state
- Works: 79/79 tests (node --test tests/*.test.js); stand-in Real-ESRGAN (100 textures, crash at 40 → 60 retried) and stand-in texconv (args checked) runs
- Not tested with real tools / on Windows since handoff #2

## Decisions
- Multi-GPU skipped: user's PC is a desktop with one RTX 4060 8 GB
- BC7 default Best (user's choice, per report)
- -wrap/-mirror only when both axes agree; mixed → plain edges
- -g stays the Settings choice (Auto = ncnn default, prefers discrete GPU)
- Anime = ai + realesrgan-x4plus-anime; AI = ai + realesrgan-x4plus
- NC models only as opt-in downloads; upscayl-bin is AGPL (don't bundle)

## Watch out for
- Pushing: device shell gets 403 from proxy; the cloud GitHub link has no push access to this repo. User pushes manually.
- Use $HOME/mnt/R64texHD (delete allowed there) for git, not $HOME/mnt/GitHub/R64texHD — the latter leaves .lock / tmp_obj files
- Commit with -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com
- Node 22: `node --test tests/*.test.js` (dir arg fails)
- CHANGELOG has two "### Upscaling" headings: insert under "## Unreleased" explicitly
- dds ALPHA_REF is 0.5 (not 128)
- Stand-in tools for tests: write them outside mnt ($HOME/…), delete after
- Old per-project starter "R64texHD — continue" (trig_01VCx4qrsXU5XNgpZrPY33h5) exists; new rule: use the shared "handoffchat — continue" only

## Enhancements
- Reuse classify cache in Smart run (S, M)
- Smart preset stays highlighted at any scale (S, L)
- BC7 quality per preset instead of global (S, L)

## Open questions
- What error did the user's `git push` show?

## Files that matter most
app/core/tasks.js (upscaleTask AI branch ~325-380, aiArgs), app/core/dds.js (texconvArgs, mipChain, isCutout), app/core/worker.js (aiPrep/aiFinish), app/core/upscale.js (fillTransparent, hardAlpha), app/ui/index.html (settings rows ~1130)
