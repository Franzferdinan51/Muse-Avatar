#!/usr/bin/env python3
"""Convert the Hermes knight mascot art to a collection sprite.

Source: Hermes desktop app asset in Duckets' local project tree
(Projects/Grok-Build-Desktop-App-work/upstream/hermes/apps/desktop/
public/hermes.png, 1254x1254 RGBA) - a chibi Hermes knight: winged
helmet, blue-and-gold armour, caduceus staff, on transparency.

Conversion: trim the transparent margin, pad to a square with a
small even border, premultiply, and downscale with Lanczos to a
192x192 full-colour transparent sprite - no white/black halo fringe,
no chunky blocks. Emits the sprite + a navy-backdrop preview
(watch backdrop 10,18,38).

Usage: make_hermes_knight.py [src] [out_sprite] [out_preview]
Defaults match the Mac layout used for the other collection tools.
"""
import sys
from PIL import Image
import numpy as np

GRID = 192
PAD_FRAC = 0.04  # border kept around the trimmed art, fraction of side

SRC = ("/Users/duckets/Projects/Grok-Build-Desktop-App-work/upstream/"
       "hermes/apps/desktop/public/hermes.png")
OUT = "/tmp/hermes-knight.png"
PREV = "/tmp/hermes-knight_prev.jpg"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out_sprite = sys.argv[2] if len(sys.argv) > 2 else OUT
    out_prev = sys.argv[3] if len(sys.argv) > 3 else PREV

    img = Image.open(src).convert("RGBA")
    a = np.asarray(img, dtype=np.float32)
    alpha = a[:, :, 3]
    ys, xs = np.where(alpha > 8)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a = a[y0:y1, x0:x1]
    h, w, _ = a.shape
    side = max(h, w)
    pad = int(side * PAD_FRAC)
    side += 2 * pad
    canvas = np.zeros((side, side, 4), dtype=np.float32)
    oy, ox = pad + (side - 2 * pad - h) // 2, pad + (side - 2 * pad - w) // 2
    canvas[oy:oy + h, ox:ox + w] = a

    # premultiply, downscale each channel with Lanczos, un-premultiply
    al_full = canvas[:, :, 3]
    chans = []
    for c in range(3):
        pm = Image.fromarray(
            ((canvas[:, :, c] * al_full) / 255.0).astype(np.uint8))
        chans.append(np.asarray(pm.resize((GRID, GRID), Image.LANCZOS),
                                 dtype=np.float32))
    al = Image.fromarray(al_full.astype(np.uint8)).resize(
        (GRID, GRID), Image.LANCZOS)
    al = np.asarray(al, dtype=np.float32)
    rgba = np.zeros((GRID, GRID, 4), dtype=np.uint8)
    safe = np.maximum(al, 1.0)
    for c in range(3):
        rgba[:, :, c] = np.clip(chans[c] * 255.0 / safe, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = al.astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out_sprite)

    # preview on the watch navy backdrop, smooth upscale (painted piece)
    bg = Image.new("RGBA", (GRID * 3, GRID * 3), (10, 18, 38, 255))
    sp = Image.fromarray(rgba, "RGBA").resize((GRID * 3, GRID * 3),
                                              Image.LANCZOS)
    bg.alpha_composite(sp)
    bg.convert("RGB").save(out_prev, quality=88)
    opaque = int((al > 250).sum())
    print(out_sprite, "trimmed:", (x0, y0, x1, y1),
          "opaque px:", opaque, "of", GRID * GRID)


if __name__ == "__main__":
    main()
