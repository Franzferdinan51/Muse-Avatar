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
    "H": (0x3A, 0x3C, 0x48),   # fur highlight (lifted 2026-10-14: sheen must read at 200px watch size)
    "G": (0x1A, 0x24, 0x36),   # glasses lens (blue-slate: hue-separates from neutral fur at watch size)
    "g": (0x58, 0x62, 0x72),   # glasses frame / shine edge (brightened so the lens rim reads at 200px)
    "W": (0xF5, 0xF2, 0xEA),   # white (shirt, glints)
    "Y": (0xF7, 0xB7, 0x31),   # bill / feet yellow
    "O": (0xE8, 0x89, 0x0C),   # bill orange shade
    "o": (0xB8, 0x5F, 0x00),   # bill line
    "S": (0x25, 0x2A, 0x36),   # suit (blue-grey lift: separates body from black fur wings at 200px)
    "s": (0x28, 0x29, 0x31),   # suit shade
    "L": (0x56, 0x5D, 0x6E),   # lapel light (brightened for watch size)
    "T": (0x0C, 0x0C, 0x10),   # tie
    "M": (0x5B, 0x2C, 0x14),   # mouth interior
    "A": (0xA7, 0x7D, 0xFF),   # accent FX (renderer tints per mode)
    "R": (0xFF, 0x4F, 0x8B),   # heart pink
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


def draw_juno(talk=False, blink=False, happy=False, glint_shift=0, wing_up=False):
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
    # wings / arms at the sides, tucked in (right one raised = wave)
    ellipse(g, 16, 45, 3.8, 7.5, "B")
    if wing_up:
        ellipse(g, 50.5, 30, 3.6, 7.0, "B")
    else:
        ellipse(g, 48, 45, 3.8, 7.5, "B")
    # head - sits low, chin tucked into the collar, shifted a touch
    # right so the profile bill has room to breathe on the left
    ellipse(g, 34, 22, 17, 16, "B")
    # head shading: a small sheen crescent on top, shade at the jaw sides
    for y in range(H):
        for x in range(W):
            if g[y][x] == "B":
                d_top = ((x - 32) / 12) ** 2 + ((y - 10) / 8) ** 2
                if d_top < 0.5:
                    g[y][x] = "H"
                elif y > 33 and (x < 24 or x > 44):
                    g[y][x] = "b"
    # tuft - three spikes
    for dx, hh in ((-4, 3), (0, 4), (4, 3)):
        for i in range(hh):
            rect(g, 34 + dx - 1, 6 - i, 34 + dx + 1 - (1 if i == hh - 1 else 0), 6 - i, "B")
    # sunglasses - 3/4 view: one full lens (near side, left), a sliver
    # of the far lens, bridge between, temple arm to the head's edge.
    for y in range(14, 26):
        for x in range(12, 54):
            if ((x - 24) / 8.2) ** 2 + ((y - 20) / 4.8) ** 2 <= 1.0 or \
               ((x - 41) / 4.6) ** 2 + ((y - 20) / 4.2) ** 2 <= 1.0 or \
               (30 <= x <= 37 and 18 <= y <= 21) or \
               (44 <= x <= 49 and 18 <= y <= 20):
                px(g, x, y, "G")
    # frame edge along the top of both lenses
    for x in range(13, 50):
        if g[15][x] == "G" or g[16][x] == "G":
            if g[15][x] == "G":
                px(g, x, 15, "g")
    # full lens rim (watch-size fix): any lens cell touching a non-lens
    # cell becomes frame, so the glasses shape reads at 200px instead
    # of melting into the fur. The blink lid fill below only replaces
    # "G", so the rim survives a blink as a closed-glasses outline.
    rim = [row[:] for row in g]
    for y in range(12, 28):
        for x in range(10, 56):
            if g[y][x] != "G":
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if g[ny][nx] != "G":
                    rim[y][x] = "g"
                    break
    g = rim
    if not blink:
        # glints: a 2px-wide diagonal slash on the near lens, a 2px
        # dash on the far lens (1px glints vanish at watch size);
        # glint_shift slides them for the look-around poses
        s = glint_shift
        for dx, dy in ((0, 0), (1, 1), (2, 2)):
            px(g, 20 + s + dx, 17 + dy, "W")
            px(g, 21 + s + dx, 17 + dy, "W")
        px(g, 40 + s, 18, "W")
        px(g, 41 + s, 18, "W")
    else:
        # blink: lids slide down over both lenses, seam at the bottom
        for y in range(16, 24):
            for x in range(12, 54):
                if g[y][x] == "G":
                    g[y][x] = "B"
        for x in range(16, 33):
            px(g, x, 23, "g")
        for x in range(37, 46):
            px(g, x, 23, "g")
    # bill - profile, pointing left. Front-on was the weird part
    # (owner); in profile the bill reads. Two stacked ellipses: the
    # base hides inside the face, the visible half rounds to the tip.
    ellipse(g, 21.5, 29.5, 10.5, 3.4, "Y")
    if talk:
        rect(g, 13, 32, 28, 33, "M")                # open mouth
        ellipse(g, 21, 35.5, 8, 2.0, "O")           # lower bill dropped
    else:
        ellipse(g, 21, 33, 8, 2.0, "O")             # lower bill
        for x in range(13, 30):                     # mouth seam
            px(g, x, 32, "o")
        if happy:                                   # tip lifts: smile
            px(g, 12, 31, "o")
            px(g, 12, 30, "o")
            px(g, 13, 30, "o")
    px(g, 25, 28, "o")  # nostril near the base
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


def decor(g, cells):
    """Flat FX cells (no outline) drawn over a finished sprite."""
    for x, y, c in cells:
        px(g, x, y, c)
    return g


def dot(g, x, y, s, c):
    for dy in range(s):
        for dx in range(s):
            px(g, x + dx, y + dy, c)


def heart(g, x, y, c="R"):
    for dx, dy in ((0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)):
        px(g, x + dx, y + dy, c)


_idle = draw_juno()
_blink = draw_juno(blink=True)
frames = {
    "idle": _idle,
    "blink": _blink,
    "lookl": draw_juno(glint_shift=-2),
    "lookr": draw_juno(glint_shift=2),
    "talk": draw_juno(talk=True),
    "happy": draw_juno(happy=True),
}
# listening: sound arcs rolling in toward the bill tip. Each arc
# point is a 2px dash - single pixels read as dust at 200px.
frames["listen"] = decor([r[:] for r in _idle], [
    (5, 25, "A"), (6, 25, "A"), (4, 28, "A"), (5, 28, "A"),
    (4, 31, "A"), (5, 31, "A"), (5, 34, "A"), (6, 34, "A"),
    (2, 22, "A"), (3, 22, "A"), (1, 26, "A"), (2, 26, "A"),
    (1, 33, "A"), (2, 33, "A"), (2, 37, "A"), (3, 37, "A"),
])
# thinking: thought dots climbing away from the head
_t = [r[:] for r in _idle]
dot(_t, 52, 27, 2, "A")
dot(_t, 55, 20, 2, "A")
dot(_t, 58, 12, 3, "A")
frames["think"] = _t
# wave: raised wing + hearts (the pet reaction)
_w = draw_juno(happy=True, wing_up=True)
heart(_w, 57, 14)
heart(_w, 52, 7)
frames["wave"] = _w
# error: alert mark
frames["error"] = decor([r[:] for r in _idle], [
    (55, 14, "R"), (56, 14, "R"), (55, 15, "R"), (56, 15, "R"),
    (55, 16, "R"), (56, 16, "R"), (55, 17, "R"), (56, 17, "R"),
    (55, 18, "R"), (56, 18, "R"), (55, 20, "R"), (56, 20, "R"),
])
# sleep: lids down + Zzz drifting up
_s = [r[:] for r in _blink]
for cx, cy, s in ((49, 12, 5), (56, 4, 4)):
    for i in range(s):
        px(_s, cx + i, cy, "A")
        px(_s, cx + i, cy + s - 1, "A")
    for i in range(1, s - 1):
        px(_s, cx + s - 1 - i, cy + i, "A")
frames["sleep"] = _s

ORDER = ["idle", "blink", "lookl", "lookr", "listen", "think",
         "talk", "happy", "wave", "error", "sleep"]

# contact sheet, two rows
cols = 6
rows = 2
cell = W * 5
sheet = Image.new("RGBA", (cols * cell + (cols + 1) * 4, rows * cell + (rows + 1) * 4),
                  (24, 24, 32, 255))
for i, name in enumerate(ORDER):
    r, c = divmod(i, cols)
    sheet.alpha_composite(render(frames[name], 5), (4 + c * (cell + 4), 4 + r * (cell + 4)))
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

# animation revue: every pose in sequence
revue_names = ["idle", "idle", "blink", "lookl", "lookr", "listen",
               "think", "talk", "talk", "happy", "wave", "wave",
               "error", "sleep", "sleep"]
revue = [render(frames[n], 5, bg=(10, 18, 38)).convert("RGB") for n in revue_names]
revue[0].save("/home/hatch/workspace/juno-design/juno_revue.gif", save_all=True,
              append_images=revue[1:], duration=480, loop=0)

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
