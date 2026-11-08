# Changelog

## Unreleased

### Upscaling
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
