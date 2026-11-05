# Alpha handling for cut-outs (roadmap 4)
## Summary
Alpha classifier (opaque / binary / soft), full colour bleed under hidden pixels, alpha upscaled separately from colour (AI does colour only), user cut-out threshold. Before/after: `docs/screenshots/alpha-cutout-before-after.png` (source, before, after 50/30/70%).
## Decisions
- Binary = alpha within 8 of 0/255, with up to 0.5% in-between pixels allowed (DXT edges). Smart routing uses the same classifier.
- Pixels with alpha ≤ 8 count as hidden for the colour fill (they caused black fringes).
- Fill grows ring by ring until done (O(pixels)) instead of 8×scale steps.
- Real-ESRGAN input gets alpha = 255; upscale() grows alpha from the source at 1×.
- Threshold stored as percent (`upscale.alphaThreshold`, default 50) and passed as 0..1, clamped 0.02–0.98.
- DDS keep-coverage stays at ALPHA_REF 0.5: it must match the game's alpha test, not the cut threshold.
## Files touched
app/core/upscale.js, smart.js, worker.js, tasks.js · app/main.js · app/ui/index.html · tests/alpha.test.js · CHANGELOG.md · docs/screenshots/alpha-cutout-before-after.png
## Follow-ups / open questions
- Untested in the Electron UI on Windows (slider row + preview refresh) and with a real Real-ESRGAN run.
