# Roadmap 6: seam padding for tiny textures
## Summary
Before Real-ESRGAN, textures ≤ 32 px on both sides are padded by max(8, w, h) (a full 3×3 tiling by their edge mode) instead of 8 px; aiFinish / previewAi crop the same amount back. The AI tile size counts the real padded size.
## Decisions
- "Replicate for clamp" was already there: clamp edgeIndex repeats the edge pixel. Nothing to add.
- Pad is computed in the worker from the source size (job.pad = 'auto'), so prep and finish always agree.
- One pad for both axes (padImage takes one value); a 32×16 texture gets 32 px on all sides.
## Files touched
app/core/upscale.js (aiPad), app/core/worker.js, app/core/tasks.js, tests/core.test.js, CHANGELOG.md
## Follow-ups / open questions
- Not checked with the real Real-ESRGAN: compare a 16 px wrap texture tiled 3×3 before/after on Windows.
