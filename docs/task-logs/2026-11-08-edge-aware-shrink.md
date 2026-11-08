# Edge-aware shrink (half copy + supersample)
## Summary
Lanczos shrink reads across the border by the texture's edge mode (wrap / mirror), anti-ringing range too, so tiling textures shrink without a seam. Used by the half-size copy and Supersample.
## Decisions
- Clamp keeps the old fast path; wrap/mirror use a separate indexed kernel (`resizeEdges`).
## Files touched
app/core/upscale.js · app/core/worker.js · tests/shrink-edges.test.js · CHANGELOG.md
## Follow-ups / open questions
- Offer "pack the half-size copy too" in the finish dialog.
