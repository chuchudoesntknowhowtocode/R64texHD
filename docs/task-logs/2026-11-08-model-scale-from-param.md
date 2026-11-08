# Own models: scale from .param
## Summary
New app/core/ncnn.js: modelScale(paramText) multiplies Interp (1=/2= scales) and PixelShuffle (0=) factors; nameScale(name) reads 4x-/_x2-style names. addModel (main.js) uses the layer scale, falls back to the name when the layers don't say, and rejects anything not 4× with "that is a N× model".
## Decisions
- Name wins when it says a smaller scale than the layers: x2plus-style models shrink the input first (pixel-unshuffle as Reshape/Permute), so their layers read 4.
- Already-added models are not re-checked (listing unchanged).
## Files touched
app/core/ncnn.js (new), app/main.js, tests/ncnn.test.js (new), CHANGELOG.md
## Follow-ups / open questions
- No real .param on the PC under C:\GitHub: try adding 4x-UltraSharp / a 2× model in the Windows test.
