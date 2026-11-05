# Roadmap 3: texconv BC7 quality + tiling-aware mips
## Summary
texconv gets -bc x (Best, default) / none (Normal) / -bc q (Fast) from a new Settings row "BC7 quality", and -wrap / -mirror when both axes of the texture tile the same way. Roadmap 2 (multi-GPU) skipped: user has a single RTX 4060.
## Decisions
- Default Best, as the research report recommends (user's choice).
- -wrap/-mirror only when both axes agree (texconv's flag covers both axes); mixed or clamp → plain.
- Already in place before this task: --keep-coverage only for cut-outs, parallel texconv (one per worker).
- Global setting (like AI tile/GPU), not per preset.
## Files touched
app/core/dds.js (texconvArgs), app/core/image.js, app/core/tasks.js, app/core/worker.js, app/main.js, app/ui/index.html, tests/core.test.js, CHANGELOG.md
## Follow-ups / open questions
- Not run with the real texconv on Windows; checked with a stand-in that logs its arguments.
- Measure Best vs Normal time on a real dump; if too slow, consider Normal for HUD-free bulk.
