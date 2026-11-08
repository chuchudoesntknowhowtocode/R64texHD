# Roadmap 9: supersample and half-size copy
## Summary
upscale(): opts.supersample renders at min(2× target, max size) and shrinks with Lanczos (shrinkCut: re-cuts binary alpha at the threshold, forces opaque alpha back to 255). Worker saveHalf(): with halfNoExt, saves a half-size copy (never below the source size). tasks: half → "<output> (half size)" with other files copied too, .part cleanup on cancel, result.half; estimate: disk ×1.25 for half, seconds ×3 for supersample. Two Advanced rows; defaults off.
## Decisions
- MMPX and Pixel art skip supersampling (they're exact by design).
- Half folder sits next to the output folder, not inside it (keeps the main pack clean for .rtz packing).
- Resize uses clamp edges (tiling not passed through the shrink; small effect at the border).
## Files touched
app/core/upscale.js, app/core/worker.js, app/core/tasks.js, app/ui/index.html, app/main.js, tests/core.test.js, CHANGELOG.md
## Follow-ups / open questions
- Offer "pack the half-size copy too" in the finish dialog.
- Edge-aware (wrap/mirror) shrink.
