"""Text-bearing level textures re-typeset: our own lettering on a board of the kept grid colour.

LABELS: texture key -> (lines, text colour, flip, (tile index, tiles across)). Most Banjo-Tooie sign
textures are stored upside down (t runs upward): flip=True. A sign split over two side-by-side tiles
is drawn once and cropped. Textures with a kept alpha outline get transparent backgrounds.
Kept facts used: the words, the texture size, the grid colour.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(__file__), "fonts", "LilitaOne-Regular.ttf")
WHITE, BLACK, YEL, GRN, NAVY, BLUE = (250, 250, 250), (20, 20, 20), (250, 230, 40), (40, 170, 40), (30, 30, 90), (30, 60, 200)
MAG, RED = (230, 40, 200), (220, 40, 40)

LABELS = {}


def _l(key, lines, col, flip=True, part=(0, 1)):
    LABELS[key] = (lines, col, flip, part)


_l("m6aa.0", ["GUN", "POWDER"], WHITE)
_l("m8d2.0", ["JOLLY'S"], GRN, True, (0, 2))
_l("m8d2.1", ["JOLLY'S"], GRN, True, (1, 2))
_l("m8fe.21", ["HAG 1"], BLACK)
_l("m91c.17", ["HAG 1"], BLACK)
_l("m903.0", ["GO"], YEL, False)
_l("m96c.0", ["CLOSED"], NAVY, False)
_l("m96d.0", ["NO", "ENTRY"], WHITE)
_l("x246d", ["TICKETS"], YEL)
for _k, _p in (("x24b5", 0), ("x24b6", 1)):
    _l(_k, [("SAUCER", YEL), ("of", WHITE), ("PERIL", MAG)], WHITE, True, (_p, 2))
for _k, _p in (("x258e", 0), ("x258f", 1)):
    _l(_k, [("CAVE", WHITE), ("OF", BLUE), ("HORRORS", RED)], WHITE, True, (_p, 2))
_l("x2985", ["FLOOR 1"], WHITE)
_l("x2986", ["FLOOR 4"], WHITE)
_l("x2989", ["FLOOR 3"], WHITE)
_l("x29c0", ["FIRE EXIT"], WHITE, False)
_l("x2a26", ["DOWN TO", "FLOOR 1"], WHITE)
_l("x2a58", ["BOILER", "PLANT"], WHITE)
_l("x2a69", ["SEWER", "ACCESS"], WHITE)
_l("x2a6d", ["QUALITY", "CONTROL"], WHITE)
_l("x2a72", ["CABLE", "ROOM"], WHITE)
_l("x2acf", ["REPAIR", "DEPOT"], WHITE)
_l("x2b3a", ["PACKING", "ROOM"], WHITE)
_l("x2b82", ["HAILFIRE PEAKS", "OIL PIPELINE"], BLACK)
_l("x2e8d", ["SOUR", "MILK", "HIGH FAT", "LOW IN CALCIUM"], BLUE)


def _board(fact, W, H, col):
    """Board colour: the grid cells that are far from the text colour (the background), averaged."""
    g = np.asarray(fact["grid"], np.float32)[:, :3]
    d = np.abs(g - np.asarray(col, np.float32)).sum(1)
    bg = g[d >= np.median(d)].mean(0)
    if np.abs(bg - np.asarray(col, np.float32)).sum() < 150:      # too close to read: darken / lighten the board
        bg = bg * 0.35 if sum(col) > 380 else bg * 0.5 + 127
    return Image.new("RGBA", (W, H), tuple(int(v) for v in bg) + (255,))


def paint(key, fact):
    lines, col, flip, (part, parts) = LABELS[key]
    w, h = fact["w"], fact["h"]
    S = 6
    W, H = w * parts * S, h * S
    alpha = "alpha2" in fact
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if alpha else _board(fact, W, H, col)
    d = ImageDraw.Draw(im)
    n = len(lines)
    for k, line in enumerate(lines):
        text, c = line if isinstance(line, tuple) else (line, col)
        px = int(H * 0.8 / n)
        f = ImageFont.truetype(FONT, px)
        while px > 6 and f.getbbox(text)[2] - f.getbbox(text)[0] > W * 0.9:
            px -= 2
            f = ImageFont.truetype(FONT, px)
        kw = dict(stroke_width=max(2, px // 10), stroke_fill=(15, 15, 25, 255)) if alpha else {}
        d.text((W / 2, H * (k + 0.5) / n), text, font=f, fill=tuple(c) + (255,), anchor="mm", **kw)
    im = im.crop((part * w * S, 0, (part + 1) * w * S, H)).resize((w, h), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    out = np.asarray(im, np.uint8).copy()
    if alpha:                                   # keep colour under transparent texels (no dark fringe, no empty tile)
        m = out[..., 3] < 8
        out[m, :3] = np.clip(np.asarray(col) + np.random.default_rng(len(key)).integers(-20, 21, (int(m.sum()), 3)), 0, 255)
    return out


def hook(key, fact, rgba):
    return paint(key, fact) if key in LABELS else None
