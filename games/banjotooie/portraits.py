"""Dialog head icons rendered from the characters' own models with our generated textures.

MAP: sprite uid -> (model uid, crop). crop = (x0, y0, x1, y1) fractions of the model's front-view
extent (x right, y up) that frame the head. The pairing and the crops are our own brief; the picture
is a render (project.render3d) of kept geometry with clean textures, so no retail pixels are involved.
Sprites without an entry keep the faces.py brief (grid colours + eyes).
"""
import numpy as np
from PIL import Image

from games.banjotooie import formats as F, project as P

HEAD = (0.35, 0.62, 0.65, 1.0)
MAP = {
    0xB89: (0x62A, HEAD),                       # Banjo
    0xB8A: (0x61C, (0.4, 0.74, 0.6, 1.0)),      # Kazooie
    0xB8B: (0x61C, (0.4, 0.74, 0.6, 1.0)),
    0xBA4: (0x675, (0.36, 0.72, 0.64, 1.0)),    # Humba Wumba
    0xBC0: (0x759, (0.3, 0.55, 0.7, 1.0)),      # moles
    0xBC1: (0x75A, (0.3, 0.55, 0.7, 1.0)),
    0xBC2: (0x75B, (0.3, 0.55, 0.7, 1.0)),
    0xBA3: (0x8BD, (0.33, 0.58, 0.67, 1.0)),
    0xBB7: (0x6DB, HEAD),                       # pirate captain
    0xBDD: (0x7EF, (0.36, 0.64, 0.64, 1.0)),    # explorer
    0xBBD: (0x7D4, (0.33, 0.58, 0.67, 1.0)),    # pigs
    0xBBC: (0x6D1, (0.3, 0.64, 0.6, 1.0)),
    0xBF5: (0x81C, HEAD),                       # polar bear
    0xBCD: (0x64F, (0.22, 0.38, 0.78, 1.0)),    # coal king
    0xBCE: (0x896, (0.35, 0.55, 0.65, 1.0)),    # jinjo king
    0xC07: (0x674, (0.2, 0.45, 0.8, 1.0)),
    0xC13: (0x84D, (0.0, 0.0, 1.0, 1.0)),
    0xBFF: (0x60B, (0.0, 0.0, 1.0, 1.0)),       # snowball
    0xBDE: (0x7FC, (0.3, 0.3, 0.7, 1.0)),       # dragons
    0xBDF: (0x7FD, (0.3, 0.3, 0.7, 1.0)),
    0xBA8: (0x794, (0.3, 0.6, 0.7, 1.0)),       # crocodile
    0xBB9: (0x6AE, HEAD),                       # rhino
    0xBB6: (0x6D8, (0.3, 0.45, 0.7, 1.0)),
    0xBB5: (0x6D6, (0.4, 0.78, 0.6, 1.0)),
    0xB9E: (0x673, (0.35, 0.6, 0.65, 1.0)),     # golden figure
    0xBA5: (0x66B, (0.3, 0.55, 0.7, 1.0)),
    0xBF2: (0x919, (0.33, 0.55, 0.67, 1.0)),
    0xBF4: (0x91A, (0.45, 0.5, 0.85, 1.0)),
    0xC09: (0x609, (0.3, 0.72, 0.7, 1.0)),     # dinosaurs
    0xC0A: (0x60D, (0.33, 0.8, 0.67, 1.0)),
    0xBB1: (0x6AD, (0.4, 0.76, 0.6, 1.0)),      # fox
    0xC06: (0x766, (0.15, 0.2, 0.85, 1.0)),
    0xBC8: (0x6BA, (0.2, 0.45, 0.8, 1.0)),      # hooded frog
    0xB9B: (0x7A7, (0.0, 0.0, 1.0, 1.0)),       # cauldron
    0xBBB: (0x6BE, (0.0, 0.0, 1.0, 1.0)),
    0xBCC: (0x790, (0.35, 0.6, 0.65, 1.0)),     # hat and beard
    0xBF6: (0x83B, (0.33, 0.35, 0.67, 0.8)),     # long ears
    0xBA0: (0x66D, (0.25, 0.4, 0.75, 1.0)),     # miner
    0xBE0: (0x808, (0.0, 0.0, 1.0, 1.0)),       # metal box
}
ENTRIES = {}      # uid -> generated model bytes (set by generate.build_entries as models are generated)
_CACHE = {}


def render(model, crop, size):
    d = ENTRIES.get(model)
    if d is None:
        return None
    tex = {}
    for r in F.model_textures(model, d):
        p = r["key"].split(".")
        if len(p) == 2:
            tex[int(p[1])] = F.decode_region(d, r)
    return P.render3d(d, tex, size=size, crop=crop)


def hook(key, fact, rgba):
    if key[0] != "s":
        return None
    uid = int(key[1:].split(".")[0], 16)
    if uid not in MAP:
        return None
    w, h = fact["w"], fact["h"]
    ck = (uid, w, h)
    if ck not in _CACHE:
        im = render(*MAP[uid], size=max(w, h) * 3)
        if im is None or im[..., 3].max() == 0:
            _CACHE[ck] = None
        else:
            a = im[..., 3] > 100
            ys, xs = np.nonzero(a)
            im = Image.fromarray(im, "RGBA").crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
            s = min((w - 2) / im.width, (h - 2) / im.height)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
            o = np.asarray(out, np.uint8).copy()
            solid = o[..., 3] > 110
            edge = np.zeros_like(solid)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                edge |= np.roll(solid, (dy, dx), (0, 1)) & ~solid
            o[..., 3] = np.where(solid, 255, 0)
            o[edge] = (25, 20, 20, 255)                      # dark outline around the head
            o[~(solid | edge), :3] = (25, 20, 20)
            _CACHE[ck] = o
    return _CACHE[ck]
