# ONNX engine (roadmap 11)
## Summary
Second AI engine: app/core/onnx-run.js (Real-ESRGAN-style folder CLI) runs onnxruntime-node in its own process (process.execPath + ELECTRON_RUN_AS_NODE), DirectML on Windows with CPU fallback, tiles > 256 px with 16 px overlap. Models TextureDAT2 and RGT-S dither (CC BY 4.0) as the optional "ONNX engine" download (108 MB, R64texHD-v<ver>-onnx.zip, assets/onnx/remote.json). Works in the existing AI pipeline (pad, colour fix, finish), AI model setting, Compare and picks. v0.9.1.0.
## Decisions
- Separate process, not utilityProcess: same spawn path as Real-ESRGAN, testable with plain Node.
- onnxruntime-node 1.22.0 win32-x64 binaries only (its npm package ships DirectML.dll); no CUDA.
- Smart still routes AI to Real-ESRGAN models; ONNX is chosen via AI model / Compare / picks.
- Spike verified on CPU in the cloud (Linux): both models load (opset 17, dynamic size) and run ~1 s for 48 px input.
## Files touched
app/core/onnx-run.js · app/core/tasks.js · app/main.js · app/ui/index.html · build/package.sh · build/onnx/CREDITS.txt · tests/onnx.test.js · tests/fixtures/nearest4x.onnx · CHANGELOG.md · THIRD_PARTY_NOTICES.md
## Follow-ups / open questions
- Windows test: DirectML start, speed per texture, VRAM; tile size vs GPU memory setting.
- Smart: RGT-S dither for dithered world textures when the engine is installed.
- ORT session per GPU / size buckets (research item), fp16 models.
