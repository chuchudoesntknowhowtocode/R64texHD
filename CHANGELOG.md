# Changelog

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
