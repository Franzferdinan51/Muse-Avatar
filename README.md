# Muse avatar backup - 2026-10-13


Canonical copy: this repo (pushed 2026-10-13) - work on the avatar here.
The live firmware copy ships in Franzferdinan51/muse-gadget-206.
The watch character ("Muse") and everything that moves it, copied out of
muse-gadget-206 (branch museos-bringup, flash10 era) so the character can
be worked on separately from the firmware.

- avatar/muse_pixel.c - the whole character: procedural 64x64 pixel
  renderer. Palette + state colour schemes, body/face/eyes/mouth, aura,
  sparkles, expressions per mode, blink/breath/look animation, the
  RGB565 + RGB565A8 (alpha) strip scalers the LVGL decoder serves.
- muse_pixel.h - its header (poses, modes, render API).
- avatar/happy_anim.c/.h - the "happy" reaction animation.
- avatar/jollybot.gif - reference animation asset shipped in-tree.
- muse_ui.c - the frame loop that drives it: image_sync (pose/mode ->
  invalidate), the LVGL custom decoder (strip buffers, get_area), the
  canvas layout. The avatar only exists on screen through this file.

Design canon (owner, 2026-10-13): character sits directly on the page
backdrop (no black box - background cells are alpha-transparent), the
old gradient backdrop stays, no progress ring on the rectangular 206
layout, aura is a soft state-coloured halo (alpha 150/90), state word
and name never overlap.
