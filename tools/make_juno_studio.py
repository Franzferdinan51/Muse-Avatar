#!/usr/bin/env python3
"""Convert a Juno studio frame from the MuseCompanionApp idle clip
to a collection sprite.

Source: owner's own MuseCompanionApp avatar asset
(app/assets/avatar/juno_idle.mp4, 720x720, 24fps, 10s) - the
rendered Juno (black duck, suit, sunglasses) on a near-white studio
backdrop; the same art the watch's GIF face is built from. Frame at
t=8.5s: head turned three-quarter, bill in profile.

Conversion: extract the frame with ffmpeg, flood-fill key the
border-connected near-white backdrop to transparency (the enclosed
white shirt survives), drop the border-reachable neutral floor
shadow, decontaminate the 1-2px fringe by un-blending from white,
trim to the alpha bounding box, square-pad, premultiply, and
downscale with Lanczos to a 192x192 full-colour transparent sprite -
no halo fringe, no chunky blocks. Emits the sprite + a navy-backdrop
preview (watch backdrop 10,18,38).

Usage: make_juno_studio.py [src_mp4] [out_sprite] [out_preview]
Defaults match the Mac layout used for the other collection tools.
ffmpeg is taken from PATH, falling back to imageio_ffmpeg.
"""
import shutil
import subprocess
import sys
from collections import deque

from PIL import Image
import numpy as np

GRID = 192
T_SEC = 8.5
PAD_FRAC = 0.04
WHITE_T = 228      # min(r,g,b) above this counts as background-ish
SHADOW_LO = 100    # border-reachable neutral band = studio floor shadow
WEDGE_MIN_Y = 520  # enclosed white components starting below this row
                   # are studio backdrop showing between the legs (the
                   # frame's only other enclosed whites are a sunglass
                   # highlight at y~95-113 and the shadowed shirt, both
                   # far above the jacket hem)

SRC = "/Users/duckets/MuseCompanionApp/app/assets/avatar/juno_idle.mp4"
OUT = "/tmp/juno-studio.png"
PREV = "/tmp/juno-studio_prev.jpg"


def ffmpeg_exe():
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_frame(mp4):
    out = "/tmp/juno_studio_frame.png"
    subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-i", mp4,
                    "-ss", str(T_SEC), "-frames:v", "1", out],
                   check=True)
    return Image.open(out).convert("RGB")


def key_frame(rgb):
    """(rgb array, alpha 0..1) with the border-connected near-white
    flooded to transparent, the reachable floor shadow dropped, and
    the fringe un-blended from white."""
    a = np.asarray(rgb).astype(np.float32)
    h, w, _ = a.shape
    whiteish = a.min(axis=2) > WHITE_T
    bg = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if whiteish[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if whiteish[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and whiteish[ny, nx] \
                    and not bg[ny, nx]:
                bg[ny, nx] = True
                dq.append((ny, nx))
    # floor shadow: neutral mid-grey pixels the flood can reach
    mn = a.min(axis=2)
    mx = a.max(axis=2)
    shadowish = (mn >= SHADOW_LO) & (mn <= WHITE_T) & ((mx - mn) < 40) & ~bg
    reach = bg.copy()
    ys, xs = np.nonzero(bg)
    for y, x in zip(ys.tolist(), xs.tolist()):
        dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and shadowish[ny, nx] \
                    and not reach[ny, nx]:
                reach[ny, nx] = True
                dq.append((ny, nx))
    gone = reach  # backdrop + its reachable shadow
    # enclosed backdrop: white the border flood cannot reach (between
    # the legs) - drop white components that start below the jacket
    hi = (a.min(axis=2) > 200) & ~gone
    seen = np.zeros((h, w), bool)
    for sy in range(h):
        for sx in range(w):
            if hi[sy, sx] and not seen[sy, sx]:
                comp = []
                dq.append((sy, sx))
                seen[sy, sx] = True
                while dq:
                    cy, cx = dq.popleft()
                    comp.append((cy, cx))
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx),
                                   (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < h and 0 <= nx < w and hi[ny, nx] \
                                and not seen[ny, nx]:
                            seen[ny, nx] = True
                            dq.append((ny, nx))
                if min(p[0] for p in comp) > WEDGE_MIN_Y:
                    for cy, cx in comp:
                        gone[cy, cx] = True
    alpha = np.where(gone, 0.0, 1.0)
    # decontaminate fringe pixels next to transparency
    near = np.zeros((h, w), bool)
    near[1:, :] |= gone[:-1, :]
    near[:-1, :] |= gone[1:, :]
    near[:, 1:] |= gone[:, :-1]
    near[:, :-1] |= gone[:, 1:]
    fringe = near & ~gone
    lum = a.mean(axis=2)
    est_a = np.clip((255.0 - lum) / 90.0, 0.35, 1.0)
    for c in range(3):
        ch = a[:, :, c]
        ch[fringe] = np.clip(
            (ch[fringe] - (1 - est_a[fringe]) * 255.0) / est_a[fringe],
            0, 255)
    return a, alpha


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out_sprite = sys.argv[2] if len(sys.argv) > 2 else OUT
    out_prev = sys.argv[3] if len(sys.argv) > 3 else PREV

    rgb, alpha = key_frame(extract_frame(src))
    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    ys, xs = np.where(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = rgba[y0:y1, x0:x1]
    h, w, _ = rgba.shape
    side = max(h, w)
    pad = int(side * PAD_FRAC)
    side += 2 * pad
    canvas = np.zeros((side, side, 4), dtype=np.uint8)
    oy = pad + (side - 2 * pad - h) // 2
    ox = pad + (side - 2 * pad - w) // 2
    canvas[oy:oy + h, ox:ox + w] = rgba

    # premultiply, downscale each channel with Lanczos, un-premultiply
    a = canvas.astype(np.float32)
    al_full = a[:, :, 3]
    chans = []
    for c in range(3):
        pm = Image.fromarray(((a[:, :, c] * al_full) / 255.0).astype(np.uint8))
        chans.append(np.asarray(pm.resize((GRID, GRID), Image.LANCZOS),
                                 dtype=np.float32))
    al = Image.fromarray(al_full.astype(np.uint8)).resize(
        (GRID, GRID), Image.LANCZOS)
    al = np.asarray(al, dtype=np.float32)
    out = np.zeros((GRID, GRID, 4), dtype=np.uint8)
    safe = np.maximum(al, 1.0)
    for c in range(3):
        out[:, :, c] = np.clip(chans[c] * 255.0 / safe, 0, 255).astype(np.uint8)
    out[:, :, 3] = al.astype(np.uint8)
    sprite = Image.fromarray(out, "RGBA")
    sprite.save(out_sprite)

    # preview on the watch navy backdrop, smooth upscale (rendered piece)
    bgim = Image.new("RGBA", (GRID * 3, GRID * 3), (10, 18, 38, 255))
    bgim.alpha_composite(sprite.resize((GRID * 3, GRID * 3), Image.LANCZOS))
    bgim.convert("RGB").save(out_prev, quality=88)
    print(out_sprite, "trimmed:", (x0, y0, x1, y1),
          "opaque px:", int((al > 250).sum()), "of", GRID * GRID)


if __name__ == "__main__":
    main()
