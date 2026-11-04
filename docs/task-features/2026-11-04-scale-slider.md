# Scale slider + full-original compare (1 · Upscale)
## Summary
Stepped Scale slider (1×, 2×, 4×, 8×, 16×, Fit, Anime, AI) replaces the Size buttons and sets the real run settings; dragging updates the preview live, release saves. Compare view now draws the full original under the upscaled image. Tested live in Chromium against the real UI + preview engine (GIF); 77/77 tests pass.
## Decisions
- Anime = method ai + realesrgan-x4plus-anime, AI = method ai + realesrgan-x4plus (sets the global AI model, same as Settings).
- Number steps switch method ai → standard; other methods (smart, pixel…) are kept.
- Anime / AI stops are disabled without Real-ESRGAN; dragging snaps to the nearest available stop.
- Old 3× / 6× settings show on the stop below, noted "custom". Longest side row moved next to the slider (shown for Fit).
- Preview passes its AI model to Real-ESRGAN (tasks.preview), so Anime vs AI previews differ before saving.
- Upscaled canvas gets its own checker so see-through parts don't show the original underneath.
## Files touched
app/ui/index.html, app/core/tasks.js, CHANGELOG.md
## Follow-ups / open questions
- Not tested on Windows / Electron, or with Real-ESRGAN previews.
- Smart preset stays highlighted at any scale (its preset doesn't fix size).
