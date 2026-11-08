# Smart: RGT-S dither route with the ONNX engine
## Summary
New Smart route `aidither`: when the ONNX engine is installed, a dithered texture that would go AI goes to RGT-S dither (rgts-dither-x4) with no dither-softening pre-pass. Falls back to the normal AI route if the model is missing. Run, estimate and preview all use it.
## Decisions
- Only textures Smart already sends to AI (≥ 32 px, ≥ 96 colours) and dithered (score ≥ 0.12); HD / MMPX / pixel routes unchanged.
- Needs only the ONNX engine (not Real-ESRGAN).
## Files touched
app/core/smart.js · app/core/tasks.js · app/ui/index.html · tests/smart.test.js · CHANGELOG.md
## Follow-ups / open questions
- Check on real dithered N64 dumps (thresholds DITHERED 0.12 / DITHER_NEAR 56).
