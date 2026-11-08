# Your own models (roadmap 12, lite)
## Summary
Settings › AI upscaling › Your own models: add a 4× Real-ESRGAN ncnn model (.param + .bin); it is copied into Real-ESRGAN's models folder, listed in AI model and the Compare chips, removable.
## Decisions
- No NC model downloads from R64texHD (licence risk): the user brings the files; R64texHD never ships them.
- Names are sanitised (lower-case, [a-z0-9._-]); built-in names (realesr*, texture pack) refused; .param must start with 7767517; 1×/2×/3×/8×/16× file names refused (AI step is always 4×).
- Removing the selected model resets AI model to General.
## Files touched
app/main.js · app/preload.js · app/ui/index.html · CHANGELOG.md
## Follow-ups / open questions
- Windows test with a real converted model; detect scale from the .param instead of the file name.
- Fast/Balanced/Quality variants per family; .pth → ncnn conversion in-app (convert.py is Python).
