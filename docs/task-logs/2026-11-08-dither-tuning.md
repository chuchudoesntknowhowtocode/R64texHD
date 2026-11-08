# Dither threshold tuning on real captures
## Summary
Scored 160 SF2 Turbo screen captures (C:\GitHub\test\capture, .map ignored) with tools/dither-tune.js and checked the top scorers by eye (dither mask overlay). DITHER_NEAR 56 is right (40-80 give the same hits; 32 drops real gradients). The weak spot was the share: flat/black areas watered it down, so 3 of 7 clearly dithered gradients sat under 0.12. ditherScore now divides by busy (non-flat) pixels: dithered gradients 0.136-0.226, partly dithered jet 0.090, noisy detail <= 0.027. DITHERED stays 0.12 (sits in the gap).
## Decisions
- Keep DITHER_NEAR 56 and DITHERED 0.12; change the denominator instead (one-line idea, keeps small N64 textures, which have few flat pixels, close to old scores).
- Jet (0.090, checker shading mixed with real detail) left out on purpose: conservative.
## Files touched
app/core/upscale.js (ditherScore busy share, `lim` param, DITHER_NEAR exported), tools/dither-tune.js, tests/smart.test.js (flat-screen band case), CHANGELOG.md
## Follow-ups / open questions
- Re-check on a raw N64 dump (all captures were SNES, none hit the AI route: colours < 96, so aidither untested on real data).
