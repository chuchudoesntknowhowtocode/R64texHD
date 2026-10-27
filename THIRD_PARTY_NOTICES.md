# Third-party notices

R64texHD is licensed under GPL-2.0-or-later (see LICENSE). It includes code ported from
the projects below. Their licences require these notices to be kept with copies of the
software.

## RT64

Ported parts: the RT64 texture-dump decoder (`app/core/tmem.js`, from RT64's
`shaders/TextureDecoder.hlsli`), the `rt64.json` replacement-database rules
(`app/core/rt64db.js`) and the `.rtz` pack / low-mip-cache layout
(`app/core/rtz.js`, from RT64's `tools/texture_packer`).
Source: https://github.com/rt64/rt64

```
MIT License

Copyright (c) 2024 RT64 Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## GLideN64, Rice Video and RT64 texture_hasher (GPL)

Ported parts: the Rice texture ID formula (RiceCRC32, the load width / height / row
size rules, palette range) in `app/core/rice.js`, from RT64's `tools/texture_hasher`,
which references GLideN64 and Rice Video and is under the GPL for that reason; and the
GLideN64 hi-res texture cache file layout (`.hts` / `.htc`) in the same file, written
from GLideN64's `GLideNHQ/TxCache.cpp`.
Sources: https://github.com/gonetz/GLideN64 (GPL version 2 or any later version),
https://github.com/rt64/rt64 (`src/tools/texture_hasher`, GPL),
Rice Video plugin (Mupen64Plus, GPL version 2 or later).

## bcdec

Ported parts: the BC7 partition tables (`app/core/bc7tables.js`) and the
BC1-BC5 / BC7 block decoders (`app/core/bc.js`).
Source: https://github.com/iOrange/bcdec (dual licensed MIT / Unlicense; used under MIT)

```
MIT License

Copyright (c) 2022 Sergii Kudlai

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Electron

The Windows release runs on Electron (MIT, Copyright (c) Electron contributors,
Copyright (c) 2013-2020 GitHub Inc.), which includes Chromium and its
components. Their licences ship in the release folder as `LICENSE` and
`LICENSES.chromium.html`. https://github.com/electron/electron

## Optional tools (not included)

Downloaded by the user from Settings, not redistributed with R64texHD:
- texconv from Microsoft DirectXTex (MIT) - https://github.com/microsoft/DirectXTex
- Real-ESRGAN ncnn Vulkan (BSD-3-Clause) - https://github.com/xinntao/Real-ESRGAN

## Artwork

The R64 app icon (`app/assets/icon.*`) and the header artwork
(`app/ui/header-art.jpg`) were supplied by the project author.
