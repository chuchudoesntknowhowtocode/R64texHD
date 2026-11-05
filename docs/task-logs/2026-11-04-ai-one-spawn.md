# Roadmap 1: one Real-ESRGAN run per AI group
## Summary
The AI upscale loop spawns realesrgan-ncnn-vulkan once for the whole AI group instead of once per 32 textures. It passes -j 4:4:4, and on Auto memory use sets -t to cover the largest padded texture (capped at 400). Progress is counted from the output folder. On failure, unfinished textures retry once with -t 128, then fall back to HD 4×.
## Decisions
- -g stays as the user's Settings choice (Auto = ncnn's default, which prefers a discrete GPU). Multi-GPU split by pixel count needs a GPU tick list mapped to ncnn device ids: deferred.
- Tile auto rule: ceil(maxPadded/32)*32, min 32; above 400 px, leave it to Real-ESRGAN.
- Progress weights per texture: 10% prepare, 60% AI, 30% finish.
## Files touched
app/core/tasks.js (upscaleTask AI branch, aiArgs), tests/core.test.js, CHANGELOG.md
## Follow-ups / open questions
- Not run with the real Real-ESRGAN or on Windows; tested with a stand-in exe (100 textures; crash after 40 → 60 retried at -t 128).
- Multi-GPU split (needs GPU picker UI).
