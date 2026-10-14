#!/usr/bin/env python3
"""Convert the Hermes ink-girl avatar art to high-count pixel sprites.

Source: owner's own HermesDesktopBuddy / HermesGadget assets (1024px
ink illustration). Renders at a 192x192 grid with 4 coverage levels
so edges stay smooth - lots of pixels, no blocky slop. Emits the
sprite (transparent bg) + a navy-backdrop preview.
"""
import sys
from PIL import Image
import numpy as np

GRID = 192
LEVELS = [0, 85, 170, 255]


def coverage(img, white_art=False):
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    alpha = a[:, :, 3] / 255.0
    lum = a[:, :, :3].mean(axis=2) / 255.0
    if white_art:
        cov = alpha * lum          # white line art: brightness is ink
    else:
        cov = alpha * (1.0 - lum)  # black line art: darkness is ink
        if alpha.max() < 0.05:     # no alpha channel: white bg instead
            cov = 1.0 - lum
    return cov


def convert(src, out_sprite, out_prev, rgb, white_art=False):
    img = Image.open(src)
    cov = Image.fromarray((coverage(img, white_art) * 255).astype(np.uint8))
    small = cov.resize((GRID, GRID), Image.LANCZOS)
    q = np.asarray(small, dtype=np.float32)
    q = np.digitize(q, [42, 127, 212]) * 85  # -> 0/85/170/255
    rgba = np.zeros((GRID, GRID, 4), dtype=np.uint8)
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = rgb
    rgba[:, :, 3] = q.astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out_sprite)
    # preview on the watch navy backdrop
    bg = Image.new("RGBA", (GRID * 3, GRID * 3), (10, 18, 38, 255))
    sp = Image.fromarray(rgba, "RGBA").resize((GRID * 3, GRID * 3), Image.NEAREST)
    bg.alpha_composite(sp)
    bg.convert("RGB").save(out_prev, quality=88)
    ink_px = int((q > 0).sum())
    print(out_sprite, "ink cells:", ink_px)


convert("/Users/duckets/HermesDesktopBuddy/app/src/main/res/drawable-xxxhdpi/hermes_avatar.png",
        "/tmp/hermes-ink.png", "/tmp/hermes-ink_prev.jpg", (12, 12, 16))
convert("/Users/duckets/HermesGadget/assets/mascot/nous-girl-white-1024.png",
        "/tmp/hermes-ink-white.png", "/tmp/hermes-ink-white_prev.jpg", (245, 242, 234),
        white_art=True)
