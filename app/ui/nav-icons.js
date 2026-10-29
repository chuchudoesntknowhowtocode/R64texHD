'use strict';
// Icons for the folded left menu: 32 x 32 RGBA PNGs in assets/nav, made by build/nav_icons.py.
//   upscale  a bar graph climbing          rt64     RT64 (the owner's image)
//   rtz      a zip file labelled .rtz      ship     a ship labelled .o2r (the owner's image)
//   classic  G64 (the owner's image)       roms     a cartridge under a magnifying glass
//   queue    a list with a play arrow      settings a gear      about    "i" in a speech bubble
(function () {
  const SMOOTH = new Set(['rt64', 'classic', 'ship']);                  // scaled-down pictures: no hard pixel edges
  window.navIcon = (name) => `<img src="../assets/nav/${name}.png" width="32" height="32" alt="" draggable="false"${SMOOTH.has(name) ? '' : ' style="image-rendering:pixelated"'}>`;
  window.NAV_ICONS = ['upscale', 'rt64', 'rtz', 'ship', 'classic', 'roms', 'queue', 'settings', 'about'];
})();
