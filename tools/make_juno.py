#!/usr/bin/env python3
"""Pixel Juno designer - v1.

Juno (black duck, suit + sunglasses) as a 64x64 pixel character in the
Muse-Avatar house style: palette-indexed sprite maps, hard outline,
transparent background (sits on the backdrop, no box), soft shadow.
Outputs the sprite maps as a C header plus PNG/GIF previews.
"""
import math
from PIL import Image

W = H = 64

PAL = {
    "K": (0x14, 0x10, 0x0E),   # outline
    "B": (0x17, 0x18, 0x1C),   # black fur
    "b": (0x23, 0x24, 0x2A),   # fur shade
    "H": (0x2C, 0x2D, 0x35),   # fur highlight (soft sheen, not a helmet)
    "G": (0x05, 0x05, 0x07),   # glasses lens
    "g": (0x46, 0x48, 0x52),   # glasses frame / shine edge
    "W": (0xF5, 0xF2, 0xEA),   # white (shirt, glints)
    "Y": (0xF7, 0xB7, 0x31),   # bill / feet yellow
    "O": (0xE8, 0x89, 0x0C),   # bill orange shade
    "o": (0xB8, 0x5F, 0x00),   # bill line
    "S": (0x1D, 0x1E, 0x24),   # suit
    "s": (0x28, 0x29, 0x31),   # suit shade
    "L": (0x3A, 0x3B, 0x45),   # lapel light
    "T": (0x0C, 0x0C, 0x10),   # tie
    "M": (0x5B, 0x2C, 0x14),   # mouth interior
}


def new_grid():
    return [["." for _ in range(W)] for _ in range(H)]


def px(g, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        g[y][x] = c


def ellipse(g, cx, cy, rx, ry, c):
    for y in range(H):
        for x in range(W):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                px(g, x, y, c)


def rect(g, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(g, x, y, c)


def tri(g, cx, y0, y1, half_top, half_bot, c):
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, (y1 - y0))
        half = half_top + (half_bot - half_top) * t
        for x in range(int(cx - half), int(cx + half) + 1):
            px(g, x, y, c)


def outline_pass(g):
    """Any opaque cell touching transparency becomes outline."""
    out = [row[:] for row in g]
    for y in range(H):
        for x in range(W):
            if g[y][x] == ".":
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if not (0 <= nx < W and 0 <= ny < H) or g[ny][nx] == ".":
                    out[y][x] = "K"
                    break
    return out


def draw_juno(talk=False, blink=False, happy=False):
    g = new_grid()
    # feet
    ellipse(g, 24, 58, 6.5, 2.6, "Y")
    ellipse(g, 40, 58, 6.5, 2.6, "Y")
    # body / suit - a rounded bell
    ellipse(g, 32, 48, 15, 11.5, "S")
    for y in range(38, 60):  # side shading
        for x in range(W):
            if g[y][x] == "S" and (x < 21 or x > 43):
                g[y][x] = "s"
    # shirt triangle + tie
    tri(g, 32, 39, 52, 5.5, 0.5, "W")
    rect(g, 30, 39, 34, 41, "T")            # knot
    rect(g, 31, 42, 33, 52, "T")            # tie blade
    px(g, 32, 53, "T")
    # lapel light lines
    for i in range(7):
        px(g, 26 - 0, 40 + i, "L") if False else None
    for i in range(6):
        px(g, 25, 41 + i, "L")
        px(g, 39, 41 + i, "L")
    # wings / arms at the sides, tucked in
    ellipse(g, 16, 45, 3.8, 7.5, "B")
    ellipse(g, 48, 45, 3.8, 7.5, "B")
    # head - sits low, chin tucked into the collar
    ellipse(g, 32, 22, 17, 16, "B")
    # head shading: a small sheen crescent on top, shade at the jaw sides
    for y in range(H):
        for x in range(W):
            if g[y][x] == "B":
                d_top = ((x - 30) / 12) ** 2 + ((y - 10) / 8) ** 2
                if d_top < 0.5:
                    g[y][x] = "H"
                elif y > 33 and (x < 22 or x > 42):
                    g[y][x] = "b"
    # tuft - three spikes
    for dx, hh in ((-4, 3), (0, 4), (4, 3)):
        for i in range(hh):
            rect(g, 32 + dx - 1, 6 - i, 32 + dx + 1 - (1 if i == hh - 1 else 0), 6 - i, "B")
    # sunglasses - band across the eyes
    for y in range(16, 25):
        for x in range(13, 52):
            if ((x - 22.5) / 9.5) ** 2 + ((y - 20) / 4.6) ** 2 <= 1.0 or \
               ((x - 41.5) / 9.5) ** 2 + ((y - 20) / 4.6) ** 2 <= 1.0 or \
               (27 <= x <= 37 and 18 <= y <= 21):
                px(g, x, y, "G")
    # glasses frame edge (top) + glints
    for x in range(14, 51):
        if g[16][x] == "G":
            px(g, x, 16, "g")
    if not blink:
        for dx, dy in ((0, 0), (1, 1), (2, 2)):
            px(g, 19 + dx, 18 + dy, "W")
            px(g, 38 + dx, 18 + dy, "W")
        px(g, 20, 18, "W")
        px(g, 39, 18, "W")
    else:
        # blink: lids slide down over the lenses, seam line at the bottom
        for y in range(17, 24):
            for x in range(13, 52):
                if g[y][x] == "G":
                    g[y][x] = "B"
        for x in range(14, 51):
            if g[23][x] == "B" and x not in range(28, 37):
                px(g, x, 23, "K")
    # bill
    if talk:
        ellipse(g, 32, 29.5, 11, 3.6, "Y")          # upper
        rect(g, 24, 33, 40, 34, "M")                # open mouth
        ellipse(g, 32, 36, 8, 2.2, "O")             # lower bill dropped
    else:
        ellipse(g, 32, 30, 11, 4.2, "Y")
        ellipse(g, 32, 33.5, 8, 2.2, "O")
        # mouth line with a smile upturn (wider when happy)
        lift = 2 if happy else 1
        for x in range(23, 42):
            px(g, x, 32, "o")
        for i in range(lift + 1):
            px(g, 22, 32 - i, "o")
            px(g, 42, 32 - i, "o")
    px(g, 28, 28, "o")
    px(g, 36, 28, "o")  # nostrils
    return outline_pass(g)


def render(g, scale=6, bg=(10, 18, 38), shadow=True):
    img = Image.new("RGBA", (W * scale, H * scale), bg + (255,))
    pix = img.load()
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sp = sh.load()
        for y in range(H * scale):
            for x in range(W * scale):
                gx, gy = x / scale, y / scale
                if ((gx - 32) / 17) ** 2 + ((gy - 60) / 3) ** 2 <= 1.0:
                    sp[x, y] = (0, 0, 0, 110)
        img.alpha_composite(sh)
    for y in range(H):
        for x in range(W):
            c = g[y][x]
            if c == ".":
                continue
            col = PAL[c] + (255,)
            for dy in range(scale):
                for dx in range(scale):
                    pix[x * scale + dx, y * scale + dy] = col
    return img


frames = {
    "idle": draw_juno(),
    "blink": draw_juno(blink=True),
    "talk": draw_juno(talk=True),
    "happy": draw_juno(happy=True),
}

# contact sheet
sheet = Image.new("RGBA", (W * 6 * 4 + 50, H * 6 + 20), (24, 24, 32, 255))
for i, (name, g) in enumerate(frames.items()):
    sheet.alpha_composite(render(g, 6), (10 + i * (W * 6 + 3), 10))
sheet.convert("RGB").save("/home/hatch/workspace/juno-design/juno_sheet.png")

# animated idle gif: bob + blink
seq = []
base = frames["idle"]
for i in range(16):
    g = frames["blink"] if i in (7,) else base
    bob = 1 if i in (4, 5, 6, 7, 12, 13, 14, 15) else 0
    img = render(g, 5, bg=(10, 18, 38))
    if bob:
        canvas = Image.new("RGBA", img.size, (10, 18, 38, 255))
        canvas.alpha_composite(img, (0, 5))
        img = canvas
    seq.append(img.convert("RGB"))
seq[0].save("/home/hatch/workspace/juno-design/juno_idle.gif", save_all=True,
            append_images=seq[1:], duration=110, loop=0)

# C header with the sprite maps
def c_map(name, g):
    rows = ",\n".join('    "%s"' % "".join(r) for r in g)
    return f"static const char *const JUNO_{name.upper()}[{H}] = {{\n{rows}\n}};\n"

hdr = ["/* Juno pixel sprites - 64x64 palette maps. See juno_pixel.h. */\n",
       "/* Legend: " + " ".join(f"{k}={v}" for k, v in PAL.items()) + " . = transparent */\n"]
for name, g in frames.items():
    hdr.append(c_map(name, g))
open("/home/hatch/workspace/juno-design/juno_sprites.h", "w").write("\n".join(hdr))
print("wrote sheet, gif, header")
