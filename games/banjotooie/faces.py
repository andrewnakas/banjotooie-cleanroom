"""Sprite faces and HUD buttons from our own briefs (a 4x4 colour grid alone turns 32x32 heads to mush).

Each brief is our description: where the eyes are (normalised frame coordinates, x right, y down),
their radius and iris colour, plus optional facepaint ops (nose, mouth). Colours come from the kept
grid, the silhouette from the kept 2-bit alpha. Buttons get their letter / arrow re-typeset.
A brief applies to every frame of its sprite.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cleanroom.decomp.gen import h32, unpack_alpha2
from cleanroom.gfx import facepaint

FONT = os.path.join(os.path.dirname(__file__), "fonts", "LilitaOne-Regular.ttf")
K, W, RED, GRN, BLU, YEL, ORG = [12, 12, 16], [250, 250, 250], [220, 30, 30], [60, 170, 40], [50, 90, 220], [240, 210, 40], [240, 140, 30]

EYES = {}     # uid -> (list of (x, y, r), iris colour, look, extra ops)
TEXT = {}     # uid -> (text, fill, outline, height fraction, (cx, cy))


def _e(uids, eyes, iris=K, look=(0.25, 0.05), ops=()):
    for u in uids if isinstance(uids, (tuple, list, range)) else (uids,):
        EYES[u] = (eyes, iris, look, list(ops))


def nose(x, y, r, c=K):
    return {"sphere": [x, y, r, r], "c": c}


def mouth(x0, x1, y, c=K, w=0.05):
    return {"arc": [(x0 + x1) / 2, y - 0.04, (x1 - x0) / 2, 0.08, 20, 160], "w": w, "c": c}


def P2(x, y, r=0.085, d=0.2):
    return [(x, y, r), (x + d, y - 0.02, r)]


# --- Banjo, Kazooie, split-up pairs
_e(0xB89, P2(0.40, 0.33, 0.08, 0.15), BLU, ops=[nose(0.86, 0.43, 0.10)])
_e(0xB8A, P2(0.33, 0.36, 0.08, 0.14), GRN)
_e(0xB8B, P2(0.34, 0.40, 0.08, 0.14), GRN)
_e((0xB54, 0xB55, 0xB56), P2(0.38, 0.36, 0.08, 0.13))
_e(range(0xB50, 0xB54), [(0.11, 0.33, 0.045), (0.19, 0.3, 0.045), (0.36, 0.33, 0.045), (0.43, 0.31, 0.045)], BLU)
_e(0xB86, [(0.3, 0.3, 0.14), (0.7, 0.3, 0.14)], K, (0, 0))
# --- characters, sheet 1
_e(0xB99, P2(0.36, 0.42, 0.075, 0.14))
_e(0xB9A, P2(0.35, 0.30, 0.075))
_e(0xB9B, P2(0.40, 0.42, 0.06), GRN, (0, 0))
_e(0xB9D, P2(0.40, 0.62, 0.07, 0.22), K, (0, 0))
_e(0xB9E, P2(0.44, 0.60, 0.05, 0.16), K, (0, 0))
_e(0xB9F, P2(0.45, 0.30, 0.09, 0.23), K, (0, 0))
_e(0xBA0, P2(0.40, 0.62, 0.06), K, (0, 0))
_e(0xBA3, P2(0.40, 0.50, 0.075, 0.22), GRN, (0, 0), [mouth(0.35, 0.7, 0.75)])
_e(0xBA4, P2(0.40, 0.52, 0.07, 0.22), [90, 50, 20], (0, 0), [mouth(0.42, 0.62, 0.8, RED)])
_e(0xBA5, P2(0.38, 0.76, 0.06, 0.18), K, (0, 0))
_e(0xBA8, P2(0.30, 0.25, 0.08), K)
_e(0xBAB, P2(0.44, 0.50, 0.06, 0.16), K)
_e(0xBAC, P2(0.35, 0.60, 0.07, 0.17), GRN)
_e(0xBAD, P2(0.45, 0.50, 0.07, 0.17), K)
_e(0xBB0, P2(0.48, 0.55, 0.07, 0.17), GRN)
_e(0xBB1, P2(0.44, 0.50, 0.06, 0.16), GRN)
_e(0xBB2, P2(0.33, 0.35, 0.07, 0.17), K, ops=[nose(0.72, 0.62, 0.035, [150, 60, 80]), nose(0.86, 0.6, 0.035, [150, 60, 80])])
_e(0xBB4, P2(0.40, 0.60, 0.06, 0.16))
_e(0xBB5, P2(0.50, 0.70, 0.06, 0.16))
_e(0xBB6, P2(0.40, 0.60, 0.08, 0.2), BLU, (0, 0.1))
_e(0xBB7, P2(0.40, 0.55, 0.07, 0.2), K, (0, 0), [mouth(0.4, 0.7, 0.8)])
_e(0xBB8, P2(0.50, 0.50, 0.07, 0.16), BLU)
_e(0xBB9, [(0.45, 0.50, 0.06)])
_e(0xBBA, P2(0.45, 0.45, 0.06, 0.15))
_e(0xBBB, [(0.5, 0.5, 0.17)], YEL, (0, 0))
_e(0xBBC, P2(0.45, 0.40, 0.08, 0.18))
_e(0xBBD, P2(0.40, 0.30, 0.08, 0.18), K, ops=[nose(0.6, 0.6, 0.035, [170, 70, 90]), nose(0.76, 0.6, 0.035, [170, 70, 90])])
_e(0xBBE, [(0.40, 0.30, 0.06)], YEL)
_e(0xBBF, P2(0.40, 0.55, 0.07, 0.22), RED, (0, 0))
# --- sheet 2
_e((0xBC0, 0xBC1, 0xBC2), P2(0.40, 0.50, 0.095, 0.19), GRN, ops=[nose(0.86, 0.76, 0.08)])
_e(0xBC3, [(0.6, 0.36, 0.2)], GRN)
_e(0xBC4, [(0.6, 0.36, 0.2)], YEL)
_e(0xBC5, [(0.6, 0.36, 0.2)], RED)
_e((0xBC7, 0xBC8, 0xBC9, 0xBE1), P2(0.40, 0.42, 0.09, 0.22), K, (0, 0), [mouth(0.35, 0.68, 0.66, [30, 70, 20], 0.04)])
_e(0xBCD, P2(0.45, 0.20, 0.06, 0.17), ORG, (0, 0), [{"rect": [0.3, 0.42, 0.75, 0.56], "c": YEL}, {"line": [[0.3, 0.49], [0.75, 0.49]], "w": 0.03, "c": K}])
_e((0xBCE, 0xBCF), P2(0.38, 0.56, 0.05, 0.12))
_e(range(0xBD0, 0xBD9), P2(0.42, 0.38, 0.10, 0.19), [40, 60, 120], (0.1, 0.05))
_e(0xBD9, [(0.35, 0.6, 0.11), (0.66, 0.6, 0.11)], YEL, (0, 0))
_e(0xBDB, [(0.5, 0.35, 0.06)])
_e(0xBDD, P2(0.40, 0.50, 0.06, 0.18), K, (0, 0))
_e((0xBDE, 0xBDF), [(0.30, 0.45, 0.08)], GRN)
_e(0xBE0, P2(0.45, 0.14, 0.07, 0.2))
_e(0xBE5, P2(0.35, 0.56, 0.09, 0.26), RED, (0, 0))
_e(0xBE8, [(0.45, 0.5, 0.09)])
_e(0xBF1, P2(0.55, 0.45, 0.11, 0.21), GRN)
_e(0xBF2, P2(0.45, 0.45, 0.09, 0.18))
_e(0xBF3, P2(0.50, 0.25, 0.08, 0.15))
_e(0xBF4, P2(0.50, 0.45, 0.08, 0.18))
_e(0xBF5, P2(0.45, 0.40, 0.06, 0.15), K, ops=[nose(0.87, 0.6, 0.08)])
_e(0xBF6, [(0.35, 0.35, 0.07)])
_e(0xBF8, P2(0.50, 0.30, 0.06, 0.13), RED, (0, 0))
_e((0xBF9, 0xBFA), P2(0.50, 0.12, 0.07, 0.18))
_e(0xBFB, [(0.45, 0.30, 0.06)])
_e(0xBFC, [(0.30, 0.45, 0.06)])
_e(0xBFD, [(0.25, 0.30, 0.08)])
_e(0xBFE, P2(0.40, 0.30, 0.08, 0.16))
_e(0xBFF, P2(0.40, 0.30, 0.08, 0.2), K, (0, 0), [mouth(0.3, 0.7, 0.62, K, 0.06)])
_e(0xC05, [(0.5, 0.35, 0.09)])
_e(0xC06, P2(0.40, 0.30, 0.09, 0.2), K, (0, 0))
_e((0xC07, 0xC08), P2(0.36, 0.62, 0.08, 0.28), RED, (0, 0), [{"rect": [0.38, 0.8, 0.62, 0.9], "c": K}])
_e((0xC09, 0xC0A), [(0.45, 0.30, 0.06)], YEL)
_e(0xC0B, [(0.6, 0.35, 0.08)])
_e((0xC0C, 0xC0D, 0xC0E), P2(0.40, 0.30, 0.07, 0.2), RED, (0, 0))
_e(0xC13, P2(0.40, 0.35, 0.11, 0.22), YEL, (0, 0))
_e(0xC14, [(0.35, 0.5, 0.07)])
_e(0xC16, P2(0.40, 0.30, 0.06, 0.2), GRN, (0, 0))

# --- re-typeset buttons and marks
TEXT[0xB58] = ("A", W, [20, 30, 120], 0.6, (0.5, 0.5))
TEXT[0xB59] = ("B", W, [10, 80, 10], 0.6, (0.5, 0.5))
for _u, _a in zip(range(0xB5A, 0xB5E), "<>^v"):
    TEXT[_u] = (_a, [250, 240, 120], [150, 100, 0], 0.5, (0.5, 0.5))
TEXT[0xB5E] = ("R", W, [60, 60, 60], 0.45, (0.5, 0.5))
TEXT[0xB5F] = ("Z", W, [60, 60, 60], 0.45, (0.5, 0.45))
TEXT[0xB60] = ("START", W, [110, 0, 0], 0.3, (0.5, 0.5))
TEXT[0xBAE] = ("?", W, [50, 50, 50], 0.75, (0.5, 0.5))
TEXT[0xC19] = ("?", YEL, [10, 20, 90], 0.45, (0.5, 0.6))
TEXT[0xB4E] = ("?", RED, [80, 0, 0], 0.6, (0.5, 0.5))


def _arrow(d, cx, cy, s, ch, fill, outline):
    pts = {"<": [(-1, 0), (0.7, -0.9), (0.7, 0.9)], ">": [(1, 0), (-0.7, -0.9), (-0.7, 0.9)],
           "^": [(0, -1), (-0.9, 0.7), (0.9, 0.7)], "v": [(0, 1), (-0.9, -0.7), (0.9, -0.7)]}[ch]
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=tuple(fill) + (255,), outline=tuple(outline) + (255,), width=4)


def _text(rgba, spec):
    text, fill, outline, hf, (cx, cy) = spec
    h, w = rgba.shape[:2]
    S = 8
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if text in "<>^v":
        _arrow(d, cx * w * S, cy * h * S, hf * h * S / 2, text, fill, outline)
    else:
        px = int(hf * h * S)
        f = ImageFont.truetype(FONT, px)
        while px > 8 and f.getbbox(text)[2] - f.getbbox(text)[0] > 0.9 * w * S:
            px -= 2
            f = ImageFont.truetype(FONT, px)
        d.text((cx * w * S, cy * h * S), text, font=f, fill=tuple(fill) + (255,), anchor="mm",
               stroke_width=max(2, px // 10), stroke_fill=tuple(outline) + (255,))
    t = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32)
    out = rgba.astype(np.float32)
    a = t[..., 3:4] / 255
    out[..., :3] = out[..., :3] * (1 - a) + t[..., :3] * a
    return out.astype(np.uint8)


def paint(uid, key, fact):
    w, h = fact["w"], fact["h"]
    alpha = unpack_alpha2(fact["alpha2"], w, h) if "alpha2" in fact else None
    ops = []
    if uid in EYES:
        eyes, iris, look, extra = EYES[uid]
        ops += extra
        for x, y, r in eyes:
            ops.append({"eye": {"c": [x, y], "r": [r, r * w / h], "iris": iris, "irisr": 0.62,
                                "pupil": 0.0 if iris == K else 0.5, "look": list(look), "border": 0.3, "hl": r >= 0.08}})
    ops.append({"outline": 1, "c": [25, 20, 20]})
    out = facepaint.render({"base": "grid", "detail": 0.04, "ops": ops}, w, h, grid=fact["grid"], alpha=alpha,
                           seed=h32("face", key))
    out = np.clip(out, 0, 255).astype(np.uint8)
    if uid in TEXT:
        out = _text(out, TEXT[uid])
    return out


def hook(key, fact, rgba):
    if key[0] != "s":
        return None
    uid = int(key[1:].split(".")[0], 16)
    if uid in EYES or uid in TEXT or 0xB4F <= uid <= 0xC1C:
        return paint(uid, key, fact)
    return None
