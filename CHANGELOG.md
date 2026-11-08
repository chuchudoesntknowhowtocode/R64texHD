# Changelog

## Unreleased

### Smart
- Dither detection counts only the busy (non-flat) pixels, so a dithered sky or floor on a mostly black or flat texture is now found and softened (tuned on SF2 Turbo screen captures: 7 of 7 dithered gradients found, was 4; no noisy texture flagged). New `tools/dither-tune.js` scores a folder at several limits.

### Upscale page
- The preview takes the left 70% and half the window's height; drag the small handle under it to make it taller or shorter (back to half the window when you leave the page or restart).
- New **Output** panel on the right: **File type** (.PNG / .DDS, moved from Advanced options; "Same as input" is gone, old settings become DDS), **DDS compression**, **Compare** (on/off, picks saved, clear all), **Open folder** and **Reset Upscaler** (every Upscale setting back to default and the input cleared, after a Yes / Cancel).
- The input is no longer remembered between starts: the box shows a grey "Normal Textures" until you choose one. The output box shows a grey "HD Upscaled Textures" when empty and still remembers its folder.
- **Smart + ONNX engine**: with the ONNX engine installed, dithered detailed textures go to **RGT-S dither** (trained on dithered textures) instead of being softened first and run through Real-ESRGAN. Works without Real-ESRGAN too. The estimate, the log and the preview caption show the new "AI dither 4×" route.
- Splash catchphrase: three characters more space between the blue and the pink half.

## v0.9.1.0

### Upscaling
- **ONNX engine** (Settings › Helper tools, optional 108 MB download): a second AI engine on onnxruntime with **DirectML** (any DirectX 12 graphics card; falls back to the CPU), with the two strongest permissive game-texture models: **TextureDAT2** (4xTextureDAT2_otf) and **RGT-S dither** (4xTextures_GTAV_rgt-s_dither, trained with dithering), both CC BY 4.0 by Philip Hofmann. Pick them under Settings › AI model; they also show up in the Compare grid. Real-ESRGAN isn't needed for them. It runs as its own process, so the app stays responsive; big textures run in overlapping tiles. Credits in `ONNX-CREDITS.txt`.

## v0.9.0.0

### Upscaling
- **Your own models** (Settings › AI upscaling): add any 4× Real-ESRGAN ncnn model (.param + .bin), e.g. a converted OpenModelDB model. It joins the AI model choices and the Compare grid, and can be removed again. Models stay on your PC: many popular ones are non-commercial, so R64texHD never ships or shares them.
- **Compare** (Upscale preview): a button next to the zoom shows 2–4 versions of the same texture side by side (HD 4×, MMPX, Pixel-perfect and each AI model you have), with one zoom and scroll for all. **Use this** saves the pick for that texture (by its RT64 hash); the run then makes that version instead of the chosen method or Smart's route. Picked textures get a ✓ in the texture list; picks can be cleared one by one or all at once.
- **Supersample** (Advanced options): each texture is made twice as big, then shrunk back with Lanczos, for calmer sharpening and fewer AI artefacts (with AI on a 2× target, the AI's 4× result is shrunk to 2×). Cut-outs stay hard.
- **Half-size copy** (Advanced options): also saves everything at half size in "<output> (half size)", other files included, so one run gives a 4K pack and an HD pack. Tiling textures (wrap / mirror edges) are shrunk across their border, so the half copy and Supersample have no seams. When the run finishes, **Pack the half-size copy** opens Pack with that folder.
- **Smart mode v2**: true pixel art (sprites, fonts, HUD with hard cut-outs and few colours, flat tiles) now goes to **MMPX**, which smooths diagonals but only uses the texture's own colours. With the texture models installed, big detailed textures use **GameAI** and colourful cut-out sprites (16–64 px) the **Pixel** model; HDCube is never picked for small textures. Dithered textures (checker / ordered dither dots) are softened before HD or AI upscaling. The preview names the route (e.g. "AI 4× (GameAI), dither softened").
- New method **MMPX** (pixel art with smooth diagonals) under Advanced options › Method.
- **Texture models** (Settings › Helper tools): an optional download of three AI models made for game textures, for Real-ESRGAN: **HDCube** (CC0, keeps the game's look), **GameAI 2.0** (WTFPL, game textures) and **Pixel** (PixelPerfectV4, WTFPL, sprites). Pick them under Settings › AI model; the Scale slider's AI stop uses that choice. Credits in `texture-models-CREDITS.txt`.
- AI upscale: textures 32 px or smaller get a full copy of themselves on every side (by their tiling) before Real-ESRGAN, instead of an 8 px border, so tiny repeating textures don't get seams.
- Preview: the box grows with the window (300–720 px tall) and Fit fills it with the whole texture. New − / + buttons and the **mouse wheel** zoom from 100% up to 800%, centred on the cursor; the % button jumps to 100% (actual size). Replaces Fit / 1:1 / 2:1.
- **AI colour fix** (on by default): AI results are pulled back to the original's colours (broad hue / brightness drift removed, detail kept, colour only). Grey intensity textures stay grey.
- **Cut-out alpha**: alpha is sorted into opaque / cut-out / soft (DXT noise near 0 or 255 still counts as cut-out), grown on its own (never sharpened, never by the AI) and cut at the new **Cut-out threshold** slider (default 50%). Hidden colours now bleed all the way out, so no dark fringes or halos on fences and leaves.
- **BC7 quality** (Settings › Upscaling › Performance): Fast · Normal · Best, default **Best** (texconv `-bc x`, sharpest on flat colours and text, slower). Applies to Upscale, Convert and the pack DDS fix.
- BC7 DDS mipmaps follow the texture's tiling: textures that tile or mirror on both axes get `-wrap` / `-mirror`, so far-away mip levels have no seams.
- **Scale slider** on 1 · Upscale: one stepped slider for 1× · 2× · 4× · 8× · 16× · Fit · Anime · AI (Anime / AI use Real-ESRGAN's Art / General model). The preview follows it live while dragging; it replaces the Size buttons.
- Preview compare: the full original now sits underneath, and the line uncovers it; Smart's caption shows the real scale (e.g. HD 16×).
- The input box on 1 · Upscale shows a folder-with-texture icon and is clickable: it opens the textures' folder, or the folder picker when nothing is chosen.

### Speed
- AI upscale: Real-ESRGAN now runs once per job instead of once per 32 textures, so the model and graphics card start once (about 156 starts saved on a 5,000-texture dump). It uses 4 load / process / save threads, and on Auto memory use the tile covers the largest texture, so there are no seams inside a texture. Progress counts the AI's finished files live.
- If Real-ESRGAN fails (often out of video memory), only the unfinished textures run again with Low memory use; anything still left is upscaled HD 4×.
- Upscale estimate: what each texture looks like is remembered (by path, size and date), so changing a setting re-estimates without reading every texture again; a running estimate stops when a task starts.

### Fixes
- AI upscale: a Real-ESRGAN failure on one batch (e.g. out of video memory) now upscales that batch HD 4× and carries on, instead of stopping the run.
- Downloads: stop after 30 s with no data, catch cut-off downloads, and remove the leftover .part file.
- Upscale: two textures that would save to the same file are skipped with a log line instead of overwriting each other; a file that can't be copied under "Copy other files" is logged and skipped.
- texconv gets a 5-minute limit per texture; the estimate's PNG size uses the right samples; preview reads tiling once; preview / ROM workers close on quit.

## v0.8.0.1

### Upscaling
- **Presets** on the Upscale page: **Smart** (the new default), **Faithful 2×**, **HD 4×**, **Ultra AI 4×**
  and **Pixel-perfect**, plus **Save as preset** for your own. The options fold away under
  **Advanced options**; changing one makes the preset "Custom".
- **Smart mode**: every texture is looked at (size, colours, transparency) and gets its own method:
  pixel-perfect for tiny, font and HUD textures; AI for big, detailed ones; HD 4× for the rest.
  - **No Real-ESRGAN:** Smart asks once to download it.
  - **No Vulkan graphics card:** the AI part uses HD 4× instead.
  - The log says what each texture got.
- **Estimate** before the run: disk size, video memory in game, time on this PC, and Smart's split.
- **Before / after preview**: one image with a drag line between the original and the result.
- **Existing setups:** on the first v0.8 launch, your Upscale options switch to the Smart preset once. Your
  folders are kept.

### The wizard of R64 (the footer)
- **The footer is the progress bar.** It replaces the bars in the status card, and the taskbar button shows
  the same progress (red on errors).
- **Scenes while a job runs:** classic scenes, **fights** (goblin, golem, robot, dark twin) with VS
  banners, and a **bonus stage** after every third win.
  - The wins are saved between launches.
  - A job ending mid-fight is an instant win; cancel and errors end in a burst.
- **Psychedelic mode:** LSD and DMT trip scenes and the machine elf, off by default. New installs are
  asked on first launch.
- **When idle:** he peeks out of the pipe with a catchphrase.
- **Poking:** click him (or whoever he's fighting).
- **Minimum window width** is now 1280 px, so every scene plays as drawn.

### Sound
- **Sound effects** for the scenes, off by default.
- **Background music**, on by default: a normal playlist, and a Psychedelic one when that mode is on. Each
  cycles through its tracks.
- **Custom sounds:** add your own tracks (names starting with `dmt` go in the Psychedelic playlist), or
  replace an effect by dropping `<slot>.ogg` in `data\sounds`.
- **Mute button** in the bottom right corner. It silences everything without changing your settings.

### Settings and look
- **Settings layout:** each area is a box (Folders, Helper tools, Upscaling, Look and feel, Sound, App)
  with subsections.
- **Volume sliders** for sound effects and music.
- **Graphics card line** above Real-ESRGAN: Vulkan or not, the GPU model and its video memory.
- **Collapsible menu:** the grey tab on its edge folds it into a narrow strip of icons.
- The idle peek's speech bubble sits beside the wizard's head.

### Smaller download
- **222 MB → 163 MB** zipped:
  - English is the only Chromium language shipped;
  - box art is WebP at the size it's shown;
  - music is Opus at 96 kbps.
- **Scenes:** the fights and trips (about 30 MB) are a separate pack on the release, downloaded once in
  the background into `data\scenes` and checked against a SHA-256. The classic scenes ship with the app.

## v0.7.1.1

- **Ship Mods .o2r** for the Harbour Masters ports:
  - recognises the game from the archive;
  - finds the ports installed on this PC;
  - works with older `.otr` archives.
- **Rice / GLideN64** packs, both ways, and into Ship ports. R64texHD becomes GPL-2.0-or-later.
- **Check a pack** with a one-click **Make them DDS** fix.
- **Recomp mod info** in `.rtz` packs.
- **ROM Tools** with box art for 303 North American games.
- **Splash screen** with catchphrases.

Earlier versions: see the [git history](../../commits/main).
