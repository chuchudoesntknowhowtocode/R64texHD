# Upscale preview: fit to the box, zoom buttons, mouse-wheel zoom
## Summary
The preview box now fills the visible space (height clamp(300px, 100vh - 620px, 720px), was 180–360 px), and Fit shows the whole upscaled texture in it. Fit / 1:1 / 2:1 became − · Fit · + · %: steps of 25% between 100% (or Fit, if smaller) and 800%; the wheel over the preview zooms around the cursor; the % button = 100%.
## Decisions
- Fit is the default and the snap point; zoom-out stops at min(Fit, 100%).
- Ctrl+wheel is left to the browser.
- Panning when zoomed: scrollbars (wheel is zoom).
## Files touched
app/ui/index.html, CHANGELOG.md
## Follow-ups / open questions
- Drag-to-pan (e.g. middle or right mouse) if scrollbars feel clumsy.
- Built dist/R64texHD-v0.8.0.1 on the PC (Electron cached); not run in Electron by Claude — checked in Chromium with the mock bridge (1280×800, 1920×1040).
