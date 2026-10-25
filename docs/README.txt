HD TEXTURE TOOLKIT - RT64 SUPPORT  (portable)
=============================================
A simple tool designed to upscale DDS/PNG with support for RT64 texture
dumps & .rtz texture packs.


Start: double-click "R64texHD.exe" (it shows as R64texHD in Task Manager).
Nothing is installed: no Python, no registry, nothing in AppData.
Put this folder anywhere you can write to (for example C:\Tools\HD Texture Toolkit,
a second drive or a USB stick) and keep its files together.

Everything the toolkit saves stays in the "data" folder next to the program:
  data\settings.json   your folders and choices
  data\tools\          texconv / Real-ESRGAN if you download them in Settings
  data\chromium\       the window engine's own cache
  data\temp\           scratch files, cleared when you close the toolkit
To reset the toolkit, delete the data folder. To remove it, delete this folder.

First launch shows a Setup page: RT64 texture dump folder (optional), output
folder, and an optional Desktop shortcut.

THE THREE OPTIONS (sidebar)

1  Upscale Textures
   PNG / DDS textures: a whole folder (subfolders kept) or picked files.
   - Method: Standard (2x steps, sharpened after each step), Smooth,
     Pixel art, or AI (Real-ESRGAN, downloadable in Settings).
   - Size: 2x 3x 4x 6x 8x, or Fit the longest side to 512 - 4096 px.
   - Sharpness: Off / Soft / Normal / Strong / Extra.
   - Edges: Normal / Tile (seamless repeating textures) / Mirror.
   - Cut-out edges: Hard (crisp leaves, fences, text) or Smooth.
   - Output: same format as input, PNG or DDS (Auto BC1/BC3, BC7, BC3, BC1, none).
   - Other files such as rt64.json are copied along; "Skip" resumes a run.
   - Live preview: the original and the upscaled texture side by side. It is
     regenerated whenever you change a setting (DDS output shows its compression
     too). Pick any texture from the input, view it Fit, 1:1 or 2:1; zoomed
     views scroll together. The preview stays at the top while you scroll the
     settings.
   When it finishes it asks whether to go to 3 Pack / Unpack .rtz, with the
   upscaled folder already filled in.

2  Convert RT64 Dump
   Turns an RT64 texture dump (.tmem + .tile.json files, from RT64's debugger:
   F1 > Textures > Start dumping textures) into PNG or DDS textures plus
   rt64.json. When it finishes it asks whether to pack the result into an .rtz.

3  Pack / Unpack .rtz
   One page, two modes (switch at the top):
   - Pack folder -> .rtz: packs a DDS / PNG texture pack folder into a single
     .rtz file (Zstandard like RT64's own packer, Deflate or Store; low-mip
     cache for DDS). Uses the folder's rt64.json, or builds one from
     hash-named files.
   - Unpack .rtz -> folder: opens an .rtz pack (zstd, deflate or stored) back
     into a folder of textures and rt64.json, ready to edit, upscale or repack.

OPTIONAL TOOLS (Settings)
   texconv     - Microsoft DirectXTex, for BC7 DDS output (1 MB download).
   Real-ESRGAN - for the AI upscale method, needs a Vulkan GPU (45 MB download).

Your input folders and packs are only read, never changed.
