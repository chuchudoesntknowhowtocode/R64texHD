R64texHD v0.7.1.1 - Reimagine Every Pixel  (portable)
==================================================
HD textures for N64 games: RT64 dumps, .rtz packs, Ship port .o2r mods and
classic Rice / GLideN64 packs.


Start: double-click "R64texHD.exe" (it shows as R64texHD in Task Manager).
Nothing is installed: no Python, no registry, nothing in AppData.
Put this folder anywhere you can write to (for example C:\Tools\R64texHD,
a second drive or a USB stick) and keep its files together.

Everything the toolkit saves stays in the "data" folder next to the program:
  data\settings.json   your folders and choices
  data\tools\          texconv / Real-ESRGAN if you download them in Settings
  data\chromium\       the window engine's own cache
  data\temp\           scratch files, cleared when you close the toolkit
To reset the toolkit, delete the data folder. To remove it, delete this folder.
To update, unzip the new version next to this one and copy this data folder
into it to keep your settings and downloaded tools.

First launch shows a Setup page: RT64 texture dump folder (optional), output
folder, and an optional Desktop shortcut.

At every start R64texHD checks for the two optional tools below. If either one
has not been downloaded yet it opens on Settings, where "Download" fetches it
into data\tools. Choose "Not now" to carry on without them, or turn off
"Check tools at startup" in Settings.

THE PAGES (sidebar)

1  Upscale Textures
   PNG / DDS textures: a whole folder (subfolders kept) or picked files.
   - Method: Standard (2x steps, sharpened after each step), Smooth,
     Pixel art, or AI (Real-ESRGAN, downloadable in Settings).
   - Size: 2x 3x 4x 6x 8x, or Fit the longest side to 512 - 4096 px.
   - Sharpness: Off / Soft / Normal / Strong / Extra.
   - Edges: Auto uses each texture's own tiling from the RT64 dump, so floors
     and walls stay seamless. Or Normal / Tile / Mirror for everything.
   - Cut-out edges: Hard (crisp leaves, fences, text) or Smooth.
   - Fences far away: keeps fences, grass and leaves from fading out in the
     distance (DDS output).
   - Output: same format as input, PNG or DDS (Auto BC1/BC3, BC7, BC3, BC1, none).
   - Live preview: the original and the upscaled texture side by side.
   When it finishes it offers to take you to 3 Pack / Check .rtz.

2  Convert RT64 Dump
   Turns an RT64 texture dump (.tmem + .tile.json files, from RT64's debugger:
   F1 > Textures > Start dumping textures) into PNG or DDS textures plus
   rt64.json. "Remember tiling" saves how each texture repeats (for Edges:
   Auto). "Only new textures" converts just what you dumped since last time.

3  Pack / Check .rtz
   - Pack: a DDS / PNG texture folder into a single .rtz file (Zstandard like
     RT64's own packer, Deflate or Store; low-mip cache for DDS).
   - Unpack: an .rtz back into a folder of textures and rt64.json.
   - Check a pack and Recomp mod info: coming in the next builds.

4  Ship Mods .o2r          (coming in the next builds)
   HD texture mods for 2 Ship 2 Harkinian, Ship of Harkinian, Starship and
   other .o2r ports.

5  Rice / GLideN64         (coming in the next builds)
   Classic Rice and GLideN64 packs into RT64 and Ship ports, and GLideN64
   packs for Project64, RetroArch, RMG and BizHawk.

OPTIONAL TOOLS (Settings, offered at startup until downloaded)
   texconv     - Microsoft DirectXTex, for BC7 DDS output (1 MB download).
                 Downloads are checked against a fixed checksum.
   Real-ESRGAN - for the AI upscale method, needs a Vulkan GPU (45 MB download).

Your input folders and packs are only read, never changed.

Source code, issues and updates:
   https://github.com/chuchudoesntknowhowtocode/R64texHD
