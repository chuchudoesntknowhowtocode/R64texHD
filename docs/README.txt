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

R64texHD opens straight away; there is nothing to set up first. The first
launch opens on the Welcome page, and the green button at the bottom left
brings you back to it any time. The output folder is in Settings.

At every start R64texHD checks for the two optional tools below. If either one
has not been downloaded yet, a small window asks "Download Helper Tools?".
Yes downloads them into data\tools; No carries on without them. You can also
download them in Settings, or turn off "Check tools at startup" there.

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
   - Recomp mod info: a name, author, picture and on / off switch for the
     mod menu in Zelda 64: Recompiled and other recomps.
   - Check a pack: looks over an .rtz or pack folder before you share it.
     "Make them DDS" saves a fixed copy (<name>-fixed.rtz) with every PNG
     texture turned into DDS. The original is never changed.

4  Ship Mods .o2r
   HD texture mods for 2 Ship 2 Harkinian, Ship of Harkinian, Starship and
   other .o2r ports, in three steps:
   - Get textures: every texture in the game's .o2r as a PNG.
   - Upscale the folder on page 1 (as PNG).
   - Build HD mod: makes an .o2r for the port's mods folder. With the in-game
     switch on, players turn it on and off with "Use Alternate Assets" (Tab).

5  Rice / GLideN64
   - Use in RT64: a classic pack (Rice PNG folder, or GLideN64 .hts / .htc)
     into an RT64 pack folder. It is matched through your RT64 dump, so
     convert the dump first with "Add Rice IDs" on.
   - Make GLideN64: a .hts pack for Project64, RetroArch, RMG and BizHawk
     from textures with Rice IDs.
   - Use in Ship port: a classic pack into a Ship port .o2r mod.

6  ROM Tools
   A quick look inside your N64 ROMs. Pick the folder they're in (subfolders
   too: .z64, .v64, .n64 and .zip) and click a ROM to see its title, game code,
   region, version, CIC chip, whether the header checksum is right, CRC32 / MD5
   / SHA-1, and for Zelda 64 games the file table. ROMs are only read.
   303 North American games also show their box art and a short description,
   and the counter says how many of them your folder has.

R64texHD is free software under the GNU General Public License, version 2
or later (see LICENSE.R64texHD.txt).

OPTIONAL TOOLS (Settings, offered at startup until downloaded)
   texconv     - Microsoft DirectXTex, for BC7 DDS output (1 MB download).
                 Downloads are checked against a fixed checksum.
   Real-ESRGAN - for the AI upscale method, needs a Vulkan GPU (45 MB download).

Your input folders and packs are only read, never changed.

Source code, issues and updates:
   https://github.com/chuchudoesntknowhowtocode/R64texHD
