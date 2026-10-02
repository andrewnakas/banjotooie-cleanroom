"""Drawn pictures: textures that mean something and are drawn from our own briefs (facepaint ops).

  clock faces: white dial, hour ticks, two hands (the kept grid only gives a white blob)
"""
import math

import numpy as np

from cleanroom.decomp.gen import unpack_alpha2
from cleanroom.gfx import facepaint

K = [25, 25, 30]


def clock(fact, rim=None, r=0.46):
    ops = []
    if rim is not None:
        ops += [{"e": [0.5, 0.5, r + 0.03, r + 0.03], "c": rim}]
    ops += [{"e": [0.5, 0.5, r, r], "c": [250, 248, 240]}, {"ring": [0.5, 0.5, r, r], "w": 0.03, "c": K}]
    for h in range(12):
        a = math.radians(h * 30)
        r0 = r * (0.78 if h % 3 == 0 else 0.86)
        ops.append({"line": [[0.5 + r0 * math.sin(a), 0.5 - r0 * math.cos(a)], [0.5 + r * 0.95 * math.sin(a), 0.5 - r * 0.95 * math.cos(a)]],
                    "w": 0.035 if h % 3 == 0 else 0.02, "c": K})
    ops += [{"line": [[0.5, 0.5], [0.5 + r * 0.45, 0.5 - r * 0.25]], "w": 0.05, "c": K},      # hour hand: about two o'clock
            {"line": [[0.5, 0.5], [0.5, 0.5 - r * 0.75]], "w": 0.035, "c": K},
            {"e": [0.5, 0.5, 0.035, 0.035], "c": [200, 40, 40]}]
    return ops


def _rim(fact):
    g = np.asarray(fact["grid"], np.float32).reshape(-1, 4)
    n = int(round(len(g) ** 0.5))
    g = g.reshape(n, n, 4)
    return [float(v) for v in np.mean([g[0, 0, :3], g[0, -1, :3], g[-1, 0, :3], g[-1, -1, :3]], 0)]


BRIEFS = {"m8b7.4": lambda f: {"base": [250, 248, 240], "ops": clock(f)},
          "x22ac": lambda f: {"base": _rim(f), "ops": clock(f, [215, 170, 60], 0.40)}}


def hook(key, fact, rgba):
    b = BRIEFS.get(key)
    if b is None:
        return None
    w, h = fact["w"], fact["h"]
    alpha = unpack_alpha2(fact["alpha2"], w, h) if "alpha2" in fact else None
    return np.clip(facepaint.render(b(fact), w, h, alpha=alpha), 0, 255).astype(np.uint8)
