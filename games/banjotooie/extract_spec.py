"""DIRTY ROOM: retail ROM -> clean-room spec (kept facts only).

    python -m games.banjotooie.extract_spec <rom.z64> <spec dir>
Writes:
  rom_kept.bin                      the ROM with the asset filesystem and both sound regions zeroed
                                    (header, IPL3, code and overlays are kept facts: the decomp builds them)
  kept_assets.bin + kept_assets.json   every asset decompressed, with all texture, palette, sprite pixel and
                                    font pixel bytes zeroed (geometry, display lists, animations, level
                                    setups, text, note sequences are kept facts)
  textures.json.gz                  per model texture / external texture / sprite frame / font glyph: format,
                                    size, colour grid (4x4; 16x16 from 128 px; alpha-weighted), 2-bit alpha
                                    outline if alpha varies, 2-bit intensity outline for I formats
Prints a one-screen summary.
"""
import gzip
import json
import os
import sys

import numpy as np

from cleanroom.decomp.spec import alpha2
from cleanroom.gfx import texfmt as T
from games.banjotooie import assetfs as A, formats as F

SOUND = (0x1A14580, 0x1E29B60)


def agrid(rgba, n):
    """Colour grid weighted by alpha (transparent texels carry no colour); alpha is the plain mean."""
    h, w = rgba.shape[:2]
    f = rgba.astype(np.float64)
    a = f[..., 3:4] / 255.0
    tot = (f[..., :3] * a).reshape(-1, 3).sum(0) / max(a.sum(), 1e-6)
    out = []
    for gy in range(n):
        for gx in range(n):
            y0, y1 = gy * h // n, max(gy * h // n + 1, (gy + 1) * h // n)
            x0, x1 = gx * w // n, max(gx * w // n + 1, (gx + 1) * w // n)
            c, ca = f[y0:y1, x0:x1, :3], a[y0:y1, x0:x1]
            rgb = (c * ca).reshape(-1, 3).sum(0) / ca.sum() if ca.sum() > 0.5 else tot
            out.append([int(round(v)) for v in rgb] + [int(round(f[y0:y1, x0:x1, 3].mean()))])
    return out


def fact(rgba, fmt=None):
    h, w = rgba.shape[:2]
    n = 16 if max(w, h) >= 128 else 4
    d = {"w": w, "h": h, "grid": agrid(rgba, n)}
    if (rgba[..., 3] < 250).any():
        d["alpha2"] = alpha2(rgba[..., 3])
    if fmt == T.I:        # intensity formats: the intensity pattern is the shape (drawn as alpha by the game)
        lum = rgba[..., :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
        d["ishape2"] = alpha2(lum.clip(0, 255).astype(np.uint8))
    return d


def zero_ranges(e, kind, rs):
    d = e.data
    if kind == "model":
        _, base, size, _ = F.tex_list(d)
        return [(base, size)]
    if kind == "ext":
        return [(0, len(d))]
    if kind == "sprite":
        n = F._u16(d, 0)
        po, vo = (0x1C + 12 * n + 7) & ~7, F._u32(d, 0x14)
        return [(po, (vo if po < vo <= len(d) else len(d)) - po)]
    if kind == "font":
        base = F._u32(d, 8)
        return [(base, len(d) - base)]
    return []


def main(argv):
    rom = open(argv[1], "rb").read()
    out = argv[2]
    os.makedirs(out, exist_ok=True)
    es = A.parse(rom)
    info = F.ext_info(es)
    regs = {e.uid: (k, r) for e, k, r in F.all_regions(es, info)}
    tex = {}
    blob = bytearray()
    meta = []
    counts = {"model": 0, "ext": 0, "sprite": 0, "font": 0}
    zeroed = 0
    for e in es:
        d = e.data
        if not d:
            meta.append({"uid": e.uid, "t": e.type, "off": None})
            continue
        d = bytearray(d)
        kind = None
        if e.uid in regs:
            kind, rs = regs[e.uid]
            if kind == "sprite":
                for f in sorted(set(r["frame"] for r in rs)):
                    fr = [r for r in rs if r["frame"] == f]
                    tex[fr[0]["key"]] = dict(fact(F.compose(e.data, fr), fr[0]["fmt"]), fmt=fr[0]["fmt"], siz=fr[0]["siz"])
                    counts[kind] += 1
            else:
                for r in rs:
                    tex[r["key"]] = dict(fact(F.decode_region(e.data, r), r["fmt"]), fmt=r["fmt"], siz=r["siz"])
                    counts[kind] += 1
            for a, n in zero_ranges(e, kind, rs):
                d[a:a + n] = bytes(n)
                zeroed += n
        m = {"uid": e.uid, "t": e.type, "off": len(blob), "len": len(d)}
        if kind:
            m["kind"] = kind
        meta.append(m)
        blob += d
    kept = bytearray(rom)
    kept[A.TABLE:A.END] = bytes(A.END - A.TABLE)
    kept[SOUND[0]:SOUND[1]] = bytes(SOUND[1] - SOUND[0])
    open(os.path.join(out, "rom_kept.bin"), "wb").write(kept)
    open(os.path.join(out, "kept_assets.bin"), "wb").write(blob)
    json.dump(meta, open(os.path.join(out, "kept_assets.json"), "w"), separators=(",", ":"))
    with gzip.open(os.path.join(out, "textures.json.gz"), "wt") as f:
        json.dump(tex, f, separators=(",", ":"))
    print(f"assets {len(meta)} ({len(blob) / 1e6:.1f} MB kept, {zeroed / 1e6:.1f} MB pixel bytes zeroed); "
          f"texture facts {len(tex)}: {counts}")


if __name__ == "__main__":
    main(sys.argv)
