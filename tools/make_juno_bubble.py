#!/usr/bin/env python3
"""Convert the glossy Juno bubble logo to a collection sprite.

Source: owner's own MuseCompanionApp brand asset
(app/assets/brand/juno-logo-glossy.png, 1616x1584) - Juno the black
duck in sunglasses inside a blue water bubble, on a white backdrop.

The bubble is a circle (measured on the source: centre ~(808, 771),
radius ~656 px). This tool crops that circle, builds a smooth
anti-aliased alpha mask from the signed distance to the rim,
premultiplies, and downscales with Lanczos to a 192x192 transparent
sprite - full colour kept, no chunky blocks, no white halo fringe.
Emits the sprite + a navy-backdrop preview (watch backdrop 10,18,38).

Usage: make_juno_bubble.py [src] [out_sprite] [out_preview]
Defaults match the Mac layout used for the other collection tools.
"""
import sys
from PIL import Image
import numpy as np

GRID = 192
CX, CY, R = 808.0, 771.0, 656.0
EDGE = 5.0  # source px over which the rim alpha feathers

SRC = "/Users/duckets/MuseCompanionApp/app/assets/brand/juno-logo-glossy.png"
OUT = "/tmp/juno-bubble.png"
PREV = "/tmp/juno-bubble_prev.jpg"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out_sprite = sys.argv[2] if len(sys.argv) > 2 else OUT
    out_prev = sys.argv[3] if len(sys.argv) > 3 else PREV

    img = Image.open(src).convert("RGB")
    a = np.asarray(img, dtype=np.float32)
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    alpha = np.clip((R + EDGE / 2 - dist) / EDGE, 0.0, 1.0) * 255.0

    # crop to the circle's bounding square
    x0, y0 = int(CX - R), int(CY - R)
    x1, y1 = int(CX + R), int(CY + R)
    a = a[y0:y1, x0:x1]
    alpha = alpha[y0:y1, x0:x1]

    # premultiply, downscale each channel with Lanczos, un-premultiply
    chans = []
    for c in range(3):
        pm = Image.fromarray(((a[:, :, c] * alpha) / 255.0).astype(np.uint8))
        chans.append(np.asarray(pm.resize((GRID, GRID), Image.LANCZOS),
                                 dtype=np.float32))
    al = Image.fromarray(alpha.astype(np.uint8)).resize((GRID, GRID),
                                                        Image.LANCZOS)
    al = np.asarray(al, dtype=np.float32)
    rgba = np.zeros((GRID, GRID, 4), dtype=np.uint8)
    safe = np.maximum(al, 1.0)
    for c in range(3):
        rgba[:, :, c] = np.clip(chans[c] * 255.0 / safe, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = al.astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out_sprite)

    # preview on the watch navy backdrop, smooth upscale (glossy piece)
    bg = Image.new("RGBA", (GRID * 3, GRID * 3), (10, 18, 38, 255))
    sp = Image.fromarray(rgba, "RGBA").resize((GRID * 3, GRID * 3),
                                              Image.LANCZOS)
    bg.alpha_composite(sp)
    bg.convert("RGB").save(out_prev, quality=88)
    opaque = int((al > 250).sum())
    print(out_sprite, "opaque px:", opaque, "of", GRID * GRID)


if __name__ == "__main__":
    main()
