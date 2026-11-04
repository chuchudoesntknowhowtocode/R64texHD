Project: R64texHD — #2 — 2026-11-04 — 08a848a
Root: C:\GitHub\R64texHD
Scope: portable Windows Electron app: upscale DDS/PNG, convert RT64 dumps, pack/unpack .rtz
Goal: roadmap items 1–6 from docs/research/Better N64 texture upscaling.md (one commit each)
Done when: items 1–6 committed locally, 77+ tests pass, before/after pictures sent where the look changes
Stopped at: plan approved in principle ("i like it all"); item 1 not started — app/core/tasks.js:325-360 (AI batch loop, batch = 32)
Next action: item 1 — one realesrgan spawn per model/GPU folder, -j 4:4:4, explicit -g, -t >= padded size, progress by watching outDir; keep per-batch HD fallback
Last cmd: node --test tests/*.test.js → 77 pass
Last error: none
Uncommitted: none
Settings: chuchu on; previews=yes (send pictures/GIF); visual=live test in Chromium harness; commit locally, never push; commits authored chuchudoesntknowhowtocode
Open Qs: none
Read more: HANDOFF §Changes we should make, §Watch out for
