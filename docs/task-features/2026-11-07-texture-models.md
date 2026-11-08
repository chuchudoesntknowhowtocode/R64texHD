# Roadmap 7: texture models for Real-ESRGAN (HDCube, GameAI 2.0, PixelPerfectV4)
## Summary
build/models/convert.py turns ESRGAN .pth files (zip or legacy pickle, old or BasicSR keys) into ncnn .param/.bin without PyTorch (fp16 weights, fp32 bias, Split layers for fan-out). build/models/check.py runs the result with ncnn (CPU) against a NumPy ESRGAN on the same weights (self-test: 4.8e-9). package.sh packs build/models/out + CREDITS into <name>-models.zip and writes assets/models/remote.json; Settings › Texture models downloads it into Real-ESRGAN's models folder; AI model row gains HDCube / GameAI / Pixel (two rows of three).
## Decisions
- Optional download, not in the app zip (user default): keeps the zip at 163 MB.
- Only 4x ESRGAN models; the 1x DitherDeleter / DEDXT wait for roadmap 8 (Real-ESRGAN can't run 1x).
- Model ids: hdcube-x4, gameai2-x4, pixelperfect4-x4 (Real-ESRGAN -n). Scale slider's AI stop keeps the Settings model (Art → General).
- Not in the startup "missing tools" prompt (optional).
## Files touched
build/models/{convert.py, check.py, CREDITS.txt}, build/package.sh, app/main.js, app/ui/index.html, .gitignore, THIRD_PARTY_NOTICES.md, CHANGELOG.md
## Follow-ups / open questions
- Waiting for the user to download the three .pth files into build/models/src; then: convert.py, check.py on each, rebuild, test on Windows with the real Real-ESRGAN.
- The pack URL points at the GitHub release (v<version>): it only downloads once that release exists and the repo is public (same as the scenes pack).
