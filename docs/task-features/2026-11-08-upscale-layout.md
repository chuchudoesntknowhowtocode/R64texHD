# Upscale page rework: 70/30 preview + Output panel
## Summary
Preview 70% wide, 50vh tall with a bottom-centre grip (PV.h, in memory only: reset on page change / restart). Right 30% "Output" panel: File type (.PNG/.DDS), DDS compression, Compare on/off + picks/clear all, Open folder, Reset Upscaler (confirm). Input path not remembered ("Normal Textures" placeholder); output placeholder "HD Upscaled Textures" (remembered). Splash phrase letter-spacing 2px.
## Decisions
- Output format is PNG or DDS only; old "same" settings / user presets → DDS (UI and main.js default).
- Format and DDS compression rows removed from Advanced (now in the panel); "Fences far away" stays there.
- Reset keeps the output folder and Compare picks; uses the Smart preset defaults.
- Preview no longer sticky: at half the window it would cover the settings below.
- "Do the same for the output text" read as the grey placeholder, not letter spacing.
## Files touched
app/ui/index.html · app/main.js · CHANGELOG.md
## Follow-ups / open questions
- Windows check at small window sizes (panel squeezes below ~1100 px wide).
