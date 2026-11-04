# Estimate: cache classify results, stop on task start
## Summary
tasks.estimate reuses per-texture classify results (path + size + mtime, cap 200k); main.runTask calls tasks.stopEstimate(). 77/77 tests pass; 400-texture check: 534 ms → 347 ms on re-estimate (gain grows with texture size).
## Decisions
- Cache only in estimate; Smart upscale run still classifies fresh.
- Clear the whole cache when it hits 200k entries (simple, bounded memory).
## Files touched
app/core/tasks.js, app/main.js, CHANGELOG.md
## Follow-ups / open questions
- Could reuse the cache in Smart upscale's "Looking at the textures" step.
