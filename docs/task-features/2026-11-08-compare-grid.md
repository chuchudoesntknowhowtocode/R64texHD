# Compare grid + per-texture picks (roadmap 10)
## Summary
Upscale preview has a Compare button: 2–4 versions of one texture side by side (HD 4×, MMPX, Pixel-perfect, each installed AI model), shared zoom/scroll. "Use this" saves a pick per texture (RT64 hash, else path in the input); the run makes that version instead of the method / Smart route. Released as v0.9.0.0.
## Decisions
- Picks live in settings (`cfg.picks`, `cfg.compareSet`), sent with the upscale params; not part of presets.
- Pick ids: `hd` · `pixel` · `mmpx` · `ai:<model>`; AI picks fall back to the method (logged) when Real-ESRGAN / Vulkan / texture pack is missing.
- Dither softening for picks only when the run method is Smart, never for pixel / MMPX picks (same in preview and run).
- Cells render one at a time through the existing preview worker (no new IPC).
## Files touched
app/core/tasks.js · app/ui/index.html · tests/picks.test.js · CHANGELOG.md · app/package.json · build/ui-preview/mock-htk.js
## Follow-ups / open questions
- Test on Windows with real Real-ESRGAN (AI cells, timing with 4 AI cells).
- Maybe export/import picks with a pack; "Original" cell option.
