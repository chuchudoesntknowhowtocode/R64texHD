# AI colour fix (roadmap 5)
## Summary
`colourFix()` in upscale.js removes low-frequency hue/brightness drift from Real-ESRGAN output vs the source (RGB only, before alpha merge). Grey sources come back grey. Setting `upscale.colourFix` (default on), shown for AI and Smart. Before/after: `docs/screenshots/colour-fix-before-after.png`.
## Decisions
- Difference measured at source size (AI area-averaged), visible pixels only (alpha > 8), blurred with a weighted 2× box blur, radius max(2, min side / 16), grown back bilinearly.
- Grey test: every visible pixel within 2 between channels → output R=G=B.
- Only the AI path; Standard/Smooth/Pixel can't drift this way. ~130 ms for a 256→1024 texture.
## Files touched
app/core/upscale.js, tasks.js · app/main.js · app/ui/index.html · tests/colour.test.js, tests/alpha.test.js · CHANGELOG.md · docs/screenshots/colour-fix-before-after.png · docs/handoff/RESUME.md
## Follow-ups / open questions
- Demo uses simulated drift; check on a real Real-ESRGAN run on Windows.
